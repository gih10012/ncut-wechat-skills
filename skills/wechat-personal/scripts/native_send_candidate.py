#!/usr/bin/env python3
"""Pinned-build development trial: one authorized filehelper text, not a ready backend."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REQUEST_ID = 'linux-native-filehelper-text-v1'
POLL_SYSCALLS = {7: 'poll', 232: 'epoll_wait', 271: 'ppoll', 281: 'epoll_pwait', 441: 'epoll_pwait2'}


def classify_poll_stop(syscall_number, previous_instruction, library):
    # Recent glibc routes cancellable syscalls through an unnamed common stub.
    # A function name therefore cannot distinguish ppoll from futex/read/etc.
    accepted = (syscall_number in POLL_SYSCALLS and previous_instruction == b'\x0f\x05'
                and Path(library or '').name == 'libc.so.6')
    return {'verified': accepted, 'syscall_number': syscall_number,
            'syscall_name': POLL_SYSCALLS.get(syscall_number, 'not_poll'),
            'syscall_instruction_verified': previous_instruction == b'\x0f\x05',
            'library': Path(library or '').name}


def varint(number):
    if not 0 <= number <= 0xffffffff:
        raise ValueError('uint32 out of range')
    data = bytearray()
    while number > 127:
        data.append((number & 127) | 128)
        number >>= 7
    return bytes(data + bytes([number]))


def blob(field, value):
    return varint((field << 3) | 2) + varint(len(value)) + value


def make_payload(timestamp):
    # A fixed destination and recognizable acceptance text limit this first trial.
    text = ('Linux 微信原生发送验收 ' + REQUEST_ID).encode()
    client_id = int.from_bytes(hashlib.sha256(REQUEST_ID.encode()).digest()[:4], 'little')
    body = blob(1, blob(1, b'filehelper')) + blob(2, text)
    body += b'\x18\x01\x20' + varint(timestamp) + b'\x28' + varint(client_id)
    body += blob(6, b'<msgsource/>')
    return b'\x08\x01' + blob(2, body)


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.chmod(0o600)
    temp.replace(path)


def compile_helper(work, uid=None, gid=None):
    output = work/'helper.so'
    identity = {'user': uid, 'group': gid, 'extra_groups': []} if uid is not None else {}
    subprocess.run(['/usr/bin/gcc', '-shared', '-fPIC', '-O2', '-std=c11', '-Wall',
                    '-Wextra', '-Werror', '-pthread', str(HERE/'native_send_helper.c'),
                    '-o', str(output)], check=True, capture_output=True, timeout=30, **identity)
    output.chmod(0o600)
    return output


def inject_in_gdb(gdb):
    cfg = json.loads(Path(os.environ['NCUT_SEND_CONFIG']).read_text())
    status = {'status': 'preflight', 'attached': False, 'detached': False,
              'launch_call_entered': False, 'launch_returned': False}
    output = Path(cfg['injection_result'])
    allocated = 0
    call_thread = None
    call_origin = None

    def inferior_call(expression, evaluate=True):
        nonlocal call_origin
        call_thread.switch()
        call_origin = (int(gdb.parse_and_eval('$pc')), int(gdb.parse_and_eval('$sp')))
        value = (gdb.parse_and_eval(expression) if evaluate
                 else gdb.execute(expression, to_string=True))
        # A normally returned GDB call restores the caller's machine state.
        call_thread.switch()
        current = (int(gdb.parse_and_eval('$pc')), int(gdb.parse_and_eval('$sp')))
        if current != call_origin:
            raise RuntimeError('inferior_call_origin_not_restored')
        call_origin = None
        return value

    def pending_call():
        pending = False
        try:
            inferior = gdb.selected_inferior()
            for thread in inferior.threads() if inferior.pid else ():
                if not thread.is_valid():
                    continue
                if not thread.is_stopped():
                    pending = True
                    break
                thread.switch()
                frame = gdb.newest_frame()
                while frame:
                    if frame.type() == gdb.DUMMY_FRAME:
                        pending = True
                        break
                    frame = frame.older()
                if pending:
                    break
            # Unwind metadata can be unavailable for a newly loaded module.
            # Then the stack walk can end before the DUMMY_FRAME. Keep the
            # interrupted call active until its original PC/SP are restored.
            if inferior.pid and call_origin is not None:
                call_thread.switch()
                current = (int(gdb.parse_and_eval('$pc')), int(gdb.parse_and_eval('$sp')))
                pending = pending or current != call_origin
        except gdb.error:
            # An unreadable thread is uncertainty, not proof a call has ended.
            pending = True
        finally:
            try:
                if call_thread is not None and call_thread.is_valid():
                    call_thread.switch()
            except gdb.error:
                pending = True
        return pending

    def finish_pending_call():
        nonlocal call_origin
        # Never issue another call, unwind or detach across an unfinished call.
        # The outer process will report the live debugger if this cannot finish.
        while pending_call():
            status['status'] = 'inferior_call_pending'
            save(output, status)
            try:
                gdb.execute('continue', to_string=True)
            except gdb.error:
                time.sleep(1)
        call_origin = None
    try:
        for command in ('set pagination off', 'set confirm off', 'set auto-load off',
                        'set debuginfod enabled off', 'set print thread-events off',
                        'set auto-solib-add off', 'set exec-file-mismatch off',
                        'set unwind-on-signal off', 'set unwind-on-timeout off'):
            gdb.execute(command, to_string=True)
        gdb.execute('file ' + json.dumps(cfg['binary_copy']), to_string=True)
        if cfg.get('fixture'):
            if cfg.get('interrupt_loader'):
                gdb.execute('handle SIGUSR1 stop nopass', to_string=True)
            gdb.execute('break fixture_idle', to_string=True)
            gdb.execute('run', to_string=True)
            if cfg.get('poll_fixture'):
                gdb.execute('catch syscall poll', to_string=True)
                gdb.execute('continue', to_string=True)
                # No catchpoint may fire inside later inferior calls.
                for breakpoint in gdb.breakpoints() or ():
                    breakpoint.delete()
        else:
            gdb.execute('attach ' + str(cfg['pid']), to_string=True)
        status['attached'] = True
        inferior = gdb.selected_inferior()
        status['inferior_pid'] = inferior.pid
        gdb.execute('sharedlibrary libc', to_string=True)
        gdb.execute('set scheduler-locking off', to_string=True)
        if not cfg.get('fixture') or cfg.get('poll_fixture'):
            main_pid = inferior.pid
            main = next(t for t in inferior.threads() if t.ptid[1] == main_pid)
            main.switch()
            pc = int(gdb.parse_and_eval('$pc'))
            status['idle_check'] = classify_poll_stop(int(gdb.parse_and_eval('$orig_rax')),
                bytes(inferior.read_memory(pc - 2, 2)), gdb.solib_name(pc))
            if not status['idle_check']['verified']:
                raise ValueError('main_thread_not_idle_in_poll: no inferior call made')
        if not cfg.get('fixture'):
            base = cfg['load_bias']
            word = lambda address: int.from_bytes(inferior.read_memory(address, 8), 'little')
            account = word(base + 0xacef550)
            service = word(account + 0x250) if account else 0
            if (not service or word(service) != base + 0xa981948
                    or word(word(service) + 0x28) != base + 0x79e46b0
                    or not (bytes(inferior.read_memory(service + 8, 1))[0] & 1)):
                raise ValueError('network_service_chain_mismatch')
            status['network_service_chain_verified'] = True
        call_thread = gdb.selected_thread()
        data = bytes.fromhex(cfg['payload_hex'])
        helper = os.fsencode(cfg['helper']) + b'\0'
        result = os.fsencode(cfg['worker_result']) + b'\0'
        symbol = (b'ncut_test_launch' if cfg.get('fixture') else b'ncut_launch') + b'\0'
        total = helper + result + symbol + data
        # Only loader/allocation/thread launch calls occur under the debugger.
        status['status'] = 'loader_calls'
        save(output, status)
        allocated = int(inferior_call(f'(void *)malloc({len(total)})'))
        if not allocated:
            raise ValueError('allocation_failed')
        inferior.write_memory(allocated, total)
        result_ptr = allocated + len(helper)
        symbol_ptr = result_ptr + len(result)
        data_ptr = symbol_ptr + len(symbol)
        handle = int(inferior_call(f'(void *)dlopen((char *){allocated}, 2)'))
        if not handle:
            raise ValueError('helper_dlopen_failed')
        launcher = int(inferior_call(f'(void *)dlsym((void *){handle}, (char *){symbol_ptr})'))
        if not launcher:
            raise ValueError('helper_symbol_missing')
        status['launch_call_entered'] = True
        save(output, status)
        expression = (f'((int (*)(unsigned long,void*,unsigned long,char*,int)){launcher})'
                      f'({cfg["load_bias"]},(void*){data_ptr},{len(data)},'
                      f'(char*){result_ptr},{int(cfg["send"])})')
        code = int(inferior_call(expression))
        status['launch_returned'] = True
        status['launch_code'] = code
        status['status'] = 'launched' if code == 0 else 'launch_rejected'
    except Exception as error:
        status['status'] = 'injection_failed'
        status['error'] = str(error)[:600]
        # Never unwind an incomplete loader call and pretend locks are restored.
        finish_pending_call()
        status['status'] = 'injection_failed'
    finally:
        if status['attached']:
            if allocated:
                try:
                    inferior_call(f'call (void)free((void *){allocated})', evaluate=False)
                except Exception:
                    status['scratch_release_unverified'] = True
                    finish_pending_call()
            try:
                gdb.execute('detach', to_string=True)
                status['detached'] = True
            except Exception:
                pass
        save(output, status)


def process_running_untraced(pid, start_time=None):
    target = Path('/proc')/str(pid)
    try:
        if start_time and target.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] != start_time:
            return False
        rows = dict(line.split(':', 1) for line in target.joinpath('status').read_text().splitlines())
        return int(rows['TracerPid']) == 0 and rows['State'].split()[0] not in ('T', 't', 'Z')
    except (OSError, ValueError, KeyError):
        return False


def run_injection(cfg, work):
    save(work/'config.json', cfg)
    script = str(Path(__file__).resolve())
    env = {**os.environ, 'NCUT_SEND_CONFIG': str(work/'config.json'), 'DEBUGINFOD_URLS': ''}
    # GDB embeds its system Python. A caller's venv/CI libpython path can load
    # another Python runtime with incompatible stdlib extension directories.
    for key in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    if cfg.get('fixture'):
        env['NCUT_TEST_RESUMED_PATH'] = str(work/'main-resumed')
        if cfg.get('poll_fixture'):
            env['NCUT_TEST_POLL'] = '1'
    if cfg.get('fixture') and cfg.get('interrupt_loader'):
        env['NCUT_TEST_INTERRUPT_LOADER'] = '1'
    command = f'python __file__={script!r}; exec(compile(open({script!r}).read(), {script!r}, "exec"))'
    with (work/'debugger.log').open('wb') as log:
        proc = subprocess.Popen(['/usr/bin/gdb', '--nx', '--nh', '-q', '--batch', '-ex', command],
                                stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    save(work/'debugger-process.json', {'pid': proc.pid})
    try:
        proc.wait(timeout=25)
    except subprocess.TimeoutExpired:
        return {'status': 'debugger_still_running', 'debugger_pid': proc.pid,
                'armed': False, 'automatic_retry_allowed': False}
    if not Path(cfg['injection_result']).exists():
        return {'status': 'debugger_failed_before_result', 'armed': False}
    result = json.loads(Path(cfg['injection_result']).read_text())
    if result.get('status') != 'launched' or not result.get('detached'):
        return result
    if not cfg.get('fixture') and not process_running_untraced(cfg['pid'], cfg['start_time']):
        result['status'] = 'detach_not_verified'
        return result
    arm = Path(cfg['worker_result'] + '.arm')
    arm.touch(mode=0o600, exist_ok=False)
    if 'uid' in cfg:
        os.chown(arm, cfg['uid'], cfg['gid'])
    result['armed'] = True
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            worker = json.loads(Path(cfg['worker_result']).read_text())
        except (OSError, ValueError):
            time.sleep(.1)
            continue
        result['worker'] = worker
        if worker['worker_done'] and worker['live_callbacks'] == 0:
            break
        time.sleep(.1)
    worker = result.get('worker', {})
    result['status'] = ('worker_pending' if not worker.get('worker_done') else
                        'callback_pending' if worker.get('live_callbacks') else 'trial_finished')
    result['automatic_retry_allowed'] = False
    return result


def reserve_trial_work(root, name):
    work = root/name
    if work.exists():
        # Only this exact pre-call rejection is known not to have allocated,
        # loaded a module or launched a worker. Keep its full evidence archived.
        try:
            previous = json.loads((work/'result.json').read_text())
            debugger = json.loads((work/'debugger-process.json').read_text())
            retryable = (previous.get('status') == 'injection_failed'
                         and previous.get('error') == 'main_thread_not_idle_in_poll: no inferior call made'
                         and previous.get('detached') is True
                         and previous.get('client_running_untraced') is True
                         and previous.get('launch_call_entered') is False
                         and previous.get('launch_returned') is False
                         and not (work/'worker.json').exists()
                         and not (work/'worker.json.arm').exists()
                         and not Path('/proc', str(debugger['pid'])).exists())
        except (OSError, ValueError, KeyError):
            retryable = False
        if not retryable:
            raise ValueError('Existing trial: inspect its result; do not repeat a possibly submitted message: ' + str(work))
        work.rename(root/(name + '-preflight-' + str(time.time_ns())))
    work.mkdir(mode=0o700)
    return work


def trial(send):
    from native_send_probe import desktop_identity, run_desktop_preparation
    uid = int(os.environ.get('SUDO_UID', '0'))
    if os.geteuid() != 0 or uid == 0:
        raise ValueError('Run with sudo from the desktop account; no client was touched')
    owner = pwd.getpwuid(uid)
    with desktop_identity(uid, owner.pw_gid):
        root = Path(owner.pw_dir)/'.local/state/ncut-wechat-skills/native-send-trial'
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        # One fixed acceptance operation; uncertainty never causes automatic replay.
        work = reserve_trial_work(root, REQUEST_ID if send else 'native-roundtrip-v1')
    targets = []
    for target in Path('/proc').iterdir():
        if not target.name.isdigit():
            continue
        try:
            if target.stat().st_uid == uid and Path(os.readlink(target/'exe')).name == 'wechat':
                targets.append(target)
        except OSError:
            pass
    if len(targets) != 1:
        raise ValueError('Exactly one desktop WeChat process is required')
    target = targets[0]
    pid = int(target.name)
    start = (target/'stat').read_text().rsplit(')', 1)[1].split()[19]
    if not process_running_untraced(pid, start):
        raise ValueError('Client is already traced, stopped or exiting')
    prepared = run_desktop_preparation(target, work, uid, owner.pw_gid)
    helper = compile_helper(work, uid, owner.pw_gid)
    cfg = {**prepared, 'pid': pid, 'start_time': start, 'uid': uid, 'gid': owner.pw_gid,
           'binary_copy': str(work/'wechat.elf'), 'helper': str(helper),
           'injection_result': str(work/'injection.json'), 'worker_result': str(work/'worker.json'),
           'payload_hex': make_payload(int(time.time())).hex(), 'send': send}
    save(work/'request.json', {'request_id': REQUEST_ID, 'recipient': 'filehelper', 'send': send,
                              'status': 'reserved', 'runtime_verified': False})
    result = run_injection(cfg, work)
    result['client_running_untraced'] = process_running_untraced(pid, start)
    result['recipient_delivery_verified'] = False
    result['helper_unload_policy'] = 'small_module_remains_until_client_exit_for_callback_safety'
    save(work/'result.json', result)
    if result.get('status') != 'debugger_still_running':
        (work/'wechat.elf').unlink(missing_ok=True)
    for artifact in work.iterdir():
        artifact.chmod(0o600)
        os.chown(artifact, uid, owner.pw_gid)
    return {'result_path': str(work/'result.json'), **result}


def inspect_trial():
    """Read the persisted trial without attaching, compiling or sending."""
    uid = int(os.environ.get('SUDO_UID', str(os.getuid())))
    root = Path(pwd.getpwuid(uid).pw_dir)/'.local/state/ncut-wechat-skills/native-send-trial'
    work = root/REQUEST_ID
    if not (work/'result.json').exists():
        raise ValueError('No completed trial report is available yet: ' + str(work))
    result = json.loads((work/'result.json').read_text())
    if (work/'worker.json').exists():
        result['worker'] = json.loads((work/'worker.json').read_text())
    return {'result_path': str(work/'result.json'), 'read_only': True, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('check', 'filehelper-once', 'status'))
    args = parser.parse_args()
    os.umask(0o077)
    result = inspect_trial() if args.operation == 'status' else trial(args.operation == 'filehelper-once')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.operation == 'status':
        return 0
    worker = result.get('worker', {})
    return 0 if (worker.get('worker_done') and worker.get('native_roundtrip_verified')
                 and not worker.get('failure') and result.get('client_running_untraced')
                 and (args.operation == 'check' or (worker.get('callback_count') == 1
                      and worker.get('live_callbacks') == 0 and not worker.get('error_type')
                      and not worker.get('error_code')))) else 1


try:
    import gdb
except ImportError:
    if __name__ == '__main__':
        try:
            raise SystemExit(main())
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
            raise SystemExit(1)
else:
    inject_in_gdb(gdb)
