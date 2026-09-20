#!/usr/bin/env python3
"""Explicit development aid: bounded hardware-breakpoint observation, never sends."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import tempfile
import time

EXPECTED = '2ca28ea56b1a400543d0128ebaf0b93f88172dd66dc0426d3d74fdb971eab959'
ENTRY = 0x8f60a90
PROLOGUE = bytes.fromhex('4156534881ec080100004889f34989fe')
REQ2BUF_RETURN = 0x8e828ed
REQ2BUF_SIGNATURE = bytes.fromhex('4883c43089c5e996000000')
CGIS = ('/cgi-bin/micromsg-bin/newsendmsg', '/cgi-bin/micromsg-bin/uploadmsgimg')


@contextmanager
def desktop_identity(uid, gid):
    """Temporarily access ordinary user files; insufficient for user-only FUSE."""
    previous_uid, previous_gid = os.geteuid(), os.getegid()
    try:
        if previous_gid != gid:
            os.setegid(gid)
        if previous_uid != uid:
            os.seteuid(uid)
        yield
    finally:
        if os.geteuid() != previous_uid:
            os.seteuid(previous_uid)
        if os.getegid() != previous_gid:
            os.setegid(previous_gid)


def copy_verified_executable(source, destination, expected=EXPECTED):
    """Copy only the program image; never copy process memory or user data."""
    digest = hashlib.sha256()
    count = 0
    try:
        with source.open('rb') as src, destination.open('xb') as dst:
            destination.chmod(0o600)
            while block := src.read(1024 * 1024):
                count += len(block)
                if count > 256 * 1024 * 1024:
                    raise ValueError('Executable exceeds the bounded copy size')
                digest.update(block)
                dst.write(block)
        if digest.hexdigest() != expected:
            raise ValueError('Unsupported WeChat binary; revalidate the Linux addresses first')
        return digest.hexdigest()
    except BaseException as error:
        try:
            destination.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise ValueError(f'{type(error).__name__}: {error}; '
                             f'copy_cleanup_failed: errno={cleanup_error.errno}') from error
        raise


def prepare_desktop_executable(request):
    """Runs in a disposable child with all real/effective/saved IDs dropped."""
    uid, gid = request['uid'], request['gid']
    if uid == 0 or os.getresuid() != (uid, uid, uid) or os.getresgid() != (gid, gid, gid):
        raise ValueError('desktop_identity_incomplete: all real/effective/saved IDs must match')
    target, work = Path(request['target']), Path(request['work'])
    stage = 'copy_appimage_as_desktop_user'
    try:
        digest = copy_verified_executable(target/'exe', work/'wechat.elf', request['expected'])
        stage = 'read_desktop_process_maps'
        exe_real = os.readlink(target/'exe')
        mappings = [line.split(maxsplit=5) for line in (target/'maps').read_text().splitlines()]
        bases = [int(x[0].split('-')[0], 16) for x in mappings
                 if len(x) == 6 and x[2] == '00000000' and x[5] == exe_real]
        if len(bases) != 1:
            raise ValueError('Cannot determine unique WeChat ELF load bias')
        return {'binary_sha256': digest, 'load_bias': bases[0],
                'reader_uids': list(os.getresuid()), 'reader_gids': list(os.getresgid())}
    except OSError as error:
        raise ValueError(f'{stage}: {type(error).__name__} (errno={error.errno})') from None


def run_desktop_preparation(target, work, uid, gid, expected=EXPECTED):
    # Popen's user/group set real and effective IDs before exec (also replacing
    # saved IDs); euid-only switching leaves saved root and fails FUSE checks.
    script = str(Path(__file__).resolve())
    code = '''import json, runpy, sys
module = runpy.run_path(sys.argv[1], run_name='ncut_probe_preparation')
try:
    result = module['prepare_desktop_executable'](json.load(sys.stdin))
except (ValueError, OSError) as error:
    print(json.dumps({'error': str(error)}))
    sys.exit(1)
print(json.dumps(result))
'''
    identity = {'user': uid, 'group': gid, 'extra_groups': []} if os.geteuid() == 0 else {}
    request = {'target': str(target), 'work': str(work), 'uid': uid, 'gid': gid, 'expected': expected}
    try:
        child = subprocess.run([sys.executable, '-I', '-c', code, script],
                               input=json.dumps(request), text=True, capture_output=True,
                               timeout=60, cwd='/', **identity)
    except subprocess.TimeoutExpired:
        raise ValueError('desktop_preparation_timeout: exceeded 60 seconds') from None
    try:
        prepared = json.loads(child.stdout)
    except ValueError:
        raise ValueError('desktop_preparation_failed_before_result') from None
    if child.returncode or 'error' in prepared:
        raise ValueError(prepared.get('error', 'desktop_preparation_failed'))
    return prepared


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)


def trace_in_gdb(gdb):
    cfg = json.loads(Path(os.environ['NCUT_WECHAT_OBSERVE_CONFIG']).read_text())
    out = Path(cfg['output'])
    state = {'status': 'starting', 'events': [], 'hits': 0, 'errors': 0,
             'req2buf_events': [], 'req2buf_hits': 0,
             'message_send_performed': False, 'process_payload_written': False,
             'breakpoint_type': 'hardware', 'self_test': cfg['self_test']}
    bp = None
    req_bp = None
    inferior = None
    attached = False
    observation_start = None
    watched_tasks = {}
    try:
        for command in ('set pagination off', 'set confirm off', 'set print thread-events off',
                        'set auto-load off', 'set debuginfod enabled off',
                        'set auto-solib-add off', 'set exec-file-mismatch off'):
            gdb.execute(command, to_string=True)
        if cfg['self_test']:
            gdb.execute('file ' + json.dumps(cfg['fixture']), to_string=True)
            gdb.execute('starti', to_string=True)
            address = int(gdb.parse_and_eval('&observe_fixture'))
            req_address = int(gdb.parse_and_eval('&observe_req_result'))
        else:
            # Root cannot open a user-only FUSE mount. Use the verified plain-file
            # copy for ELF metadata; target addresses still come from /proc/maps.
            gdb.execute('file ' + json.dumps(cfg['binary_copy']), to_string=True)
            gdb.execute('attach ' + str(cfg['pid']), to_string=True)
            attached = True
            address = cfg['address']
            req_address = cfg['load_bias'] + REQ2BUF_RETURN
        inferior = gdb.selected_inferior()
        if not cfg['self_test'] and bytes(inferior.read_memory(address, len(PROLOGUE))) != PROLOGUE:
            raise RuntimeError('instruction_signature_mismatch')
        if not cfg['self_test'] and bytes(inferior.read_memory(req_address, len(REQ2BUF_SIGNATURE))) != REQ2BUF_SIGNATURE:
            raise RuntimeError('req2buf_instruction_signature_mismatch')

        def hit_limit():
            return state['hits'] + state['req2buf_hits'] >= 100 or state['errors'] >= 3

        def read_word(address):
            return int.from_bytes(bytes(inferior.read_memory(address, 8)), 'little')

        def module_offset(address):
            base = cfg.get('load_bias', 0)
            return hex(address - base) if base <= address < base + 0xb000000 else None

        class Observe(gdb.Breakpoint):
            def stop(self):
                state['hits'] += 1
                try:
                    task = int(gdb.parse_and_eval('$rsi'))
                    header = bytes(inferior.read_memory(task, 0x30))
                    string = header[0x18:0x30]
                    if string[0] & 1:
                        size = int.from_bytes(string[8:16], 'little')
                        ptr = int.from_bytes(string[16:24], 'little')
                        if not 1 <= size <= 96:
                            return hit_limit()
                        cgi = bytes(inferior.read_memory(ptr, size)).decode('ascii', 'strict')
                    else:
                        size = string[0] >> 1
                        if not 1 <= size <= 22:
                            return hit_limit()
                        cgi = string[1:1+size].decode('ascii', 'strict')
                    if cgi in CGIS and len(state['events']) < 2:
                        record = {'cgi': cgi, 'task_id': int.from_bytes(header[0:4], 'little'),
                                  'cmd_id': int.from_bytes(header[4:8], 'little'),
                                  'channel_select': int.from_bytes(header[16:20], 'little'),
                                  'transport_protocol': int.from_bytes(header[20:24], 'little'),
                                  'cgi_offset': '0x18', 'thread_id': gdb.selected_thread().num}
                        # user_context survives asynchronous Task copies. Keep its
                        # pointer only in memory, never read the pointed-to object.
                        watched_tasks[record['task_id']] = read_word(task + 0x58)
                        frames = []
                        frame = gdb.newest_frame()
                        for _ in range(6):
                            if frame is None:
                                break
                            pc = frame.pc()
                            if cfg.get('load_bias', 0) <= pc < cfg.get('load_bias', 0) + 0xb000000:
                                frames.append(hex(pc - cfg.get('load_bias', 0)))
                            frame = frame.older()
                        record['module_callers'] = frames
                        state['events'].append(record)
                        save(out, state)
                except Exception:
                    state['errors'] += 1
                return hit_limit()

        class ObserveReq2Buf(gdb.Breakpoint):
            def stop(self):
                state['req2buf_hits'] += 1
                try:
                    # These callee-saved registers hold the inputs immediately
                    # after the common StnManager virtual callback has returned.
                    task_id = int(gdb.parse_and_eval('$ebp')) & 0xffffffff
                    context = int(gdb.parse_and_eval('$r13'))
                    if task_id not in watched_tasks or watched_tasks[task_id] != context:
                        return hit_limit()
                    manager = int(gdb.parse_and_eval('$rbx'))
                    bridge = read_word(manager + 0x48)
                    dispatch = read_word(read_word(bridge) + 0x38) if bridge else 0
                    out_buffer = int(gdb.parse_and_eval('$r15'))
                    extend_buffer = int(gdb.parse_and_eval('$r14'))
                    state['req2buf_events'].append({
                        'task_id': task_id, 'user_context_matches': True,
                        'callback_returned_true': bool(int(gdb.parse_and_eval('$al'))),
                        'bridge_dispatch_offset': module_offset(dispatch),
                        'out_length': read_word(out_buffer + 0x10),
                        'extend_length': read_word(extend_buffer + 0x10),
                        'thread_id': gdb.selected_thread().num,
                        'payload_read': False,
                    })
                    save(out, state)
                    return True
                except Exception:
                    state['errors'] += 1
                    return hit_limit()

        bp = Observe('*' + hex(address), type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        req_bp = ObserveReq2Buf('*' + hex(req_address), type=gdb.BP_HARDWARE_BREAKPOINT, internal=True)
        state['status'] = 'observing'
        state['observation_started_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
        observation_start = time.monotonic()
        save(out, state)
        print('OBSERVING: send one short text manually from Linux WeChat to File Transfer Assistant.', flush=True)
        gdb.execute('continue', to_string=True)
        state['status'] = 'captured' if state['events'] else 'no_matching_task'
    except KeyboardInterrupt:
        state['status'] = 'captured' if state['events'] else 'deadline_no_matching_task'
    except Exception as error:
        state['status'] = 'probe_error'
        state['error_type'] = type(error).__name__
    finally:
        for breakpoint in (bp, req_bp):
            if breakpoint is not None:
                try:
                    breakpoint.delete()
                except Exception:
                    pass
        # An interrupted attach can already have selected the target.
        if not cfg['self_test']:
            try:
                attached = attached or gdb.selected_inferior().pid == cfg['pid']
            except Exception:
                pass
        if attached:
            try:
                gdb.execute('detach', to_string=True)
                state['detached'] = True
            except Exception:
                state['detached'] = False
        elif cfg['self_test'] and inferior is not None:
            try:
                gdb.execute('kill', to_string=True)
            except Exception:
                pass
        state['observation_ended_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
        if observation_start is not None:
            state['observation_elapsed_seconds'] = round(time.monotonic() - observation_start, 2)
        save(out, state)
    gdb.execute('quit', to_string=True)


def run_gdb(cfg, work, seconds, on_started=None):
    config = work / 'config.json'
    save(config, cfg)
    env = {**os.environ, 'NCUT_WECHAT_OBSERVE_CONFIG': str(config), 'DEBUGINFOD_URLS': ''}
    log = work / 'debugger.log'
    script = str(Path(__file__).resolve())
    load_script = f'python exec(compile(open({script!r}).read(), {script!r}, "exec"))'
    with log.open('wb') as output:
        log.chmod(0o600)
        proc = subprocess.Popen(['/usr/bin/gdb', '--nx', '--nh', '--quiet', '--batch',
                                 '-iex', 'set auto-load off', '-iex', 'set debuginfod enabled off',
                                 '-ex', load_script],
                                stdout=output, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        if on_started is not None:
            on_started()
        stop_reason = 'debugger_finished'
        try:
            deadline = time.monotonic() + seconds
            announced = False
            while proc.poll() is None and time.monotonic() < deadline:
                result = Path(cfg['output'])
                if not announced and result.exists():
                    try:
                        state = json.loads(result.read_text())
                    except (OSError, ValueError):
                        state = {}
                    if state.get('status') == 'observing':
                        ready = state.get('observation_started_at', '')
                        print(f'观测已就绪（{ready}）：请现在从这台 Linux 电脑的微信窗口向文件传输助手发一条短文字；本轮最多等待{seconds}秒。', flush=True)
                        announced = True
                time.sleep(.2)
            if proc.poll() is None:
                stop_reason = 'deadline'
        except KeyboardInterrupt:
            stop_reason = 'operator_interrupt'
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
    result = Path(cfg['output'])
    state = json.loads(result.read_text()) if result.exists() else {'status': 'debugger_failed_before_result'}
    state['wait_stop_reason'] = stop_reason
    return state


def self_test():
    if os.geteuid() == 0:
        raise ValueError('Run self-test as the regular user')
    with tempfile.TemporaryDirectory(prefix='ncut-observe-test-') as tmp:
        work = Path(tmp)
        c = work / 'fixture.c'
        c.write_text(r'''#include <stdint.h>
#include <stddef.h>
#include <string.h>
struct Task {
    uint32_t id, cmd; uint64_t channel; uint32_t select, protocol;
    uint64_t cap, size; const char *cgi; char padding[0x28]; void *context;
};
struct Buffer { void *data; uint64_t pos, length, capacity, unit; };
struct Bridge { void **vtable; };
struct Manager { char padding[0x48]; struct Bridge *bridge; };
_Static_assert(offsetof(struct Task, context) == 0x58, "Task context offset");
_Static_assert(offsetof(struct Buffer, length) == 0x10, "Buffer length offset");
__attribute__((noinline)) void observe_fixture(void *mgr, struct Task *task) {
    asm volatile("" : : "r"(mgr), "r"(task) : "memory");
}
__attribute__((naked, noinline)) void req_fixture(void *mgr, uint32_t id, void *context,
                                               void *out, void *extend, int result) {
    asm volatile(
        "push %rbp\n\tpush %rbx\n\tpush %r13\n\tpush %r14\n\tpush %r15\n\t"
        "mov %rdi,%rbx\n\tmov %esi,%ebp\n\tmov %rdx,%r13\n\t"
        "mov %rcx,%r15\n\tmov %r8,%r14\n\tmov %r9d,%eax\n\t"
        ".global observe_req_result\nobserve_req_result:\n\tnop\n\t"
        "pop %r15\n\tpop %r14\n\tpop %r13\n\tpop %rbx\n\tpop %rbp\n\tret\n\t");
}
int main(void) {
    int context=0, unrelated=0;
    void *vtable[8]={0}; vtable[7]=(void*)observe_fixture;
    struct Bridge bridge={vtable}; struct Manager manager={.bridge=&bridge};
    struct Buffer out={.length=123}, extend={.length=9};
    struct Task task={.id=7,.cmd=522,.select=2,.cap=97,
                     .cgi="/cgi-bin/micromsg-bin/newsendmsg",.context=&context};
    task.size=strlen(task.cgi);
    observe_fixture(&manager,&task);
    req_fixture(&manager,8,&context,&out,&extend,1);
    req_fixture(&manager,7,&unrelated,&out,&extend,1);
    req_fixture(&manager,7,&context,&out,&extend,1);
    return 0;
}
''')
        exe = work / 'fixture'
        subprocess.run(['/usr/bin/gcc', '-g', '-O0', '-fno-pie', '-no-pie', str(c), '-o', str(exe)],
                       check=True, capture_output=True, timeout=20)
        copied = work/'verified-fixture'
        copy_verified_executable(exe, copied, hashlib.sha256(exe.read_bytes()).hexdigest())
        copied.chmod(0o700)  # Only the synthetic fixture is executed by this test.
        cfg = {'self_test': True, 'fixture': str(copied), 'output': str(work/'result.json'), 'load_bias': 0}
        result = run_gdb(cfg, work, 8)
        if result.get('status') != 'captured' or len(result.get('events', [])) != 1:
            raise ValueError('Synthetic debugger validation failed: ' + result.get('status', 'unknown'))
        if any(x['cmd_id'] != 522 or x['cgi_offset'] != '0x18' for x in result['events']):
            raise ValueError('Synthetic task fields did not match')
        callbacks = result.get('req2buf_events', [])
        if (len(callbacks) != 1 or result['req2buf_hits'] != 3
                or callbacks[0]['out_length'] != 123 or callbacks[0]['extend_length'] != 9
                or not callbacks[0]['callback_returned_true'] or callbacks[0]['payload_read']
                or not callbacks[0]['bridge_dispatch_offset']):
            raise ValueError('Synthetic task/callback correlation failed')
        return {'ok': True, 'scope': 'synthetic_two_hardware_breakpoints_task_callback_correlation',
                'wechat_runtime_verified': False, 'message_send_performed': False}


def observe(seconds):
    sudo_uid = os.environ.get('SUDO_UID')
    if os.geteuid() != 0 or not sudo_uid or int(sudo_uid) == 0:
        raise ValueError('PROCESS_TRACE_PERMISSION_REQUIRED: invoke once with sudo from your desktop account')
    uid = int(sudo_uid)
    owner = pwd.getpwuid(uid)
    found = []
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            status = (item/'status').read_text()
            actual_uid = int(next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1])
            if actual_uid == uid and Path(os.readlink(item/'exe')).name == 'wechat':
                found.append((item, status))
        except (OSError, StopIteration):
            pass
    if len(found) != 1:
        raise ValueError('Need exactly one running WeChat owned by your desktop account')
    target, status = found[0]
    start_time = (target/'stat').read_text().rsplit(')', 1)[1].split()[19]
    state_line = next(x for x in status.splitlines() if x.startswith('State:'))
    if int(next(x for x in status.splitlines() if x.startswith('TracerPid:')).split()[1]) or state_line.split()[1] in ('T', 't'):
        raise ValueError('WeChat is already traced or stopped; leave it unchanged')
    work = None
    cleanup = {'verified': False}
    debugger_started = False

    def mark_debugger_started():
        nonlocal debugger_started
        debugger_started = True

    stage = 'prepare_private_directory'
    try:
        with desktop_identity(uid, owner.pw_gid):
            root = Path(owner.pw_dir)/'.local/state/ncut-wechat-skills/native-send-observe'
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            root.chmod(0o700)
            work = Path(tempfile.mkdtemp(prefix='run-', dir=root))
        stage = 'prepare_in_desktop_child'
        prepared = run_desktop_preparation(target, work, uid, owner.pw_gid)
        cfg = {'self_test': False, 'pid': int(target.name), 'load_bias': prepared['load_bias'],
               'address': prepared['load_bias'] + ENTRY, 'output': str(work/'result.json'),
               'binary_sha256': prepared['binary_sha256'], 'binary_copy': str(work/'wechat.elf')}
        stage = 'start_bounded_debugger'
        result = run_gdb(cfg, work, seconds, on_started=mark_debugger_started)
    except OSError as error:
        raise ValueError(f'{stage}: {type(error).__name__} (errno={error.errno})') from None
    finally:
        primary_error = sys.exc_info()[1]
        try:
            current_start = (target/'stat').read_text().rsplit(')', 1)[1].split()[19]
            if current_start == start_time:
                after = (target/'status').read_text()
                traced = int(next(x for x in after.splitlines() if x.startswith('TracerPid:')).split()[1])
                stopped = next(x for x in after.splitlines() if x.startswith('State:')).split()[1] in ('T', 't')
                if debugger_started and not traced and stopped:
                    os.kill(int(target.name), signal.SIGCONT)
                    time.sleep(.05)
                    after = (target/'status').read_text()
                    stopped = next(x for x in after.splitlines() if x.startswith('State:')).split()[1] in ('T', 't')
                cleanup = {'verified': not traced and not stopped,
                           'tracer_present': bool(traced), 'process_stopped': stopped}
            else:
                cleanup['reason'] = 'process_identity_changed'
        except (OSError, StopIteration):
            pass
        if work is not None:
            try:
                (work/'wechat.elf').unlink(missing_ok=True)
                for file in work.iterdir():
                    file.chmod(0o600)
                    os.chown(file, uid, owner.pw_gid)
                os.chown(work, uid, owner.pw_gid)
            except OSError as error:
                cleanup['verified'] = False
                cleanup['artifact_error'] = f'{type(error).__name__} (errno={error.errno})'
                if primary_error is not None:
                    raise ValueError(f'{primary_error}; artifact_cleanup_failed: '
                                     f'{cleanup["artifact_error"]}') from None
    result['cleanup'] = cleanup
    with desktop_identity(uid, owner.pw_gid):
        save(work/'result.json', result)
    return {'ok': result.get('status') == 'captured' and cleanup['verified'], 'status': result.get('status'),
            'event_count': len(result.get('events', [])), 'result_path': str(work/'result.json'),
            'req2buf_event_count': len(result.get('req2buf_events', [])),
            'message_send_performed': False, 'cleanup': cleanup,
            'observation_window': {key: result.get(key) for key in
                                   ('observation_started_at', 'observation_ended_at',
                                    'observation_elapsed_seconds', 'wait_stop_reason')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('self-test', 'observe'))
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    if not 10 <= args.seconds <= 60:
        parser.error('--seconds must be 10..60')
    os.umask(0o077)
    result = self_test() if args.operation == 'self-test' else observe(args.seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok') else 1


try:
    import gdb
except ImportError:
    if __name__ == '__main__':
        try:
            raise SystemExit(main())
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            print(json.dumps({'ok': False, 'error': str(error) if isinstance(error, ValueError) else type(error).__name__}))
            raise SystemExit(1)
else:
    trace_in_gdb(gdb)
