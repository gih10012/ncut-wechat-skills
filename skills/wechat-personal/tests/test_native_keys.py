import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_keys as nk


class NativeKeyTests(unittest.TestCase):
    def page(self,key,salt):
        body=os.urandom(4016)
        mac_key=hashlib.pbkdf2_hmac('sha512',key,bytes(b^0x3a for b in salt),2,32)
        return salt+body+hmac.new(mac_key,body+struct.pack('<I',1),hashlib.sha512).digest()

    def test_candidate_is_accepted_only_after_database_hmac_matches(self):
        key=os.urandom(32);salt=os.urandom(16);page=self.page(key,salt)
        good=b"x'"+(key+salt).hex().encode()+b"'"
        bad=b"x'"+(os.urandom(32)+salt).hex().encode()+b"'"
        self.assertEqual(nk.candidates(bad+good,{salt.hex():page}),{salt.hex():key.hex()})
        self.assertFalse(nk.verified(key,page[:-1]+bytes([page[-1]^1])))
        self.assertEqual(nk.candidates(good,{os.urandom(16).hex():page}),{})

    def test_capture_scan_is_bounded_and_handles_key_across_chunks(self):
        key=os.urandom(32);salt=os.urandom(16);page=self.page(key,salt)
        raw=b"x'"+(key+salt).hex().encode()+b"'"
        chunks=[b'prefix'+raw[:45],raw[45:]+b'end']
        with patch.object(nk.os,'pread',side_effect=chunks):
            found,count=nk.scan(1,[(0,999999)],{salt.hex():page},10000,5)
        self.assertEqual(found,{salt.hex():key.hex()});self.assertLess(count,10000)

    def test_private_save_has_owner_only_permissions_and_no_stdout(self):
        with tempfile.TemporaryDirectory() as temp,patch('sys.stdout',new_callable=io.StringIO) as output:
            p=Path(temp)/'keys/account.json';nk.private_save(p,{'keys':{'fake':'secret'}})
            self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(p.parent.stat().st_mode),0o700)
            self.assertEqual(output.getvalue(),'')
            self.assertEqual(json.loads(p.read_text())['keys']['fake'],'secret')


if __name__=='__main__':unittest.main()
