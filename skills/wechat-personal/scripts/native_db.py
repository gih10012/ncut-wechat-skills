"""Bounded, in-memory SQLCipher4 snapshots of the owner's existing WeChat DBs."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import struct
import time

PAGE = 4096
MAX_BYTES = 256 * 1024 * 1024


def load_keys(account):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', account):
        raise ValueError('Invalid account alias')
    path = Path.home()/'.local/state/wechat-personal/native-keys'/(account+'.json')
    if not path.exists():
        raise ValueError('NATIVE_KEYS_REQUIRED: see references/workflows/native-linux.md')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Unsafe native key file permissions')
    value = json.loads(path.read_text())
    if value.get('format') != 'wcdb-sqlcipher4-raw':
        raise ValueError('Unsupported native key format')
    return value


def signature(path):
    try:
        st = path.stat()
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    except FileNotFoundError:
        return None


def stable_read(path):
    wal_path = Path(str(path)+'-wal')
    for _ in range(3):
        before = (signature(path), signature(wal_path))
        if before[0] is None:
            raise ValueError('Native database missing')
        if sum(s[2] for s in before if s) > MAX_BYTES:
            raise ValueError('DATABASE_SIZE_LIMIT: narrow the source before reading')
        try:
            with path.open('rb') as stream:
                data = stream.read(MAX_BYTES+1)
            with wal_path.open('rb') as stream:
                wal = stream.read(MAX_BYTES+1)
        except FileNotFoundError:
            wal = b''
        if before == (signature(path), signature(wal_path)):
            if len(data)+len(wal) > MAX_BYTES:
                raise ValueError('DATABASE_SIZE_LIMIT')
            return data, wal
    raise ValueError('DATABASE_BUSY: source changed while taking a snapshot; retry later')


def checksum(data, endian, state=(0, 0)):
    a, b = state
    for x, y in struct.iter_unpack(endian+'II', data):
        a = (a+x+b) & 0xffffffff
        b = (b+y+a) & 0xffffffff
    return a, b


def committed_wal(wal):
    """Ignore stale generations and uncommitted tail; reject current corruption."""
    if not wal:
        return {}, None, 0
    if len(wal) < 32:
        raise ValueError('Incomplete WAL header')
    magic, version, size = struct.unpack('>III', wal[:12])
    if magic not in (0x377f0682, 0x377f0683) or version != 3007000 or size != PAGE:
        raise ValueError('Unsupported WAL format')
    endian = '<' if magic == 0x377f0682 else '>'
    state = checksum(wal[:24], endian)
    if state != struct.unpack('>II', wal[24:32]):
        raise ValueError('WAL header checksum mismatch')
    pages, pending, db_size, frames = {}, {}, None, 0
    for offset in range(32, len(wal)-PAGE-23, PAGE+24):
        header = wal[offset:offset+24]
        if header[8:16] != wal[16:24]:
            break
        page = wal[offset+24:offset+24+PAGE]
        state = checksum(page, endian, checksum(header[:8], endian, state))
        if state != struct.unpack('>II', header[16:24]):
            raise ValueError('WAL frame checksum mismatch')
        number, commit = struct.unpack('>II', header[:8])
        if not 1 <= number <= MAX_BYTES//PAGE or commit > MAX_BYTES//PAGE:
            raise ValueError('WAL page outside bounded snapshot')
        pending[number] = page
        if commit:
            pages.update(pending)
            pending.clear()
            db_size = commit
            pages = {n: p for n, p in pages.items() if n <= commit}
            frames = (offset-32)//(PAGE+24)+1
    return pages, db_size, frames


def decrypt_page(page, number, key, mac_key):
    try:
        from Crypto.Cipher import AES
    except ImportError:
        raise ValueError('Install the optional pycryptodome dependency for native reads') from None
    if len(page) != PAGE:
        raise ValueError('Incomplete database page')
    if number != 1 and page == bytes(PAGE):
        return page  # WCDB preallocated unused pages.
    start = 16 if number == 1 else 0
    mac = hmac.new(mac_key, page[start:-64]+struct.pack('<I', number), hashlib.sha512).digest()
    if not hmac.compare_digest(mac, page[-64:]):
        raise ValueError('DATABASE_AUTH_FAILED: database changed or key needs recapture')
    plain = AES.new(key, AES.MODE_CBC, page[-80:-64]).decrypt(page[start:-80])
    return (b'SQLite format 3\x00' if number == 1 else b'')+plain+bytes(80)


def open_database(keys, relative):
    root = Path(keys['database_root']).resolve()
    path = (root/relative).resolve()
    if not path.is_relative_to(root) or relative not in keys['files']:
        raise ValueError('Database is outside the captured account')
    data, wal = stable_read(path)
    salt = bytes.fromhex(keys['files'][relative])
    if data[:16] != salt:
        raise ValueError('DATABASE_KEY_STALE: capture keys for the current client')
    key = bytes.fromhex(keys['keys'][salt.hex()])
    mac_key = hashlib.pbkdf2_hmac('sha512', key, bytes(b ^ 0x3a for b in salt), 2, 32)
    overlays, size, frames = committed_wal(wal)
    if len(data) % PAGE:
        raise ValueError('Incomplete database snapshot')
    size = size if size is not None else len(data)//PAGE
    plain = bytearray()
    for number in range(1, size+1):
        page = overlays.get(number, data[(number-1)*PAGE:number*PAGE])
        plain.extend(decrypt_page(page, number, key, mac_key))
    if plain[16:18] != b'\x10\x00' or plain[20] != 80:
        raise ValueError('Unsupported decrypted database layout')
    # The private in-memory image is already checkpointed; no disk-side WAL needed.
    plain[18:20] = b'\x01\x01'
    conn = sqlite3.connect(':memory:')
    try:
        conn.deserialize(plain)
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.row_factory = sqlite3.Row
        conn.execute('SELECT count(*) FROM sqlite_master').fetchone()
    except Exception:
        conn.close()
        raise
    return conn, {'database': relative, 'wal_committed_frames': frames,
                  'snapshot_at': int(time.time()), 'source': 'local_client_database'}
