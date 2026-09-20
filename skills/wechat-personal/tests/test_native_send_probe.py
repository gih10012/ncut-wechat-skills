import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_send_probe as probe


class NativeSendProbePreparationTests(unittest.TestCase):
    def test_user_only_source_is_copied_then_identity_restored(self):
        identity = {'uid': 0, 'gid': 0}
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp)/'appimage', Path(tmp)/'snapshot'
            src.write_bytes(b'synthetic program image')
            expected = hashlib.sha256(src.read_bytes()).hexdigest()
            real_open = Path.open

            def fuse_open(path, *args, **kwargs):
                if path == src and identity['uid'] != 1000:
                    raise PermissionError('synthetic user-only FUSE source')
                return real_open(path, *args, **kwargs)

            with patch.object(probe.os, 'geteuid', side_effect=lambda: identity['uid']), \
                    patch.object(probe.os, 'getegid', side_effect=lambda: identity['gid']), \
                    patch.object(probe.os, 'seteuid', side_effect=lambda x: identity.update(uid=x)), \
                    patch.object(probe.os, 'setegid', side_effect=lambda x: identity.update(gid=x)), \
                    patch.object(Path, 'open', fuse_open):
                with self.assertRaises(PermissionError):
                    probe.copy_verified_executable(src, dst, expected)
                with probe.desktop_identity(1000, 1000):
                    self.assertEqual(probe.copy_verified_executable(src, dst, expected), expected)
                self.assertEqual(identity, {'uid': 0, 'gid': 0})
                self.assertEqual(dst.read_bytes(), b'synthetic program image')
                self.assertEqual(dst.stat().st_mode & 0o777, 0o600)

    def test_unsupported_binary_does_not_leave_debugger_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp)/'image', Path(tmp)/'snapshot'
            src.write_bytes(b'wrong build')
            with self.assertRaisesRegex(ValueError, 'Unsupported WeChat binary'):
                probe.copy_verified_executable(src, dst)
            self.assertFalse(dst.exists())

    def test_identity_is_restored_after_file_failure(self):
        identity = {'uid': 0, 'gid': 0}
        with patch.object(probe.os, 'geteuid', side_effect=lambda: identity['uid']), \
                patch.object(probe.os, 'getegid', side_effect=lambda: identity['gid']), \
                patch.object(probe.os, 'seteuid', side_effect=lambda x: identity.update(uid=x)), \
                patch.object(probe.os, 'setegid', side_effect=lambda x: identity.update(gid=x)):
            with self.assertRaises(PermissionError):
                with probe.desktop_identity(1000, 1000):
                    raise PermissionError('read failed')
            self.assertEqual(identity, {'uid': 0, 'gid': 0})


if __name__ == '__main__':
    unittest.main()
