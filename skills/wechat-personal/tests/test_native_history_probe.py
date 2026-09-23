import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_history_probe as probe


@unittest.skipUnless(shutil.which('gdb') and shutil.which('gcc'), 'requires GDB and GCC')
class NativeHistoryProbeTests(unittest.TestCase):
    def exercise(self, timeout=False, skip_send=False):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            fixture = work/'fixture'
            subprocess.run(['gcc', '-g', '-O0', '-fno-pie', '-no-pie',
                            str(Path(__file__).with_name('native_history_fixture.c')), '-o', str(fixture)],
                           check=True, capture_output=True)
            config = {'self_test': True, 'fixture': str(fixture), 'load_bias': 0,
                      'timeout_fixture': timeout, 'skip_send_fixture': skip_send,
                      'output': str(work/'result.json')}
            result = probe.run_gdb(config, work, 2 if timeout else 8)
            try:
                self.assertTrue(result.get('detached'), (result, (work/'history-debugger.log').read_text()))
                self.assertEqual(result['errors'], 0)
                self.assertNotIn('PRIVATE_FIXTURE_BODY', (work/'result.json').read_text())
                self.assertFalse(result['message_send_performed'])
                status = Path('/proc',str(result['inferior_pid']),'status').read_text()
                self.assertIn('TracerPid:\t0',status)
                self.assertNotIn(status.split('State:')[1].split()[0], ('T','t','Z'))
                if timeout:
                    self.assertEqual(result['status'], 'incomplete_observation')
                    self.assertEqual(result['events'], [])
                    self.assertEqual(result['wait_stop_reason'], 'deadline')
                else:
                    self.assertEqual(result['status'], 'captured')
                    events = result['events']
                    stages = ['insert','assigned','assigned'] + ([] if skip_send else ['send']) + ['update']
                    self.assertEqual([e['stage'] for e in events], stages)
                    self.assertEqual([e['message_object'] for e in events],
                                     [1,2,3] + ([] if skip_send else [2]) + [2])
                    self.assertEqual([e['local_id'] for e in events],
                                     [0,42,43] + ([] if skip_send else [42]) + [42])
                    self.assertEqual(events[-1]['send_state'], 2)
                    self.assertEqual(events[-1]['server_id'], 99)
            finally:
                if result.get('inferior_pid'):
                    os.kill(result['inferior_pid'], signal.SIGTERM)

    def test_real_gdb_matches_context_across_message_replacement_and_filters_other_targets(self):
        self.exercise()

    def test_deadline_detaches_without_fabricating_events(self):
        self.exercise(timeout=True)

    def test_update_is_captured_when_send_breakpoint_is_not_hit(self):
        self.exercise(skip_send=True)


if __name__ == '__main__':
    unittest.main()
