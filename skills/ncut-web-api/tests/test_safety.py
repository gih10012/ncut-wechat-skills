import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import safety
import ncut


class SafetyCourseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = patch.object(safety, 'STATE', Path(self.tmp.name))
        self.state.start(); self.addCleanup(self.state.stop)
        self.row = {'resourceId': 'assigned-resource', 'userCourseId': '11111111-1111-1111-1111-111111111111',
                    'resourceName': 'Synthetic course', 'source': 1, 'finished': 2, 'categoryCode': 'category'}
        self.args = argparse.Namespace(account='me', project='assigned-project', course='assigned-resource', action='finish', reviewed=True)
        self.record = safety.STATE / 'safety/me/assigned-project' / (self.row['userCourseId'] + '.json')
        ncut.private_write(self.record, json.dumps({'course_id': self.args.course, 'user_course_id': self.row['userCourseId'], 'cs_capt': 'false'}))

    def run_course(self, *, body=b'ncutSafety({"code":"0"})', updated=None, response_ok=True):
        session = {'service_data': {'weiban': {'userId': 'owner', 'tenantCode': 'school'}}}
        updated = [{**self.row, 'finished': 1}] if updated is None else updated
        with patch.object(safety, 'load_session', return_value=session), \
             patch.object(safety, 'assigned_courses', return_value=({'ok': True}, [self.row])), \
             patch.object(safety, 'fetch', return_value=({'ok': response_ok}, body)) as fetch, \
             patch.object(safety, '_post', return_value=({'ok': True}, updated)), \
             patch.object(safety, 'emit') as emit:
            safety.course(self.args)
            return emit.call_args.args[0], fetch.call_count

    def test_jsonp_is_parsed_without_executing_javascript(self):
        self.assertEqual(safety.parse_completion('jQuery_123({"code":"0"});')['code'], '0')
        with self.assertRaises(ValueError):
            safety.parse_completion('alert("bad");jQuery_123({"code":"0"})')

    def test_unknown_submission_is_resolved_with_readback_once(self):
        result, writes = self.run_course(response_ok=False, body=b'')
        self.assertTrue(result['finished'])
        self.assertFalse(result['submission_response_known'])
        self.assertEqual(writes, 1)

    def test_success_response_alone_does_not_mean_the_course_is_finished(self):
        result, writes = self.run_course(updated=[self.row])
        self.assertFalse(result['ok'])
        self.assertEqual(result['code'], 'COMPLETION_NOT_VERIFIED')
        self.assertEqual(writes, 1)

    def test_unresolved_completion_is_read_back_without_resubmitting(self):
        first, writes = self.run_course(updated=[self.row])
        self.assertFalse(first['ok'])
        second, writes = self.run_course(updated=[self.row])
        self.assertEqual(second['code'], 'USE_NATIVE_COMPLETION_FLOW')
        self.assertEqual(writes, 0)

    def test_701_is_a_temporary_lock_and_not_a_login_failure(self):
        with patch.object(safety, 'fetch', return_value=({'ok': False, 'status': 701, 'code': 'HTTP_ERROR'}, b'')):
            info, data = safety._post({}, {'userId': 'owner', 'tenantCode': 'school'}, 'exam/listPlan.do', {})
        self.assertEqual(info['code'], 'ACCOUNT_TEMPORARILY_LOCKED')
        self.assertIsNone(data)

    def test_captcha_enabled_courses_use_the_native_flow(self):
        saved = json.loads(ncut.private_read(self.record)); saved['cs_capt'] = 'true'
        ncut.private_write(self.record, json.dumps(saved))
        result, writes = self.run_course()
        self.assertEqual(result['code'], 'USE_NATIVE_CAPTCHA_FLOW')
        self.assertEqual(writes, 0)

    def test_completed_courses_are_not_submitted_again(self):
        self.row['finished'] = 1
        result, writes = self.run_course()
        self.assertTrue(result['already_finished'])
        self.assertEqual(writes, 0)

    def test_course_assignment_is_checked_before_any_write(self):
        self.args.course = 'unassigned-resource'
        result, writes = self.run_course()
        self.assertEqual(result['code'], 'COURSE_NOT_ASSIGNED')
        self.assertEqual(writes, 0)


if __name__ == '__main__':
    unittest.main()
