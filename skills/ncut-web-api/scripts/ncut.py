#!/usr/bin/env python3
"""Bounded service discovery and origin-scoped HTTP sessions. Python stdlib only."""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import sys
import tempfile
import urllib.error as ue
import urllib.parse as up
import urllib.request as ur
from zoneinfo import ZoneInfo
from knowledge import search, capability

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / '.local/state/ncut-web-api'
MAX_BYTES = 2_000_000
SECRET = re.compile(r'(?i)(token|ticket|password|passwd|secret|authorization|cookie|session|csrf|code)')


def now():
    return dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def emit(value):
    def clean(v):
        if isinstance(v, dict):
            return {k: '[REDACTED]' if re.fullmatch(r'(?i)(?:access[_-]?token|refresh[_-]?token|token|password|passwd|secret|authorization|cookie|set-cookie)', k) else clean(x) for k, x in v.items()}
        if isinstance(v, list): return [clean(x) for x in v]
        return v
    print(json.dumps(clean(value), ensure_ascii=False, indent=2))


def registry():
    return json.loads((ROOT / 'references/services.json').read_text())['services']


def service(alias):
    found = [s for s in registry() if alias.casefold() in [s['id'].casefold(), *[x.casefold() for x in s['aliases']]]]
    if len(found) != 1: raise ValueError('Unknown or ambiguous service; run registry')
    return found[0]


def origin(url):
    p = up.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only registered HTTPS origins are accepted')
    return 'https://' + p.hostname.lower()


def allowed_origins():
    return {o for s in registry() for o in s['origins']}


def safe_url(url):
    p = up.urlsplit(url)
    return up.urlunsplit((p.scheme, p.netloc, p.path, '', ''))


def relative_url(s, path):
    if not path.startswith('/') or path.startswith('//') or '\\' in path or up.urlsplit(path).fragment:
        raise ValueError('Use an observed absolute relative path without fragment')
    return s['origins'][0] + path


