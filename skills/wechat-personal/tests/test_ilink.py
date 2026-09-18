import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT.parent/'ncut-web-api/scripts'))
import ilink
import ncut


class IlinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.access = SimpleNamespace(STATE=self.root, account_path=ncut.account_path,
            private_write=ncut.private_write, private_read=ncut.private_read, now=ncut.now)
        self.account = self.root/'bots/me/account.json'
        self.pending = self.root/'bots/me/login.json'

    def seed(self, path, data):
        ncut.private_write(path, json.dumps(data))

    def credentials(self):
        return {'bot_token': 'private-token', 'baseurl': ilink.BASE,
                'ilink_bot_id': 'bot-id', 'cursor': 'old-cursor'}

    def login_pending(self):
        self.seed(self.pending, {'qrcode': 'private-qr', 'qr_url': 'https://liteapp.weixin.qq.com/q/example',
                                'baseurl': ilink.BASE, 'created_at': time.time()})

    def test_credentials_are_reused_without_new_login(self):
        self.seed(self.account, self.credentials())
        with patch.object(ilink, 'request') as request:
            result = ilink.main(['login'], self.access)
        self.assertEqual(result['code'], 'BOT_CREDENTIALS_PRESENT')
        self.assertFalse(result['login_verified'])
        request.assert_not_called()

    def test_malformed_confirmation_preserves_existing_credentials(self):
        self.seed(self.account, self.credentials()); self.login_pending()
        before = self.account.read_bytes()
        with patch.object(ilink, 'request', return_value={'status': 'confirmed', 'ilink_bot_id': 'other'}):
            result = ilink.main(['finish'], self.access)
        self.assertFalse(result['ok'])
        self.assertEqual(self.account.read_bytes(), before)

    def test_confirmation_saves_credentials_but_does_not_claim_message_read(self):
        self.login_pending()
        response = {'status': 'confirmed', 'bot_token': 'private-token', 'ilink_bot_id': 'bot-id',
                    'ilink_user_id': 'user-id', 'baseurl': ilink.BASE}
        with patch.object(ilink, 'request', return_value=response):
            result = ilink.main(['finish'], self.access)
        self.assertTrue(result['ok']); self.assertFalse(result['message_read_verified'])
        self.assertNotIn('private-token', json.dumps(result))
        self.assertEqual(self.account.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.pending.exists())

    def test_untrusted_redirect_cannot_replace_polling_host(self):
        self.login_pending(); before = self.pending.read_bytes()
        with patch.object(ilink, 'request', return_value={'status': 'scaned_but_redirect', 'redirect_host': 'example.com'}):
            result = ilink.main(['finish'], self.access)
        self.assertEqual(result['code'], 'BOT_UNTRUSTED_API_ORIGIN')
        self.assertEqual(self.pending.read_bytes(), before)

    def test_pending_updates_survive_output_limit_without_second_http(self):
        self.seed(self.account, self.credentials())
        response = {'ret': 0, 'get_updates_buf': 'next-cursor', 'msgs': [
            {'message_id': i, 'context_token': 'private-context', 'item_list': [
                {'type': 1, 'text_item': {'text': 'message '+str(i)}},
                {'type': 2, 'image_item': {'aeskey': 'private-media-key'}}]} for i in range(3)]}
        with patch.object(ilink, 'request', return_value=response) as request:
            first = ilink.main(['updates', '--limit', '1'], self.access)
            second = ilink.main(['updates', '--limit', '2'], self.access)
        self.assertEqual([m['message_id'] for m in first['items']+second['items']], [0, 1, 2])
        request.assert_called_once()
        self.assertEqual(json.loads(self.account.read_text())['cursor'], 'next-cursor')
        self.assertNotIn('private-', json.dumps(first))
        self.assertFalse(first['personal_inbox'])

    def test_auth_error_does_not_advance_cursor_or_claim_empty_inbox(self):
        self.seed(self.account, self.credentials()); before = self.account.read_bytes()
        with patch.object(ilink, 'request', side_effect=ilink.BotError('BOT_AUTH_REQUIRED')) as request:
            result = ilink.main(['updates'], self.access)
        self.assertEqual(result, {'ok': False, 'code': 'BOT_AUTH_REQUIRED'})
        self.assertEqual(self.account.read_bytes(), before)
        request.assert_called_once()

    def test_live_success_shape_can_omit_return_code(self):
        self.seed(self.account, self.credentials())
        with patch.object(ilink, 'request', return_value={'msgs': [], 'get_updates_buf': 'next'}):
            result = ilink.main(['updates'], self.access)
        self.assertTrue(result['ok'])
        self.assertEqual(json.loads(self.account.read_text())['cursor'], 'next')

    def test_empty_http_object_is_not_empty_inbox(self):
        self.seed(self.account, self.credentials()); before = self.account.read_bytes()
        with patch.object(ilink, 'request', return_value={}):
            result = ilink.main(['updates'], self.access)
        self.assertEqual(result['code'], 'BOT_INVALID_UPDATES')
        self.assertEqual(self.account.read_bytes(), before)

    def test_concurrent_poll_cannot_consume_or_overwrite_another_cursor(self):
        import fcntl
        self.seed(self.account, self.credentials())
        with (self.account.parent/'command.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(ilink, 'request') as request:
                result = ilink.main(['updates'], self.access)
        self.assertEqual(result['code'], 'BOT_ACCOUNT_BUSY')
        request.assert_not_called()

    def test_malformed_message_cannot_advance_cursor(self):
        self.seed(self.account, self.credentials()); before = self.account.read_bytes()
        with patch.object(ilink, 'request', return_value={'ret': 0, 'get_updates_buf': 'new',
                                                        'msgs': [{'item_list': 'invalid'}]}):
            result = ilink.main(['updates'], self.access)
        self.assertEqual(result['code'], 'BOT_INVALID_MESSAGE_ITEMS')
        self.assertEqual(self.account.read_bytes(), before)

    def test_origins_require_official_https_host(self):
        for value in ['http://ilinkai.weixin.qq.com', 'https://weixin.qq.com.example.com',
                      'https://user@ilinkai.weixin.qq.com', 'https://ilinkai.weixin.qq.com/path']:
            with self.subTest(value=value), self.assertRaises(ilink.BotError):
                ilink.api_origin(value)

    def test_send_only_targets_bound_owner_and_repeated_id_does_not_resend(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        args = ['send', '--text', 'test', '--request-id', 'one']
        with patch.object(ilink, 'request', return_value={}) as request:
            first = ilink.main(args, self.access)
            again = ilink.main(args, self.access)
            conflict = ilink.main(['send', '--text', 'different', '--request-id', 'one'], self.access)
        request.assert_called_once()
        msg = request.call_args.kwargs['body']['msg']
        self.assertEqual(msg['to_user_id'], 'owner')
        self.assertEqual(msg['item_list'][0]['text_item']['text'], 'test')
        self.assertTrue(first['api_accepted']); self.assertFalse(first['delivery_verified'])
        self.assertTrue(again['replayed'])
        self.assertEqual(conflict['code'], 'BOT_SEND_REQUEST_ID_CONFLICT')
        self.assertEqual((self.account.parent/'sends/one.json').stat().st_mode & 0o777, 0o600)

    def test_uncertain_send_is_journaled_before_request_and_never_retried(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        def fail(*args, **kwargs):
            attempt = json.loads((self.account.parent/'sends/timeout.json').read_text())
            self.assertEqual(attempt['client_id'], kwargs['body']['msg']['client_id'])
            raise ilink.BotError('BOT_NETWORK_TIMEOUT')
        with patch.object(ilink, 'request', side_effect=fail) as request:
            result = ilink.main(['send', '--text', 'test', '--request-id', 'timeout'], self.access)
            again = ilink.main(['send', '--text', 'test', '--request-id', 'timeout'], self.access)
        request.assert_called_once()
        self.assertTrue(result['outcome_unknown']); self.assertTrue(again['replayed'])

    def test_context_is_cached_only_for_bound_owner_and_kept_private(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        response = {'get_updates_buf': 'next', 'msgs': [
            {'from_user_id': 'owner', 'to_user_id': 'bot-id', 'message_type': 1,
             'context_token': 'private-owner-context'},
            {'from_user_id': 'other', 'to_user_id': 'bot-id', 'message_type': 1,
             'context_token': 'unrelated-context'}]}
        with patch.object(ilink, 'request', return_value=response):
            result = ilink.main(['updates'], self.access)
        self.assertNotIn('context', json.dumps(result))
        self.assertEqual(json.loads(self.account.read_text())['owner_context']['token'], 'private-owner-context')
        with patch.object(ilink, 'request', return_value={}) as request:
            sent = ilink.main(['send', '--text', 'test', '--request-id', 'context'], self.access)
        self.assertEqual(request.call_args.kwargs['body']['msg']['context_token'], 'private-owner-context')
        self.assertNotIn('private-owner-context', json.dumps(sent))

    def test_send_validates_text_and_request_id_before_network(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        with patch.object(ilink, 'request') as request:
            for args in [['send'], ['send', '--text', 'test'],
                         ['send', '--text', 'test', '--request-id', '../escape']]:
                self.assertFalse(ilink.main(args, self.access)['ok'])
        request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
