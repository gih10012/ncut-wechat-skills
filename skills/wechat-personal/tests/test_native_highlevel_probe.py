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
import native_highlevel_probe as probe


@unittest.skipUnless(shutil.which('gdb') and shutil.which('gcc'), 'requires GDB and GCC')
class HighlevelProbeTests(unittest.TestCase):
    def exercise(self, mode='normal', signatures=None):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            fixture = work/'fixture'
            subprocess.run(['gcc','-g','-O0','-fno-pie','-no-pie','-pthread',
                            str(Path(__file__).with_name('native_highlevel_fixture.c')),
                            '-o',str(fixture)], check=True, capture_output=True, timeout=20)
            cfg = {'self_test':True,'fixture':str(fixture),'load_bias':0,'fixture_mode':mode,
                   'output':str(work/'result.json')}
            if signatures is not None:
                cfg['fixture_signatures'] = signatures
            result = probe.run_gdb(cfg, work, 1 if mode == 'timeout' else 8)
            try:
                self.assertTrue(result.get('detached'), (result,(work/'highlevel-debugger.log').read_text()))
                serialized = (work/'result.json').read_text()
                for secret in ('PRIVATE_', 'filehelper', 'someone'):
                    self.assertNotIn(secret, serialized)
                    self.assertNotIn(secret, (work/'highlevel-debugger.log').read_text())
                self.assertFalse(result['message_send_performed'])
                self.assertFalse(result['process_payload_written'])
                self.assertFalse(result['message_body_read'])
                status = Path('/proc',str(result['inferior_pid']),'status').read_text()
                self.assertIn('TracerPid:\t0',status)
                self.assertNotIn(status.split('State:')[1].split()[0], ('T','t','Z'))
                self.assertLessEqual(result['hits'],100)
                return result
            finally:
                if result.get('inferior_pid'):
                    try:
                        os.kill(result['inferior_pid'],signal.SIGTERM)
                    except ProcessLookupError:
                        pass

    def test_real_gdb_filters_and_correlates_request_context_replacement_and_native_threads(self):
        result = self.exercise()
        self.assertEqual(result['status'],'captured')
        self.assertEqual(result['errors'],0)
        events = result['events']
        self.assertEqual([e['stage'] for e in events],['request','insert','assigned','update'])
        self.assertEqual([e['request_object'] for e in events],[1,1,1,1])
        self.assertEqual([e['context_object'] for e in events[1:]],[1,1,1])
        self.assertEqual([e['message_object'] for e in events[1:]],[1,2,2])
        self.assertEqual([e['local_id'] for e in events[1:]],[0,42,42])
        self.assertEqual([e['same_thread_as_request'] for e in events],[True,True,True,False])
        self.assertEqual(events[0]['native_tid'],events[2]['native_tid'])
        self.assertNotEqual(events[0]['native_tid'],events[3]['native_tid'])
        self.assertEqual(events[-1]['send_state'],2)
        self.assertEqual(events[-1]['server_id'],99)
        self.assertEqual(events[-1]['update_type'],1)
        self.assertTrue(all(e['module_stack'] for e in events))

    def test_deadline_detaches_without_fabricating_events(self):
        result = self.exercise('timeout')
        self.assertEqual(result['status'],'incomplete_observation')
        self.assertEqual(result['events'],[])
        self.assertEqual(result['errors'],0)
        self.assertEqual(result['wait_stop_reason'],'deadline')

    def test_hundred_unrelated_hits_stop_and_detach(self):
        result = self.exercise('hit_limit')
        self.assertEqual(result['hits'],100)
        self.assertEqual(result['events'],[])
        self.assertEqual(result['errors'],0)
        self.assertEqual(result['status'],'incomplete_observation')

    def test_three_memory_read_errors_stop_and_detach_without_raw_errors(self):
        result = self.exercise('read_error')
        self.assertEqual(result['errors'],3)
        self.assertEqual(result['hits'],3)
        self.assertEqual(result['events'],[])
        self.assertEqual(result['status'],'incomplete_observation')
        self.assertNotIn('Cannot access',json.dumps(result))

    def test_signature_mismatch_fails_before_any_breakpoint_hit(self):
        result = self.exercise(signatures={'request':'0000000000000000'})
        self.assertEqual(result['status'],'observation_failed')
        self.assertEqual(result['hits'],0)
        self.assertEqual(result['events'],[])

    def test_rejects_out_of_bounds_observation_window(self):
        for seconds in (0,61):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                probe.run_gdb({'self_test':True},Path('/nonexistent'),seconds)


if __name__ == '__main__':
    unittest.main()
