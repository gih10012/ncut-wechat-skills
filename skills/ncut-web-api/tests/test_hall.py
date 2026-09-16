import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hall
import ncut


class HallTests(unittest.TestCase):
    def args(self,**kw):
        return argparse.Namespace(**(dict(account='test',operation='verify',query='Service',value=None,allow_write=True)|kw))

    def test_verify_restores_preexisting_favorite_in_both_directions(self):
        for original in (False,True):
            before={'id':'observed','name':'Service','favorite':original}
            with tempfile.TemporaryDirectory() as temp,patch.object(ncut,'STATE',Path(temp)),patch.object(hall,'ensure_login',return_value={'ok':True}),patch.object(hall,'lookup',side_effect=[before,before|{'favorite':not original},before]),patch.object(hall,'verify_source',return_value='sha'),patch.object(hall,'set_favorite',return_value={'ok':True}) as writes,patch.object(ncut,'emit') as emit:
                hall.favorite(self.args())
                self.assertEqual([c.args[-1] for c in writes.call_args_list],[not original,original])
                result=emit.call_args.args[0]
                self.assertTrue(result['ok']);self.assertTrue(result['original_state_restored'])
                self.assertTrue(json.loads(Path(result['journal']).read_text())['restored'])

    def test_failed_readback_still_restores_and_never_claims_success(self):
        before={'id':'observed','name':'Service','favorite':False}
        with tempfile.TemporaryDirectory() as temp,patch.object(ncut,'STATE',Path(temp)),patch.object(hall,'ensure_login',return_value={'ok':True}),patch.object(hall,'lookup',side_effect=[before,ValueError('READBACK_FAILED'),before]),patch.object(hall,'verify_source',return_value='sha'),patch.object(hall,'set_favorite',return_value={'ok':True}) as writes,patch.object(ncut,'emit') as emit:
            hall.favorite(self.args())
            self.assertEqual([c.args[-1] for c in writes.call_args_list],[True,False])
            self.assertFalse(emit.call_args.args[0]['ok']);self.assertTrue(emit.call_args.args[0]['original_state_restored'])

    def test_no_authorization_no_remote_mutation(self):
        with patch.object(hall,'ensure_login',return_value={'ok':True}),patch.object(hall,'lookup',return_value={}),patch.object(hall,'set_favorite') as writes:
            with self.assertRaises(ValueError):hall.favorite(self.args(allow_write=False))
            writes.assert_not_called()

    def test_failed_restore_blocks_another_validation(self):
        before={'id':'observed','name':'Service','favorite':False}
        with tempfile.TemporaryDirectory() as temp,patch.object(ncut,'STATE',Path(temp)),patch.object(hall,'ensure_login',return_value={'ok':True}),patch.object(hall,'lookup',return_value=before),patch.object(hall,'verify_source',return_value='sha'),patch.object(hall,'set_favorite') as writes:
            ncut.private_write(ncut.STATE/'write-checks/hall-favorite-test.json','{"restored":false}')
            with self.assertRaises(ValueError):hall.favorite(self.args())
            writes.assert_not_called()

    def test_entry_permission_tip_stops_before_navigation(self):
        with patch.object(hall,'ensure_login',return_value={'ok':True}), patch.object(hall,'lookup',return_value={'id':'observed'}), patch.object(ncut,'load_session',return_value={}), patch.object(ncut,'fetch',return_value=({'ok':True,'data':{'tip':'Not available to this account'}},b'')), patch.object(hall,'follow_login') as navigate:
            result=hall.resolve_entry('test','Service')
        self.assertEqual(result['code'],'SERVICE_UNAVAILABLE')
        navigate.assert_not_called()

    def test_resolved_entry_keeps_tickets_private_and_checks_actual_site(self):
        def navigate(url,state,*,terminal):
            self.assertIn('ticket-secret',url)
            terminal.update(url='https://workflow.ncut.edu.cn/reservation/fe/site/reservationInfo?id=321&platform_id=24&token=landing-secret',body=b'html')
            return {'ok':True,'chain':[]},state
        values=[({'ok':True,'data':{'url':'https://workflow.ncut.edu.cn/reservation/api/url/resource?token=ticket-secret'}},b''),
                ({'ok':True,'data':{'e':'OK','d':{'id':321,'name':'Test court','config':{'anti_bot':1,'rule':[]}}}},b'')]
        with tempfile.TemporaryDirectory() as temp, patch.object(ncut,'STATE',Path(temp)), patch.object(hall,'ensure_login',return_value={'ok':True}), patch.object(hall,'lookup',return_value={'id':'observed'}), patch.object(ncut,'load_session',return_value={}), patch.object(ncut,'fetch',side_effect=values), patch.object(hall,'follow_login',side_effect=navigate):
            result=hall.resolve_entry('test','Service')
            self.assertTrue(result['business_verified'])
            self.assertEqual(result['business']['site_id'],'321')
            self.assertNotIn('secret',json.dumps(result))
            self.assertIn('ticket-secret',Path(result['private_entry']).read_text())

    def test_unregistered_entry_is_not_opened(self):
        with patch.object(hall,'ensure_login',return_value={'ok':True}), patch.object(hall,'lookup',return_value={'id':'observed'}), patch.object(ncut,'load_session',return_value={}), patch.object(ncut,'fetch',return_value=({'ok':True,'data':{'url':'https://unknown.example/'}},b'')), patch.object(hall,'follow_login') as navigate:
            result=hall.resolve_entry('test','Service')
        self.assertEqual(result['code'],'UNREGISTERED_SERVICE_ENTRY')
        navigate.assert_not_called()


if __name__=='__main__':unittest.main()
