import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.parse as up

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import grades


SETUP = '''<form id="kscjQueryForm" method="post">
<input name="mold" type="hidden" value=""><input name="kcmc" value="">
<input name="unchecked" type="checkbox" value="1">
<select name="kksj"><option value="">全部学期</option>
<option value="2024-2025-1">2024秋</option><option value="2024-2025-2">2025春</option></select>
<select name="xsfs"><option value="max" selected>最好成绩</option><option value="all">全部成绩</option></select>
</form><script>var actionUrl = "/jsxsd/kscj/cjcx_list";</script>'''.encode()
HEADERS = ['序号', '开课学期', '课程编号', '课程名称', '成绩（原始成绩）', '学分', '考试性质']


def table(rows=(), empty=False):
    body = '<table id="dataList"><tr>'+''.join('<th>'+h+'</th>' for h in HEADERS)+'</tr>'
    for row in rows:
        body += '<tr>'+''.join('<td>'+value+'</td>' for value in row)+'</tr>'
    if empty:
        body += '<tr><td colspan="7">未查询到数据</td></tr>'
    return (body+'</table>').encode()


class GradesTests(unittest.TestCase):
    def query(self, responses, term=None):
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            if url.endswith(grades.QUERY):
                return {'ok': True}, SETUP
            selected = up.parse_qs(kwargs['data'].decode(), keep_blank_values=True)['kksj'][0]
            return responses[selected]
        args = SimpleNamespace(account='me', term=term, output=None)
        with patch.object(grades.ncut, 'load_session', return_value={}), patch.object(grades.ncut, 'fetch', side_effect=fetch), contextlib.redirect_stdout(io.StringIO()) as out:
            grades.grades(args)
        return json.loads(out.getvalue()), calls

    def test_latest_nonempty_term_preserves_all_attempts_and_text_scores(self):
        rows = [['1', '2024秋', 'example', '示例课程', '不及格', '2', '正常考试'],
                ['2', '2024秋', 'example', '示例课程', '及格', '2', '补考']]
        result, calls = self.query({'2024-2025-2': ({'ok': True}, table(empty=True)),
                                    '2024-2025-1': ({'ok': True}, table(rows))})
        self.assertEqual(result['semester']['id'], '2024-2025-1')
        self.assertEqual([r['score'] for r in result['entries']], ['不及格', '及格'])
        self.assertEqual(len(calls), 3)
        for _, kwargs in calls[1:]:
            body = up.parse_qs(kwargs['data'].decode(), keep_blank_values=True)
            self.assertEqual(body['xsfs'], ['all'])
            self.assertNotIn('unchecked', body)
            self.assertEqual(kwargs['method'], 'POST')

    def test_explicit_empty_term_does_not_fall_back(self):
        result, calls = self.query({'2024-2025-2': ({'ok': True}, table(empty=True))}, '2024-2025-2')
        self.assertEqual(result['code'], 'GRADES_EMPTY')
        self.assertEqual(result['semester']['id'], '2024-2025-2')
        self.assertEqual(len(calls), 2)

    def test_unknown_term_is_rejected_before_post(self):
        result, calls = self.query({}, 'guessed-semester')
        self.assertEqual(result['code'], 'GRADES_UNKNOWN_TERM')
        self.assertEqual(len(calls), 1)

    def test_permission_or_auth_failure_is_not_empty_and_not_retried(self):
        for code in ('AUTH_REQUIRED', 'FORBIDDEN', 'TIMEOUT'):
            result, calls = self.query({'2024-2025-2': ({'ok': False, 'code': code}, b'')})
            self.assertFalse(result['ok'])
            self.assertEqual(result['code'], code)
            self.assertEqual(len(calls), 2)

    def test_query_action_drift_is_not_submitted(self):
        with self.assertRaisesRegex(ValueError, 'action changed'):
            grades.parse_query(SETUP.replace(b'cjcx_list', b'unknown_action'))

    def test_schema_or_semester_mismatch_is_not_reported_as_grades(self):
        term = {'id': '2024-2025-2', 'name': '2025春'}
        with self.assertRaisesRegex(ValueError, 'GRADES_TERM_MISMATCH'):
            grades.parse_grades(table([['1', '2024秋', 'example', '示例课程', '80', '2', '正常考试']]), term)
        for body in (b'<html>unrecognized response</html>', table([['incomplete']]),
                     table([['1', '2025春', 'example', '示例课程', '', '2', '正常考试']])):
            with self.assertRaisesRegex(ValueError, 'GRADES_RESPONSE_UNVERIFIED'):
                grades.parse_grades(body, term)


if __name__ == '__main__':
    unittest.main()
