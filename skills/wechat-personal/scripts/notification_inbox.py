"""Bounded, owner-configured Android notification ingest; not a WeCom inbox API."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import time
from urllib.parse import urlsplit

PACKAGE = 'com.tencent.wework'
SCOPE = {'source': 'android_notification', 'complete_chat_history': False,
         'personal_inbox_verified': False}
MAX_BODY = 65536
BODY_TEMPLATE = {'package': '[from]', 'title': '[title]', 'text': '[org_content]',
                 'phone_time': '[receive_time:yyyy-MM-dd HH:mm:ss.SSS]'}


def account_dir(access, account):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', account):
        raise ValueError('Invalid account alias')
    return access.STATE / 'notification-inbox' / account


def private_host(value):
    address = ipaddress.IPv4Address(value)
    if address.is_unspecified or address.is_multicast or not address.is_private:
        raise ValueError('Use a specific local/private IPv4 address')
    return str(address)


def database(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
            raise ValueError('Expected an owner-only regular database')
    finally:
        os.close(fd)
    db = sqlite3.connect(path, timeout=3)
    db.execute('''CREATE TABLE IF NOT EXISTS notifications (
        sequence INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
        phone_time TEXT NOT NULL, received_at TEXT NOT NULL,
        title TEXT NOT NULL, text TEXT NOT NULL)''')
    return db


def normalize(payload):
    if not isinstance(payload, dict) or payload.get('package') != PACKAGE:
        raise ValueError('WECOM_NOTIFICATION_REQUIRED')
    result = {'package': PACKAGE}
    for key, limit in [('title', 4096), ('text', 32768), ('phone_time', 32)]:
        value = payload.get(key)
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError('INVALID_NOTIFICATION_FIELDS')
        result[key] = value
    if not result['title'].strip() and not result['text'].strip():
        raise ValueError('EMPTY_NOTIFICATION')
    try:
        datetime.strptime(result['phone_time'], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        raise ValueError('INVALID_PHONE_TIME') from None
    return result


def store(path, payload):
    payload = normalize(payload)
    event_id = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with closing(database(path)) as db, db:
        cursor = db.execute('''INSERT OR IGNORE INTO notifications
            (event_id, phone_time, received_at, title, text) VALUES (?, ?, ?, ?, ?)''',
            (event_id, payload['phone_time'], datetime.now(timezone.utc).isoformat(),
             payload['title'], payload['text']))
        inserted = cursor.rowcount == 1
    return {'ok': True, 'event_id': event_id, 'duplicate': not inserted, **SCOPE}


def read_notifications(path, limit):
    if not path.exists():
        return {'ok': True, 'items': [], 'count': 0, **SCOPE}
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise ValueError('Expected an owner-only regular database')
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''SELECT sequence, event_id, phone_time, received_at, title, text
            FROM notifications ORDER BY sequence DESC LIMIT ?''', (max(1, min(limit, 100)),)).fetchall()
    items = [dict(row) for row in rows]
    return {'ok': True, 'items': items, 'count': len(items), **SCOPE}


def make_server(host, port, token, path):
    private_host(host)
    with closing(database(path)):
        pass

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *_):
            pass  # Never log notification bodies, credentials, or request URLs.

        def reply(self, status, data):
            raw = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if urlsplit(self.path).path == '/health':
                self.reply(200, {'ok': True, **SCOPE})
            else:
                self.reply(404, {'ok': False, 'code': 'NOT_FOUND'})

        def do_POST(self):
            if urlsplit(self.path).path != '/wecom/notifications':
                self.reply(404, {'ok': False, 'code': 'NOT_FOUND'})
                return
            auth = self.headers.get('Authorization', '').encode()
            if not hmac.compare_digest(auth, ('Bearer ' + token).encode()):
                self.reply(401, {'ok': False, 'code': 'UNAUTHORIZED'})
                return
            if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                self.reply(415, {'ok': False, 'code': 'JSON_BODY_REQUIRED'})
                return
            length = self.headers.get('Content-Length', '')
            if not length.isdecimal() or not 0 < int(length) <= MAX_BODY:
                self.reply(413, {'ok': False, 'code': 'BODY_SIZE_INVALID'})
                return
            try:
                raw = self.rfile.read(int(length))
                if len(raw) != int(length):
                    raise ValueError('INCOMPLETE_BODY')
                payload = json.loads(raw)
                normalize(payload)
            except (ValueError, UnicodeError):
                self.reply(400, {'ok': False, 'code': 'INVALID_WECOM_NOTIFICATION'})
                return
            try:
                result = store(path, payload)
            except (sqlite3.Error, OSError, ValueError):
                self.reply(503, {'ok': False, 'code': 'LOCAL_STORAGE_UNAVAILABLE'})
                return
            self.reply(200, result)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.timeout = 0.25
    return server


def setup(access, directory, host, port):
    host = private_host(host)
    if not 1024 <= port <= 65535:
        raise ValueError('Use a port between 1024 and 65535')
    config_path = directory / 'receiver.json'
    config = json.loads(access.private_read(config_path)) if config_path.exists() else {}
    token = config.get('token') or secrets.token_urlsafe(32)
    config = {'host': host, 'port': port, 'token': token}
    access.private_write(config_path, json.dumps(config))
    url = f'http://{host}:{port}/wecom/notifications'
    template = json.dumps(BODY_TEMPLATE, ensure_ascii=False, indent=2)
    guide = f'''# 企微通知补充测试（本机私有配置）

安装来源：https://github.com/pppscn/SmsForwarder/releases/tag/v3.5.0
手机与电脑连接同一可信局域网。此配置只用于本轮限时接收测试。

1. 在 SmsForwarder 开启“APP通知”及系统“通知使用权”。
2. 新建 Webhook 发送通道，方法 POST，地址：`{url}`。
3. 请求头：

```text
Content-Type: application/json
Authorization: Bearer {token}
```

4. 自定义请求参数使用下面的 JSON；成功响应关键字可填 `"ok":true`：

```json
{template}
```

5. 新建 APP 通知转发规则，包名完全匹配 `com.tencent.wework`，选择上述发送通道。
   只开启这条企微规则；保持“自动消除通知”关闭。短信、来电、远程控制功能无需开启。
6. 设置完成后在提问卡片回复“已设置”，再启动限时接收。

连通检查：接收端运行时，用手机浏览器访问 `http://{host}:{port}/health`。
此检查只证明网络连通。验收必须在手机收到一条实际企微文字通知后，从技能读回同一文字。
通道自带的模拟测试不等于实际企微消息成功。

此入口只转存通知展示的标题/文字，不访问完整聊天，不保证静音群、隐藏内容或历史消息。
收件人、群名称只能按通知原文展示，不能把通知标题推断成可靠的会话ID。
'''
    guide_path = directory / 'phone-setup.md'
    access.private_write(guide_path, guide)
    return {'ok': True, 'code': 'NOTIFICATION_SETUP_PREPARED', 'guide': str(guide_path),
            'url': url, 'started': False, **SCOPE}


def main(argv, access):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'serve', 'list'])
    parser.add_argument('--account', default='me')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=16792)
    parser.add_argument('--seconds', type=int, default=300)
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args(argv)
    directory = account_dir(access, args.account)
    if args.action == 'setup':
        return setup(access, directory, args.host, args.port)
    if args.action == 'list':
        return read_notifications(directory / 'notifications.sqlite', args.limit)
    config_path = directory / 'receiver.json'
    if not config_path.exists():
        return {'ok': False, 'code': 'NOTIFICATION_SETUP_REQUIRED', **SCOPE}
    if not 1 <= args.seconds <= 900:
        raise ValueError('Receiver duration must be between 1 and 900 seconds')
    config = json.loads(access.private_read(config_path))
    deadline = time.monotonic() + args.seconds
    server = make_server(config['host'], config['port'], config['token'], directory / 'notifications.sqlite')
    print(json.dumps({'ok': True, 'code': 'NOTIFICATION_RECEIVER_LISTENING',
                      'host': config['host'], 'port': config['port'],
                      'seconds': args.seconds, **SCOPE}), flush=True)
    try:
        while time.monotonic() < deadline:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return {'ok': True, 'code': 'NOTIFICATION_RECEIVER_STOPPED', **SCOPE}
