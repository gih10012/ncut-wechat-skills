#!/usr/bin/env python3
"""One-shot, owner-scoped Linux WeChat raw-key capture; never prints key material."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import pwd
import re
import stat
import struct
import tempfile
import time

PATTERN=re.compile(rb"x'([0-9a-fA-F]{96}|[0-9a-fA-F]{64})'")


def verified(key,page):
    if len(key)!=32 or len(page)!=4096:return False
    salt=bytes(b^0x3a for b in page[:16])
    mac_key=hashlib.pbkdf2_hmac('sha512',key,salt,2,32)
    actual=hmac.new(mac_key,page[16:-64]+struct.pack('<I',1),hashlib.sha512).digest()
    return hmac.compare_digest(actual,page[-64:])


def candidates(data,pages):
    found={}
    for match in PATTERN.finditer(data):
        raw=bytes.fromhex(match[1].decode('ascii'));key=raw[:32]
        salts=[raw[32:].hex()] if len(raw)==48 else pages
        for salt in salts:
            if salt in pages and verified(key,pages[salt]):found[salt]=key.hex()
    return found


def owner():
    uid=int(os.environ.get('SUDO_UID',os.getuid())) if os.getuid()==0 else os.getuid()
    if uid==0:raise ValueError('Run sudo from your normal desktop account; do not use a root login')
    return pwd.getpwuid(uid)


def processes(uid):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if p.stat().st_uid==uid and Path(os.readlink(p/'exe')).name in ('wechat','WeChat','weixin','Weixin'):
                found.append(int(p.name))
        except OSError:pass
    return found


def inventory(home):
    roots=[]
    for base in (home/'Documents/xwechat_files',home/'xwechat_files'):
        if base.exists():roots.extend(p for p in base.glob('*/db_storage') if p.is_dir())
    roots=list(dict.fromkeys(p.resolve() for p in roots))
    if len(roots)!=1:raise ValueError('Expected one local account database directory; select the current account before capture')
    root=roots[0];pages={};files={}
    for p in root.rglob('*.db'):
        if any('corrupt' in name for name in p.parts) or p.is_symlink():continue
        if len(files)>=64:raise ValueError('Database inventory exceeds the bounded capture scope')
        with p.open('rb') as f:page=f.read(4096)
        if len(page)!=4096 or page[:16]==b'SQLite format 3\x00':continue
        salt=page[:16].hex();pages[salt]=page;files[str(p.relative_to(root))]=salt
    if not pages:raise ValueError('No supported encrypted database headers found')
    return root,pages,files


def ranges(pid):
    result=[]
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        parts=line.split(maxsplit=5)
        if parts[1]!='rw-p':continue
        begin,end=(int(x,16) for x in parts[0].split('-'))
        name=parts[5] if len(parts)>5 else ''
        result.append((name!='[heap]',bool(name),begin,end))
    return [(a,b) for _,_,a,b in sorted(result)]


def scan(fd,regions,pages,max_bytes,seconds):
    found={};total=0;start=time.monotonic()
    for begin,end in regions:
        offset=begin;tail=b''
        while offset<end and total<max_bytes and time.monotonic()-start<seconds:
            amount=min(4*1024*1024,end-offset,max_bytes-total)
            try:data=os.pread(fd,amount,offset)
            except OSError:break
            if not data:break
            found.update(candidates(tail+data,pages))
            offset+=len(data);total+=len(data);tail=data[-100:]
            if len(found)==len(pages):return found,total
        if total>=max_bytes or time.monotonic()-start>=seconds:break
    return found,total


def private_save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    st=path.parent.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid():raise ValueError('Unsafe private output directory')
    path.parent.chmod(0o700)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.keys-')
    try:
        with os.fdopen(fd,'w') as stream:json.dump(value,stream)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['status','capture']);p.add_argument('--account',default='me')
    p.add_argument('--pid',type=int);p.add_argument('--max-mib',type=int,default=256);p.add_argument('--seconds',type=int,default=15)
    args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.account):raise ValueError('Invalid account alias')
    who=owner();home=Path(who.pw_dir);pids=processes(who.pw_uid)
    output=home/'.local/state/wechat-personal/native-keys'/(args.account+'.json')
    if args.operation=='status':
        print(json.dumps({'ok':True,'process_count':len(pids),'keys_file_exists':output.is_file(),'native_messages_verified':False}));return
    pid=args.pid if args.pid is not None else pids[0] if len(pids)==1 else None
    if pid not in pids:raise ValueError('Select exactly one running WeChat process owned by your desktop account')
    regions=ranges(pid)
    try:fd=os.open(f'/proc/{pid}/mem',os.O_RDONLY)
    except PermissionError:raise ValueError('PROCESS_MEMORY_PERMISSION_REQUIRED: run this capture once with sudo; no ptrace policy change is needed') from None
    try:
        # Only opening this one verified process requires privilege. Permanently
        # drop privileges before reading databases or creating credential files.
        if os.getuid()==0:
            os.setgroups([]);os.setgid(who.pw_gid);os.setuid(who.pw_uid)
        root,pages,files=inventory(home)
        keys,total=scan(fd,regions,pages,min(max(args.max_mib,1),1024)*1024*1024,min(max(args.seconds,1),45))
    finally:os.close(fd)
    if not keys:
        print(json.dumps({'ok':False,'code':'NO_VERIFIED_KEYS','scanned_mib':round(total/1048576,1),'existing_keys_preserved':True}));return
    private_save(output,{'format':'wcdb-sqlcipher4-raw','database_root':str(root),'files':{f:s for f,s in files.items() if s in keys},'keys':keys,'captured_at':int(time.time())})
    print(json.dumps({'ok':True,'verified_key_count':len(keys),'database_count':sum(s in keys for s in files.values()),'unmatched_salt_count':len(pages)-len(keys),'scanned_mib':round(total/1048576,1),'private_file':str(output),'native_messages_verified':False}))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as error:
        print(json.dumps({'ok':False,'code':'CAPTURE_UNAVAILABLE','message':str(error) if isinstance(error,ValueError) else type(error).__name__}));raise SystemExit(1)
