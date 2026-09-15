import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ncut
import school_login as login


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = patch.object(ncut, 'STATE', Path(self.tmp.name))
        self.state.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.state.stop)

    def args(self, operation='start', service=None):
        return argparse.Namespace(operation=operation, service=service, account='me', open=False)

    def test_valid_session_does_not_open_browser(self):
        with patch.object(login, 'check', return_value={'ok': True}), patch.object(login, 'browser') as browser, patch.object(ncut, 'emit'):
            login.main(self.args())
            browser.assert_not_called()

    def test_outage_does_not_trigger_login(self):
        with patch.object(login, 'check', return_value={'ok': False, 'code': 'TIMEOUT'}), patch.object(login, 'browser') as browser, patch.object(ncut, 'emit'):
            login.main(self.args())
            browser.assert_not_called()

    def test_finish_uses_persisted_service(self):
        path = ncut.STATE / 'login-pending/me.json'
        ncut.private_write(path, json.dumps({'service': 'workflow'}))
        with patch.object(login, 'browser', return_value={'ok': True}), patch.object(login, 'check', return_value={'ok': True}) as check, patch.object(ncut, 'emit'):
            login.main(self.args('finish'))
            check.assert_called_once_with('me', 'workflow')
            self.assertFalse(path.exists())

    def test_http_200_sso_script_is_expired_login(self):
        ncut.private_write(ncut.account_path('me'), '{}')
        raw = b'<script>top.location.href="https://sso.ncut.edu.cn/sso/login?service=abc";</script>'
        with patch.object(ncut, 'fetch', return_value=({'ok': True}, raw)):
            self.assertEqual(login.check('me', 'jwxt')['code'], 'AUTH_REQUIRED')

    def test_status_reports_live_expired_qr_for_persisted_service(self):
        path = ncut.STATE / 'login-pending/me.json'
        ncut.private_write(path, json.dumps({'service': 'workflow'}))
        with patch.object(login, 'browser', return_value={'ok': True, 'login_state': 'qr_expired'}) as browser, patch.object(ncut, 'emit') as emit, patch.object(login, 'check') as check:
            login.main(self.args('status'))
            browser.assert_called_once_with('status', 'me')
            check.assert_not_called()
            result = emit.call_args.args[0]
            self.assertEqual(result['service'], 'workflow')
            self.assertEqual(result['browser']['login_state'], 'qr_expired')
            self.assertFalse(result['live_identity_verified'])

    def test_status_without_pending_login_does_not_probe_browser(self):
        with patch.object(login, 'browser') as browser, patch.object(ncut, 'emit') as emit:
            login.main(self.args('status'))
            browser.assert_not_called()
            self.assertFalse(emit.call_args.args[0]['pending'])


if __name__ == '__main__':
    unittest.main()
