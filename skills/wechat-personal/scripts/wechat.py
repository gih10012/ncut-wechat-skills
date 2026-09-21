#!/usr/bin/env python3
"""Personal web access and an optional existing client adapter. No daemon."""
import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import urllib.parse as up

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT.parent / 'ncut-web-api/scripts'
if not (CORE / 'ncut.py').is_file():
    raise SystemExit('Install the companion ncut-web-api skill containing the shared HTTP client')
sys.path.insert(0, str(CORE))
import ncut as access
access.ROOT = ROOT
access.STATE = Path.home() / '.local/state/wechat-personal'


class Article(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth = 0; self.body_depth = None; self.title_depth = None
        self.text = []; self.title = []; self.images = []; self.meta = {}; self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property', attrs.get('name', ''))] = attrs.get('content', '')
        if tag in ('script', 'style'): self.skip += 1
        if tag not in ('img','br','meta','link','input','hr','source','wbr','area','base','embed','param','track','col'):
            self.depth += 1
            if attrs.get('id') == 'js_content': self.body_depth = self.depth
            if attrs.get('id') == 'activity-name': self.title_depth = self.depth
        if self.body_depth and tag == 'img':
            url = attrs.get('data-src', attrs.get('src', ''))
            if url.startswith('https://'): self.images.append(url)
        if self.body_depth and tag in ('p','br','section'): self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in ('img','br','meta','link','input','hr','source','wbr','area','base','embed','param','track','col'): return
        if tag in ('script','style'): self.skip = max(0,self.skip-1)
        if self.depth == self.body_depth: self.body_depth = None
        if self.depth == self.title_depth: self.title_depth = None
        if tag not in ('img','br','meta','link','input','hr','source','wbr','area','base','embed','param','track','col'):
            self.depth = max(0,self.depth-1)

    def handle_data(self, data):
        if self.skip: return
        if self.title_depth: self.title.append(data)
        if self.body_depth: self.text.append(data)


def article(argv):
    p = argparse.ArgumentParser(); p.add_argument('--url', required=True); p.add_argument('--max-chars', type=int, default=6000)
    p.add_argument('--images', type=int, default=0, help='Include at most 8 observed image URLs only when needed')
    a = p.parse_args(argv); u = up.urlsplit(a.url)
    if access.origin(a.url) != 'https://mp.weixin.qq.com' or not (u.path == '/s' or u.path.startswith('/s/')):
        raise ValueError('Use the exact observed mp.weixin.qq.com/s article URL')
    info, raw = access.fetch(a.url, max_bytes=8_000_000)
    if not info['ok']: access.emit(info); return
    parser = Article(); parser.feed(raw.decode('utf-8', errors='replace'))
    text = re.sub(r'\n\s*\n+', '\n\n', ''.join(parser.text)).strip()
    if not text and not parser.images:
        access.emit({**info, 'ok': False, 'code': 'ARTICLE_BODY_UNAVAILABLE', 'hint': 'Current response has no article body. May require browser verification; do not retry or claim a successful read.'}); return
    limit = max(100, min(a.max_chars, 12000))
    access.emit({**info, 'title': ''.join(parser.title).strip() or parser.meta.get('og:title'), 'text': text[:limit], 'truncated': len(text)>limit, 'image_count': len(parser.images), 'image_urls': parser.images[:max(0,min(a.images,8))], 'text_layer_only': True, 'authenticated_inbox': False})


def client(argv):
    allow_write = False
    if argv and argv[0] == '--allow-write': allow_write = True; argv = argv[1:]
    reads = {('accounts','list'), ('accounts','status'), ('conversations','list'), ('conversations','search'), ('messages','history'), ('surfaces','snapshot'), ('surfaces','actions')}
    writes = {('messages','prepare-send'), ('messages','commit-send'), ('surfaces','act'), ('surfaces','share')}
    navigation = {('surfaces','open'), ('surfaces','back'), ('surfaces','close'), ('surfaces','export')}
    pair = tuple(argv[:2])
    if not (pair in reads | navigation or (argv and argv[0]=='capabilities') or (allow_write and pair in writes)):
        raise ValueError('Supported: scoped message/account reads, surface navigation; explicit --allow-write for an authorized send/action. No lifecycle/provisioning commands.')
    if pair != ('accounts','list') and '--account' not in argv and pair != ('messages','commit-send'):
        raise ValueError('Select an explicit account from accounts list')
    exe = Path.home()/'.local/bin/wechatcopilot'
    if not exe.is_file(): access.emit({'ok':False,'code':'CLIENT_NOT_CONNECTED'}); return
    env = dict(os.environ)
    for name in ['environment','state-mount.environment','swap-policy.environment']:
        file = Path.home()/'.config/wechatcopilot'/name
        if not file.exists(): continue
        for raw in access.private_read(file).splitlines():
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1)
            if re.fullmatch(r'WECHATCOPILOT_[A-Z_]+',k): env.setdefault(k,' '.join(shlex.split(v)))
    command=[str(exe),*argv]
    if '--json' not in argv: command.append('--json')
    if pair[0] == 'surfaces' and pair[1] in ('open','snapshot','act','back') and '--without-image-data' not in argv and '--screenshot-out' not in argv:
        command.append('--without-image-data')
    try: result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=25)
    except subprocess.TimeoutExpired:
        access.emit({'ok':False,'code':'CLIENT_TIMEOUT','retry_safe':pair in reads}); return
    try: value=json.loads(result.stdout)
    except ValueError: value={'ok':False,'code':'CLIENT_BAD_RESPONSE','exit_code':result.returncode}
    access.emit(value)


if __name__ == '__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='article': article(sys.argv[2:])
        elif len(sys.argv)>1 and sys.argv[1]=='native':
            if len(sys.argv) > 2 and sys.argv[2] in ('send', 'send-status'):
                from native_send_candidate import main
                operation = 'send-text' if sys.argv[2] == 'send' else 'status'
                raise SystemExit(main([operation, *sys.argv[3:]]))
            else:
                from native_messages import main
                access.emit(main(sys.argv[2:]))
        elif len(sys.argv)>1 and sys.argv[1]=='notifications':
            from notification_inbox import main
            access.emit(main(sys.argv[2:], access))
        elif len(sys.argv)>1 and sys.argv[1]=='onebot':
            from native_onebot import main
            raise SystemExit(main(sys.argv[2:]))
        elif len(sys.argv)>1 and sys.argv[1]=='bot':
            bot_python = Path.home()/'.local/share/ncut-wechat-skills/bot-venv/bin/python'
            if bot_python.is_file() and Path(sys.prefix) != bot_python.parent.parent:
                os.execv(str(bot_python), [str(bot_python), str(Path(__file__).resolve()), *sys.argv[1:]])
            from ilink import main
            access.emit(main(sys.argv[2:], access))
        elif len(sys.argv)>1 and sys.argv[1]=='login':
            from personal_login import main
            main(sys.argv[2:], access)
        elif len(sys.argv)>1 and sys.argv[1]=='client': client(sys.argv[2:])
        elif len(sys.argv)>1 and sys.argv[1]=='desktop':
            from desktop import main
            access.emit(main(sys.argv[2:]))
        else: access.run()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        access.emit({'ok':False,'code':'LOCAL_ERROR','message':str(exc) if isinstance(exc,ValueError) and not isinstance(exc,json.JSONDecodeError) else type(exc).__name__})
        sys.exit(1)
