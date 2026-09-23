#!/usr/bin/env python3
"""Bounded read-only observation of the pinned client's outgoing message lifecycle."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


POINTS = {
    'insert': (0x6965b60, '554157415641554154534881ecc80300004989d74989f648'),
    'assigned': (0x6965cf8, '498b0f4c8b7c24084d85ff740af049ff4708f049ff470848'),
    'send': (0x6957340, '554157415641554154534881ec680300004989d44889b424'),
    'update': (0x6965580, '554157415641554154534881ec0802000089cd89d34989f4'),
}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def trace_in_gdb(gdb):
    cfg = json.loads(Path(os.environ['NCUT_HISTORY_CONFIG']).read_text())
    state = {'status': 'starting', 'probe': 'outgoing_local_history', 'events': [],
             'hits': 0, 'errors': 0, 'detached': False, 'breakpoint_type': 'hardware',
             'point_hits': {name: 0 for name in POINTS},
             'self_test': cfg.get('self_test', False), 'message_send_performed': False,
             'process_payload_written': False}
    points = []
    attached = False
    start = None
    contexts = set()
    message_ids = {}
    local_ids = set()
    try:
        for command in ('set pagination off', 'set confirm off', 'set print thread-events off',
                        'set auto-load off', 'set debuginfod enabled off',
                        'set auto-solib-add off', 'set exec-file-mismatch off'):
            gdb.execute(command, to_string=True)
        if cfg.get('self_test'):
            gdb.execute('file ' + json.dumps(cfg['fixture']), to_string=True)
            if cfg.get('timeout_fixture'):
                gdb.execute('set environment NCUT_HISTORY_FIXTURE_TIMEOUT 1', to_string=True)
            if cfg.get('skip_send_fixture'):
                gdb.execute('set environment NCUT_HISTORY_FIXTURE_SKIP_SEND 1', to_string=True)
            gdb.execute('starti', to_string=True)
            addresses = {name: int(gdb.parse_and_eval('&history_' + name)) for name in POINTS}
        else:
            gdb.execute('file ' + json.dumps(cfg['binary_copy']), to_string=True)
            gdb.execute('attach ' + str(cfg['pid']), to_string=True)
            addresses = {name: cfg['load_bias'] + point[0] for name, point in POINTS.items()}
        attached = True
        inferior = gdb.selected_inferior()
        state['inferior_pid'] = inferior.pid
        for name, address in addresses.items():
            if not cfg.get('self_test'):
                signature = bytes.fromhex(POINTS[name][1])
                if bytes(inferior.read_memory(address, len(signature))) != signature:
                    raise ValueError('instruction_signature_mismatch: ' + name)

        def read(address, length):
            return bytes(inferior.read_memory(address, length))

        def integer(address, length=8):
            return int.from_bytes(read(address, length), 'little')

        def reg(name):
            return int(gdb.parse_and_eval('$' + name))

        def matches(message):
            if not message or integer(message + 0xc, 4) != 1:
                return False
            encoded = read(message + 0x30, 24)
            if encoded[0] & 1:
                size = int.from_bytes(encoded[8:16], 'little')
                return size == 10 and read(int.from_bytes(encoded[16:24], 'little'), 10) == b'filehelper'
            return encoded[0] >> 1 == 10 and encoded[1:11] == b'filehelper'

        def fields(message):
            tag = message_ids.setdefault(message, len(message_ids) + 1)
            return {'message_object': tag, 'type': integer(message + 0xc, 4),
                    'local_id': integer(message + 0xf4, 4), 'server_id': integer(message + 0xf8),
                    'created_at': integer(message + 0x114, 4), 'send_state': integer(message + 0x118, 4)}

        def stack():
            result = []
            frame = gdb.newest_frame()
            for _ in range(10):
                if frame is None or len(result) == 6:
                    break
                pc = int(frame.pc()) - cfg.get('load_bias', 0)
                if 0 <= pc < 0xb000000:
                    result.append(hex(pc))
                frame = frame.older()
            return result

        class Point(gdb.Breakpoint):
            def __init__(self, name, address):
                super().__init__('*' + hex(address), type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
                self.name = name

            def stop(self):
                state['hits'] += 1
                state['point_hits'][self.name] += 1
                try:
                    name = self.name
                    if name in ('insert', 'send'):
                        current = integer(reg('rdx'))
                        message = integer(current + 0x18)
                        if not matches(message):
                            return state['hits'] >= 100
                        if name == 'insert':
                            if len(contexts) >= 8 and current not in contexts:
                                return state['hits'] >= 100
                            contexts.add(current)
                        elif current not in contexts or integer(message + 0xf4, 4) not in local_ids:
                            return state['hits'] >= 100
                    elif name == 'assigned':
                        if not contexts or integer(reg('r15')) not in contexts:
                            return state['hits'] >= 100
                        message = reg('rax')
                        if not matches(message) or not integer(message + 0xf4, 4):
                            return state['hits'] >= 100
                        local_ids.add(integer(message + 0xf4, 4))
                    else:
                        if not local_ids:
                            return state['hits'] >= 100
                        message = integer(reg('rsi'))
                        if not matches(message) or integer(message + 0xf4, 4) not in local_ids:
                            return state['hits'] >= 100
                    event = {'stage': name, 'thread': gdb.selected_thread().num,
                             **fields(message), 'module_stack': stack()}
                    if name == 'update':
                        event.update(update_type=reg('edx'), notify=reg('ecx'))
                    state['events'].append(event)
                    if name == 'update':
                        state['status'] = 'captured'
                        return True
                except Exception as error:
                    state['errors'] += 1
                    state['last_error_type'] = type(error).__name__
                return state['hits'] >= 100 or state['errors'] >= 3

        points = [Point(name, address) for name, address in addresses.items()]
        state['status'] = 'observing'
        state['observation_started_at'] = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()
        save(cfg['output'], state)
        try:
            gdb.execute('continue', to_string=True)
        except KeyboardInterrupt:
            pass
        if state['status'] == 'observing':
            state['status'] = 'incomplete_observation'
    except Exception as error:
        state['status'] = 'observation_failed'
        state['error_type'] = type(error).__name__
    finally:
        for point in points:
            try:
                point.delete()
            except Exception:
                state['errors'] += 1
        if attached:
            try:
                gdb.execute('detach', to_string=True)
                state['detached'] = True
            except Exception:
                state['errors'] += 1
        state['observation_ended_at'] = datetime.now(timezone.utc).isoformat()
        if start is not None:
            state['observation_elapsed_seconds'] = round(time.monotonic() - start, 3)
        save(cfg['output'], state)


def run_gdb(cfg, work, seconds, on_started=None):
    """Uses no inferior calls; deadline interrupts a continue before clean detach."""
    config = work/'history-config.json'
    save(config, cfg)
    script = str(Path(__file__).resolve())
    env = {**os.environ, 'NCUT_HISTORY_CONFIG': str(config), 'DEBUGINFOD_URLS': ''}
    for key in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    command = f'python __file__={script!r}; exec(compile(open({script!r}).read(), {script!r}, "exec"))'
    with (work/'history-debugger.log').open('wb') as output:
        process = subprocess.Popen(['/usr/bin/gdb', '--nx', '--nh', '-q', '--batch',
                                    '-iex', 'set auto-load off', '-ex', command],
                                   stdout=output, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        if on_started:
            on_started()
        reason = 'debugger_finished'
        try:
            deadline = time.monotonic() + seconds
            announced = False
            while process.poll() is None and time.monotonic() < deadline:
                try:
                    result = json.loads(Path(cfg['output']).read_text())
                except (OSError, ValueError):
                    result = {}
                if result.get('status') == 'observing' and not announced:
                    if not cfg.get('self_test'):
                        print('本地入库观测已就绪：请现在从这台 Linux 微信向文件传输助手发一条短文字。', flush=True)
                    announced = True
                time.sleep(.1)
            if process.poll() is None:
                reason = 'deadline'
        except KeyboardInterrupt:
            reason = 'operator_interrupt'
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # This debugger performs only reads/hardware breakpoints.
                    # Kernel ptrace cleanup follows debugger exit; caller checks
                    # the same client identity and resumes a leftover stop.
                    process.kill()
                    process.wait(timeout=3)
    result = (json.loads(Path(cfg['output']).read_text()) if Path(cfg['output']).exists()
              else {'status': 'debugger_failed_before_result'})
    result['wait_stop_reason'] = reason
    return result


def observe(seconds):
    # Reuse the proven owner, FUSE-copy, hash and process-identity cleanup path.
    # Import only in ordinary Python: importing the legacy module inside GDB
    # would launch its unrelated network probe.
    import native_send_probe as preparation
    preparation.run_gdb = run_gdb
    return preparation.observe(seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['observe'])
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args(argv)
    if not 10 <= args.seconds <= 60:
        parser.error('--seconds must be 10..60')
    os.umask(0o077)
    try:
        result = observe(args.seconds)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result = {'ok': False, 'error': str(error) if isinstance(error, ValueError) else type(error).__name__}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok') else 1


try:
    import gdb
except ImportError:
    if __name__ == '__main__':
        raise SystemExit(main())
else:
    trace_in_gdb(gdb)
