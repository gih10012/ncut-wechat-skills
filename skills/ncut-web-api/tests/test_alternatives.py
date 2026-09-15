import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from alternatives import pairs,entry_url


class AlternativeTests(unittest.TestCase):
    def test_only_same_action_is_paired_and_catalog_is_not_permission_proof(self):
        rows=[{'id':'x','name':'服务','service':[{'blArr':[{'blname':'A','blpcurl':'web-a','blmurl':'mobile-a'},{'blname':'B','blmurl':'mobile-b'}]}]}]
        raw=("vjson=mini.decode('"+json.dumps(rows)+"')").encode()
        result=pairs(raw)[0]
        self.assertEqual(result['actions'][0]['mapping'],'paired_entries')
        self.assertEqual(result['actions'][1]['mapping'],'mobile_only')
        self.assertIsNone(result['actions'][1]['web']);self.assertFalse(result['same_business_verified'])

    def test_dynamic_query_or_fragment_credentials_are_not_emitted(self):
        self.assertIsNone(entry_url('https://service.ncut.edu.cn/start?ticket=private'))
        self.assertIsNone(entry_url('https://service.ncut.edu.cn/#/login?token=private'))
        self.assertEqual(entry_url('https://service.ncut.edu.cn/EIP/form?id=123'),'https://service.ncut.edu.cn/EIP/form?id=123')


if __name__=='__main__':unittest.main()
