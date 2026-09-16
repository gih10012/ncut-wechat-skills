"""Read bounded recent conversations/messages from the current Linux client."""
import argparse
import ctypes
import ctypes.util
from datetime import datetime
import hashlib
import re
import sqlite3
import xml.etree.ElementTree as ET

from native_db import load_keys, open_database


def decode_content(value):
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if value[:4] == b'\x28\xb5\x2f\xfd':
        library = ctypes.util.find_library('zstd')
        if not library:
            raise ValueError('Install libzstd for compressed message content')
        lib = ctypes.CDLL(library)
        lib.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
        lib.ZSTD_decompress.restype = ctypes.c_size_t
        lib.ZSTD_isError.argtypes = [ctypes.c_size_t]
        lib.ZSTD_isError.restype = ctypes.c_uint
        output = ctypes.create_string_buffer(1024*1024)
        size = lib.ZSTD_decompress(output, len(output), value, len(value))
        if lib.ZSTD_isError(size):
            raise ValueError('UNSUPPORTED_MESSAGE_COMPRESSION: dictionary or larger output required')
        value = output.raw[:size]
    return value.decode('utf-8', errors='replace')


def contact_names(keys):
    conn, meta = open_database(keys, 'contact/contact.db')
    try:
        return {r['username']: r['remark'] or r['nick_name'] or r['username']
                for r in conn.execute('SELECT username, remark, nick_name FROM contact')}, meta
    finally:
        conn.close()


def session_rows(keys):
    conn, meta = open_database(keys, 'session/session.db')
    try:
        rows = [dict(r) for r in conn.execute('SELECT username, unread_count, summary, last_timestamp, '
                'last_msg_type, is_hidden FROM SessionTable ORDER BY sort_timestamp DESC')]
        return rows, meta
    finally:
        conn.close()


def iso(value):
    return datetime.fromtimestamp(value).astimezone().isoformat() if value else None


def conversations(keys, query='', limit=10, unread=False):
    names, cm = contact_names(keys)
    rows, sm = session_rows(keys)
    matches = [r for r in rows if not r['is_hidden'] and
               (not unread or r['unread_count'] > 0) and
               (not query or query.casefold() in (r['username']+' '+names.get(r['username'], '')).casefold())]
    return {'ok': True, 'source': 'local_client_database', 'matched_count': len(matches),
            'items': [{'chat_id': r['username'], 'name': names.get(r['username'], r['username']),
                       'unread_count': r['unread_count'], 'last_time': iso(r['last_timestamp']),
                       'preview': decode_content(r['summary'])[:160]} for r in matches[:limit]],
            'snapshots': [sm, cm], 'marks_read': False, 'server_sync_verified': False}


def resolve_chat(keys, query, names):
    rows, _ = session_rows(keys)
    exact = [r['username'] for r in rows if r['username'] == query]
    if not exact:
        exact = [r['username'] for r in rows if names.get(r['username']) == query]
    if len(exact) != 1:
        raise ValueError('CHAT_NOT_UNIQUE: use conversations --query and select its exact chat_id')
    return exact[0]


def message_body(row, max_chars):
    text = decode_content(row['message_content'] or row['compress_content'])
    sender = row.get('sender_id')
    if sender and text.startswith(sender+':\n'):
        text = text[len(sender)+2:]
    kind = row['local_type'] & 0xffff
    result = {'type': kind}
    if kind == 49:
        try:
            app = ET.fromstring(text).find('appmsg')
            if app is not None:
                text = app.findtext('title') or '[分享消息]'
                url = app.findtext('url')
                if url:
                    result['url'] = url[:4096]
                result['description'] = (app.findtext('des') or '')[:max_chars]
        except ET.ParseError:
            pass
    elif kind in (3, 34, 43, 47):
        text = {3: '[图片]', 34: '[语音]', 43: '[视频]', 47: '[表情]'}[kind]
    result.update(text=text[:max_chars], truncated=len(text) > max_chars)
    return result


