import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import desktop


class DesktopTests(unittest.TestCase):
    def test_foreign_window_cannot_be_captured(self):
        with patch.object(desktop, 'run', return_value=json.dumps([
            {'id': 1, 'app_id': 'kitty', 'title': 'terminal'},
            {'id': 2, 'app_id': 'wechat', 'title': '微信'},
        ])) as command:
            with self.assertRaises(ValueError):
                desktop.main(['capture', '--window', '1'])
            self.assertEqual(command.call_count, 1)

    def test_visible_window_is_not_login_proof(self):
        with patch.object(desktop, 'windows', return_value=[{'id': 2, 'app_id': 'wechat', 'title': '微信'}]):
            self.assertFalse(desktop.main(['status'])['login_verified'])

    def test_ambiguous_client_does_not_guess(self):
        with patch.object(desktop, 'windows', return_value=[{'id': 2}, {'id': 3}]):
            with self.assertRaises(ValueError):
                desktop.main(['capture'])


if __name__ == '__main__':
    unittest.main()
