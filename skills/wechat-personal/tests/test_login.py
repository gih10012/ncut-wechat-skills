from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import personal_login


class PersonalLoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.results = []
        self.access = SimpleNamespace(STATE=Path(self.tmp.name), ROOT=Path(self.tmp.name),
            private_write=lambda path, text: path.write_text(text),
            private_read=lambda path: path.read_text(), emit=self.results.append)

    def test_missing_wecom_does_not_launch_unrelated_environment(self):
        with patch.object(personal_login.subprocess, 'Popen') as launch, patch.object(personal_login.subprocess, 'run') as run:
            personal_login.main(['--platform', 'wecom', '--transport', 'current-desktop'], self.access)
            self.assertEqual(self.results[-1]['code'], 'WECOM_CLIENT_SETUP_REQUIRED')
            launch.assert_not_called()
            run.assert_not_called()

    def test_existing_wechat_does_not_relaunch_or_claim_login(self):
        with patch.object(personal_login.desktop, 'windows', return_value=[{'id': 1, 'title': '微信'}]), patch.object(personal_login.desktop, 'main', return_value={'ok': True, 'image': '/private/window.png'}), patch.object(personal_login.subprocess, 'Popen') as launch:
            personal_login.main(['--platform', 'wechat', '--transport', 'current-desktop'], self.access)
            launch.assert_not_called()
            self.assertFalse(self.results[-1]['login_verified'])

    def test_default_login_does_not_touch_current_desktop(self):
        with patch.object(personal_login.desktop, 'windows') as windows, patch.object(personal_login.subprocess, 'Popen') as launch:
            personal_login.main(['--platform', 'wechat'], self.access)
            self.assertEqual(self.results[-1]['code'], 'COMPANION_LOGIN_NOT_CONFIGURED')
            windows.assert_not_called()
            launch.assert_not_called()

    def test_finish_reuses_explicit_transport_without_prior_conversation(self):
        with patch.object(personal_login.desktop, 'windows', return_value=[{'id': 1, 'title': '微信'}]), patch.object(personal_login.desktop, 'main', return_value={'ok': True, 'image': '/private/window.png'}) as capture:
            personal_login.main(['--platform', 'wechat', '--transport', 'current-desktop'], self.access)
            personal_login.main(['finish'], self.access)
            self.assertEqual(capture.call_count, 2)
            self.assertEqual(self.results[-1]['code'], 'CLIENT_WINDOW_READY')

    def test_explicit_new_platform_does_not_inherit_desktop_opt_in(self):
        (self.access.STATE/'login.json').write_text('{"platform":"wechat","transport":"current-desktop"}')
        with patch.object(personal_login.desktop, 'windows') as windows:
            personal_login.main(['--platform', 'wecom'], self.access)
            self.assertEqual(self.results[-1]['code'], 'COMPANION_LOGIN_NOT_CONFIGURED')
            windows.assert_not_called()


if __name__ == '__main__':
    unittest.main()
