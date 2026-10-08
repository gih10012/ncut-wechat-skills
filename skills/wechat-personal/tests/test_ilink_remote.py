"""Private fixtures and loopback-only tests; no real iLink credentials/network."""
import fcntl
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT.parent / 'ncut-web-api/scripts'))
import ilink
import ilink_media
import ilink_remote
import ncut


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.root = self.state / 'bots' / 'me'
        self.access = SimpleNamespace(STATE=self.state, account_path=ncut.account_path,
                                      private_write=ncut.private_write, private_read=ncut.private_read,
                                      now=ncut.now)
        self.token = self.state / 'fixture-token'
        self.access.private_write(self.token, 'fixture-token-not-a-real-credential')
        self.config = {'control_url': 'http://127.0.0.1:17680', 'token_file': str(self.token)}
        self.seed(self.root / 'remote.json', self.config)
        self.seed(self.root / 'account.json', {'cursor': 'fixture-local-iLink-cursor',
                                            'bot_token': 'fixture-account-token'})

    def seed(self, path, value):
        self.access.private_write(path, json.dumps(value))

    def call(self, args, response=None, side_effect=None):
        with patch.object(ilink, 'request') as local, patch.object(
                ilink_remote, 'request', return_value=response, side_effect=side_effect) as remote:
            result = ilink.main(args, self.access)
        local.assert_not_called()
        return result, remote

    def test_status_is_remote_and_never_reads_a_local_status_as_fallback(self):
        result, remote = self.call(['status'], {'leader': {'node': 'fixture-cloud'}})
        self.assertEqual(result['code'], 'BOT_REMOTE_STATUS')
        self.assertEqual(result['source'], 'mesh')
        self.assertFalse(result['desktop_required'])
        self.assertEqual(remote.call_args.args[2], '/v1/status')

    def test_network_failure_never_falls_back_to_local_sdk(self):
        before = (self.root / 'account.json').read_bytes()
        for operation in ('status', 'updates'):
            with self.subTest(operation=operation):
                result, _ = self.call([operation], side_effect=ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'))
                self.assertEqual(result, {'ok': False, 'code': 'BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'})
        self.assertEqual((self.root / 'account.json').read_bytes(), before)
        self.assertFalse((self.root / 'command.lock').exists())

    def test_remote_login_finish_and_native_renew_are_refused(self):
        for args, code in ((['login'], 'BOT_REMOTE_OWNER_MUST_REBIND_ON_AUTHORITY'),
                           (['finish'], 'BOT_REMOTE_OWNER_MUST_REBIND_ON_AUTHORITY'),
                           (['recovery', '--renew', '--request-id', 'fixture-renew'],
                            'BOT_REMOTE_RECOVERY_REQUIRES_AUTHORITY_BRIDGE')):
            with self.subTest(args=args):
                result, remote = self.call(args)
                self.assertEqual(result['code'], code)
                remote.assert_not_called()

    def test_bad_remote_config_is_structured_and_never_uses_local(self):
        for value in ({}, [], {'control_url': 7, 'token_file': str(self.token)},
                      {'control_url': 'https://', 'token_file': str(self.token)}):
            with self.subTest(value=value):
                self.seed(self.root / 'remote.json', value)
                with patch.object(ilink, 'request') as local:
                    result = ilink.main(['updates'], self.access)
                self.assertFalse(result['ok'])
                self.assertTrue(result['code'].startswith('BOT_'))
                local.assert_not_called()

    def test_invalid_json_in_remote_config_does_not_escape_or_fall_back(self):
        self.access.private_write(self.root / 'remote.json', '{invalid json')
        with patch.object(ilink, 'request') as local:
            result = ilink.main(['updates'], self.access)
        self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_STATE')
        local.assert_not_called()

    def test_remote_config_must_be_private_and_not_symlinked(self):
        path = self.root / 'remote.json'
        path.chmod(0o644)
        result, remote = self.call(['status'])
        self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_STATE')
        remote.assert_not_called()
        path.unlink()
        path.symlink_to(self.state / 'nonexistent-fixture-config')
        result, remote = self.call(['updates'])
        self.assertFalse(result['ok'])
        remote.assert_not_called()
        self.assertFalse((self.root / 'command.lock').exists())

    def test_token_must_be_private_and_not_symlinked(self):
        for mode in (0o644, 0o640):
            self.token.chmod(mode)
            with self.subTest(mode=mode):
                result, remote = self.call(['status'])
                self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_STATE')
                remote.assert_not_called()
        self.token.chmod(0o600)
        link = self.state / 'token-link'
        link.symlink_to(self.token)
        self.seed(self.root / 'remote.json', dict(self.config, token_file=str(link)))
        result, remote = self.call(['status'])
        self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_STATE')
        remote.assert_not_called()

    def test_control_origin_requires_tls_or_exact_loopback_without_credentials(self):
        origins = ('http://example.test', 'http://127.0.0.1.example.test',
                   'https://fixture-user@control.test', 'https://control.test?token=fixture',
                   'https://control.test#fixture', 'https://', 'http://[::1]:0',
                   'http://127.0.0.1:wrong', 'file:///fixture')
        with patch.object(ilink_remote.urllib.request, 'build_opener') as opener:
            for origin in origins:
                with self.subTest(origin=origin), self.assertRaisesRegex(ValueError, 'BOT_REMOTE_UNTRUSTED_ORIGIN'):
                    ilink_remote.request(dict(self.config, control_url=origin), self.access, '/v1/status')
        opener.assert_not_called()

    def test_tls_and_loopback_use_no_environment_proxy(self):
        for origin in ('https://control.test', 'http://127.0.0.1:17680',
                       'http://localhost:17680', 'http://[::1]:17680'):
            with self.subTest(origin=origin):
                response = io.BytesIO(b'{"leader":null}')
                with patch.object(ilink_remote.urllib.request, 'build_opener') as build:
                    build.return_value.open.return_value = response
                    value = ilink_remote.request(dict(self.config, control_url=origin), self.access, '/v1/status')
                self.assertEqual(value, {'leader': None})
                self.assertEqual(build.call_args.args[0].proxies, {})
                self.assertIsInstance(build.call_args.args[1], ilink_remote.NoRedirect)
                request = build.return_value.open.call_args.args[0]
                self.assertEqual(request.get_header('Authorization'), 'Bearer fixture-token-not-a-real-credential')

    def test_redirect_is_not_followed_or_forwarded_a_bearer(self):
        observed = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append(self.path)
                self.send_response(302)
                self.send_header('Location', '/must-not-be-requested')
                self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
        thread.start()
        try:
            config = dict(self.config, control_url='http://127.0.0.1:' + str(server.server_port))
            with self.assertRaisesRegex(ValueError, 'BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'):
                ilink_remote.request(config, self.access, '/fixture-redirect')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(observed, ['/fixture-redirect'])

    def test_malformed_or_oversized_control_response_is_rejected(self):
        for payload in (b'[]', b'{invalid', b'x' * (1024 * 1024 + 1)):
            with self.subTest(size=len(payload)):
                with patch.object(ilink_remote.urllib.request, 'build_opener') as build:
                    build.return_value.open.return_value = io.BytesIO(payload)
                    with self.assertRaises(ValueError):
                        ilink_remote.request(self.config, self.access, '/v1/status')

    def test_updates_have_an_independent_archive_cursor(self):
        before = (self.root / 'account.json').read_bytes()
        responses = [{'items': [{'message_id': 'fixture-one'}], 'next_cursor': 11},
                     {'items': [], 'next_cursor': 11}]
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request', side_effect=responses) as remote:
            first = ilink.main(['updates', '--limit', '1'], self.access)
            second = ilink.main(['updates', '--limit', '2'], self.access)
        self.assertEqual(first['items'][0]['message_id'], 'fixture-one')
        self.assertEqual(second['items'], [])
        self.assertEqual([call.args[3] for call in remote.call_args_list],
                         [{'after': 0, 'limit': 1}, {'after': 11, 'limit': 2}])
        cursor = self.root / 'remote-read-cursor.json'
        self.assertEqual(json.loads(cursor.read_text()), {'cursor': 11})
        self.assertEqual(cursor.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'account.json').read_bytes(), before)
        self.assertFalse(first['personal_inbox'])
        self.assertFalse(first['automatic_reply'])
        local.assert_not_called()

    def test_bad_archive_responses_never_advance_cursor(self):
        path = self.root / 'remote-read-cursor.json'
        self.seed(path, {'cursor': 7})
        before = path.read_bytes()
        for value in ({'items': [], 'next_cursor': 6}, {'items': [], 'next_cursor': True},
                      {'items': [], 'next_cursor': '8'}, {'items': [None], 'next_cursor': 8}, {}):
            with self.subTest(value=value):
                result, _ = self.call(['updates'], value)
                self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_RESPONSE')
                self.assertEqual(path.read_bytes(), before)

    def test_invalid_local_archive_cursor_never_requests(self):
        for value in (-1, True, '7'):
            with self.subTest(value=value):
                self.seed(self.root / 'remote-read-cursor.json', {'cursor': value})
                result, remote = self.call(['updates'])
                self.assertEqual(result['code'], 'BOT_REMOTE_INVALID_CURSOR')
                remote.assert_not_called()

    def test_remote_commands_are_locked_before_cursor_or_upload_work(self):
        lock_path = self.root / 'remote-command.lock'
        with lock_path.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, remote = self.call(['updates'])
        self.assertEqual(result['code'], 'BOT_ACCOUNT_BUSY')
        remote.assert_not_called()

    def test_simultaneous_remote_updates_cannot_overwrite_the_read_cursor(self):
        entered, release = threading.Event(), threading.Event()
        values = []
        def archive(*args):
            entered.set()
            if not release.wait(2):
                raise AssertionError('Fixture did not release the request')
            return {'items': [], 'next_cursor': 9}
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request', side_effect=archive) as remote:
            thread = threading.Thread(target=lambda: values.append(ilink.main(['updates'], self.access)))
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                second = ilink.main(['updates'], self.access)
            finally:
                release.set()
                thread.join(timeout=2)
        self.assertEqual(second['code'], 'BOT_ACCOUNT_BUSY')
        self.assertTrue(values[0]['ok'])
        self.assertEqual(json.loads((self.root / 'remote-read-cursor.json').read_text())['cursor'], 9)
        remote.assert_called_once()
        local.assert_not_called()

    def test_text_reservation_precedes_submit_and_replay_only_reads_status(self):
        def remote(config, access, endpoint, body=None):
            if endpoint == '/v1/notify':
                journal = self.root / 'remote-sends' / 'fixture-text.json'
                self.assertTrue(json.loads(journal.read_text())['fingerprint'])
                self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
                self.assertEqual(body, {'request_id': 'fixture-text', 'text': 'fixture text'})
                return {'id': body['request_id']}
            return {'id': 'fixture-text', 'status': 'accepted', 'delivery_verified': True}
        args = ['send', '--text', 'fixture text', '--request-id', 'fixture-text']
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request', side_effect=remote) as request:
            first = ilink.main(args, self.access)
            replay = ilink.main(args, self.access)
        self.assertEqual([call.args[2] for call in request.call_args_list],
                         ['/v1/notify', '/v1/notify/status', '/v1/notify/status'])
        self.assertTrue(first['ok'])
        self.assertFalse(first['delivery_verified'])
        self.assertFalse(first['automatic_retry'])
        self.assertTrue(replay['replayed'])
        local.assert_not_called()

    def test_unknown_text_submit_is_never_reposted_on_same_id(self):
        def remote(config, access, endpoint, body=None):
            if endpoint == '/v1/notify':
                self.assertTrue((self.root / 'remote-sends' / 'fixture-timeout.json').exists())
            raise ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK')
        args = ['send', '--text', 'fixture text', '--request-id', 'fixture-timeout']
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request', side_effect=remote) as request:
            first = ilink.main(args, self.access)
            second = ilink.main(args, self.access)
        self.assertEqual([call.args[2] for call in request.call_args_list], ['/v1/notify', '/v1/notify/status'])
        self.assertTrue(first['outcome_unknown'])
        self.assertEqual(second['code'], 'BOT_REMOTE_SEND_OUTCOME_UNKNOWN')
        self.assertTrue(second['outcome_unknown'])
        self.assertFalse(second['ok'])
        local.assert_not_called()

    def test_crash_reserved_text_is_only_inspected_after_restart(self):
        args = ['send', '--text', 'fixture text', '--request-id', 'fixture-crash']
        with patch.object(ilink_remote, 'request', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                ilink.main(args, self.access)
        result, request = self.call(args, {'id': 'fixture-crash', 'status': 'unknown'})
        self.assertEqual(request.call_args.args[2], '/v1/notify/status')
        self.assertTrue(result['replayed'])
        self.assertFalse(result['ok'])
        self.assertTrue(result['outcome_unknown'])

    def test_changed_text_under_same_id_is_refused_before_any_request(self):
        args = ['send', '--text', 'fixture original', '--request-id', 'fixture-conflict']
        self.call(args, side_effect=ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'))
        result, request = self.call(['send', '--text', 'fixture changed', '--request-id', 'fixture-conflict'])
        self.assertEqual(result['code'], 'BOT_REQUEST_ID_CONFLICT')
        request.assert_not_called()

    def test_send_validation_precedes_remote_network(self):
        for args in (['send'], ['send', '--text', ' '], ['send', '--text', 'fixture'],
                     ['send', '--text', 'fixture', '--request-id', '../escape']):
            with self.subTest(args=args):
                result, request = self.call(args)
                self.assertFalse(result['ok'])
                request.assert_not_called()

    def test_missing_malformed_or_wrong_id_status_stays_unknown(self):
        args = ['send', '--text', 'fixture text', '--request-id', 'fixture-status']
        self.call(args, side_effect=ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'))
        for value in ({}, {'status': 'delivered'}, {'status': 'accepted', 'id': 'another-fixture'}):
            with self.subTest(value=value):
                result, request = self.call(args, value)
                self.assertEqual(request.call_args.args[2], '/v1/notify/status')
                self.assertEqual(result['code'], 'BOT_REMOTE_SEND_OUTCOME_UNKNOWN')
                self.assertFalse(result['ok'])
                self.assertTrue(result['outcome_unknown'])
                self.assertFalse(result['delivery_verified'])

    def test_rejected_authority_status_is_not_reported_as_success(self):
        args = ['send', '--text', 'fixture text', '--request-id', 'fixture-rejected']
        self.call(args, side_effect=ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'))
        result, request = self.call(args, {'id': 'fixture-rejected', 'status': 'rejected'})
        self.assertEqual(request.call_args.args[2], '/v1/notify/status')
        self.assertEqual(result['code'], 'BOT_REMOTE_SEND_REJECTED')
        self.assertFalse(result['ok'])
        self.assertFalse(result['outcome_unknown'])

    def test_private_text_file_is_supported_without_content_in_the_journal(self):
        path = self.state / 'fixture-message.txt'
        self.access.private_write(path, 'fixture private text')
        result, request = self.call(['send', '--text-file', str(path), '--request-id', 'fixture-from-file'],
                                    side_effect=[{'id': 'fixture-from-file'}, {'id': 'fixture-from-file', 'status': 'pending'}])
        self.assertTrue(result['ok'])
        self.assertEqual(request.call_args_list[0].args[3]['text'], 'fixture private text')
        journal = (self.root / 'remote-sends' / 'fixture-from-file.json').read_text()
        self.assertNotIn('fixture private text', journal)

    def media(self):
        path = self.state / 'fixture.txt'
        path.write_bytes(b'fixture bytes')
        item = {'type': 4, 'file_item': {'file_name': path.name, 'len': str(path.stat().st_size),
                                      'media': {'aes_key': 'fixture-key', 'encrypt_query_param': 'fixture-reference'}}}
        return path, item

    def test_media_reservation_precedes_upload_and_unknown_upload_is_not_retried(self):
        path, _ = self.media()
        def upload(*args):
            record = self.root / 'remote-uploads' / 'fixture-upload.json'
            self.assertTrue(json.loads(record.read_text())['fingerprint'])
            self.assertEqual(record.stat().st_mode & 0o777, 0o600)
            raise ilink.BotError('BOT_MEDIA_TIMEOUT')
        args = ['send', '--file', str(path), '--request-id', 'fixture-upload']
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request') as remote, patch.object(ilink_media, 'upload', side_effect=upload) as mocked:
            first = ilink.main(args, self.access)
            replay = ilink.main(args, self.access)
        mocked.assert_called_once()
        remote.assert_not_called()
        local.assert_not_called()
        self.assertTrue(first['outcome_unknown'])
        self.assertEqual(replay['code'], 'BOT_REMOTE_UPLOAD_UNKNOWN_NO_RETRY')
        self.assertTrue(replay['outcome_unknown'])
        self.assertFalse(replay['automatic_retry'])

    def test_media_upload_is_reused_and_unknown_submit_only_checks_status(self):
        path, item = self.media()
        def remote(config, access, endpoint, body=None):
            if endpoint == '/v1/notify/media':
                self.assertEqual(body['items'], [item])
                self.assertTrue((self.root / 'remote-sends' / 'fixture-media.json').exists())
                raise ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK')
            return {'id': 'fixture-media', 'status': 'accepted'}
        args = ['send', '--file', str(path), '--request-id', 'fixture-media']
        with patch.object(ilink, 'request') as local, patch.object(ilink_remote, 'request', side_effect=remote) as request, patch.object(ilink_media, 'upload', return_value=item) as upload:
            first = ilink.main(args, self.access)
            replay = ilink.main(args, self.access)
        upload.assert_called_once()
        self.assertEqual([call.args[2] for call in request.call_args_list], ['/v1/notify/media', '/v1/notify/status'])
        self.assertTrue(first['outcome_unknown'])
        self.assertTrue(replay['replayed'])
        self.assertFalse(replay['delivery_verified'])
        self.assertEqual(len(replay['attachment_id']), 64)
        self.assertNotIn('fixture-key', json.dumps(replay))
        local.assert_not_called()

    def test_crashed_upload_reservation_is_never_uploaded_again(self):
        path, _ = self.media()
        args = ['send', '--file', str(path), '--request-id', 'fixture-upload-crash']
        with patch.object(ilink_media, 'upload', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                ilink.main(args, self.access)
        with patch.object(ilink_media, 'upload') as upload:
            result, request = self.call(args)
        self.assertEqual(result['code'], 'BOT_REMOTE_UPLOAD_UNKNOWN_NO_RETRY')
        self.assertTrue(result['outcome_unknown'])
        upload.assert_not_called()
        request.assert_not_called()

    def test_definite_upload_auth_failure_is_retained_without_false_unknown(self):
        path, _ = self.media()
        args = ['send', '--file', str(path), '--request-id', 'fixture-upload-auth']
        with patch.object(ilink_media, 'upload', side_effect=ilink.BotError('BOT_AUTH_REQUIRED')) as upload:
            first, request = self.call(args)
            replay, replay_request = self.call(args)
        upload.assert_called_once()
        request.assert_not_called()
        replay_request.assert_not_called()
        self.assertEqual(first['code'], 'BOT_AUTH_REQUIRED')
        self.assertFalse(first['outcome_unknown'])
        self.assertEqual(replay['code'], 'BOT_AUTH_REQUIRED')
        self.assertTrue(replay['replayed'])

    def test_missing_media_sdk_is_a_structured_error_not_an_unhandled_crash(self):
        path, _ = self.media()
        with patch.object(ilink_media, 'upload', side_effect=ImportError('fixture unavailable SDK')):
            result, request = self.call(['send', '--file', str(path), '--request-id', 'fixture-sdk'])
        self.assertEqual(result['code'], 'BOT_SDK_INSTALL_REQUIRED')
        self.assertFalse(result['outcome_unknown'])
        request.assert_not_called()

    def test_changed_media_under_same_id_is_refused_before_upload_or_enqueue(self):
        path, item = self.media()
        with patch.object(ilink_media, 'upload', return_value=item):
            self.call(['send', '--file', str(path), '--request-id', 'fixture-file-conflict'],
                      side_effect=ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK'))
        path.write_bytes(b'changed fixture bytes')
        with patch.object(ilink_media, 'upload') as upload:
            result, request = self.call(['send', '--file', str(path), '--request-id', 'fixture-file-conflict'])
        self.assertEqual(result['code'], 'BOT_REQUEST_ID_CONFLICT')
        upload.assert_not_called()
        request.assert_not_called()

    def test_bad_remote_binding_prevents_even_media_upload(self):
        path, _ = self.media()
        self.seed(self.root / 'remote.json', dict(self.config, control_url='http://example.test'))
        with patch.object(ilink_media, 'upload') as upload:
            result, request = self.call(['send', '--file', str(path), '--request-id', 'fixture-bad-origin'])
        self.assertEqual(result['code'], 'BOT_REMOTE_UNTRUSTED_ORIGIN')
        upload.assert_not_called()
        request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
