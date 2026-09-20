import hashlib
import os
from pathlib import Path
import pwd
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_send_probe as probe


class NativeSendProbePreparationTests(unittest.TestCase):
    @unittest.skipUnless(os.geteuid() == 0, 'requires root; exercised separately in CI')
    def test_root_child_drops_all_ids_without_changing_parent(self):
        uid = int(os.environ.get('SUDO_UID', '0'))
        owner = pwd.getpwuid(uid) if uid else pwd.getpwnam('nobody')
        parent_identity = (os.getresuid(), os.getresgid())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target, work = root/'process', root/'work'
            target.mkdir()
            work.mkdir()
            for directory in (root, target, work):
                os.chown(directory, owner.pw_uid, owner.pw_gid)
            source = target/'image'
            source.write_bytes(b'synthetic program image')
            source.chmod(0o644)
            (target/'exe').symlink_to(source)
            (target/'maps').write_text(f'1000-2000 r--p 00000000 00:00 0 {source}\n')
            (target/'maps').chmod(0o644)
            result = probe.run_desktop_preparation(target, work, owner.pw_uid, owner.pw_gid,
                                                  hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(result['reader_uids'], [owner.pw_uid]*3)
            self.assertEqual(result['reader_gids'], [owner.pw_gid]*3)
            self.assertEqual((work/'wechat.elf').stat().st_uid, owner.pw_uid)
            self.assertEqual((os.getresuid(), os.getresgid()), parent_identity)

    def test_child_prepares_program_with_complete_desktop_identity(self):
        if os.geteuid() == 0:
            self.skipTest('run the regular-user child test without sudo')
        parent_identity = (os.getresuid(), os.getresgid())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target, work = root/'process', root/'work'
            target.mkdir()
            work.mkdir()
            src, dst = root/'appimage', work/'wechat.elf'
            src.write_bytes(b'synthetic program image')
            expected = hashlib.sha256(src.read_bytes()).hexdigest()
            (target/'exe').symlink_to(src)
            (target/'maps').write_text(f'1000-2000 r--p 00000000 00:00 0 {src}\n')
            result = probe.run_desktop_preparation(target, work, os.getuid(), os.getgid(), expected)
            self.assertEqual(result['reader_uids'], [os.getuid()]*3)
            self.assertEqual(result['reader_gids'], [os.getgid()]*3)
            self.assertEqual(result['binary_sha256'], expected)
            self.assertEqual(result['load_bias'], 0x1000)
            self.assertEqual(dst.read_bytes(), src.read_bytes())
            self.assertEqual(dst.stat().st_mode & 0o777, 0o600)
            self.assertEqual((os.getresuid(), os.getresgid()), parent_identity)

    def test_effective_only_identity_is_rejected_before_fuse_access(self):
        # The old euid-only mock missed the kernel's real/saved-ID checks.
        for uids, gids in [((0, 1000, 0), (1000, 1000, 1000)),
                           ((1000, 1000, 1000), (0, 1000, 0))]:
            with self.subTest(uids=uids, gids=gids), \
                    patch.object(probe.os, 'getresuid', return_value=uids), \
                    patch.object(probe.os, 'getresgid', return_value=gids), \
                    patch.object(probe, 'copy_verified_executable') as copy:
                with self.assertRaisesRegex(ValueError, 'desktop_identity_incomplete'):
                    probe.prepare_desktop_executable({'uid': 1000, 'gid': 1000})
                copy.assert_not_called()

    def test_child_failure_keeps_stage_and_errno(self):
        if os.geteuid() == 0:
            self.skipTest('run the regular-user child test without sudo')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'exe').write_bytes(b'no read permission')
            (root/'exe').chmod(0)
            with self.assertRaisesRegex(ValueError, 'copy_appimage_as_desktop_user: PermissionError.*13'):
                probe.run_desktop_preparation(root, root, os.getuid(), os.getgid())
            self.assertFalse((root/'wechat.elf').exists())

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
