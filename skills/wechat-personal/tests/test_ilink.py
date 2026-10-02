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
import ilink_media
import ilink_recovery
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

    def owner_message(self, identifier, created, token='private-context', text='hello', **extra):
        return {'message_id': identifier, 'create_time_ms': created,
                'from_user_id': 'owner', 'to_user_id': 'bot-id', 'message_type': 1,
                'context_token': token, 'item_list': [{'type': 1, 'text_item': {'text': text}}], **extra}

    def recovery_credentials(self):
        state = dict(self.credentials(), ilink_user_id='owner')
        state['native_recovery'] = {'enabled': True, 'native_chat': 'exact-bot@weclaw',
                                    'ilink_user_id': 'owner', 'ilink_bot_id': 'bot-id'}
        return state

    def test_latest_context_beyond_output_page_survives_older_buffered_page(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        response = {'get_updates_buf': 'next', 'msgs': [self.owner_message(2, 2000, 'new-context'),
                                                        self.owner_message(1, 1000, 'old-context')]}
        with patch.object(ilink, 'request', return_value=response) as request:
            first = ilink.main(['updates', '--limit', '1'], self.access)
            saved = json.loads(self.account.read_text())['owner_context']
            second = ilink.main(['updates', '--limit', '1'], self.access)
        request.assert_called_once()
        self.assertEqual([m['message_id'] for m in first['items'] + second['items']], [2, 1])
        self.assertEqual(saved['token'], 'new-context')
        self.assertEqual(json.loads(self.account.read_text())['owner_context'], saved)
        # A fresh message at the end of an output page also becomes available immediately.
        with patch.object(ilink, 'request', return_value={'get_updates_buf': 'later', 'msgs': [
                self.owner_message(3, 3000, 'older'), self.owner_message(4, 4000, 'newest')]}):
            ilink.main(['updates', '--limit', '1'], self.access)
        self.assertEqual(json.loads(self.account.read_text())['owner_context']['token'], 'newest')

    def test_empty_or_duplicate_poll_does_not_refresh_context_age(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        response = {'get_updates_buf': 'next', 'msgs': [self.owner_message(1, 1000)]}
        with patch.object(ilink, 'request', return_value=response):
            ilink.main(['updates'], self.access)
        saved = json.loads(self.account.read_text())['owner_context']
        for messages in ([], response['msgs']):
            with patch.object(ilink, 'request', return_value={'get_updates_buf': 'next', 'msgs': messages}):
                ilink.main(['updates'], self.access)
            self.assertEqual(json.loads(self.account.read_text())['owner_context'], saved)
            self.assertFalse(json.loads(self.account.read_text())['last_update_poll']['reply_context_refreshed'])

    def test_new_inbound_with_same_token_records_new_message_time(self):
        state = dict(self.credentials(), ilink_user_id='owner')
        self.assertTrue(ilink.remember_owner_context(state, [self.owner_message(1, 1000)], 'first'))
        self.assertTrue(ilink.remember_owner_context(state, [self.owner_message(2, 2000)], 'second'))
        self.assertEqual(state['owner_context']['received_at'], 'second')
        self.assertEqual(state['owner_context']['message_created_at_ms'], 2000)
        self.assertFalse(ilink.remember_owner_context(state, [self.owner_message(1, 1000)], 'older'))

    def test_malformed_later_page_never_persists_its_context_or_cursor(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        before = self.account.read_bytes()
        with patch.object(ilink, 'request', return_value={'get_updates_buf': 'new', 'msgs': [
                self.owner_message(1, 1000), self.owner_message(2, 2000, item_list='malformed')]}):
            result = ilink.main(['updates', '--limit', '1'], self.access)
        self.assertEqual(result['code'], 'BOT_INVALID_MESSAGE_ITEMS')
        self.assertEqual(self.account.read_bytes(), before)

    def test_status_is_private_local_and_available_during_poll(self):
        import fcntl
        state = self.recovery_credentials()
        state['owner_context'] = {'user_id': 'owner', 'token': 'private-context', 'received_at': 'then'}
        state['last_update_poll'] = {'checked_at': 'then', 'authenticated': True, 'token': 'private-token'}
        self.seed(self.account, state)
        before = self.account.read_bytes()
        with (self.account.parent/'command.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(ilink, 'request') as request:
                result = ilink.main(['status'], self.access)
        request.assert_not_called()
        self.assertNotIn('private-', json.dumps(result))
        self.assertFalse(result['remote_login_verified'])
        self.assertEqual(result['reply_context_validity'], 'unknown')
        self.assertTrue(result['native_recovery_enabled'])
        self.assertEqual(self.account.read_bytes(), before)

    def test_known_rejection_recovers_once_preserves_inbox_and_replays_without_writes(self):
        state = self.recovery_credentials()
        state['pending'] = [self.owner_message(0, 500, text='previous unread')]
        self.seed(self.account, state)
        sent = []
        refresh = {}
        def native(text, request_id, recipient, timeout):
            refresh['text'] = text
            self.assertEqual(recipient, 'exact-bot@weclaw')
            self.assertTrue(request_id.startswith('bot-renew-'))
            return {'ok': True, 'native_submission_entered': True, 'local_history_integrated': True}
        def api(base, endpoint, **kwargs):
            if endpoint == 'getupdates':
                return {'get_updates_buf': 'next', 'msgs': [
                    self.owner_message(1, 1000, text='unrelated unread'),
                    self.owner_message(2, 2000, 'fresh-context', refresh['text'])]}
            sent.append(kwargs['body']['msg'].copy())
            if len(sent) == 1:
                raise ilink.BotError('BOT_BUSINESS_ERROR_-2')
            journal = json.loads((self.account.parent/'sends/recover.json').read_text())
            self.assertEqual(journal['phase'], 'resubmitting')
            self.assertTrue(journal['result']['outcome_unknown'])
            self.assertEqual(journal['client_id'], sent[-1]['client_id'])
            return {'message_id': 123}
        args = ['send', '--text', 'original notification', '--request-id', 'recover']
        with patch.object(ilink, 'request', side_effect=api), patch.object(ilink_recovery.native_cli, 'send_text', side_effect=native) as send:
            result = ilink.main(args, self.access)
            replay = ilink.main(args, self.access)
            inbox = ilink.main(['updates'], self.access)
        send.assert_called_once()
        self.assertEqual(len(sent), 2)
        self.assertNotEqual(sent[0]['client_id'], sent[1]['client_id'])
        self.assertEqual(sent[1]['context_token'], 'fresh-context')
        self.assertEqual(sent[0]['item_list'], sent[1]['item_list'])
        self.assertTrue(result['api_accepted'])
        self.assertFalse(result['delivery_verified'])
        self.assertTrue(replay['replayed'])
        self.assertEqual([m['message_id'] for m in inbox['items']], [0, 1, 2])
        history = json.loads((self.account.parent/'sends/recover.json').read_text())['attempts']
        self.assertEqual([r['api_accepted'] for r in history], [False, True])
        self.assertNotIn('fresh-context', json.dumps(result))

    def test_timeout_or_auth_failure_never_uses_native_recovery(self):
        for code in ('BOT_NETWORK_TIMEOUT', 'BOT_AUTH_REQUIRED'):
            with self.subTest(code=code):
                self.seed(self.account, self.recovery_credentials())
                args = ['send', '--text', 'test', '--request-id', code]
                with patch.object(ilink, 'request', side_effect=ilink.BotError(code)) as request, patch.object(ilink_recovery, 'renew_context') as renew:
                    first = ilink.main(args, self.access)
                    again = ilink.main(args, self.access)
                request.assert_called_once(); renew.assert_not_called()
                self.assertFalse(first['ok']); self.assertTrue(again['replayed'])

    def test_upload_rejection_never_recovers_or_submits_a_text_in_place_of_media(self):
        self.seed(self.account, self.recovery_credentials())
        source = self.root/'sample.txt'; source.write_bytes(b'hello')
        with patch.object(ilink_media, 'upload', side_effect=ilink.BotError('BOT_BUSINESS_ERROR_-2')), patch.object(ilink_recovery, 'renew_context') as renew, patch.object(ilink, 'request') as request:
            result = ilink.main(['send', '--file', str(source), '--request-id', 'upload-rejected'], self.access)
        renew.assert_not_called(); request.assert_not_called()
        self.assertFalse(result['message_submission_attempted'])

    def test_media_context_recovery_reuses_uploaded_item_exactly_once(self):
        state = self.recovery_credentials()
        state['owner_context'] = {'user_id': 'owner', 'token': 'fresh'}
        self.seed(self.account, state)
        source = self.root/'sample.txt'; source.write_bytes(b'hello')
        item = {'type': 4, 'file_item': {'file_name': 'sample.txt', 'len': '5'}}
        observed = []
        def api(base, endpoint, **kwargs):
            observed.append(kwargs['body']['msg']['item_list'])
            if len(observed) == 1:
                raise ilink.BotError('BOT_BUSINESS_ERROR_-2')
            return {'message_id': 123}
        with patch.object(ilink_media, 'upload', return_value=item) as upload, patch.object(ilink, 'request', side_effect=api), patch.object(ilink_recovery, 'renew_context', return_value={'ok': True, 'fresh_for_current_send': True}):
            result = ilink.main(['send', '--file', str(source), '--request-id', 'media-recovered'], self.access)
        upload.assert_called_once()
        self.assertEqual(observed, [[item], [item]])
        self.assertTrue(result['api_accepted'])

    def test_second_rejection_or_timeout_does_not_retry_again(self):
        for code in ('BOT_BUSINESS_ERROR_-2', 'BOT_NETWORK_TIMEOUT'):
            with self.subTest(code=code):
                state = self.recovery_credentials()
                state['owner_context'] = {'user_id': 'owner', 'token': 'fresh'}
                self.seed(self.account, state)
                args = ['send', '--text', 'test', '--request-id', 'second-' + code]
                with patch.object(ilink, 'request', side_effect=[ilink.BotError('BOT_BUSINESS_ERROR_-2'), ilink.BotError(code)]) as request, patch.object(ilink_recovery, 'renew_context', return_value={'ok': True, 'fresh_for_current_send': True}) as renew:
                    result = ilink.main(args, self.access)
                    again = ilink.main(args, self.access)
                self.assertEqual(request.call_count, 2); renew.assert_called_once()
                self.assertEqual(result['code'], code)
                self.assertEqual(result['outcome_unknown'], code == 'BOT_NETWORK_TIMEOUT')
                self.assertTrue(again['replayed'])

    def test_native_refresh_failure_or_cached_old_success_cannot_resubmit(self):
        for renewed in ({'ok': False, 'code': 'BOT_NATIVE_RECOVERY_SEND_FAILED'},
                        {'ok': True, 'replayed': True, 'fresh_for_current_send': False}):
            with self.subTest(renewed=renewed):
                self.seed(self.account, self.recovery_credentials())
                request_id = 'failed-refresh' if not renewed['ok'] else 'old-refresh'
                with patch.object(ilink, 'request', side_effect=ilink.BotError('BOT_BUSINESS_ERROR_-2')) as request, patch.object(ilink_recovery, 'renew_context', return_value=renewed) as renew:
                    result = ilink.main(['send', '--text', 'test', '--request-id', request_id], self.access)
                request.assert_called_once(); renew.assert_called_once()
                self.assertFalse(result['api_accepted'])

    def test_native_preflight_failure_never_polls_or_resends(self):
        self.seed(self.account, self.recovery_credentials())
        args = ['recovery', '--renew', '--request-id', 'native-failed']
        with patch.object(ilink_recovery.native_cli, 'send_text', return_value={
                'ok': False, 'code': 'NATIVE_PREFLIGHT_FAILED', 'native_submission_entered': False}) as native, patch.object(ilink, 'request') as request:
            first = ilink.main(args, self.access)
            again = ilink.main(args, self.access)
        self.assertEqual(first['code'], 'BOT_NATIVE_RECOVERY_SEND_FAILED')
        self.assertTrue(again['replayed'])
        native.assert_called_once(); request.assert_not_called()

    def test_renewal_requires_correlated_owner_message_and_never_replays_write(self):
        self.seed(self.account, self.recovery_credentials())
        def api(base, endpoint, **kwargs):
            return {'get_updates_buf': 'next', 'msgs': [self.owner_message(1, 1000, text='other fresh message')]}
        with patch.object(ilink, 'request', side_effect=api), patch.object(ilink_recovery.native_cli, 'send_text', return_value={'ok': True}) as native, patch.object(ilink_recovery.time, 'monotonic', side_effect=[0, 0, 0, 40]):
            result = ilink.main(['recovery', '--renew', '--request-id', 'unmatched'], self.access)
            again = ilink.main(['recovery', '--renew', '--request-id', 'unmatched'], self.access)
        self.assertEqual(result['code'], 'BOT_NATIVE_RECOVERY_INBOUND_NOT_OBSERVED')
        self.assertTrue(again['replayed']); native.assert_called_once()

    def test_foreign_or_group_refresh_text_does_not_authorize_send(self):
        state = self.recovery_credentials()
        for extra in ({'from_user_id': 'someone-else'}, {'to_user_id': 'another-bot'}, {'group_id': 'group'}, {'message_type': 2}):
            with self.subTest(extra=extra):
                self.assertFalse(ilink_recovery.matches_refresh(self.owner_message(1, 1000, text='nonce', **extra), state, 'nonce'))

    def test_rebinding_disables_recovery_to_old_chat(self):
        state = self.recovery_credentials()
        state['ilink_user_id'] = 'new-owner'
        self.assertFalse(ilink.recovery_enabled(state))

    def test_recovery_configuration_is_explicit_and_has_no_send(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        with patch.object(ilink_recovery.native_cli, 'available', return_value=True), patch.object(ilink, 'request') as request, patch.object(ilink_recovery.native_cli, 'send_text') as native:
            wrong = ilink.main(['recovery', '--native-chat', 'regular-friend'], self.access)
            enabled = ilink.main(['recovery', '--native-chat', 'exact-bot@weclaw'], self.access)
            disabled = ilink.main(['recovery', '--disable-native-recovery'], self.access)
        request.assert_not_called(); native.assert_not_called()
        self.assertFalse(wrong['ok']); self.assertTrue(enabled['enabled']); self.assertFalse(disabled['enabled'])

    def test_media_upload_send_and_replay_are_owner_scoped(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        source = self.root/'sample.txt'; source.write_bytes(b'hello')
        item = {'type': 4, 'file_item': {'file_name': 'sample.txt', 'len': '5',
                'media': {'aes_key': 'private-key', 'encrypt_query_param': 'private-reference'}}}
        args = ['send', '--file', str(source), '--request-id', 'media']
        with patch.object(ilink_media, 'upload', return_value=item) as upload, patch.object(ilink, 'request', return_value={}) as request:
            first = ilink.main(args, self.access)
            again = ilink.main(args, self.access)
            source.write_bytes(b'changed')
            conflict = ilink.main(args, self.access)
        upload.assert_called_once(); request.assert_called_once()
        self.assertEqual(request.call_args.kwargs['body']['msg']['to_user_id'], 'owner')
        self.assertEqual(request.call_args.kwargs['body']['msg']['item_list'], [item])
        self.assertTrue(first['api_accepted']); self.assertTrue(again['replayed'])
        self.assertFalse(first['desktop_required'])
        self.assertNotIn('private-', json.dumps(first))
        self.assertEqual(conflict['code'], 'BOT_SEND_REQUEST_ID_CONFLICT')

    def test_failed_upload_does_not_submit_message_or_retry(self):
        self.seed(self.account, dict(self.credentials(), ilink_user_id='owner'))
        source = self.root/'sample.txt'; source.write_bytes(b'hello')
        args = ['send', '--file', str(source), '--request-id', 'failed-media']
        with patch.object(ilink_media, 'upload', side_effect=ilink.BotError('BOT_MEDIA_NETWORK_ERROR')) as upload, patch.object(ilink, 'request') as request:
            result = ilink.main(args, self.access)
            again = ilink.main(args, self.access)
        request.assert_not_called(); upload.assert_called_once()
        self.assertFalse(result['message_submission_attempted'])
        self.assertFalse(result['outcome_unknown']); self.assertTrue(again['replayed'])

    def test_inbound_media_and_unknown_items_retained_without_credential_leak(self):
        self.seed(self.account, self.credentials())
        response = {'get_updates_buf': 'next', 'msgs': [{'message_id': 'media', 'item_list': [
            {'type': 2, 'image_item': {'media': {'aes_key': 'private-key', 'encrypt_query_param': 'private-reference'}}},
            {'type': 99, 'unknown_item': {'secret': 'private-unknown'}}]}]}
        with patch.object(ilink, 'request', return_value=response):
            result = ilink.main(['updates'], self.access)
        items = result['items'][0]['items']
        self.assertNotIn('private-', json.dumps(result))
        self.assertEqual((self.account.parent/'media'/(items[0]['attachment_id']+'.json')).stat().st_mode & 0o777, 0o600)
        self.assertFalse(items[1]['supported'])
        self.assertIn('private-unknown', (self.account.parent/'unrecognized'/(items[1]['raw_item_id']+'.json')).read_text())
        self.assertEqual(json.loads(self.account.read_text())['cursor'], 'next')

    def test_download_rejects_path_traversal_and_untrusted_origin(self):
        with self.assertRaises(ilink.BotError):
            ilink_media.download(self.access, self.account.parent, '../account', 100)
        for url in ('http://cdn.weixin.qq.com/a', 'https://weixin.qq.com.example.com/a',
                    'https://user@cdn.weixin.qq.com/a', 'https://cdn.weixin.qq.com:444/a'):
            with self.subTest(url=url), self.assertRaises(ilink.BotError):
                ilink_media.cdn_url(url)

    def test_cached_download_can_run_while_poll_owns_account_lock(self):
        import fcntl
        self.account.parent.mkdir(parents=True)
        with (self.account.parent/'command.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(ilink_media, 'download', return_value={'ok': True}) as download, patch.object(ilink, 'request') as request:
                result = ilink.main(['download', '--attachment-id', 'a'*64], self.access)
        self.assertTrue(result['ok'])
        download.assert_called_once(); request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