def messages(keys, chat, limit=20, before=None, since=None, max_chars=1000):
    names, cm = contact_names(keys)
    chat_id = resolve_chat(keys, chat, names)
    table = 'Msg_'+hashlib.md5(chat_id.encode()).hexdigest()
    sources = sorted(f for f in keys['files'] if re.fullmatch(r'message/(?:biz_)?message_\d+\.db', f))
    if len(sources) > 16:
        raise ValueError('Too many message shards; narrow the source')
    items, snapshots, found = [], [cm], False
    for relative in sources:
        conn, meta = open_database(keys, relative)
        try:
            if not conn.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?', ('table', table)).fetchone():
                continue
            found = True
            snapshots.append(meta)
            where, values = [], []
            if before is not None:
                where.append('m.create_time < ?'); values.append(before)
            if since is not None:
                where.append('m.create_time >= ?'); values.append(since)
            sql = ('SELECT m.local_id, m.server_id, m.local_type, m.create_time, m.sort_seq, '
                   'm.message_content, m.compress_content, n.user_name AS sender_id '
                   'FROM "'+table+'" m LEFT JOIN Name2Id n ON n.rowid=m.real_sender_id')
            if where:
                sql += ' WHERE '+' AND '.join(where)
            sql += ' ORDER BY m.create_time DESC, m.sort_seq DESC LIMIT ?'
            for row in conn.execute(sql, [*values, limit]):
                value = dict(row)
                value['database'] = relative
                items.append(value)
        finally:
            conn.close()
    if not found:
        raise ValueError('CHAT_HISTORY_NOT_LOCAL: no captured message table for this conversation')
    items.sort(key=lambda r: (r['create_time'], r['sort_seq']), reverse=True)
    result = []
    for row in items[:limit]:
        try:
            body = message_body(row, max_chars)
        except ValueError as exc:
            body = {'type': row['local_type'] & 0xffff, 'text': '[正文暂不可解码]', 'decode_error': str(exc)}
        result.append({'local_id': row['local_id'], 'server_id': str(row['server_id']),
                       'timestamp': row['create_time'], 'time': iso(row['create_time']),
                       'sender_id': row['sender_id'], 'sender': names.get(row['sender_id'], row['sender_id']),
                       'database': row['database'], **body})
    return {'ok': True, 'chat_id': chat_id, 'name': names.get(chat_id, chat_id), 'items': result,
            'order': 'newest_first', 'snapshots': snapshots, 'source': 'local_client_database',
            'coverage': 'messages already synced to this Linux client; media contents excluded',
            'server_sync_verified': False, 'marks_read': False}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['status', 'conversations', 'messages'])
    parser.add_argument('--account', default='me')
    parser.add_argument('--query', default='')
    parser.add_argument('--unread', action='store_true')
    parser.add_argument('--chat')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--before', type=int, help='Exclusive Unix timestamp')
    parser.add_argument('--since', type=int, help='Inclusive Unix timestamp')
    parser.add_argument('--max-chars', type=int, default=1000)
    args = parser.parse_args(argv)
    keys = load_keys(args.account)
    limit = max(1, min(args.limit, 50))
    try:
        if args.operation == 'status':
            conn, meta = open_database(keys, 'session/session.db')
            try:
                count = conn.execute('SELECT count(*) FROM SessionTable').fetchone()[0]
            finally:
                conn.close()
            return {'ok': True, 'session_count': count, 'snapshot': meta, 'native_send_verified': False}
        if args.operation == 'conversations':
            return conversations(keys, args.query, limit, args.unread)
        if not args.chat:
            raise ValueError('messages requires --chat with an exact chat_id or unique display name')
        return messages(keys, args.chat, limit, args.before, args.since, max(80, min(args.max_chars, 3000)))
    except sqlite3.DatabaseError:
        raise ValueError('NATIVE_SCHEMA_UNSUPPORTED: inspect only the relevant current schema') from None
