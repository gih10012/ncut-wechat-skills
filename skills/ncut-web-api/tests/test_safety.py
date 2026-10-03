import argparse
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import safety
import ncut


class SafetyCourseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        state = patch.object(safety, 'STATE', Path(self.tmp.name))
        state.start(); self.addCleanup(state.stop)
        self.row = {'resourceId': 'assigned-resource', 'userCourseId': '11111111-1111-1111-1111-111111111111',
                    'resourceName': 'Synthetic course', 'source': 1, 'finished': 2, 'categoryCode': 'category'}
        self.args = argparse.Namespace(account='me', project='assigned-project', course='assigned-resource', action='verify')
        self.record = safety.STATE / 'safety/me/assigned-project' / (self.row['userCourseId'] + '.json')

    def run_course(self):
        session = {'service_data': {'weiban': {'userId': 'owner', 'tenantCode': 'school'}}}
        with patch.object(safety, 'load_session', return_value=session), \
             patch.object(safety, 'assigned_courses', return_value=({'ok': True}, [self.row])), \
             patch.object(safety, 'fetch') as fetch, patch.object(safety, '_post') as post, \
             patch.object(safety, 'emit') as emit:
            safety.course(self.args)
            return emit.call_args.args[0], fetch.call_count, post.call_count

    def test_verification_never_submits_completion_for_an_unfinished_course(self):
        result, fetches, posts = self.run_course()
        self.assertTrue(result['ok'])
        self.assertFalse(result['finished'])
        self.assertEqual(result['code'], 'COURSE_NOT_FINISHED')
        self.assertEqual((fetches, posts), (0, 0))

    def test_verification_reports_the_actual_native_completion(self):
        self.row['finished'] = 1
        result, fetches, posts = self.run_course()
        self.assertTrue(result['finished'])
        self.assertEqual(result['code'], 'COURSE_FINISHED')
        self.assertEqual((fetches, posts), (0, 0))

    def test_completed_courses_are_not_started_again(self):
        self.args.action = 'start'; self.row['finished'] = 1
        result, fetches, posts = self.run_course()
        self.assertTrue(result['already_finished'])
        self.assertEqual((fetches, posts), (0, 0))

    def test_unresolved_submission_is_not_reset_by_start(self):
        self.args.action = 'start'
        saved = {'submission_started_at': 'observed-prior-submission'}
        ncut.private_write(self.record, json.dumps(saved))
        result, fetches, posts = self.run_course()
        self.assertEqual(result['code'], 'USE_NATIVE_COMPLETION_FLOW')
        self.assertEqual(json.loads(ncut.private_read(self.record)), saved)
        self.assertEqual((fetches, posts), (0, 0))

    def test_course_assignment_is_checked_before_any_write(self):
        self.args.action = 'start'; self.args.course = 'unassigned-resource'
        result, fetches, posts = self.run_course()
        self.assertEqual(result['code'], 'COURSE_NOT_ASSIGNED')
        self.assertEqual((fetches, posts), (0, 0))

    def test_701_is_a_temporary_lock_and_not_a_login_failure(self):
        with patch.object(safety, 'fetch', return_value=({'ok': False, 'status': 701, 'code': 'HTTP_ERROR'}, b'')):
            info, data = safety._post({}, {'userId': 'owner', 'tenantCode': 'school'}, 'exam/listPlan.do', {})
        self.assertEqual(info['code'], 'ACCOUNT_TEMPORARILY_LOCKED')
        self.assertIsNone(data)


if __name__ == '__main__':
    unittest.main()
