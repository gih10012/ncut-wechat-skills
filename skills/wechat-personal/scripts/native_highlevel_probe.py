#!/usr/bin/env python3
"""Read-only, bounded observation of one filehelper text's native high-level lifecycle.

No inferior calls, payload writes, message body reads, or send operations.
ABI offsets are statically derived for one pinned ELF, not an active-call ABI.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time

POINTS = {
    'request': (0x64c7bd0, '415741564154534883ec384989d44989f64889fb884c2406'),
    'insert': (0x6965b60, '554157415641554154534881ecc80300004989d74989f648'),
    'assigned': (0x6965cf8, '498b0f4c8b7c24084d85ff740af049ff4708f049ff470848'),
    'update': (0x6965580, '554157415641554154534881ec0802000089cd89d34989f4'),
}
REQUEST_VPTR = 0xa899f78
MAX_HITS = 100


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def trace_in_gdb(gdb):
    cfg = json.loads(Path(os.environ['NCUT_HIGHLEVEL_CONFIG']).read_text())
    state = {'status': 'starting', 'probe': 'highlevel_local_history', 'events': [],
             'hits': 0, 'errors': 0, 'detached': False, 'breakpoint_type': 'hardware',
             'point_hits': {name: 0 for name in POINTS}, 'self_test': cfg.get('self_test', False),
             'message_send_performed': False, 'process_payload_written': False,
             'message_body_read': False, 'runtime_abi_verified': False}
    points, attached, start = [], False, None
    selected = {'request': None, 'context': None, 'manager': None,
                'local_id': None, 'inserted': False}
    object_tags = {kind: {} for kind in ('request', 'context', 'manager', 'sender', 'message')}
    try:
        for command in ('set pagination off', 'set confirm off', 'set print thread-events off',
                        'set auto-load off', 'set debuginfod enabled off',
                        'set auto-solib-add off', 'set exec-file-mismatch off'):
            gdb.execute(command, to_string=True)
        if cfg.get('self_test'):
            gdb.execute('file ' + json.dumps(cfg['fixture']), to_string=True)
            mode = cfg.get('fixture_mode', 'normal')
            if mode not in ('normal', 'timeout', 'hit_limit', 'read_error'):
                raise ValueError('invalid_fixture_mode')
            gdb.execute('set environment NCUT_HIGHLEVEL_FIXTURE_MODE ' + mode, to_string=True)
            gdb.execute('starti', to_string=True)
            addresses = {name: int(gdb.parse_and_eval('&highlevel_' + name)) for name in POINTS}
            expected_vptr = int(gdb.parse_and_eval('&highlevel_request_vtable'))
        else:
            gdb.execute('file ' + json.dumps(cfg['binary_copy']), to_string=True)
            gdb.execute('attach ' + str(cfg['pid']), to_string=True)
            addresses = {name: cfg['load_bias'] + point[0] for name, point in POINTS.items()}
            expected_vptr = cfg['load_bias'] + REQUEST_VPTR
        attached = True
        inferior = gdb.selected_inferior()
        state['inferior_pid'] = inferior.pid
        # Validate every point before installing even the first hardware breakpoint.
        for name, address in addresses.items():
            signature = (cfg.get('fixture_signatures', {}).get(name) if cfg.get('self_test')
                         else POINTS[name][1])
            if signature is not None:
                expected = bytes.fromhex(signature)
                if bytes(inferior.read_memory(address, len(expected))) != expected:
                    raise ValueError('instruction_signature_mismatch')

        def read(address, length):
            return bytes(inferior.read_memory(address, length))

        def integer(address, length=8):
            return int.from_bytes(read(address, length), 'little')

        def reg(name):
            return int(gdb.parse_and_eval('$' + name))

        def tag(kind, address):
            values = object_tags[kind]
            return values.setdefault(address, len(values) + 1)

        def recipient_matches(address):
            encoded = read(address, 24)
            if encoded[0] & 1:
                size = int.from_bytes(encoded[8:16], 'little')
                return size == 10 and read(int.from_bytes(encoded[16:24], 'little'), 10) == b'filehelper'
            return encoded[0] >> 1 == 10 and encoded[1:11] == b'filehelper'

        def request_matches(request):
            return (request and integer(request) == expected_vptr
                    and integer(request + 0x7c, 4) == 1 and recipient_matches(request + 0x90))

        def message_matches(message):
            return message and integer(message + 0xc, 4) == 1 and recipient_matches(message + 0x30)

        def fields(message):
            return {'message_object': tag('message', message), 'type': integer(message + 0xc, 4),
                    'local_id': integer(message + 0xf4, 4), 'server_id': integer(message + 0xf8),
                    'created_at': integer(message + 0x114, 4), 'send_state': integer(message + 0x118, 4)}

        def stack():
            result, frame = [], gdb.newest_frame()
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
                limit = state['hits'] >= MAX_HITS
                try:
                    name = self.name
                    thread = gdb.selected_thread()
                    ptid = thread.ptid
                    native_tid = int(ptid[1] or ptid[2] or ptid[0])
                    event = {'stage': name, 'thread': thread.num, 'native_tid': native_tid}
                    if name == 'request':
                        if selected['request'] is not None:
                            return limit
                        request = integer(reg('rdx'))
                        if not request_matches(request):
                            return limit
                        selected.update(request=request, manager=reg('rsi'), native_tid=native_tid)
                        event.update(request_type=integer(request + 0x7c, 4),
                                     request_mode=integer(request + 0xe4, 4), flag=reg('cl'),
                                     manager_object=tag('manager', selected['manager']))
                    elif name == 'insert':
                        if selected['request'] is None:
                            return limit
                        context = integer(reg('rdx'))
                        if (not context or integer(context + 8) != selected['request']
                                or selected['inserted']):
                            return limit
                        message = integer(context + 0x18)
                        if not message_matches(message):
                            return limit
                        selected['context'] = context
                        selected['inserted'] = True
                        event['sender_object'] = tag('sender', reg('rsi'))
                        event.update(context_object=tag('context', context),
                                     context_stage=integer(context + 0xb4, 4), **fields(message))
                    elif name == 'assigned':
                        if not selected['inserted'] or selected['local_id'] is not None:
                            return limit
                        context = integer(reg('r15'))
                        if context != selected['context']:
                            return limit
                        message = reg('rax')
                        if not message_matches(message):
                            return limit
                        local_id = integer(message + 0xf4, 4)
                        if not local_id:
                            return limit
                        selected['local_id'] = local_id
                        event.update(context_object=tag('context', context), **fields(message))
                    else:
                        if selected['local_id'] is None:
                            return limit
                        # The async update may run after the context has been
                        # released. Correlate by the assigned local ID without
                        # dereferencing the old context pointer.
                        message = integer(reg('rsi'))
                        if not message_matches(message):
                            return limit
                        if integer(message + 0xf4, 4) != selected['local_id']:
                            return limit
                        event.update(context_object=tag('context', selected['context']), **fields(message),
                                     update_type=reg('edx'), notify=reg('ecx'))
                    event.update(request_object=tag('request', selected['request']), module_stack=stack(),
                                 same_thread_as_request=native_tid == selected['native_tid'])
                    state['events'].append(event)
                    save(cfg['output'], state)
                    if name == 'update':
                        state['status'] = 'captured'
                        return True
                except Exception as error:
                    state['errors'] += 1
                    state['last_error_type'] = type(error).__name__
                return limit or state['errors'] >= 3

        for name, address in addresses.items():
            points.append(Point(name, address))
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
        # An interrupted attach can have selected the process before returning.
        if not cfg.get('self_test'):
            try:
                attached = attached or gdb.selected_inferior().pid == cfg['pid']
            except Exception:
                pass
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
    if not 0 < seconds <= 60 or (not cfg.get('self_test') and seconds < 10):
        raise ValueError('invalid_observation_window')
    config = work/'highlevel-config.json'
    save(config, cfg)
    script = str(Path(__file__).resolve())
    env = {**os.environ, 'NCUT_HIGHLEVEL_CONFIG': str(config), 'DEBUGINFOD_URLS': ''}
    for key in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    command = f'python __file__={script!r}; exec(compile(open({script!r}).read(), {script!r}, "exec"))'
    with (work/'highlevel-debugger.log').open('wb') as output:
        process = subprocess.Popen(['/usr/bin/gdb', '--nx', '--nh', '-q', '--batch',
                                    '-iex', 'set auto-load off', '-ex', command],
                                   stdout=output, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        if on_started:
            on_started()
        reason = 'debugger_finished'
        try:
            # The observation window starts only after GDB has attached and
            # installed the breakpoints. On a busy host, startup alone can
            # exceed a short synthetic observation deadline.
            startup_deadline = time.monotonic() + 30
            deadline = None
            announced = False
            while process.poll() is None:
                try:
                    result = json.loads(Path(cfg['output']).read_text())
                except (OSError, ValueError):
                    result = {}
                if result.get('status') == 'observing' and not announced:
                    deadline = time.monotonic() + seconds
                    if not cfg.get('self_test'):
                        print('本地入库观测已就绪：请现在从这台 Linux 微信向文件传输助手发一条短文字。', flush=True)
                    announced = True
                now = time.monotonic()
                if (deadline is not None and now >= deadline) or (deadline is None and now >= startup_deadline):
                    reason = 'deadline' if deadline is not None else 'startup_deadline'
                    break
                time.sleep(.1)
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
    if not 10 <= seconds <= 60:
        raise ValueError('observation_seconds_must_be_10_to_60')
    # Same process-identity checks, full-ID FUSE preparation, pinned SHA256,
    # copy removal, and stopped-process cleanup as the established probe.
    # Never import this legacy module within GDB (it has its own GDB entry).
    import native_send_probe as preparation
    previous = preparation.run_gdb
    try:
        preparation.run_gdb = run_gdb
        return preparation.observe(seconds)
    finally:
        preparation.run_gdb = previous


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