def private_write(path, data):
    if path.is_relative_to(STATE):
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        root_stat = STATE.lstat()
        if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.getuid(): raise ValueError('Unsafe account state root')
        STATE.chmod(0o700)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    st = path.parent.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise ValueError('Unsafe private directory')
    path.parent.chmod(0o700)
    fd, temp = tempfile.mkstemp(prefix='.save-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f: f.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def private_read(path):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o077:
        raise ValueError('Expected an owner-only regular file (0600)')
    return path.read_text()


def account_path(account):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', account): raise ValueError('Invalid account alias')
    return STATE / 'accounts' / (account + '.json')


def load_session(account):
    if not account: return {'cookies': [], 'headers': {}}
    path = account_path(account)
    if not path.exists(): raise ValueError('SESSION_MISSING: import this account browser state once')
    return json.loads(private_read(path))


def scoped_headers(state, url):
    dest = origin(url); host = up.urlsplit(url).hostname; path = up.urlsplit(url).path or '/'
    cookies = []; epoch = dt.datetime.now().timestamp()
    for c in state.get('cookies', []):
        domain = c['domain'].lower(); cp = c.get('path', '/')
        matches = host == domain or (domain.startswith('.') and (host == domain[1:] or host.endswith(domain)))
        path_matches = path == cp or (path.startswith(cp) and (cp.endswith('/') or path[len(cp):].startswith('/')))
        if matches and path_matches and (c.get('expires', -1) <= 0 or c['expires'] > epoch):
            cookies.append((len(cp), c['name'] + '=' + c['value']))
    headers = dict(state.get('headers', {}).get(dest, {}))
    if cookies: headers['Cookie'] = '; '.join(v for _, v in sorted(cookies, reverse=True))
    headers['User-Agent'] = state.get('user_agent') or 'Mozilla/5.0 Personal-Service-Access/1.0'
    return headers


class NoRedirect(ur.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def fetch(url, *, method='GET', data=None, content_type=None, state=None, expect=None, timeout=12, max_bytes=MAX_BYTES, cookie_jar=None):
    if origin(url) not in allowed_origins(): raise ValueError('Destination is not registered')
    headers = scoped_headers(state or {}, url)
    handlers = [NoRedirect]
    if cookie_jar is not None:
        headers.pop('Cookie', None)
        handlers.append(ur.HTTPCookieProcessor(cookie_jar))
    if content_type: headers['Content-Type'] = content_type
    req = ur.Request(url, data=data, method=method, headers=headers)
    started = now()
    try: response = ur.build_opener(*handlers).open(req, timeout=timeout)
    except ue.HTTPError as exc: response = exc
    except (ue.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, 'reason', exc)
        kind = 'TLS_ERROR' if isinstance(reason, ssl.SSLError) else 'DNS_ERROR' if isinstance(reason, socket.gaierror) else 'TIMEOUT' if isinstance(reason, (TimeoutError, socket.timeout)) else 'NETWORK_ERROR'
        return {'ok': False, 'code': kind, 'url': safe_url(url), 'fetched_at': started}, b''
    with response:
        status = response.status; location = response.headers.get('Location')
        if 300 <= status < 400 and location:
            return {'ok': False, 'code': 'REDIRECT', 'status': status, 'url': safe_url(url), 'location': safe_url(up.urljoin(url, location)), 'fetched_at': started}, b''
        raw = response.read(max_bytes + 1)
        ct = response.headers.get_content_type(); charset = response.headers.get_content_charset() or 'utf-8'
    info = {'ok': 200 <= status < 300, 'status': status, 'url': safe_url(url), 'content_type': ct, 'fetched_at': started}
    if len(raw) > max_bytes: return {**info, 'ok': False, 'code': 'RESPONSE_TOO_LARGE'}, b''
    text = raw.decode(charset, errors='replace'); info['sha256'] = hashlib.sha256(raw).hexdigest()
    is_document = ct not in ('application/javascript','text/javascript','application/json') and text.lstrip('\ufeff \t\r\n').startswith('<')
    if status in (401, 403): info.update(ok=False, code='AUTH_REQUIRED' if status == 401 else 'FORBIDDEN')
    elif not info['ok']: info['code'] = 'HTTP_ERROR'
    elif is_document and re.search(r'<title>\s*出错页面\s*</title>', text, re.I) and '您没有访问该功能的权限' in text:
        info.update(ok=False, code='FORBIDDEN')
    elif is_document and up.urlsplit(url).hostname.endswith('.ncut.edu.cn') and re.search(r'''location(?:\.href)?\s*=\s*["']https://sso\.ncut\.edu\.cn/sso/login(?:[?"'])''', text):
        info.update(ok=False, code='AUTH_REQUIRED')
    elif is_document and re.search(r'<input[^>]+type=[\"\']password|统一身份认证|短信验证码', text, re.I) and ('<html' in text.lower() or '<form' in text.lower()):
        info.update(ok=False, code='AUTH_REQUIRED')
    elif expect == 'json':
        try:
            value = json.loads(text); info['data'] = value
            if isinstance(value, dict) and str(value.get('code', '')) in ('401', '403'):
                info.update(ok=False, code='AUTH_REQUIRED' if str(value['code']) == '401' else 'FORBIDDEN')
            elif isinstance(value, dict) and value.get('e') == 'UN_AUTH':
                info.update(ok=False, code='AUTH_REQUIRED')
            elif isinstance(value, dict) and 'e' in value and value['e'] != 'OK':
                info.update(ok=False, code='BUSINESS_ERROR')
        except ValueError: info.update(ok=False, code='RESPONSE_UNEXPECTED')
    return info, raw


def catalog_rows(raw):
    candidates = []
    for encoded in re.findall(r"vjson\s*=\s*mini\.decode\('(.*?)'\)", raw.decode('utf-8'), re.S):
        try: rows = json.loads(encoded)
        except ValueError: continue
        if isinstance(rows, list) and rows and all(isinstance(v, dict) and 'name' in v and 'id' in v for v in rows): candidates.append(rows)
    if not candidates: raise ValueError('CATALOG_SCHEMA_CHANGED: inspect current directory source')
    return max(candidates, key=len)


def parse_catalog(raw):
    result = []
    for row in catalog_rows(raw):
        entries = []
        for group in row.get('service', []):
            for entry in group.get('blArr', []):
                for key in ('blpcurl', 'blmurl'):
                    if not entry.get(key): continue
                    u = up.urljoin('https://service.ncut.edu.cn/EIP/', entry[key]); p = up.urlsplit(u)
                    if p.scheme != 'https' or any(SECRET.search(k) for k, _ in up.parse_qsl(p.query)): continue
                    entries.append({'name': entry.get('blname', ''), 'url': u, 'client': 'mobile' if key == 'blmurl' else 'web'})
        hint = 'retired_or_moved' if any(v in row['name'] for v in ('停用', '转移', '转至')) else 'test_or_trial' if any(v in row['name'] for v in ('测试', '试运行')) else 'listed_permission_unverified'
        result.append({'id': row['id'], 'name': row['name'], 'department': row.get('deptName'), 'availability': hint, 'entries': entries})
    return result


class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs); key = 'src' if tag in ('script', 'iframe') else 'action' if tag == 'form' else 'href'
        if tag in ('script', 'iframe', 'form', 'a') and attrs.get(key): self.links.append({'kind': tag, 'url': attrs[key]})


def pairs(values):
    result = {}
    for item in values or []:
        if '=' not in item: raise ValueError('Expected KEY=VALUE')
        k, v = item.split('=', 1)
        if SECRET.search(k): raise ValueError('Use private files for secrets, not command arguments')
        result[k] = v
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('registry'); q.add_argument('service', nargs='?')
    q = sub.add_parser('knowledge'); q.add_argument('--query', required=True); q.add_argument('--details', action='store_true', help='Include the matched contract and workflow bodies')
    q = sub.add_parser('login'); q.add_argument('operation', nargs='?', default='start', choices=['start','finish','status'])
    q.add_argument('--account', default='me'); q.add_argument('--service'); q.add_argument('--open', action='store_true', help='Open the existing login profile without checking saved HTTP credentials')
    q = sub.add_parser('catalog'); q.add_argument('--query', default=''); q.add_argument('--limit', type=int, default=8); q.add_argument('--cached', action='store_true'); q.add_argument('--alternatives',action='store_true')
    q.add_argument('--resolve',action='store_true'); q.add_argument('--account')
    q = sub.add_parser('favorite'); q.add_argument('operation',choices=['show','set','verify']); q.add_argument('--account',required=True); q.add_argument('--query',required=True); q.add_argument('--value',choices=['yes','no']); q.add_argument('--allow-write',action='store_true')
    q = sub.add_parser('timetable'); q.add_argument('--account', required=True); q.add_argument('--term'); q.add_argument('--week', choices=['all','current'], default='all'); q.add_argument('--date'); q.add_argument('--output')
    q = sub.add_parser('classrooms'); q.add_argument('--account', required=True); q.add_argument('--date', required=True); q.add_argument('--start', required=True); q.add_argument('--end', required=True)
    q.add_argument('--campus', default='校本部'); q.add_argument('--query', default=''); q.add_argument('--limit', type=int, default=8); q.add_argument('--output')
    q = sub.add_parser('task'); tq=q.add_subparsers(dest='operation',required=True)
    a=tq.add_parser('draft'); a.add_argument('--account',required=True); a.add_argument('--intent',required=True); a.add_argument('--key',required=True); a.add_argument('--validation-only',action='store_true')
    a=tq.add_parser('show'); a.add_argument('id'); tq.add_parser('list')
    q=sub.add_parser('reservation'); rq=q.add_subparsers(dest='operation',required=True)
    a=rq.add_parser('calendar'); a.add_argument('--account',required=True); a.add_argument('--site',required=True); a.add_argument('--date',required=True); a.add_argument('--limit',type=int,default=8)
    a=rq.add_parser('rules'); a.add_argument('--account',required=True); a.add_argument('--site',required=True)
    for name in ('probe', 'discover', 'source', 'request'):
        q = sub.add_parser(name); q.add_argument('service'); q.add_argument('--path'); q.add_argument('--account'); q.add_argument('--timeout', type=float, default=12)
        if name == 'source': q.add_argument('--match', action='append', default=[])
        if name == 'request':
            q.add_argument('--capability', required=True); q.add_argument('--method', default='GET', choices=['GET','HEAD','POST','PUT','PATCH','DELETE'])
            q.add_argument('--query', action='append'); q.add_argument('--form', action='append'); q.add_argument('--body-file'); q.add_argument('--allow-write', action='store_true')
            q.add_argument('--limit', type=int, default=8); q.add_argument('--fields', help='Comma-separated top-level row fields')
    q = sub.add_parser('session'); qs = q.add_subparsers(dest='operation', required=True)
    for name in ('status', 'import'):
        a = qs.add_parser(name); a.add_argument('--account', required=True)
        if name == 'import': a.add_argument('--file', required=True)
    args = p.parse_args()
    if args.cmd == 'favorite':
        from hall import favorite
        favorite(args); return
    if args.cmd == 'login':
        from school_login import main as login_main
        login_main(args); return
    if args.cmd == 'timetable':
        from academic import timetable
        timetable(args); return
    if args.cmd == 'classrooms':
        from classrooms import classrooms
        classrooms(args); return
    if args.cmd == 'task':
        from task_drafts import main as task_main
        task_main(args); return
    if args.cmd == 'reservation':
        from reservation import calendar, rules
        (calendar if args.operation == 'calendar' else rules)(args); return
    if args.cmd == 'registry': emit(service(args.service) if args.service else registry()); return
    if args.cmd == 'knowledge': emit(search(ROOT, args.query, details=args.details)); return
    if args.cmd == 'session':
        dest = account_path(args.account)
        if args.operation == 'status':
            state = load_session(args.account) if dest.exists() else {}
            emit({'account': args.account, 'saved': bool(state), 'imported_at': state.get('imported_at'), 'cookie_count': len(state.get('cookies', [])), 'header_origins': list(state.get('headers', {})), 'live_identity_verified': False}); return
        data = json.loads(private_read(Path(args.file).expanduser())); hosts = {up.urlsplit(o).hostname for o in allowed_origins()}; cookies = []
        for c in data.get('cookies', []):
            domain = c['domain'].lower()
            if domain.lstrip('.') not in hosts and not (domain == '.ncut.edu.cn' and any(h.endswith('.ncut.edu.cn') for h in hosts)): continue
            if any(ch in c['name'] + c['value'] for ch in '\r\n;') or not c.get('path', '/').startswith('/'): raise ValueError('Invalid cookie format')
            cookies.append(c)
        headers = {}
        for o, values in data.get('headers', {}).items():
            if o not in allowed_origins(): continue
            for k, v in values.items():
                if not re.fullmatch(r'(?i)(authorization|token|x-token|x-auth-token|x-csrf-token|x-xsrf-token)', k) or not isinstance(v, str) or '\n' in v or '\r' in v: raise ValueError('Only exact-origin authentication/CSRF headers may be imported')
            headers[o] = values
        if not cookies and not any(headers.values()): raise ValueError('No registered credentials found; existing session preserved')
        user_agent=data.get('user_agent')
        if user_agent is not None and (not isinstance(user_agent,str) or '\r' in user_agent or '\n' in user_agent or len(user_agent)>1000):raise ValueError('Invalid captured User-Agent')
        private_write(dest, json.dumps({'cookies': cookies, 'headers': headers, 'user_agent':user_agent, 'imported_at': now()}, ensure_ascii=False))
        emit({'ok': True, 'account': args.account, 'cookie_count': len(cookies), 'header_origins': list(headers), 'live_identity_verified': False}); return
    if args.cmd == 'catalog':
        if args.resolve:
            if not args.account or not args.query or args.cached or args.alternatives:
                raise ValueError('catalog --resolve requires --account and an exact --query; use without --cached/--alternatives')
            from hall import resolve_entry
            emit(resolve_entry(args.account,args.query));return
        if args.alternatives:
            from alternatives import catalog_alternatives
            catalog_alternatives(args);return
        cache = STATE / 'cache/service-catalog.json'
        if args.cached:
            value = json.loads(cache.read_text()); info = {'ok': True, 'source': 'cached', 'fetched_at': value['verified_at']}; rows = value['services']
        else:
            info, raw = fetch(service('hall')['entry'])
            if not info['ok']: emit(info); return
            rows = parse_catalog(raw); value = {'verified_at': info['fetched_at'], 'source': info['url'], 'services': rows}
            old = json.loads(cache.read_text()) if cache.exists() else {}
            if old.get('services') != rows: private_write(cache, json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            info['source'] = 'live'
        selected = [r for r in rows if args.query.casefold() in json.dumps(r, ensure_ascii=False).casefold()]; limit = max(1, min(args.limit, 30))
        emit({**info, 'total': len(rows), 'matched': len(selected), 'services': selected[:limit]}); return
    s = service(args.service); url = relative_url(s, args.path) if args.path else s['entry'].split('#')[0]
    state = load_session(args.account); method = 'GET'; body = None; content_type = None; expect = None
    if args.cmd == 'request':
        meta = capability(ROOT, args.capability)
        routes = [r for r in meta.get('requests', []) if r['method'] == args.method and r['path'] == (args.path or '/')]
        if meta.get('service') != s['id'] or len(routes) != 1: raise ValueError('Service/method/path must exactly match the capability')
        contract = routes[0]
        if meta.get('status') not in ('runtime_verified', 'source_verified'): raise ValueError('Capability is not verified enough for execution')
        if contract['effect'] != 'read' and not args.allow_write: raise ValueError('WRITE_REQUIRES_AUTHORIZATION: review exact target and body before --allow-write')
        if contract.get('auth') and not args.account: raise ValueError('This contract requires an explicit account')
        if args.form and args.body_file: raise ValueError('Choose form arguments or body file')
        method = args.method; expect = contract.get('expect'); query = pairs(args.query)
        fixed_keys = {k for k,_ in up.parse_qsl(up.urlsplit(url).query,keep_blank_values=True)}
        form = pairs(args.form)
        if fixed_keys.intersection(query) or fixed_keys.intersection(form):
            raise ValueError('Parameters cannot override the action fixed by the capability path')
        if query: url += ('&' if '?' in url else '?') + up.urlencode(query)
        if args.form: body = up.urlencode(form).encode(); content_type = 'application/x-www-form-urlencoded'
        if args.body_file:
            body = private_read(Path(args.body_file)).encode(); value = json.loads(body)
            if isinstance(value,dict) and fixed_keys.intersection(value):raise ValueError('Body cannot override the action fixed by the capability path')
            content_type = 'application/json'
    info, raw = fetch(url, method=method, data=body, content_type=content_type, state=state, expect=expect, timeout=max(1, min(args.timeout, 20)))
    if args.cmd == 'request' and info['ok'] and contract.get('required_fields'):
        value = info.get('data')
        if not isinstance(value, dict) or any(value.get(k) in (None, '') for k in contract['required_fields']):
            info.update(ok=False, code='BUSINESS_RESPONSE_INCOMPLETE')
    if args.cmd == 'request' and isinstance(info.get('data'), list):
        rows = info['data']; info['total_received'] = len(rows)
        fields = args.fields.split(',') if args.fields else contract.get('fields')
        info['data'] = [{k: r[k] for k in fields if k in r} if fields and isinstance(r, dict) else r for r in rows[:max(1,min(args.limit,30))]]
        info['truncated'] = len(rows) > len(info['data'])
    elif args.cmd == 'request' and isinstance(info.get('data'), dict):
        # Preserve wrappers but bound nested result lists and long strings.
        def bounded(value):
            if isinstance(value, list): return [bounded(v) for v in value[:max(1,min(args.limit,30))]]
            if isinstance(value, dict): return {k: bounded(v) for k,v in value.items()}
            if isinstance(value, str) and len(value)>3000: return value[:3000]+'…'
            return value
        original = info['data']
        fields = args.fields.split(',') if args.fields else contract.get('fields')
        selected = {k: original[k] for k in fields if k in original} if fields else original
        compact = bounded(selected)
        info['output_truncated'] = compact != original; info['data'] = compact
    if args.cmd == 'discover' and info['ok']:
        parser = Links(); parser.feed(raw.decode('utf-8', errors='replace'))
        links = [{**x, 'url': safe_url(up.urljoin(info['url'], x['url']))} for x in parser.links if not x['url'].startswith(('javascript:', '#'))]
        info['candidates'] = sorted(links, key=lambda x: x['kind'] not in ('script', 'form'))[:8]
    elif args.cmd == 'source' and info['ok']:
        if len(args.match) > 3: raise ValueError('At most 3 search terms')
        text = raw.decode('utf-8', errors='replace'); snippets = []
        for term in args.match:
            for m in list(re.finditer(re.escape(term), text))[:3]:
                part = text[max(0, m.start()-180):m.end()+420]
                part = re.sub(r'''(?i)((?:token|password|secret|authorization|cookie)\s*[:=]\s*)["'][^"']+["']''', r'\1"[REDACTED]"', part)
                snippets.append({'line': text.count('\n', 0, m.start())+1, 'text': part})
        info['snippets'] = snippets
        if not args.match: info['hint'] = 'Provide --match TERM for bounded snippets'
    elif args.cmd == 'request' and info['ok'] and 'data' not in info:
        info['text'] = raw.decode('utf-8', errors='replace')[:6000]
    emit(info)


def run():
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        emit({'ok': False, 'code': 'LOCAL_ERROR', 'message': str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else type(exc).__name__})
        sys.exit(1)


if __name__ == '__main__': run()
