"""Offline request regression: no WeChat process, debugger, sudo or network."""
from contextlib import ExitStack, nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import native_send_candidate as candidate
import native_send_probe as probe


def decode_message(data):
    """Decode protobuf wire fields, checking lengths instead of byte substrings."""
    fields = {}
    offset = 0

    def read_varint():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(data):
                raise AssertionError('truncated protobuf varint')
            byte = data[offset]
            offset += 1
            value |= (byte & 0x7f) << shift
            if byte < 0x80:
                return value
        raise AssertionError('oversized protobuf varint')

    while offset < len(data):
        tag = read_varint()
        number, wire = tag >> 3, tag & 7
        if not number:
            raise AssertionError('protobuf field zero')
        if wire == 0:
            value = read_varint()
        elif wire == 2:
            length = read_varint()
            end = offset + length
            if end > len(data):
                raise AssertionError('truncated length-delimited field')
            value = data[offset:end]
            offset = end
        else:
            raise AssertionError(f'unexpected protobuf wire type {wire}')
        fields.setdefault(number, []).append(value)
    return fields


def decode_text_request(payload):
    envelope = decode_message(payload)
    if set(envelope) != {1, 2} or envelope[1] != [1] or len(envelope[2]) != 1:
        raise AssertionError('expected exactly one text message')
    body = decode_message(envelope[2][0])
    if set(body) != {1, 2, 3, 4, 5, 6} or any(len(values) != 1 for values in body.values()):
        raise AssertionError('unexpected message fields or repeated values')
    recipient = decode_message(body[1][0])
    if set(recipient) != {1} or len(recipient[1]) != 1:
        raise AssertionError('expected exactly one recipient')
    return {'recipient': recipient[1][0].decode('utf-8'),
            'text': body[2][0].decode('utf-8'), 'type': body[3][0],
            'timestamp': body[4][0], 'clientmsgid': body[5][0],
            'source': body[6][0]}


class NativeTextPayloadTests(unittest.TestCase):
    def test_unicode_multiline_and_recipient_survive_real_wire_decode(self):
        text = '第一行：你好，微信 👋\nsecond line\r\n末行\t✓'
        recipient = 'wxid_synthetic-recipient.0001'
        decoded = decode_text_request(candidate.make_payload(
            1700000000, text=text, request_id='unicode-lines-0001', recipient=recipient))
        self.assertEqual(decoded['text'], text)
        self.assertEqual(decoded['recipient'], recipient)
        self.assertEqual(decoded['type'], 1)
        self.assertEqual(decoded['timestamp'], 1700000000)
        self.assertEqual(decoded['source'], b'<msgsource/>')
        self.assertGreater(decoded['clientmsgid'], 0)
        self.assertLessEqual(decoded['clientmsgid'], 0xffffffff)

    def test_clientmsgid_tracks_request_id_and_default_recipient_is_filehelper(self):
        original = decode_text_request(candidate.make_payload(
            1700000000, text='原始文字', request_id='client-id-request-0001'))
        later = decode_text_request(candidate.make_payload(
            1700000100, text='different text', request_id='client-id-request-0001',
            recipient='wxid_other_test_recipient'))
        other = decode_text_request(candidate.make_payload(
            1700000000, text='原始文字', request_id='client-id-request-0002'))
        self.assertEqual(original['recipient'], 'filehelper')
        self.assertEqual(original['clientmsgid'], later['clientmsgid'])
        self.assertNotEqual(original['clientmsgid'], other['clientmsgid'])
        for decoded in (original, later, other):
            self.assertTrue(1 <= decoded['clientmsgid'] <= 0xffffffff)

    def test_text_uses_utf8_bytes_and_native_id_uses_ascii_boundaries(self):
        text, recipient = '😀' * 256, 'a' * 128
        decoded = decode_text_request(candidate.make_payload(
            0xffffffff, text=text, request_id='boundary-request', recipient=recipient))
        self.assertEqual(decoded['text'], text)
        self.assertEqual(decoded['recipient'], recipient)
        self.assertEqual(decoded['timestamp'], 0xffffffff)
        invalid = {'text': ('', 'a' * 1025, '😀' * 257, 'nul\0text', 123),
                   'recipient': ('', 'a' * 129, '显示名', 'wxid with space', 'wxid/path',
                                 'nul\0recipient', None, 123),
                   'request_id': ('', 'abc', 'r' * 81, '../escape', 'space id', '中文编号')}
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value_type=type(value).__name__, size=len(str(value))):
                    kwargs = {'text': 'valid text', 'request_id': 'valid-request', 'recipient': 'filehelper'}
                    kwargs[field] = value
                    with self.assertRaises(ValueError):
                        candidate.make_payload(1700000000, **kwargs)


class NativeTextRequestTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.uid, self.gid = os.getuid(), os.getgid()
        self.owner = SimpleNamespace(pw_dir=str(self.home), pw_uid=self.uid, pw_gid=self.gid)
        self.stack.enter_context(patch.object(candidate.pwd, 'getpwuid', return_value=self.owner))
        self.stack.enter_context(patch.dict(os.environ, {'SUDO_UID': str(self.uid)}))
        self.euid = self.stack.enter_context(patch.object(candidate.os, 'geteuid', return_value=self.uid))
        self.stack.enter_context(patch.object(probe, 'desktop_identity', side_effect=lambda *_: nullcontext()))
        self.stack.enter_context(patch.object(candidate.os, 'chown'))
        self.stack.enter_context(patch.object(candidate, 'process_running_untraced', return_value=True))
        self.prepare = self.stack.enter_context(patch.object(probe, 'run_desktop_preparation',
                                                            side_effect=self.prepare_fake_client))
        self.compile = self.stack.enter_context(patch.object(candidate, 'compile_helper',
                                                            side_effect=self.prepare_fake_helper))
        self.injection_configs = []
        self.inject = self.stack.enter_context(patch.object(candidate, 'run_injection',
                                                           side_effect=self.finish_fake_request))
        # Fail closed even if a future implementation bypasses these boundaries.
        self.stack.enter_context(patch.object(candidate.subprocess, 'Popen',
                                             side_effect=AssertionError('a test tried to start a subprocess')))
        self.stack.enter_context(patch.object(candidate.subprocess, 'run',
                                             side_effect=AssertionError('a test tried to run a subprocess')))
        self.target = self.home / 'fake-proc' / '424242'
        self.target.mkdir(parents=True)
        (self.target / 'exe').symlink_to(self.home / 'synthetic' / 'wechat')
        (self.target / 'stat').write_text('424242 (wechat) ' + ' '.join(['S'] + ['0'] * 18 + ['12345']))
        real_iterdir = Path.iterdir

        def isolated_iterdir(path):
            if path == Path('/proc'):
                return iter([self.target])
            return real_iterdir(path)

        self.proc_scan = self.stack.enter_context(patch.object(Path, 'iterdir', autospec=True,
                                                              side_effect=isolated_iterdir))

    @staticmethod
    def prepare_fake_client(target, work, uid, gid):
        (work / 'wechat.elf').write_bytes(b'not an executable')
        return {'load_bias': 4096, 'binary_sha256': 'synthetic-build'}

    @staticmethod
    def prepare_fake_helper(work, uid, gid):
        helper = work / 'helper.so'
        helper.write_bytes(b'not a shared library')
        return helper

    def finish_fake_request(self, cfg, work):
        self.injection_configs.append(dict(cfg))
        return {'status': 'trial_finished', 'detached': True, 'armed': True,
                'worker': {'worker_done': True, 'native_roundtrip_verified': True,
                           'callback_count': 1, 'live_callbacks': 0,
                           'error_type': 0, 'error_code': 0}}

    def send_request(self, request_id='offline-request-0001', text='离线测试\n正文', recipient='filehelper'):
        return candidate.trial(True, text=text, request_id=request_id, recipient=recipient)

    def assert_no_process_work(self):
        self.prepare.assert_not_called()
        self.compile.assert_not_called()
        self.inject.assert_not_called()
        self.proc_scan.assert_not_called()

    def test_persisted_success_replays_without_privilege_or_another_injection(self):
        self.euid.return_value = 0
        text, recipient = '真实构造\n第二行 😀', 'wxid_synthetic_recipient'
        first = self.send_request(text=text, recipient=recipient)
        cfg = self.injection_configs[0]
        decoded = decode_text_request(bytes.fromhex(cfg['payload_hex']))
        self.assertEqual((decoded['text'], decoded['recipient']), (text, recipient))
        self.assertTrue(cfg['send'])
        result_path = Path(first['result_path'])
        persisted = json.loads(result_path.read_text())
        self.assertEqual(persisted['request_id'], 'offline-request-0001')
        self.assertFalse(persisted['recipient_delivery_verified'])
        self.assertEqual(result_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(result_path.parent.stat().st_mode & 0o777, 0o700)
        request = json.loads((result_path.parent / 'request.json').read_text())
        self.assertEqual(request['recipient'], recipient)
        self.assertNotIn(text, (result_path.parent / 'request.json').read_text())
        persisted['persisted_marker'] = 'read this result from disk'
        candidate.save(result_path, persisted)
        self.euid.return_value = self.uid
        replay = self.send_request(text=text, recipient=recipient)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['persisted_marker'], persisted['persisted_marker'])
        self.assertEqual(replay['request_id'], first['request_id'])
        self.inject.assert_called_once()
        self.prepare.assert_called_once()
        self.compile.assert_called_once()

    def test_same_request_id_rejects_changed_text_or_recipient(self):
        self.euid.return_value = 0
        self.send_request()
        self.euid.return_value = self.uid
        for text, recipient in (('不同正文', 'filehelper'), ('离线测试\n正文', 'wxid_other')):
            with self.subTest(recipient=recipient, changed_text=text != '离线测试\n正文'):
                with self.assertRaisesRegex(ValueError, 'REQUEST_ID_CONFLICT'):
                    self.send_request(text=text, recipient=recipient)
        self.inject.assert_called_once()
        self.prepare.assert_called_once()

    def test_new_request_without_root_fails_before_reservation_or_process_work(self):
        with self.assertRaisesRegex(ValueError, 'sudo|root'):
            self.send_request()
        self.assert_no_process_work()
        self.assertFalse((self.home / '.local').exists())

    def test_same_request_id_rejects_check_send_mode_change(self):
        for send in (False, True):
            with self.subTest(initial_send=send):
                self.inject.reset_mock()
                self.prepare.reset_mock()
                request_id = 'mode-request-' + str(send)
                self.euid.return_value = 0
                candidate.trial(send, text='same body', request_id=request_id)
                self.euid.return_value = self.uid
                with self.assertRaisesRegex(ValueError, 'REQUEST_ID_CONFLICT'):
                    candidate.trial(not send, text='same body', request_id=request_id)
                self.inject.assert_called_once()
                self.prepare.assert_called_once()

    def test_preparation_failure_is_persisted_and_cannot_start_again(self):
        self.euid.return_value = 0
        self.prepare.side_effect = ValueError('synthetic preparation failure')
        first = self.send_request()
        self.assertEqual(first['status'], 'local_failure')
        self.assertEqual(first['stage'], 'prepare_executable')
        self.assertFalse(first['automatic_retry_allowed'])
        self.assertIn('synthetic preparation failure', first['error'])
        self.prepare.side_effect = self.prepare_fake_client
        self.euid.return_value = self.uid
        replay = self.send_request()
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['status'], 'local_failure')
        self.prepare.assert_called_once()
        self.compile.assert_not_called()
        self.inject.assert_not_called()

    def test_interrupted_request_without_result_is_not_started_again(self):
        self.euid.return_value = 0
        self.inject.side_effect = KeyboardInterrupt('synthetic interrupted caller')
        with self.assertRaises(KeyboardInterrupt):
            self.send_request()
        self.euid.return_value = self.uid
        with self.assertRaisesRegex(ValueError, 'REQUEST_PENDING'):
            self.send_request()
        self.prepare.assert_called_once()
        self.compile.assert_called_once()
        self.inject.assert_called_once()

    def test_persisted_pending_results_are_replayed_without_starting_another_worker(self):
        for status in ('debugger_still_running', 'worker_pending', 'callback_pending'):
            with self.subTest(status=status):
                self.inject.reset_mock()
                self.prepare.reset_mock()
                self.compile.reset_mock()
                self.euid.return_value = 0
                self.inject.side_effect = lambda cfg, work: {'status': status, 'automatic_retry_allowed': False}
                first = self.send_request(request_id='pending-' + status)
                self.euid.return_value = self.uid
                replay = self.send_request(request_id='pending-' + status)
                self.assertEqual(replay['status'], status)
                self.assertEqual(replay['result_path'], first['result_path'])
                self.assertTrue(replay['replayed'])
                self.assertFalse(replay['automatic_retry_allowed'])
                self.inject.assert_called_once()
                self.prepare.assert_called_once()
                self.compile.assert_called_once()

    def test_status_reads_latest_worker_without_mutation_or_privilege(self):
        self.euid.return_value = 0
        first = self.send_request()
        work = Path(first['result_path']).parent
        worker = {'worker_done': True, 'callback_count': 1, 'error_code': -123,
                  'live_callbacks': 0, 'failure': 'synthetic callback failure'}
        candidate.save(work / 'worker.json', worker)
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in work.iterdir()}
        for mocked in (self.prepare, self.compile, self.inject, self.proc_scan):
            mocked.reset_mock()
        self.euid.return_value = self.uid
        status = candidate.inspect_trial('offline-request-0001')
        self.assertTrue(status['read_only'])
        self.assertEqual(status['worker'], worker)
        self.assertFalse(status['recipient_delivery_verified'])
        self.assert_no_process_work()
        after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in work.iterdir()}
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
