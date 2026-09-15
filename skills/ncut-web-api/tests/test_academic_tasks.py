import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ncut
from academic import parse_grid,in_week,parse_setup
from task_drafts import main as tasks
from knowledge import search
from reservation import read_rules

class ReservationRulesTests(unittest.TestCase):
    def data(self):
        return {'e':'OK','d':{'id':596,'name':'场馆','config':{'anti_bot':1,'rule':[{'class':'ServiceTimeRule','start_time':'12:00:00','end_time':'17:00:00','week':[1,2,3,4,5,6,7],'roles':['depart.0']},{'class':'RangeRule','start':0,'end':0,'format':'day'}],'description':{'text':'A notice cannot override server rules'},'sign':{'qrcode':{'token':'never-output'}}},'limit_info':{'error':'','reason':[]}}}
    def test_verification_and_submit_window_are_distinct_from_login(self):
        result=read_rules(self.data(),'596')
        self.assertTrue(result['verification_required']);self.assertEqual(result['submission_windows'][0]['start_time'],'12:00:00')
        self.assertFalse(result['remote_write_performed']);self.assertNotIn('never-output',json.dumps(result));self.assertNotIn('notice',json.dumps(result))
    def test_wrong_site_unknown_verification_or_auth_failure_cannot_produce_rules(self):
        for mutation in (lambda d:d.update(e='UN_AUTH'),lambda d:d['d'].update(id=999),lambda d:d['d']['config'].update(anti_bot=3)):
            d=self.data();mutation(d)
            with self.assertRaises(ValueError):read_rules(d,'596')

class AcademicTests(unittest.TestCase):
    def test_week_range_and_parity_are_both_required(self):
        self.assertTrue(in_week('[1-8周] (单周)',1))
        self.assertFalse(in_week('[1-8周] (单周)',2))
        self.assertFalse(in_week('[1-8周] (单周)',9))
        self.assertTrue(in_week('[1-4,6-8周](双周)',6))
        self.assertFalse(in_week('[1-4,6-8周](双周)',5))
        with self.assertRaises(ValueError):in_week('周次另行通知',2)

    def test_grid_keeps_multiple_courses_in_one_cell_and_untimed_courses(self):
        course=lambda name,weeks:f'<div class="person-class"><h3>{name}</h3><ul><li>group</li><li>{weeks}</li><li>teacher</li><li>room</li></ul></div>'
        raw=('<table><tr><th>节次</th>'+''.join('<th>星期'+x+'</th>' for x in '一二三四五六日')+'</tr><tr><td>第一大节 08:00-09:35</td><td>'+course('A','[1-8周]')+course('B','[9-16周]')+'</td>'+'<td></td>'*6+'</tr></table><table id="tbXs"><tr><th>课程</th></tr><tr>'+''.join('<td>'+x+'</td>' for x in ['Online','group','4','8','teacher','note'])+'</tr></table>').encode()
        entries,untimed=parse_grid(raw)
        self.assertEqual([e['course'] for e in entries],['A','B'])
        self.assertEqual([e['weekday'] for e in entries],[1,1])
        self.assertEqual(untimed[0]['course'],'Online')
        with self.assertRaises(ValueError):parse_grid(b'<html>login required</html>')

    def test_current_term_comes_from_selected_option(self):
        raw=b'<select id="xnxq"><option value="old">Old</option><option value="new" selected>New</option></select><select id="week"><option value="2026-09-14">Week 1</option></select><script>let kbjcmss=[{"kbjcmsid":"mode","mrms":"1"}];</script>'
        setup=parse_setup(raw);self.assertEqual(setup['current_term']['id'],'new');self.assertEqual(setup['mode'],'mode')

    def test_captured_user_agent_is_reused_for_cookie_bound_service(self):
        headers=ncut.scoped_headers({'cookies':[],'user_agent':'Captured Browser UA'},'https://workflow.ncut.edu.cn/')
        self.assertEqual(headers['User-Agent'],'Captured Browser UA')

class DraftTests(unittest.TestCase):
    def args(self,**changes):
        values=dict(operation='draft',account='me',intent='validation only',key='one',validation_only=True);values.update(changes);return argparse.Namespace(**values)
    def test_write_readback_is_disabled_and_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(ncut,'STATE',Path(tmp)/'state'),patch.object(ncut,'fetch') as remote:
            with contextlib.redirect_stdout(io.StringIO()) as first:tasks(self.args())
            a=json.loads(first.getvalue());file=Path(a['file']);before=file.stat().st_mtime_ns
            with contextlib.redirect_stdout(io.StringIO()) as second:tasks(self.args())
            b=json.loads(second.getvalue())
            self.assertEqual(a['task']['id'],b['task']['id']);self.assertTrue(b['idempotent_replay']);self.assertTrue(b['readback_verified'])
            self.assertFalse(b['task']['enabled']);self.assertFalse(b['validation']['remote_write_performed']);self.assertFalse(b['validation']['scheduler_registered'])
            self.assertEqual(file.stat().st_mtime_ns,before);remote.assert_not_called()
            with self.assertRaises(ValueError):tasks(self.args(intent='different task'))
    def test_no_implicit_activation(self):
        with self.assertRaises(ValueError):tasks(self.args(validation_only=False))
    def test_retrieval_includes_shared_workflow_once(self):
        value=search(ncut.ROOT,'创建羽毛球预约任务')
        workflows=[m['workflow_file'] for m in value['matches'] if 'workflow' in m]
        self.assertEqual(len(workflows),len(set(workflows)))
        self.assertLessEqual(len(value['matches']),3)

if __name__=='__main__':unittest.main()
