"""Small resumable login handoff using the existing browser helper."""
import json
import re
import subprocess
import urllib.parse as up
import ncut


def browser(action, account, service=None):
    command = ['node', str(ncut.ROOT / 'scripts/browser-session.mjs'), action, account]
    if service:
        command.append(service)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=35)
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return {'ok': False, 'code': 'LOGIN_BROWSER_UNAVAILABLE'}


def check(account, service):
    if not ncut.account_path(account).exists():
        return {'ok': False, 'code': 'AUTH_REQUIRED'}
    session = ncut.load_session(account)
    if service in ('jwxt', 'jwxtbk'):
        from academic import parse_setup
        info, raw = ncut.fetch('https://jwxtbk.ncut.edu.cn/jsxsd/xskb/xskb_list.do', state=session)
        if info['ok'] and re.search(rb'''location(?:\.href)?\s*=\s*["']https://sso\.ncut\.edu\.cn/sso/login(?:[?"'])''', raw):
            return {'ok': False, 'code': 'AUTH_REQUIRED'}
        if not info['ok']:
            location = up.urlsplit(info.get('location', ''))
            if info.get('code') == 'REDIRECT' and ((location.hostname == 'jwxtbk.ncut.edu.cn' and location.path in ('/Logon.do', '/jsxsd/', '/jsxsd')) or (location.hostname == 'sso.ncut.edu.cn' and location.path.startswith('/sso/'))):
                info['code'] = 'AUTH_REQUIRED'
            return info
        setup = parse_setup(raw)
        return {'ok': True, 'code': 'LOGIN_READY', 'verified_scope': 'personal_timetable',
                'semester': setup['current_term']['name']}
    if service == 'workflow':
        params = {'id': '596', 'collective': '0', 'date': json.dumps({
            'start_date': ncut.now()[:10], 'end_date': ncut.now()[:10]})}
        info, _ = ncut.fetch('https://workflow.ncut.edu.cn/reservation/site/resource/calendar?' + up.urlencode(params), state=session, expect='json')
        if not info['ok']:
            return {k: v for k, v in info.items() if k != 'data'}
        if info.get('data', {}).get('e') != 'OK':
            return {'ok': False, 'code': 'LOGIN_RESPONSE_UNVERIFIED'}
        return {'ok': True, 'code': 'LOGIN_READY', 'verified_scope': 'personal_reservation_calendar'}
    return {'ok': False, 'code': 'SERVICE_LOGIN_CHECK_UNAVAILABLE'}


def main(args):
    ncut.account_path(args.account)  # Validate the alias before constructing paths.
    pending_path = ncut.STATE / 'login-pending' / (args.account + '.json')
    pending = json.loads(ncut.private_read(pending_path)) if pending_path.exists() else {}
    service = ncut.service(args.service or pending.get('service', 'jwxt'))['id']
    if service == 'jwxtbk':
        service = 'jwxt'
    if args.operation == 'status':
        result = {'account': args.account, 'service': service, 'pending': bool(pending),
                  'saved': ncut.account_path(args.account).exists(), 'live_identity_verified': False}
        if pending:
            current = browser('status', args.account)
            result['browser'] = current
            phase = current.get('login_state')
            if phase == 'qr_expired':
                result['next'] = '当前学校登录二维码已失效；在窗口点击刷新后用微信扫码，或选择密码/短信登录。完成后 login finish 自动续接这个服务。'
            elif phase == 'awaiting_login':
                result['next'] = '请在当前学校窗口完成本人登录，随后 login finish；无需在对话中提供密码或验证码。'
            elif current.get('ok'):
                result['next'] = '运行 login finish 验证并保存当前业务会话；页面存在本身不证明登录成功。'
            else:
                result['next'] = '当前无法连接登录窗口；用 login --open 恢复同一账号和待登录服务。'
        ncut.emit(result)
        return
    if args.operation == 'start':
        result = check(args.account, service) if not args.open else {'ok': False, 'code': 'AUTH_REQUIRED'}
        if result['ok']:
            pending_path.unlink(missing_ok=True)
            ncut.emit({**result, 'account': args.account, 'service': service, 'browser_opened': False})
            return
        # An outage is not an expired login. No repeated browser/login loops.
        if result.get('code') not in ('AUTH_REQUIRED', 'SERVICE_LOGIN_CHECK_UNAVAILABLE'):
            ncut.emit(result)
            return
        result = browser('open', args.account, service)
        if result.get('ok'):
            ncut.private_write(pending_path, json.dumps({'service': service, 'account': args.account, 'started_at': ncut.now()}))
            result.update(code='LOGIN_WINDOW_READY', login_verified=False,
                          next='已恢复保存的会话并打开业务入口。先用 login finish 完成换票和验证；只有 login status 确认仍需本人认证时才交接，不因开窗再次要求用户登录。')
        ncut.emit(result)
        return
    captured = browser('capture', args.account)
    if not captured.get('ok'):
        ncut.emit({**captured, 'next': '若登录窗口已关闭，运行 login --open 恢复同一账号和待登录服务；完成页面登录后再 login finish。'})
        return
    result = check(args.account, service)
    if result.get('code') == 'AUTH_REQUIRED' and service == 'jwxt':
        handoff = browser('handoff', args.account)
        if not handoff.get('ok'):
            ncut.emit(handoff)
            return
        captured = browser('capture', args.account)
        if not captured.get('ok'):
            ncut.emit(captured)
            return
        result = check(args.account, service)
    if result.get('ok'):
        pending_path.unlink(missing_ok=True)
        result['browser_closed'] = bool(browser('close', args.account).get('ok'))
    ncut.emit({**result, 'account': args.account, 'service': service,
               'next': '继续原业务查询。' if result.get('ok') else '保留当前登录窗口，根据此错误继续；不要反复扫码。'})
