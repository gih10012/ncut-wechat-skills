import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_cli


class InstalledBridgeTests(unittest.TestCase):
    def test_native_xml_routes_once_and_forward_passes_precise_source(self):
        with patch.object(native_cli.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(native_cli.main(['send', '--xml', '/owner/中文 $(literal).xml',
                '--request-id', 'bridge-xml']), 0)
            self.assertEqual(run.call_args.args[0], [str(native_cli.CLI), 'send-xml',
                '--recipient', 'filehelper', '--file', '/owner/中文 $(literal).xml',
                '--request-id', 'bridge-xml'])
            with self.assertRaises(ValueError):
                native_cli.main(['send', '--xml', '/owner/card.xml', '--file', '/owner/file',
                                 '--request-id', 'mixed-xml'])
            run.assert_called_once()
            args = ['forward', '--chat', 'fixture@chatroom', '--local-id', '42',
                    '--recipient', 'filehelper', '--request-id', 'bridge-forward']
            self.assertEqual(native_cli.main(args), 0)
            self.assertEqual(run.call_args.args[0], [str(native_cli.CLI), *args])

    def test_native_file_routes_once_and_rejects_mixed_content(self):
        with patch.object(native_cli.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(native_cli.main(['send', '--recipient', 'fixture@chatroom',
                '--file', '/owner/中文 $(literal).zip', '--request-id', 'bridge-file']), 0)
            self.assertEqual(run.call_args.args[0], [str(native_cli.CLI), 'send-file',
                '--recipient', 'fixture@chatroom', '--file', '/owner/中文 $(literal).zip',
                '--request-id', 'bridge-file'])
            run.assert_called_once()
            for extra in (['--text', 'extra'], ['--image', '/owner/image.png']):
                with self.assertRaises(ValueError):
                    native_cli.main(['send', '--file', '/owner/file.zip',
                                     '--request-id', 'mixed-file', *extra])
            run.assert_called_once()

    def test_native_image_routes_once_and_rejects_mixed_content(self):
        with patch.object(native_cli.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(native_cli.main(['send', '--recipient', 'fixture@chatroom',
                '--image', '/owner/中文 $(literal).png', '--request-id', 'bridge-image']), 0)
            self.assertEqual(run.call_args.args[0], [str(native_cli.CLI), 'send-image',
                '--recipient', 'fixture@chatroom', '--file', '/owner/中文 $(literal).png',
                '--request-id', 'bridge-image'])
            run.assert_called_once()
            with self.assertRaises(ValueError):
                native_cli.main(['send', '--image', '/owner/image.png', '--text', 'extra',
                                 '--request-id', 'mixed-content'])
            run.assert_called_once()

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
