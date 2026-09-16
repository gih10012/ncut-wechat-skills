import hashlib
import hmac
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from Crypto.Cipher import AES
import native_db as db


class SnapshotTests(unittest.TestCase):
    def test_authenticated_pages_reject_wrong_number_and_tampering(self):
        key, mac_key, iv = bytes(range(32)), b'm'*32, b'i'*16
        plain = b'p'*(4096-80)
        page = AES.new(key, AES.MODE_CBC, iv).encrypt(plain)+iv
        page += hmac.new(mac_key, page+struct.pack('<I', 2), hashlib.sha512).digest()
        self.assertEqual(db.decrypt_page(page, 2, key, mac_key), plain+bytes(80))
        for damaged, number in ((page, 3), (bytes([page[0]^1])+page[1:], 2)):
            with self.assertRaisesRegex(ValueError, 'AUTH_FAILED'):
                db.decrypt_page(damaged, number, key, mac_key)

    def wal(self, frames, endian='<'):
        # Independent reference checksum, using integer words rather than the reader.
        def checksum(data, initial=(0, 0)):
            words = struct.unpack(endian+'I'*(len(data)//4), data)
            a, b = initial
            for i in range(0, len(words), 2):
                a = (a+words[i]+b) % (2**32)
                b = (b+words[i+1]+a) % (2**32)
            return a, b
        head = struct.pack('>IIIIII', 0x377f0682 if endian=='<' else 0x377f0683, 3007000, 4096, 1, 123, 456)
        state = checksum(head)
        result = head+struct.pack('>II', *state)
        for page_no, size, content in frames:
            head = struct.pack('>IIII', page_no, size, 123, 456)
            page = bytes([content])*4096
            state = checksum(head[:8]+page, state)
            result += head+struct.pack('>II', *state)+page
        return result

    def test_wal_uses_last_commit_and_ignores_uncommitted_updates(self):
        for endian in ('<', '>'):
            wal = self.wal([(2, 0, 1), (3, 3, 2), (2, 0, 9)], endian)
            pages, size, frames = db.committed_wal(wal)
            self.assertEqual((size, frames), (3, 2))
            self.assertEqual(pages, {2: bytes([1])*4096, 3: bytes([2])*4096})

    def test_wal_truncation_stale_generation_and_bad_checksum(self):
        wal = self.wal([(3, 3, 1), (2, 2, 2)])
        self.assertEqual(set(db.committed_wal(wal)[0]), {2})
        # A checkpoint-reset leaves old generation frames on disk.
        stale = bytearray(wal); stale[40] ^= 1
        self.assertEqual(db.committed_wal(stale), ({}, None, 0))
        damaged = bytearray(wal); damaged[60] ^= 1
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            db.committed_wal(damaged)
        self.assertEqual(db.committed_wal(wal[:-100])[1:], (3, 1))

    def test_busy_snapshot_does_not_fall_back_to_old_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'sample.db'; path.write_bytes(bytes(4096))
            calls = 0
            def changing(_):
                nonlocal calls
                calls += 1
                return (1, 1, 4096, calls, calls)
            with patch.object(db, 'signature', side_effect=changing):
                with self.assertRaisesRegex(ValueError, 'DATABASE_BUSY'):
                    db.stable_read(path)


if __name__ == '__main__':
    unittest.main()
