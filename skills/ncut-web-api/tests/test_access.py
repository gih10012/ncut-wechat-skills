import contextlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from email.message import Message

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import ncut
from knowledge import search

class Response(io.BytesIO):
    def __init__(self, data=b'', status=200, content_type='application/json', location=None):
        super().__init__(data);self.status=status;self.headers=Message();self.headers['Content-Type']=content_type
        if location:self.headers['Location']=location

class AccessTests(unittest.TestCase):
    def test_credentials_are_scoped_by_origin_domain_path_expiry(self):
        state={'cookies':[{'domain':'jwxt.ncut.edu.cn','path':'/api','name':'host','value':'one','expires':-1}, {'domain':'.ncut.edu.cn','path':'/','name':'wide','value':'two','expires':-1}, {'domain':'.ncut.edu.cn','path':'/','name':'expired','value':'bad','expires':1}], 'headers':{'https://jwxt.ncut.edu.cn':{'Authorization':'Bearer only-jwxt'}}}
        a=ncut.scoped_headers(state,'https://jwxt.ncut.edu.cn/api/me')
        self.assertIn('host=one',a['Cookie']);self.assertIn('Authorization',a)
        b=ncut.scoped_headers(state,'https://sso.ncut.edu.cn/sso/login')
        self.assertNotIn('Authorization',b);self.assertEqual(b['Cookie'],'wide=two')
        c=ncut.scoped_headers(state,'https://jwxt.ncut.edu.cn/apix')
        self.assertNotIn('host=one',c['Cookie'])
        d=ncut.scoped_headers(state,'https://evilncut.edu.cn/')
        self.assertNotIn('Cookie',d);self.assertNotIn('Authorization',d)

    def test_redirect_is_not_followed_or_bearer_url_printed(self):
        response=Response(status=302,location='https://outside.example/auth?ticket=do-not-output')
        with patch.object(ncut.ur,'build_opener') as op:
            op.return_value.open.return_value=response
            result,_=ncut.fetch('https://jwxt.ncut.edu.cn/')
        self.assertEqual(op.return_value.open.call_count,1)
        self.assertEqual(result['code'],'REDIRECT')
        self.assertEqual(result['location'],'https://outside.example/auth')

    def test_login_page_and_non_json_are_not_successful_business_results(self):
        cases=[(b'<html><form><input type="password"></form></html>','AUTH_REQUIRED'), (b'<html>SPA shell</html>','RESPONSE_UNEXPECTED')]
        for body,code in cases:
            with patch.object(ncut.ur,'build_opener') as op:
                op.return_value.open.return_value=Response(body,content_type='text/html')
                result,_=ncut.fetch('https://jwxt.ncut.edu.cn/',expect='json')
            self.assertFalse(result['ok']);self.assertEqual(result['code'],code)

    def test_read_only_post_uses_contract_without_write_confirmation(self):
        argv=['ncut','request','hall','--capability','hall-service-search','--method','POST','--path','/EIP/nonlogin/elobby/portal/services/list.htm','--form','keyword=邮箱']
        with patch.object(sys,'argv',argv), patch.object(ncut,'fetch',return_value=({'ok':True,'data':[{'id':'1','name':'学生邮箱申请','extra':'unneeded'}]},b'')) as call, contextlib.redirect_stdout(io.StringIO()) as out:
            ncut.main()
        self.assertEqual(call.call_args.kwargs['method'],'POST')
        self.assertEqual(json.loads(out.getvalue())['data'],[{'id':'1','name':'学生邮箱申请'}])

    def test_permission_error_in_html_200_does_not_request_login(self):
        body='<html><title>出错页面</title><p>您没有访问该功能的权限！</p></html>'.encode()
        with patch.object(ncut.ur,'build_opener') as op:
            op.return_value.open.return_value=Response(body,content_type='text/html')
            result,_=ncut.fetch('https://jwxtbk.ncut.edu.cn/jiaowu/pkgl/jsjy/jsjy_add_new.htmlx')
        self.assertFalse(result['ok']);self.assertEqual(result['code'],'FORBIDDEN')

    def test_authentication_code_in_js_is_source_not_an_expired_session(self):
        js=b'''function login(){location.href="https://sso.ncut.edu.cn/sso/login?service=example";}'''
        for kind in ('application/javascript','text/plain'):
            with patch.object(ncut.ur,'build_opener') as op:
                op.return_value.open.return_value=Response(js,content_type=kind)
                result,_=ncut.fetch('https://service.ncut.edu.cn/EIP/weixin/weui/js/cooperate-main.js')
            self.assertTrue(result['ok'])
        with patch.object(ncut.ur,'build_opener') as op:
            op.return_value.open.return_value=Response(b'<script>'+js[17:-1]+b'</script>',content_type='text/html')
            result,_=ncut.fetch('https://service.ncut.edu.cn/EIP/protected')
        self.assertEqual(result['code'],'AUTH_REQUIRED')

    def test_unknown_method_route_stops_before_network(self):
        argv=['ncut','request','hall','--capability','hall-service-search','--method','DELETE','--path','/EIP/nonlogin/elobby/portal/services/list.htm']
        with patch.object(sys,'argv',argv), patch.object(ncut,'fetch') as network:
            with self.assertRaises(ValueError): ncut.main()
        network.assert_not_called()

    def test_read_contract_action_cannot_be_overridden_by_extra_parameters(self):
        base=['ncut','request','jwxtbk','--account','me','--capability','empty-classrooms','--method','POST','--path','/jiaowu/kxjsgl/kxjsgl.do?method=queryJsjyxx']
        for option in ('--query','--form'):
            with patch.object(sys,'argv',base+[option,'method=save']),patch.object(ncut,'load_session',return_value={}),patch.object(ncut,'fetch') as network:
                with self.assertRaises(ValueError):ncut.main()
            network.assert_not_called()

    def test_import_preserves_previous_session_when_no_supported_credentials(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(ncut,'STATE',Path(temp)/'state'):
            old=ncut.account_path('me');ncut.private_write(old,'{"cookies": [{"name":"old"}]}')
            incoming=Path(temp)/'incoming.json';incoming.write_text('{"cookies": []}');incoming.chmod(0o600)
            with patch.object(sys,'argv',['ncut','session','import','--account','me','--file',str(incoming)]):
                with self.assertRaises(ValueError):ncut.main()
            self.assertIn('old',old.read_text());self.assertEqual(stat.S_IMODE(old.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(ncut.STATE.stat().st_mode),0o700)

    def test_catalog_extracts_real_entries_and_marks_retired(self):
        row={'id':'1','name':'【缓考】（停用，转至新版教务系统）','service':[{'blArr':[{'blname':'办理','blpcurl':'flow.htm?id=1'}]}]}
        raw=("vjson=mini.decode('[]');vjson=mini.decode('"+json.dumps([row],ensure_ascii=False)+"')").encode()
        actual=ncut.parse_catalog(raw)
        self.assertEqual(actual[0]['availability'],'retired_or_moved')
        self.assertEqual(actual[0]['entries'][0]['url'],'https://service.ncut.edu.cn/EIP/flow.htm?id=1')
        with self.assertRaises(ValueError):ncut.parse_catalog(b'<html>login</html>')

    def test_catalog_cache_hit_does_not_rewrite_knowledge(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'references').mkdir();(root/'cache').mkdir()
            row={'id':'1','name':'学生邮箱申请','service':[]}
            raw=("vjson=mini.decode('"+json.dumps([row],ensure_ascii=False)+"')").encode()
            rows=ncut.parse_catalog(raw);cache=root/'cache/service-catalog.json'
            cache.write_text(json.dumps({'verified_at':'old','services':rows}));before=cache.stat().st_mtime_ns
            with patch.object(ncut,'ROOT',root),patch.object(ncut,'STATE',root),patch.object(ncut,'service',return_value={'entry':'https://service.ncut.edu.cn/'}),patch.object(ncut,'fetch',return_value=({'ok':True,'fetched_at':'new','url':'https://service.ncut.edu.cn/'},raw)),patch.object(sys,'argv',['ncut','catalog']),contextlib.redirect_stdout(io.StringIO()):ncut.main()
            self.assertEqual(before,cache.stat().st_mtime_ns)
            self.assertEqual(json.loads(cache.read_text())['verified_at'],'old')

    def test_retrieval_excludes_unrelated_material_and_resolves_missing_school_route(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);caps=root/'references/capabilities';caps.mkdir(parents=True)
            (root/'references/services.json').write_text(json.dumps({'services':[{'id':'exam','aliases':['考试']}]}))
            (caps/'mail.md').write_text('---\nid: mail\nkeywords: ["邮箱"]\n---\nmail only')
            (caps/'messages.md').write_text('---\nid: messages\nkeywords: ["聊天"]\n---\nunrelated')
            result=search(root,'查学生邮箱办理入口')
            self.assertEqual(len(result['matches']),1)
            self.assertEqual(result['matches'][0]['id'], 'mail')
            self.assertNotIn('content', result['matches'][0])
            self.assertNotIn('unrelated', search(root, '查学生邮箱办理入口', details=True)['matches'][0]['content'])
            missing=search(root,'查考试安排')
            self.assertEqual(missing['matches'],[])
            self.assertEqual(missing['service_candidates'][0]['id'],'exam')

    def test_default_retrieval_does_not_read_workflow_and_details_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);caps=root/'references/capabilities';caps.mkdir(parents=True)
            (root/'references/flow.md').write_text('secret workflow body')
            (caps/'api.md').write_text('---\nid: api\nkeywords: ["课表"]\nstatus: runtime_verified\ntransport: http\ncommand: ["timetable"]\nworkflow: references/flow.md\n---\ncontract')
            with patch.object(Path, 'read_text', side_effect=AssertionError('Default retrieval must use metadata only')):
                result=search(root, '查课表')
            self.assertEqual(result['matches'][0]['command'], ['timetable'])
            self.assertNotIn('workflow',result['matches'][0])
            self.assertEqual(search(root, '查课表', details=True)['matches'][0]['workflow'], 'secret workflow body')

    def test_message_request_reports_gap_without_selecting_desktop(self):
        root=SCRIPTS.parent.parent/'wechat-personal'
        result=search(root, '查看微信消息')
        self.assertTrue(result['matches'])
        self.assertEqual({m['status'] for m in result['matches']}, {'not_connected'})
        self.assertTrue(all(m.get('transport') != 'manual-ui' for m in result['matches']))
        self.assertTrue(all('command' not in m for m in result['matches']))

    def test_business_auth_failure_inside_http_200_is_not_success(self):
        with patch.object(ncut.ur,'build_opener') as op:
            op.return_value.open.return_value=Response(b'{"e":"UN_AUTH","m":"not authenticated"}')
            result,_=ncut.fetch('https://workflow.ncut.edu.cn/reservation/site/resource/calendar',expect='json')
        self.assertFalse(result['ok']);self.assertEqual(result['code'],'AUTH_REQUIRED')

if __name__=='__main__':unittest.main()
