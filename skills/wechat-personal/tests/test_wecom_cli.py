import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/wechat.py'
spec = importlib.util.spec_from_file_location('wechat_wecom_access', path)
wx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wx)


class WeComCliTests(unittest.TestCase):
    def test_exact_arguments_pass_once_without_recipient_whitelist(self):
        response = subprocess.CompletedProcess([], 0, '{"ok":true,"status":"accepted"}')
        args = ['send', '--recipient', 'exact-session-id', '--text', '中文\n✅', '--request-id', 'operation-1']
        with patch.object(wx.shutil, 'which', return_value='/usr/bin/wecom-linux'), \
             patch.object(wx.subprocess, 'run', return_value=response) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wx.wecom(args), 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], ['/usr/bin/wecom-linux', *args])
        self.assertEqual(json.loads(output.getvalue())['status'], 'accepted')

    def test_timeout_does_not_retry_or_use_another_sender(self):
        with patch.object(wx.shutil, 'which', return_value='/usr/bin/wecom-linux'), \
             patch.object(wx.subprocess, 'run', side_effect=subprocess.TimeoutExpired('wecom-linux', 180)) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wx.wecom(['send', '--request-id', 'operation-1']), 1)
        self.assertEqual(run.call_count, 1)
        value = json.loads(output.getvalue())
        self.assertEqual(value['code'], 'WECOM_CLI_TIMEOUT')
        self.assertFalse(value['automatic_retry'])

    def test_backend_failure_preserves_original_result(self):
        response = subprocess.CompletedProcess([], 1, '{"ok":false,"code":"ORIGINAL_FAILURE"}')
        with patch.object(wx.shutil, 'which', return_value='/usr/bin/wecom-linux'), \
             patch.object(wx.subprocess, 'run', return_value=response) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wx.wecom(['status']), 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(json.loads(output.getvalue())['code'], 'ORIGINAL_FAILURE')
