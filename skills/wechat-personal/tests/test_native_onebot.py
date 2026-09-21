import copy
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
import native_onebot as onebot


def completed():
    return {'status': 'trial_finished', 'detached': True, 'client_running_untraced': True,
            'recipient_delivery_verified': False, 'completed_at': 1700000000.25,
            'worker': {'worker_done': True, 'native_roundtrip_verified': True,
                       'submission_entered': True, 'task_id': 42, 'callback_count': 1,
                       'callback_destroyed': 1, 'live_callbacks': 0,
                       'error_type': 0, 'error_code': 0, 'failure': 0}}


def message(request_id='test-request-1', text='你好', recipient='filehelper'):
    return {'action': 'send_message', 'params': {'detail_type': 'private',
            'user_id': recipient, 'message': text, 'wechat.request_id': request_id}}


class Sender:
    pending = None

    def __init__(self, result=None):
        self.calls = []
        self.result = completed() if result is None else result

    def __call__(self, text, request_id, recipient, timeout):
        self.calls.append((text, request_id, recipient, timeout))
        return copy.deepcopy(self.result)


class AdapterTests(unittest.TestCase):
    def test_configured_target_is_exact_and_version_reports_current_scope(self):
        sender = Sender()
        target = 'gh_onebot_fixture@im.bot'
        configured = [target, target]
        adapter = onebot.Adapter(sender, allowed_recipients=configured)
        configured.append('wxid_added_after_start')
        version = adapter.action({'action': 'get_version', 'params': {}})['data']
        self.assertEqual(version['wechat.allowed_recipients'], ['filehelper', target])
        self.assertFalse(version['wechat.events_enabled'])
        self.assertEqual(adapter.action(message(recipient=target))['status'], 'ok')
        self.assertEqual(sender.calls, [('你好', 'test-request-1', target, 90)])
        self.assertEqual(adapter.action(message('filehelper-request'))['status'], 'ok')
        self.assertEqual(sender.calls[-1][2], 'filehelper')
        for unknown in ('wxid_added_after_start', target.upper(), 'ClawBot', [], None):
            with self.subTest(target=unknown):
                self.assertEqual(adapter.action(message('not-enabled-request', recipient=unknown))['retcode'], 10003)
        self.assertEqual(len(sender.calls), 2)

    def test_replay_requires_both_same_content_and_same_target(self):
        sender = Sender()
        target = 'wxid_onebot_fixture'
        adapter = onebot.Adapter(sender, allowed_recipients=[target])
        original = message(recipient=target)
        first = adapter.action(original)
        for request in (message(), message(text='changed', recipient=target),
                        message(text='changed')):
            with self.subTest(request=request):
                result = adapter.action(request)
                self.assertEqual(result['retcode'], 10003)
                self.assertIn('REQUEST_ID_CONFLICT', result['message'])
        segmented = message(text=[{'type': 'text', 'data': {'text': '你'}},
                                  {'type': 'text', 'data': {'text': '好'}}], recipient=target)
        self.assertEqual(adapter.action(segmented), first)
        self.assertEqual(adapter.action(original), first)
        self.assertEqual(len(sender.calls), 1)

    def test_allowlist_rejects_display_names_groups_and_malformed_native_ids(self):
        for target in ('微信ClawBot', 'display name', '123@chatroom', '123@CHATROOM',
                       '', 'x' * 129, 'wxid_name\n', 'wxid_name\0', '.name', '*', None):
            with self.subTest(target=target), self.assertRaises(ValueError):
                onebot.Adapter(Sender(), allowed_recipients=[target])
        with self.assertRaises(ValueError):
            onebot.Adapter(Sender(), allowed_recipients='filehelper')
        adapter = onebot.Adapter(Sender(), allowed_recipients=['x' * 128])
        self.assertIn('x' * 128, adapter.allowed_recipients)
        request = message()
        request['params']['detail_type'] = 'group'
        self.assertEqual(adapter.action(request)['retcode'], 10003)
        self.assertEqual(onebot.Adapter(Sender()).allowed_recipients, {'filehelper'})

    def test_segment_join_echo_and_stable_local_id_replay(self):
        sender = Sender()
        adapter = onebot.Adapter(sender)
        request = message(text=[{'type': 'text', 'data': {'text': '你好'}},
                                {'type': 'text', 'data': {'text': '世界'}}])
        request['echo'] = 'first'
        first = adapter.action(request)
        request['echo'] = 'second'
        second = adapter.action(request)
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['data'], second['data'])
        self.assertEqual(second['echo'], 'second')
        self.assertEqual(first['data']['message_id'], 'wechat-local:test-request-1')
        self.assertEqual(first['data']['wechat.id_kind'], 'local_request')
        self.assertEqual(first['data']['wechat.native_task_id'], 42)
        self.assertFalse(first['data']['wechat.recipient_delivery_verified'])
        self.assertEqual(first['data']['time'], 1700000000.25)
        self.assertEqual(len(sender.calls), 1)
        self.assertEqual(sender.calls[0][:3], ('你好世界', 'test-request-1', 'filehelper'))
        self.assertEqual(adapter.action(message(text='changed'))['retcode'], 10003)
        self.assertEqual(len(sender.calls), 1)

    def test_rejects_invalid_targets_media_and_missing_request_id_without_sending(self):
        sender = Sender()
        adapter = onebot.Adapter(sender)
        missing = message()
        del missing['params']['wechat.request_id']
        missing['echo'] = 'not-an-authorization-key'
        wrong_target = message()
        wrong_target['params']['user_id'] = 'other-user'
        cases = [(None, 10001), ({'action': 'send_message'}, 10001),
                 ({**message(), 'echo': float('nan')}, 10001),
                 ({'action': 'delete_message', 'params': {}}, 10002),
                 (missing, 10003), (wrong_target, 10003),
                 (message(text=[{'type': 'image', 'data': {'file_id': 'image'}}]), 10005),
                 (message(text=[{'type': 'text', 'data': {}}]), 10006),
                 (message(text='你' * 342), 10003), (message(text='x\0y'), 10003),
                 (message(text='\ud800'), 10003)]
        for request, code in cases:
            with self.subTest(request=request):
                self.assertEqual(adapter.action(request)['retcode'], code)
        self.assertEqual(sender.calls, [])

    def test_uncertain_or_dirty_native_completion_is_never_successful_or_retried(self):
        variants = [('detached', False), ('client_running_untraced', False),
                    ('worker_done', False), ('native_roundtrip_verified', False),
                    ('submission_entered', False), ('callback_count', 0),
                    ('callback_destroyed', 0), ('live_callbacks', 1),
                    ('error_type', 1), ('error_code', -1), ('failure', 2)]
        for key, value in variants:
            with self.subTest(key=key):
                result = completed()
                target = result if key in result else result['worker']
                target[key] = value
                sender = Sender(result)
                adapter = onebot.Adapter(sender)
                first = adapter.action(message())
                self.assertEqual(first['status'], 'failed')
                self.assertEqual(first['data']['wechat.request_id'], 'test-request-1')
                self.assertEqual(first, adapter.action(message()))
                self.assertEqual(adapter.action(message('test-request-2'))['retcode'], 36001)
                self.assertEqual(len(sender.calls), 1)

    def test_send_cap_does_not_prevent_readonly_actions_or_replay(self):
        sender = Sender()
        adapter = onebot.Adapter(sender, max_sends=1)
        self.assertEqual(adapter.action(message())['status'], 'ok')
        self.assertEqual(adapter.action(message('test-request-2'))['retcode'], 36001)
        self.assertEqual(adapter.action(message())['status'], 'ok')
        self.assertEqual(adapter.action({'action': 'get_supported_actions', 'params': {}})['data'],
                         onebot.SUPPORTED)
        self.assertEqual(adapter.action({'action': 'get_version', 'params': {}})['data']['onebot_version'], '12')
        self.assertEqual(len(sender.calls), 1)
        with self.assertRaises(ValueError):
            onebot.Adapter(sender, max_sends=11)

    def test_subprocess_timeout_keeps_pid_and_never_terminates_native_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            sender = onebot.BackendProcess(Path(tmp), (os.getuid(), os.getgid()))
            with patch.object(onebot.subprocess, 'Popen') as spawn:
                process = spawn.return_value
                process.pid = 98765
                process.communicate.side_effect = subprocess.TimeoutExpired('hidden', 1)
                result = sender('private text', 'timeout-test', 'filehelper', 1)
                self.assertEqual(result['status'], 'adapter_timeout')
                self.assertEqual(sender.pending['pid'], 98765)
                self.assertEqual(sender.pending['request_id'], 'timeout-test')
                self.assertNotIn('private text', repr(spawn.call_args))
                process.kill.assert_not_called()
                process.terminate.assert_not_called()
                with self.assertRaises(RuntimeError):
                    sender('second', 'timeout-second', 'filehelper', 1)


class LoopbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'state/session.json'
        self.sender = Sender()
        self.adapter = onebot.Adapter(self.sender, allowed_recipients=['wxid_onebot_fixture'])
        self.server = onebot.SessionServer(self.adapter, self.path, duration=10,
                                          owner=(os.getuid(), os.getgid()))
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.run)
        self.thread.start()

    def tearDown(self):
        self.server.stop_requested = True
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())
        self.temp.cleanup()

    def http(self, body, token=None, path='/', content_type='application/json', method='POST'):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        headers = {'Content-Type': content_type}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token
        conn.request(method, path, body=body, headers=headers)
        reply = conn.getresponse()
        status, result = reply.status, json.loads(reply.read())
        conn.close()
        return status, result

    def test_private_endpoint_call_and_http_error_contract(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        result = onebot.call({**message(), 'echo': 'roundtrip'}, self.path, timeout=3)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['echo'], 'roundtrip')
        token = self.server.token
        self.assertEqual(self.http('{}')[0], 401)
        self.assertEqual(self.http('{}', 'wrong')[0], 401)
        self.assertEqual(self.http('{}', token, path='/unknown')[0], 404)
        self.assertEqual(self.http('{}', token, content_type='application/msgpack')[0], 415)
        self.assertEqual(self.http('{}', token, method='GET')[0], 405)
        status, result = self.http('{', token)
        self.assertEqual((status, result['retcode']), (200, 10001))
        status, result = self.http(json.dumps({'action': 'unsupported', 'params': {}, 'echo': ''}), token)
        self.assertEqual((status, result['retcode'], result['echo']), (200, 10002, ''))
        self.assertEqual(len(self.sender.calls), 1)

    def test_http_target_scope_and_target_aware_replay(self):
        target = 'wxid_onebot_fixture'
        state = json.loads(self.path.read_text())
        version = onebot.call({'action': 'get_version', 'params': {}}, self.path, timeout=3)
        self.assertEqual(state['allowed_recipients'], ['filehelper', target])
        self.assertEqual(version['data']['wechat.allowed_recipients'], state['allowed_recipients'])
        request = message(recipient=target)
        first = onebot.call(request, self.path, timeout=3)
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(onebot.call(request, self.path, timeout=3), first)
        conflict = onebot.call(message(), self.path, timeout=3)
        self.assertIn('REQUEST_ID_CONFLICT', conflict['message'])
        unknown = onebot.call(message('unknown-target', recipient='wxid_unknown_fixture'), self.path, timeout=3)
        self.assertEqual(unknown['retcode'], 10003)
        self.assertEqual(len(self.sender.calls), 1)
        self.assertEqual(self.sender.calls[0][:3], ('你好', 'test-request-1', target))
        self.assertLessEqual(self.sender.calls[0][3], 10)

    def test_deadline_closes_socket_and_revokes_session_token(self):
        self.server.deadline = time.monotonic() + .05
        self.thread.join(2)
        self.assertFalse(self.thread.is_alive())
        state = json.loads(self.path.read_text())
        self.assertEqual(state['status'], 'expired')
        self.assertNotIn('access_token', state)
        self.assertEqual(state['allowed_recipients'], ['filehelper', 'wxid_onebot_fixture'])
        with self.assertRaises(OSError):
            socket.create_connection(('127.0.0.1', self.port), timeout=.2)
        with self.assertRaises(ValueError):
            onebot.call(message(), self.path, timeout=1)

    def test_request_body_cannot_cross_deadline_and_then_send(self):
        body = json.dumps(message()).encode()
        client = socket.create_connection(('127.0.0.1', self.port), timeout=2)
        with client:
            headers = ('POST / HTTP/1.1\r\nHost: 127.0.0.1\r\n'
                       'Authorization: Bearer ' + self.server.token + '\r\n'
                       'Content-Type: application/json\r\nContent-Length: ' + str(len(body))
                       + '\r\n\r\n').encode()
            # Wait until the handler is blocked reading the body, then expire it.
            entered = threading.Event()
            original_read = onebot.Handler.do_POST

            def wrapped(handler):
                entered.set()
                return original_read(handler)

            with patch.object(onebot.Handler, 'do_POST', wrapped):
                client.sendall(headers)
                self.assertTrue(entered.wait(1))
                self.server.deadline = time.monotonic() - .01
                client.sendall(body)
                received = bytearray()
                while chunk := client.recv(4096):
                    received.extend(chunk)
            payload = json.loads(bytes(received).split(b'\r\n\r\n', 1)[1])
            self.assertEqual(payload['retcode'], 36001)
        self.assertEqual(self.sender.calls, [])

    def test_single_session_lock_and_pending_shutdown_state(self):
        with self.assertRaises(BlockingIOError):
            onebot.SessionServer(onebot.Adapter(Sender()), self.path, owner=(os.getuid(), os.getgid()))
        self.sender.pending = {'pid': 999999, 'request_id': 'uncertain-test'}
        self.server.stop_requested = True
        self.thread.join(2)
        state = json.loads(self.path.read_text())
        self.assertEqual(state['status'], 'stopped_pending_backend')
        self.assertEqual(state['pending_backend']['request_id'], 'uncertain-test')
        self.assertNotIn('access_token', state)
        with self.assertRaisesRegex(ValueError, 'pending native operation'):
            onebot.SessionServer(onebot.Adapter(Sender()), self.path, owner=(os.getuid(), os.getgid()))


class CommandTests(unittest.TestCase):
    def test_repeatable_recipient_flags_reach_new_session_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'session.json'
            with patch.object(onebot, 'owner_identity', return_value=(1000, 1000, Path(tmp))), \
                    patch.object(onebot, 'default_session', return_value=path), \
                    patch.object(onebot.os, 'geteuid', return_value=0), \
                    patch.object(onebot.os, 'umask'), \
                    patch.object(onebot.signal, 'signal'), \
                    patch.object(onebot, 'SessionServer') as server, \
                    patch('builtins.print'):
                self.assertEqual(onebot.main(['serve', '--allow-recipient', 'wxid_onebot_fixture',
                                             '--allow-recipient', 'gh_onebot_fixture@im.bot']), 0)
            adapter = server.call_args.args[0]
            self.assertEqual(adapter.allowed_recipients,
                             {'filehelper', 'wxid_onebot_fixture', 'gh_onebot_fixture@im.bot'})
            self.assertEqual(adapter.sender.process, None)
            server.return_value.run.assert_called_once_with()
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
