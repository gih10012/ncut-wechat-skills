#!/usr/bin/env python3
"""Explicit, temporary OneBot 12 HTTP text adapter for the owner's native WeChat.

Only filehelper private text is enabled. No events, media, daemon or installation.
The endpoint token is read from private state by `call`; never put it in arguments.
"""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import native_send_candidate as backend

SUPPORTED = ['get_supported_actions', 'get_version', 'send_message']
MAX_BODY = 16384


def response(code=0, message='', data=None):
    return {'status': 'failed' if code else 'ok', 'retcode': code,
            'data': data, 'message': message}


def owner_identity():
    owner = pwd.getpwuid(int(os.environ.get('SUDO_UID', str(os.getuid()))))
    return owner.pw_uid, owner.pw_gid, Path(owner.pw_dir)


def default_session():
    return owner_identity()[2]/'.local/state/ncut-wechat-skills/native-onebot-session.json'


def private_json(path, value, owner):
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            if os.geteuid() == 0:
                os.fchown(stream.fileno(), *owner)
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def read_private(path, uid):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
            raise ValueError('Private state must be an owner-only regular file')
        return json.load(stream)


class BackendProcess:
    """Isolate backend's process-wide UID changes; never kill an uncertain call."""
    def __init__(self, directory, owner):
        self.directory, self.owner = directory, owner
        self.process = None
        self.pending = None
        self.on_pending = None

    def __call__(self, text, request_id, recipient, timeout):
        if self.pending:
            raise RuntimeError('An earlier native operation requires inspection')
        fd, filename = tempfile.mkstemp(prefix='native-onebot-result-', suffix='.json',
                                        dir=self.directory)
        path = Path(filename)
        try:
            with os.fdopen(fd, 'wb') as output:
                if os.geteuid() == 0:
                    os.fchown(output.fileno(), *self.owner)
                self.process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), '_backend'],
                    stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL,
                    start_new_session=True)
                self.pending = {'pid': self.process.pid, 'request_id': request_id,
                                'result_file': str(path)}
                if self.on_pending:
                    self.on_pending()
                payload = json.dumps({'text': text, 'request_id': request_id,
                                      'recipient': recipient}).encode()
                try:
                    self.process.communicate(payload, timeout=timeout)
                except subprocess.TimeoutExpired:
                    # The independent child still owns its debugger and cleanup.
                    return {'status': 'adapter_timeout', 'automatic_retry_allowed': False}
            result = read_private(path, self.owner[0])
            self.pending = None
            path.unlink()
            return result
        except Exception:
            if self.process is None:
                path.unlink(missing_ok=True)
            raise


def native_response(result, request_id):
    worker = result.get('worker', {})
    good = (result.get('status') == 'trial_finished'
            and result.get('detached') is True
            and result.get('client_running_untraced') is True
            and all(worker.get(key) is True for key in
                    ('worker_done', 'native_roundtrip_verified', 'submission_entered'))
            and worker.get('callback_count') == 1
            and worker.get('callback_destroyed') == 1
            and all(worker.get(key) == 0 for key in
                    ('live_callbacks', 'error_type', 'error_code', 'failure')))
    details = {'wechat.request_id': request_id, 'wechat.id_kind': 'local_request',
               'wechat.native_task_id': worker.get('task_id'),
               'wechat.recipient_delivery_verified': result.get('recipient_delivery_verified') is True,
               'wechat.automatic_retry_allowed': False,
               'wechat.backend_status': result.get('status', 'unknown')}
    if good:
        when = result.get('completed_at')
        if not isinstance(when, (int, float)) or not math.isfinite(when):
            when = time.time()
        details.update(message_id='wechat-local:' + request_id, time=float(when))
        return response(data=details)
    return response(34001, 'Native completion is not verified; inspect this request before any retry', details)


