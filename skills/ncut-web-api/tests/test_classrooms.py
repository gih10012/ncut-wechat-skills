import argparse
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.request as ur
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import classrooms as cr
import ncut


def form(weeks=((1,'09.14-09.20'),(16,'12.28-01.03'))):
    return ('''<input id="xnxqh" value="2026-2027-1"><select id="xqbh"><option value="01">校本部</option></select><select id="zc">'''+''.join(f'<option value="{n}">第{n}周({label})</option>' for n,label in weeks)+'''</select><li class="jcclass" data-value="0910">18:00~19:35</li><li class="jcclass" data-value="1112">19:50~21:25</li><script>var query={"jxzlid":'CURRENT'};</script>''').encode()


class ClassroomTests(unittest.TestCase):
    def test_school_week_year_rollover_and_both_overlapping_periods(self):
        p,periods,_=cr.parse_form(form(),dt.date(2026,9,15),'18:00','20:00','校本部')
        self.assertEqual(p['jc'],'0910,1112');self.assertEqual(p['zc'],'1')
        p,_,_=cr.parse_form(form(),dt.date(2027,1,1),'18:00','19:35','01')
        self.assertEqual(p['zc'],'16');self.assertEqual(p['jc'],'0910')
        with self.assertRaises(ValueError):cr.parse_form(form(),dt.date(2027,9,15),'18:00','20:00','01')
        with self.assertRaises(ValueError):cr.parse_form(form(),dt.date(2026,9,15),'18:00','22:00','01')

    def data(self):
        rooms=[dict(jsid=str(i),jsmc=f'励学{i}',jslx='普通教室',yxzws=80,xqid='01',zt='1') for i in range(40)]
        for r in rooms[:35]:r['21112']='1'
        return dict(success=True,dataList=rooms,xqmxList=[dict(xqid=2,mxrq='09-15')])

    def test_filter_full_response_before_output_limit_and_check_both_blocks(self):
        params=dict(xq='2',jc='0910,1112',xqbh='01')
        rooms=cr.free_rooms(self.data(),params,dt.date(2026,9,15),'励学')
        self.assertEqual([r['id'] for r in rooms],['35','36','37','38','39'])

    def test_wrong_date_unknown_occupancy_or_missing_list_is_not_free(self):
        params=dict(xq='2',jc='0910,1112',xqbh='01')
        for mutate in (lambda d:d['xqmxList'][0].update(mxrq='09-22'),lambda d:d['dataList'][0].update({'20910':'unknown'}),lambda d:d.pop('dataList')):
            d=self.data();mutate(d)
            with self.assertRaises(ValueError):cr.free_rooms(d,params,dt.date(2026,9,15),'')

    def test_cookie_roundtrip_preserves_sessions_flags_and_other_service(self):
        state={'cookies':[dict(name='session',value='example',domain='jwxtbk.ncut.edu.cn',path='/',expires=-1,secure=True,httpOnly=True,sameSite='Lax'),dict(name='work',value='example2',domain='workflow.ncut.edu.cn',path='/',expires=-1,secure=True,httpOnly=True)],'headers':{},'user_agent':'Actual UA'}
        jar=cr.cookie_jar(state);out=cr.merged_state(state,jar)
        self.assertEqual(out,state)
        req=ur.Request('https://child.jwxtbk.ncut.edu.cn/')
        jar.add_cookie_header(req);self.assertIsNone(req.get_header('Cookie'))
        req=ur.Request(cr.ORIGIN+cr.FORM)
        jar.add_cookie_header(req);self.assertEqual(req.get_header('Cookie'),'session=example')

    def test_normal_query_is_two_http_requests_and_never_enters_booking(self):
        args=argparse.Namespace(account='me',date='2026-09-15',start='18:00',end='20:00',campus='校本部',query='',limit=2,output=None)
        with patch.object(ncut,'load_session',return_value={'cookies':[]}),patch.object(ncut,'fetch',side_effect=[({'ok':True},form()),({'ok':True,'fetched_at':'now','data':self.data()},b'')]) as fetch,patch.object(ncut,'private_write') as save,contextlib.redirect_stdout(io.StringIO()) as out:
            cr.classrooms(args)
        self.assertEqual([c.args[0] for c in fetch.call_args_list],[cr.ORIGIN+cr.FORM,cr.ORIGIN+cr.QUERY])
        self.assertEqual(fetch.call_args_list[1].kwargs['method'],'POST');save.assert_not_called()
        result=json.loads(out.getvalue());self.assertEqual(result['matched'],5);self.assertEqual(len(result['rooms']),2)
        self.assertFalse(result['remote_write_performed'])

    def test_permission_denial_stops_without_reauthentication(self):
        args=argparse.Namespace(account='me',date='2026-09-15',start='18:00',end='20:00',output=None)
        with patch.object(ncut,'load_session',return_value={'cookies':[]}),patch.object(ncut,'fetch',return_value=({'ok':False,'code':'FORBIDDEN'},b'')) as fetch,contextlib.redirect_stdout(io.StringIO()) as out:
            cr.classrooms(args)
        self.assertEqual(fetch.call_count,1);self.assertEqual(json.loads(out.getvalue())['code'],'FORBIDDEN')


if __name__=='__main__':unittest.main()
