"""Resume login with installed clients or the companion school browser."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import desktop


def main(argv, access):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', nargs='?', default='start', choices=['start', 'finish', 'status'])
    parser.add_argument('--platform', choices=['wechat', 'wecom', 'school'])
    parser.add_argument('--service', help='A registered school business service, not personal WeCom chat')
    parser.add_argument('--account', default='me')
    parser.add_argument('--window', type=int, help='An observed official WeChat window ID')
    parser.add_argument('--transport', choices=['companion', 'current-desktop'],
                        help='Prefer an independent companion login; current-desktop explicitly uses the existing Linux client')
    args = parser.parse_args(argv)
    meta_path = access.STATE / 'login.json'
    saved = json.loads(access.private_read(meta_path)) if meta_path.exists() else {}
    platform = args.platform or saved.get('platform', 'wechat')
    service = args.service or (saved.get('service') if not args.platform else None)
    transport = args.transport or (saved.get('transport', 'companion') if not args.platform else 'companion')
    if platform == 'school' or service:
        command = ['python3', str(access.ROOT.parent / 'ncut-web-api/scripts/ncut.py'),
                   'login', args.operation, '--account', args.account, '--service', service or 'jwxt']
        access.private_write(meta_path, json.dumps({'platform': platform, 'service': service or 'jwxt'}))
        result = subprocess.run(command, timeout=90, capture_output=True, text=True)
        value = json.loads(result.stdout)
        access.emit({**value, 'login_scope': 'school_business_web_only'})
        return
    if args.operation != 'status':
        access.private_write(meta_path, json.dumps({'platform': platform, 'transport': transport}))
    if transport == 'companion':
        access.emit({'ok': False, 'code': 'COMPANION_LOGIN_NOT_CONFIGURED', 'platform': platform,
                     'preferred_transport': 'independent_companion', 'login_verified': False,
                     'next': '独立伴随端尚未接入；本命令不启动客户端或容器。原生消息 API 未验证，业务网页优先复用其独立登录/API；学校业务用 --platform school --service 教务/预约。'})
        return
    if platform == 'wecom':
        access.emit({'ok': False, 'code': 'WECOM_CLIENT_SETUP_REQUIRED',
                     'next': '本机尚未配置可调用的本人企微客户端登录入口。学校业务可用 login --platform school --service 教务/预约；企微聊天需要先接入实际使用设备上的客户端。',
                     'login_verified': False})
        return
    if args.operation == 'status':
        access.emit(desktop.main(['status']))
        return
    try:
        found = desktop.windows()
        if not found:
            existing = False
            for proc in Path('/proc').iterdir():
                try:
                    if proc.name.isdigit() and Path(os.readlink(proc / 'exe')).name == 'wechat':
                        existing = True
                except OSError:
                    continue
            if not existing:
                launcher = Path('/usr/bin/wechat')
                if not launcher.is_file():
                    raise ValueError('Official WeChat launcher is not installed on this machine')
                if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
                    raise ValueError('Login requires the local graphical session')
                subprocess.Popen([str(launcher)], env={**os.environ, 'DESKTOPINTEGRATION': 'false'},
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    if desktop.windows():
                        break
                    time.sleep(.25)
        found = desktop.windows()
        primary = [w for w in found if w.get('title') == '微信']
        capture_args = ['capture', '--show']
        window = args.window if args.window is not None else primary[0]['id'] if len(primary) == 1 else None
        if window is not None:
            capture_args.extend(['--window', str(window)])
        result = desktop.main(capture_args)
        access.emit({**result, 'code': 'CLIENT_WINDOW_READY', 'login_verified': False,
                     'next': '查看 image：已登录则继续；若显示登录二维码，请本人用手机微信扫码/确认，再调用 login finish。客户端自行保存登录态，无需导出聊天数据库。'})
    except (ValueError, OSError) as exc:
        access.emit({'ok': False, 'code': 'CLIENT_LOGIN_UNAVAILABLE', 'message': str(exc)})