class Adapter:
    def __init__(self, sender, max_sends=3, action_timeout=90):
        if not 1 <= max_sends <= 10 or not 1 <= action_timeout <= 180:
            raise ValueError('max-sends must be 1..10; action-timeout must be 1..180 seconds')
        self.sender, self.max_sends, self.action_timeout = sender, max_sends, action_timeout
        self.sends, self.cache, self.blocked = 0, {}, False

    def action(self, request):
        answer = self._action(request)
        if isinstance(request, dict) and isinstance(request.get('echo'), str):
            answer = {**answer, 'echo': request['echo']}
        return answer

    def _action(self, request):
        if (not isinstance(request, dict) or not isinstance(request.get('action'), str)
                or not isinstance(request.get('params'), dict)
                or ('echo' in request and not isinstance(request['echo'], str))):
            return response(10001, 'Expected action string, params object and optional echo string')
        action, params = request['action'], request['params']
        if action not in SUPPORTED:
            return response(10002, 'Unsupported action')
        if action == 'get_supported_actions':
            return response(data=list(SUPPORTED))
        if action == 'get_version':
            return response(data={'impl': 'ncut-wechat-native-text', 'version': '0.1.0',
                                  'onebot_version': '12', 'wechat.scope': 'temporary filehelper text only',
                                  'wechat.events_enabled': False})
        if 'self' in request:
            return response(10102, 'Explicit self identities are not configured')
        request_id = params.get('wechat.request_id')
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{3,79}', request_id):
            return response(10003, 'wechat.request_id is required: 4..80 ASCII letters/digits/._-; echo is not an idempotency key')
        if params.get('detail_type') != 'private' or params.get('user_id') != 'filehelper':
            return response(10003, 'Only private user_id=filehelper is enabled')
        if set(params) - {'detail_type', 'user_id', 'message', 'wechat.request_id'}:
            return response(10004, 'Unsupported send parameter')
        message = params.get('message')
        if isinstance(message, list):
            parts = []
            for segment in message:
                if not isinstance(segment, dict) or not isinstance(segment.get('type'), str):
                    return response(10003, 'Invalid message segment')
                if segment['type'] != 'text':
                    return response(10005, 'Only text segments are supported; media is not converted to text')
                data = segment.get('data')
                if not isinstance(data, dict) or not isinstance(data.get('text'), str):
                    return response(10006, 'Text segment requires data.text string')
                if set(segment) - {'type', 'data'} or set(data) - {'text'}:
                    return response(10007, 'Unsupported text segment data')
                parts.append(data['text'])
            message = ''.join(parts)
        if not isinstance(message, str) or not message or '\0' in message:
            return response(10003, 'message must be nonempty text without NUL')
        try:
            encoded = message.encode('utf-8')
        except UnicodeError:
            return response(10003, 'message must contain valid UTF-8 text')
        if len(encoded) > 1024:
            return response(10003, 'message exceeds 1024 UTF-8 bytes')
        digest = hashlib.sha256(encoded).hexdigest()
        if request_id in self.cache:
            previous = self.cache[request_id]
            if previous['digest'] != digest:
                return response(10003, 'REQUEST_ID_CONFLICT: content differs for this request ID')
            return previous['response']
        if self.blocked or self.sends >= self.max_sends:
            return response(36001, 'Session send limit reached or an earlier send requires inspection',
                            {'wechat.request_id': request_id, 'wechat.automatic_retry_allowed': False})
        self.sends += 1
        try:
            result = self.sender(message, request_id, 'filehelper', self.action_timeout)
            answer = native_response(result, request_id)
        except Exception:
            # Exception text may include private paths/content; the backend keeps diagnostics.
            answer = response(20002, 'Native backend failed; inspect the original request before retry',
                              {'wechat.request_id': request_id, 'wechat.automatic_retry_allowed': False})
        self.blocked = answer['status'] != 'ok'
        self.cache[request_id] = {'digest': digest, 'response': answer}
        return answer


class Handler(BaseHTTPRequestHandler):
    server_version = 'NCUT-OneBot/0.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(min(5, max(.05, self.server.deadline - time.monotonic())))

    def log_message(self, *_args):
        pass  # Never log URLs, Authorization, echo or message bodies.

    def reply(self, code, value):
        body = json.dumps(value, ensure_ascii=True, allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass

    def do_POST(self):
        target = urllib.parse.urlsplit(self.path)
        if target.path != '/':
            return self.reply(404, response(10001, 'Endpoint is /'))
        auth = self.headers.get('Authorization')
        if auth is None:
            token = urllib.parse.parse_qs(target.query).get('access_token', [''])[0]
            auth = 'Bearer ' + token
        if not hmac.compare_digest(auth.encode(), ('Bearer ' + self.server.token).encode()):
            return self.reply(401, response(10001, 'Unauthorized'))
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, response(10001, 'Only application/json is supported'))
        if time.monotonic() >= self.server.deadline:
            return self.reply(200, response(36001, 'Session deadline reached'))
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise ValueError('A single Content-Length is required')
            size = int(self.headers['Content-Length'])
            if not 0 < size <= MAX_BODY:
                raise ValueError('Request body is empty or too large')
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError('Incomplete request body')
            request = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeError, TimeoutError):
            return self.reply(200, response(10001, 'Invalid JSON action request or body length'))
        if time.monotonic() >= self.server.deadline:
            return self.reply(200, response(36001, 'Session deadline reached'))
        self.server.adapter.action_timeout = min(self.server.adapter.action_timeout,
                                                max(.05, self.server.deadline - time.monotonic()))
        answer = self.server.adapter.action(request)
        self.server.record('running')
        self.reply(200, answer)

    def do_GET(self):
        self.reply(405, response(10001, 'Use POST'))

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = do_GET


class SessionServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, adapter, session_path, duration=600, owner=None):
        if not 1 <= duration <= 3600:
            raise ValueError('duration must be 1..3600 seconds')
        self.adapter, self.session_path = adapter, Path(session_path)
        self.owner = owner or owner_identity()[:2]
        self.deadline, self.expires_at = time.monotonic() + duration, time.time() + duration
        self.token, self.stop_requested = secrets.token_urlsafe(32), False
        self.session_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.session_path.parent.is_symlink():
            raise ValueError('Session directory must not be a symlink')
        self.session_path.parent.chmod(0o700)
        if os.geteuid() == 0:
            os.chown(self.session_path.parent, *self.owner)
        import fcntl
        self.lock_fd = os.open(str(self.session_path) + '.lock',
                               os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fchmod(self.lock_fd, 0o600)
            if os.geteuid() == 0:
                os.fchown(self.lock_fd, *self.owner)
            if self.session_path.exists():
                previous = read_private(self.session_path, self.owner[0])
                if previous.get('pending_backend'):
                    raise ValueError('Previous pending native operation must be inspected before a new session')
            super().__init__(('127.0.0.1', 0), Handler)
            self.timeout = .2
            if isinstance(self.adapter.sender, BackendProcess):
                self.adapter.sender.on_pending = lambda: self.record('running')
            self.record('running')
        except BaseException:
            os.close(self.lock_fd)
            self.lock_fd = None
            if hasattr(self, 'socket'):
                self.server_close()
            raise

    def record(self, status):
        pending = getattr(self.adapter.sender, 'pending', None)
        child = getattr(self.adapter.sender, 'process', None)
        if child is not None:
            child.poll()  # Reap finished children; uncertainty still requires inspection.
        value = {'status': status, 'pid': os.getpid(), 'url': 'http://127.0.0.1:%d/' % self.server_port,
                 'expires_at': self.expires_at, 'max_sends': self.adapter.max_sends,
                 'sends': self.adapter.sends, 'blocked': self.adapter.blocked,
                 'pending_backend': pending, 'events_enabled': False,
                 'scope': 'native personal identity; private filehelper text only'}
        if status == 'running':
            value['access_token'] = self.token
        else:
            value['stopped_at'] = time.time()
        private_json(self.session_path, value, self.owner)

    def run(self):
        reason = 'stopped'
        try:
            while not self.stop_requested and time.monotonic() < self.deadline:
                self.handle_request()
            reason = 'stopped' if self.stop_requested else 'expired'
        finally:
            self.server_close()
            if getattr(self.adapter.sender, 'pending', None):
                reason += '_pending_backend'
            try:
                self.record(reason)
            finally:
                if self.lock_fd is not None:
                    os.close(self.lock_fd)
                    self.lock_fd = None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def call(request, session_path=None, timeout=120):
    session = read_private(Path(session_path or default_session()), owner_identity()[0])
    endpoint = urllib.parse.urlsplit(session.get('url', ''))
    if (session.get('status') != 'running' or session.get('expires_at', 0) <= time.time()
            or endpoint.scheme != 'http' or endpoint.hostname != '127.0.0.1'
            or endpoint.username or endpoint.password or endpoint.path != '/'
            or not endpoint.port or endpoint.query or endpoint.fragment):
        raise ValueError('No active private loopback session')
    token = session.get('access_token')
    if not isinstance(token, str) or not token:
        raise ValueError('Session has no access token')
    req = urllib.request.Request(session['url'], json.dumps(request, allow_nan=False).encode(),
                                 {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    # No system proxy and no redirect can receive the local Bearer token.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=timeout) as reply:
        return json.load(reply)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['_backend']:
        try:
            data = json.load(sys.stdin)
            result = backend.trial(True, data['text'], data['request_id'], recipient=data['recipient'])
        except Exception:
            result = {'status': 'backend_exception', 'automatic_retry_allowed': False}
        print(json.dumps(result, ensure_ascii=True))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve', help='explicit temporary server; sudo from desktop account')
    serve.add_argument('--duration', type=int, default=600)
    serve.add_argument('--max-sends', type=int, default=3)
    serve.add_argument('--action-timeout', type=int, default=90)
    request = commands.add_parser('call', help='read one action JSON from stdin; ordinary desktop user')
    request.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.command == 'call':
        print(json.dumps(call(json.load(sys.stdin), timeout=args.timeout), ensure_ascii=False, indent=2))
        return 0
    uid, gid, _home = owner_identity()
    if os.geteuid() != 0 or uid == 0:
        raise ValueError('serve requires sudo from the desktop account; no client was touched')
    path = default_session()
    sender = BackendProcess(path.parent, (uid, gid))
    adapter = Adapter(sender, args.max_sends, args.action_timeout)
    server = SessionServer(adapter, path, args.duration, (uid, gid))
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_args: setattr(server, 'stop_requested', True))
    print(json.dumps({'status': 'running', 'session_file': str(path),
                      'duration_seconds': args.duration, 'max_sends': args.max_sends}), flush=True)
    server.run()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, urllib.error.URLError) as error:
        # HTTP exceptions contain status, not Authorization or message bodies.
        print(json.dumps({'ok': False, 'error_type': type(error).__name__,
                          'message': 'Operation failed; inspect private session/backend state'}))
        raise SystemExit(1)
