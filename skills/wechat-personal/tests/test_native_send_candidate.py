import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
import native_send_candidate as candidate


class NativeCandidateTests(unittest.TestCase):
    def test_poll_check_accepts_syscall_evidence_and_rejects_other_waits(self):
        for syscall in (7, 232, 271, 281, 441):
            self.assertTrue(candidate.classify_poll_stop(syscall, b'\x0f\x05', '/usr/lib/libc.so.6')['verified'])
        for syscall, code, library in ((202, b'\x0f\x05', '/usr/lib/libc.so.6'),
                                      (271, b'xx', '/usr/lib/libc.so.6'),
                                      (271, b'\x0f\x05', '/tmp/unrelated.so')):
            self.assertFalse(candidate.classify_poll_stop(syscall, code, library)['verified'])

    def test_only_proven_pre_call_failure_can_be_archived_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = candidate.reserve_trial_work(root, 'once')
            safe = {'status': 'injection_failed', 'detached': True, 'client_running_untraced': True,
                    'launch_call_entered': False, 'launch_returned': False,
                    'error': 'main_thread_not_idle_in_poll: no inferior call made'}
            candidate.save(work/'result.json', safe)
            candidate.save(work/'debugger-process.json', {'pid': 999999999})
            candidate.reserve_trial_work(root, 'once')
            self.assertEqual(len(list(root.glob('once-preflight-*'))), 1)
            candidate.save(work/'result.json', {**safe, 'launch_call_entered': True})
            candidate.save(work/'debugger-process.json', {'pid': 999999999})
            with self.assertRaisesRegex(ValueError, 'possibly submitted'):
                candidate.reserve_trial_work(root, 'once')

    def test_payload_is_one_bounded_filehelper_text(self):
        payload = candidate.make_payload(1700000000)
        self.assertEqual(payload[:2], b'\x08\x01')
        self.assertEqual(payload.count(b'\x0a\x0c\x0a\x0afilehelper'), 1)
        self.assertIn(candidate.REQUEST_ID.encode(), payload)
        self.assertLess(len(payload), 2048)
        for number in (-1, 0x100000000):
            with self.assertRaises(ValueError):
                candidate.varint(number)

    def test_callback_lifecycle_and_failure_paths_under_sanitizers(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            fixture = work/'fixture'
            subprocess.run(['gcc', '-g', '-O1', '-std=gnu11', '-pthread',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            str(Path(__file__).with_name('native_send_fixture.c')), '-o', str(fixture)],
                           check=True, capture_output=True, timeout=30)
            for case in ('success', 'check', 'parse-failure', 'unconsumed', 'server-error', 'early-completion'):
                with self.subTest(case=case):
                    output = work/(case + '.json')
                    subprocess.run([str(fixture), case, str(output)], check=True,
                                   capture_output=True, timeout=15)
                    result = json.loads(output.read_text())
                    self.assertTrue(result['worker_done'])
                    self.assertEqual(result['live_callbacks'], 0)
                    self.assertEqual(result['submission_entered'], case not in ('check', 'parse-failure'))
                    self.assertEqual(result['callback_count'], int(case in ('success', 'server-error', 'early-completion')))
                    if case == 'server-error':
                        self.assertEqual(result['error_code'], -123)

    @unittest.skipUnless(shutil.which('gdb'), 'GDB is required for real debugger fixture')
    def test_real_gdb_loader_detach_arm_and_async_completion(self):
        self.run_debugger_fixture(False)

    @unittest.skipUnless(shutil.which('gdb'), 'GDB is required for real debugger fixture')
    def test_real_poll_syscall_is_recognized_without_function_name(self):
        self.run_debugger_fixture(False, poll=True)

    @unittest.skipUnless(shutil.which('gdb'), 'GDB is required for real debugger fixture')
    def test_other_thread_signal_during_loader_never_arms_send(self):
        self.run_debugger_fixture(True)

    def run_debugger_fixture(self, interrupt, poll=False):
        if os.geteuid() == 0:
            self.skipTest('Run this synthetic debugger test as ordinary user')
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            fixture = work/'fixture'
            source = str(Path(__file__).with_name('native_send_fixture.c'))
            subprocess.run(['gcc', '-g', '-O0', '-pthread', source, '-o', str(fixture)],
                           check=True, capture_output=True, timeout=30)
            helper = work/'fixture.so'
            subprocess.run(['gcc', '-shared', '-fPIC', '-g', '-O0', '-pthread', '-DNCUT_FIXTURE_DSO', source, '-o', str(helper)],
                           check=True, capture_output=True, timeout=30)
            cfg = {'fixture': True, 'interrupt_loader': interrupt, 'poll_fixture': poll,
                   'binary_copy': str(fixture), 'helper': str(helper),
                   'load_bias': 1, 'send': True, 'payload_hex': candidate.make_payload(1700000000).hex(),
                   'injection_result': str(work/'injection.json'), 'worker_result': str(work/'worker.json')}
            result = candidate.run_injection(cfg, work)
            try:
                if interrupt:
                    self.assertEqual(result.get('status'), 'injection_failed', (result, (work/'debugger.log').read_text()))
                    self.assertTrue(result['detached'])
                    self.assertFalse(result.get('armed', False))
                    self.assertFalse(Path(cfg['worker_result']).exists())
                    time.sleep(.5)
                    self.assertTrue(candidate.process_running_untraced(result['inferior_pid']))
                    self.assertTrue((work/'main-resumed').exists())
                    return
                self.assertEqual(result.get('status'), 'trial_finished', (result, (work/'debugger.log').read_text()))
                self.assertTrue(result['detached'])
                self.assertTrue(result['armed'])
                if poll:
                    self.assertTrue(result['idle_check']['verified'])
                    self.assertEqual(result['idle_check']['syscall_name'], 'poll')
                self.assertEqual(result['worker']['task_id'], 77)
                self.assertEqual(result['worker']['callback_count'], 1)
                self.assertEqual(result['worker']['callback_destroyed'], 1)
                self.assertEqual(result['worker']['live_callbacks'], 0)
                time.sleep(.5)
                self.assertTrue(candidate.process_running_untraced(result['inferior_pid']))
                self.assertTrue((work/'main-resumed').exists())
            finally:
                if result.get('inferior_pid'):
                    try:
                        os.kill(result['inferior_pid'], signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                if result.get('debugger_pid'):
                    os.kill(result['debugger_pid'], signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
