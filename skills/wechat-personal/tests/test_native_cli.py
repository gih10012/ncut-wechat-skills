import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_cli


class InstalledBridgeTests(unittest.TestCase):
    def test_native_send_delegates_literal_unicode_once_and_never_falls_back(self):
        with patch.object(native_cli.subprocess, 'run') as run:
            run.return_value.returncode = 1
            self.assertEqual(native_cli.main(['send', '--recipient', 'fixture@chatroom',
                                              '--text', '中文\n$(literal) ✅', '--request-id', 'bridge-test']), 1)
        self.assertEqual(run.call_args.args[0], [str(native_cli.CLI), 'send-text',
                         '--recipient', 'fixture@chatroom', '--text', '中文\n$(literal) ✅',
                         '--request-id', 'bridge-test'])
        run.assert_called_once()

    def test_onebot_timeout_does_not_retry_or_invoke_legacy_native_backend(self):
        with patch.object(native_cli.subprocess, 'run', side_effect=subprocess.TimeoutExpired('cli', 1)) as run:
            result = native_cli.send_text('text', 'bridge-timeout', 'filehelper', 1)
        self.assertEqual(result['status'], 'adapter_timeout')
        self.assertFalse(result['automatic_retry_allowed'])
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
