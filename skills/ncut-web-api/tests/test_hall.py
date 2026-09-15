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


if __name__=='__main__':unittest.main()
