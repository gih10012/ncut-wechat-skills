"""Read an existing Linux WeChat window through niri; no message backend."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=6)
    except subprocess.TimeoutExpired:
        raise ValueError('Desktop command timed out: ' + args[0]) from None
    if result.returncode:
        raise ValueError('Desktop command failed: ' + args[0])
    return result.stdout


def windows():
    return [w for w in json.loads(run(['niri', 'msg', '--json', 'windows']))
            if w.get('app_id') == 'wechat']


def show():
    # Use the official client's existing tray item. Do not launch another client.
    try:
        import dbus
    except ImportError:
        raise ValueError('System Python dbus module is required to reveal the tray window') from None
    bus = dbus.SessionBus()
    names = set(str(n) for n in bus.list_names())
    candidates = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if Path(os.readlink(proc / 'exe')).name == 'wechat':
                candidates.extend(n for n in names
                                  if n.startswith('org.kde.StatusNotifierItem-' + proc.name + '-'))
        except OSError:
            continue
    if len(candidates) != 1:
        raise ValueError('No unique existing WeChat tray item; open the intended client window')
    obj = bus.get_object(candidates[0], '/StatusNotifierItem', introspect=False)
    try:
        obj.Activate(0, 0, dbus_interface='org.kde.StatusNotifierItem', timeout=5)
    except dbus.DBusException:
        raise ValueError('Existing WeChat tray did not respond; open the client window') from None
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        found = windows()
        if found:
            return found
        time.sleep(.1)
    return []


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'show', 'capture'])
    parser.add_argument('--show', action='store_true', help='Reveal the existing tray window if hidden')
    parser.add_argument('--window', type=int, help='Select an observed WeChat window ID')
    args = parser.parse_args(argv)
    found = windows()
    if not found and (args.action == 'show' or args.show):
        found = show()
    if args.action in ('status', 'show'):
        return {'ok': bool(found), 'code': 'WINDOW_AVAILABLE' if found else 'WINDOW_NOT_VISIBLE',
                'windows': [{'id': w['id'], 'app_id': w['app_id'], 'title': w['title']} for w in found],
                'login_verified': False}
    selected = [w for w in found if args.window is None or w['id'] == args.window]
    if len(selected) != 1:
        raise ValueError('Select one observed WeChat window; use desktop capture --show if hidden')
    directory = Path.home() / '.local/state/wechat-personal/runs'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    fd, filename = tempfile.mkstemp(prefix='wechat-visible-', suffix='.png', dir=directory)
    os.close(fd)
    image = Path(filename)
    try:
        run(['niri', 'msg', 'action', 'screenshot-window', '--id', str(selected[0]['id']), '--path', filename])
        deadline = time.monotonic() + 3
        while image.stat().st_size == 0 and time.monotonic() < deadline:
            time.sleep(.1)
        if image.stat().st_size == 0:
            raise ValueError('Window screenshot did not arrive')
        os.chmod(image, 0o600)
    except Exception:
        image.unlink(missing_ok=True)
        raise
    return {'ok': True, 'source': 'official-wechat-visible-window', 'window_id': selected[0]['id'],
            'image': filename, 'complete': False, 'scope': 'current visible content only',
            'clipboard_effect': 'niri also copies this screenshot to the local clipboard',
            'captured_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
