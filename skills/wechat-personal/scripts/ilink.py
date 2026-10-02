"""Bounded ClawBot login, reads and owner-directed sends; no daemon or auto replies.

Transport: corespeed-io/wechatbot, wechatbot-sdk==0.3.0.
Protocol checked against Tencent/openclaw-weixin@43675b66551d12d6853155a7869a50fb12a18a1e.
"""
import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import re
import time
import urllib.parse
import uuid

BASE = 'https://ilinkai.weixin.qq.com'


class BotError(ValueError):
    pass


def remember_owner_context(state, messages, received_at):
    """Keep the newest owner reply context, including messages beyond the output page."""
    owner, bot = state.get('ilink_user_id'), state.get('ilink_bot_id')
    eligible = [m for m in messages if owner and m.get('from_user_id') == owner
                and m.get('to_user_id') == bot and not m.get('group_id')
                and m.get('message_type') == 1 and isinstance(m.get('context_token'), str)
                and m['context_token']]
    if not eligible:
        return False
    def created(msg):
        value = msg.get('create_time_ms')
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
    latest = max(enumerate(eligible), key=lambda pair: (created(pair[1]), pair[0]))[1]
    current = state.get('owner_context', {})
    previous_time = current.get('message_created_at_ms')
    if (isinstance(previous_time, int) and not isinstance(previous_time, bool)
            and previous_time > created(latest)):
        return False
    identity = hashlib.sha256(json.dumps(latest, sort_keys=True).encode()).hexdigest()
    if current.get('user_id') == owner and current.get('message_fingerprint') == identity:
        return False
    context = {'user_id': owner, 'token': latest['context_token'], 'received_at': received_at,
               'message_fingerprint': identity}
    if created(latest):
        context['message_created_at_ms'] = created(latest)
    if isinstance(latest.get('message_id'), (str, int)):
        context['message_id'] = latest['message_id']
    state['owner_context'] = context
    return True


def local_status(state):
    context = state.get('owner_context', {})
    return {'ok': True, 'code': 'BOT_LOCAL_STATUS', 'network_request_performed': False,
            'credentials_present': bool(state.get('bot_token')),
            'remote_login_verified': False, 'desktop_required': False,
            'reply_context_present': bool(context.get('token')),
            'reply_context_owner_matches': bool(state.get('ilink_user_id'))
                and context.get('user_id') == state.get('ilink_user_id'),
            'reply_context_received_at': context.get('received_at'),
            'reply_context_message_created_at_ms': context.get('message_created_at_ms'),
            'reply_context_validity': 'unknown',
            'last_update_poll': {k: v for k, v in state.get('last_update_poll', {}).items()
                                 if k in ('checked_at', 'authenticated', 'message_count', 'reply_context_refreshed')}
                                if isinstance(state.get('last_update_poll'), dict) else None,
            'remaining_buffered': len(state.get('pending', [])),
            'native_recovery_enabled': recovery_enabled(state)}


def recovery_enabled(state):
    config = state.get('native_recovery', {})
    return (config.get('enabled') is True and config.get('ilink_user_id') == state.get('ilink_user_id')
            and config.get('ilink_bot_id') == state.get('ilink_bot_id'))


def poll_updates(access, root, state, timeout=40):
    """Append validated input atomically; recovery must not consume the caller's inbox."""
    value = request(state['baseurl'], 'getupdates', token=state['bot_token'],
                    body={'get_updates_buf': state.get('cursor', '')}, timeout=timeout)
    messages = value.get('msgs')
    if (value.get('ret') not in (None, 0) or value.get('errcode') not in (None, 0)
            or not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages)
            or not isinstance(value.get('get_updates_buf'), str)):
        raise BotError('BOT_INVALID_UPDATES')
    for message in messages:
        public_message(message)
    checked_at = access.now()
    refreshed = remember_owner_context(state, messages, checked_at)
    if value['get_updates_buf']:
        state['cursor'] = value['get_updates_buf']
    state['pending'] = state.get('pending', []) + messages
    state['last_update_poll'] = {'checked_at': checked_at, 'authenticated': True,
                                 'message_count': len(messages), 'reply_context_refreshed': refreshed}
    save(access, root / 'account.json', state)
    return messages


def api_origin(value):
    p = urllib.parse.urlsplit(value)
    if (p.scheme != 'https' or not p.hostname or not p.hostname.endswith('.weixin.qq.com')
            or p.username or p.password or p.port not in (None, 443)
            or p.path not in ('', '/') or p.query or p.fragment):
        raise BotError('BOT_UNTRUSTED_API_ORIGIN')
    return 'https://' + p.hostname.lower()


def request(base, endpoint, *, body=None, token=None, timeout=15):
    try:
        from aiohttp import ClientError
        from wechatbot.errors import ApiError
        from wechatbot.protocol import ILinkApi
    except ImportError:
        raise BotError('BOT_SDK_INSTALL_REQUIRED') from None
    base = api_origin(base)
    parsed = urllib.parse.urlsplit(endpoint)
    query = urllib.parse.parse_qs(parsed.query)
    api = ILinkApi(bot_agent='NCUTSkills/1.0')
    async def call():
        if parsed.path == 'get_bot_qrcode':
            task = api.get_qr_code(base, (body or {}).get('local_token_list', []))
        elif parsed.path == 'get_qrcode_status':
            task = api.poll_qr_status(base, query['qrcode'][0], query.get('verify_code', [None])[0])
        elif parsed.path == 'getupdates':
            task = api.get_updates(base, token, body['get_updates_buf'])
        elif parsed.path == 'sendmessage':
            task = api.send_message(base, token, body['msg'])
        else:
            raise BotError('BOT_UNSUPPORTED_OPERATION')
        return await asyncio.wait_for(task, timeout=timeout)
    try:
        value = asyncio.run(call())
    except ApiError as exc:
        if exc.is_session_expired:
            raise BotError('BOT_AUTH_REQUIRED') from None
        raise BotError('BOT_HTTP_' + str(exc.http_status) if exc.http_status >= 400
                       else 'BOT_BUSINESS_ERROR_' + str(exc.errcode)) from None
    except TimeoutError:
        raise BotError('BOT_POLL_TIMEOUT' if timeout > 15 else 'BOT_NETWORK_TIMEOUT') from None
    except (ClientError, OSError):
        raise BotError('BOT_NETWORK_ERROR') from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise BotError('BOT_INVALID_RESPONSE') from None
    if not isinstance(value, dict):
        raise BotError('BOT_INVALID_RESPONSE')
    errors = [value.get('ret'), value.get('errcode')]
    if -14 in errors:
        raise BotError('BOT_AUTH_REQUIRED')
    if any(code not in (None, 0) for code in errors):
        code = next(code for code in errors if code not in (None, 0))
        raise BotError('BOT_BUSINESS_ERROR_' + str(code))
    return value


def read(access, path):
    value = json.loads(access.private_read(path)) if path.exists() else {}
    if not isinstance(value, dict):
        raise BotError('BOT_INVALID_STATE')
    return value


def save(access, path, value):
    access.private_write(path, json.dumps(value, ensure_ascii=False) + '\n')


def nonempty(value, key):
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise BotError('BOT_RESPONSE_MISSING_' + key.upper())
    return item


def public_message(msg):
    # Only expose message content and identifiers; keep reply/media credentials private.
    value = {k: msg[k] for k in ('message_id', 'from_user_id', 'to_user_id', 'create_time_ms',
                                'message_type', 'message_state', 'group_id') if k in msg}
    value['items'] = []
    items = msg.get('item_list', [])
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise BotError('BOT_INVALID_MESSAGE_ITEMS')
    for item in items:
        output = {'type': item.get('type')}
        if item.get('type') == 1:
            text = item.get('text_item', {})
            if not isinstance(text, dict):
                raise BotError('BOT_INVALID_TEXT_ITEM')
            output['text'] = text.get('text', '')
        elif item.get('type') == 3:
            voice = item.get('voice_item', {})
            if not isinstance(voice, dict):
                raise BotError('BOT_INVALID_VOICE_ITEM')
            output['text'] = voice.get('text', '')
            output['transcription_source'] = 'service'
            output['transcription_verified'] = False
        else:
            output['content_downloaded'] = False
            kind = {2: 'image', 4: 'file', 5: 'video'}.get(item.get('type'))
            content = item.get(kind + '_item', {}) if kind else {}
            if not isinstance(content, dict):
                raise BotError('BOT_INVALID_MEDIA_ITEM')
            if kind == 'file':
                output['file_name'] = content.get('file_name', '')
                output['size'] = content.get('len')
        if item.get('type') not in (1, 2, 3, 4, 5):
            output['supported'] = False
            output['note'] = 'Unrecognized protocol item; retained privately, not discarded'
        value['items'].append(output)
    return value


def send_owner(args, access, root, state):
    text = access.private_read(args.text_file) if args.text_file else args.text
    media_path = getattr(args, 'file', None) or getattr(args, 'image', None) or getattr(args, 'video', None)
    kind = 'image' if getattr(args, 'image', None) else 'video' if getattr(args, 'video', None) else 'file'
    data = None
    if media_path:
        if not media_path.is_file() or not 0 < media_path.stat().st_size <= args.max_bytes:
            raise BotError('BOT_INVALID_MEDIA_FILE_OR_SIZE')
        with media_path.open('rb') as stream:
            data = stream.read(args.max_bytes + 1)
        if len(data) > args.max_bytes:
            raise BotError('BOT_MEDIA_TOO_LARGE')
    elif not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 16000:
        raise BotError('BOT_INVALID_TEXT')
    if not args.request_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.request_id):
        raise BotError('BOT_SEND_REQUEST_ID_REQUIRED')
    owner = nonempty(state, 'ilink_user_id')
    payload = {'kind': kind, 'name': media_path.name, 'sha256': hashlib.sha256(data).hexdigest()} if data is not None else text
    fingerprint = hashlib.sha256(json.dumps([state.get('ilink_bot_id'), owner, payload],
                                            ensure_ascii=False).encode()).hexdigest()
    attempt_path = root / 'sends' / (args.request_id + '.json')
    attempt = read(access, attempt_path)
    if attempt:
        if attempt.get('fingerprint') != fingerprint:
            raise BotError('BOT_SEND_REQUEST_ID_CONFLICT')
        return dict(attempt.get('result', {'ok': False, 'code': 'BOT_SEND_OUTCOME_UNKNOWN',
                                          'delivery_verified': False}), replayed=True,
                    request_id=args.request_id, automatic_retry=False)
    client_id = 'ncut-' + uuid.uuid4().hex
    msg = {'from_user_id': '', 'to_user_id': owner, 'client_id': client_id,
           'message_type': 2, 'message_state': 2,
           'item_list': [{'type': 1, 'text_item': {'text': text}}]}
    context = state.get('owner_context', {})
    if context.get('user_id') == owner and context.get('token'):
        msg['context_token'] = context['token']
    # Journal before the non-idempotent request. Repeated IDs never resubmit,
    # including after a crash or timeout; API acceptance is not delivery proof.
    attempt = {'fingerprint': fingerprint, 'client_id': client_id, 'created_at': access.now()}
    save(access, attempt_path, attempt)
    result = {'request_id': args.request_id, 'client_id': client_id,
              'scope': 'ClawBot to bound owner only', 'delivery_verified': False,
              'automatic_retry': False, 'desktop_required': False,
              'reply_context_used': 'context_token' in msg,
              'reply_context_received_at': context.get('received_at') if 'context_token' in msg else None}
    submitted = False
    try:
        if data is not None:
            from ilink_media import upload, cache_item
            item = upload(state, data, kind, media_path.name)
            result['attachment_id'] = cache_item(access, root, item, 'out:' + client_id)
            result.update(kind=kind, size=len(data), file_name=media_path.name)
            msg['item_list'] = [item]
        submitted = True
        value = request(state['baseurl'], 'sendmessage', token=state['bot_token'], body={'msg': msg})
        result.update(ok=True, code='BOT_SEND_ACCEPTED', api_accepted=True)
        if isinstance(value.get('message_id'), (str, int)):
            result['server_message_id'] = value['message_id']
    except BotError as exc:
        unknown = submitted and (str(exc) in ('BOT_NETWORK_TIMEOUT', 'BOT_NETWORK_ERROR', 'BOT_INVALID_RESPONSE') or str(exc).startswith('BOT_HTTP_5'))
        result.update(ok=False, code=str(exc), api_accepted=None if unknown else False,
                      outcome_unknown=unknown, message_submission_attempted=submitted)
        if str(exc) == 'BOT_BUSINESS_ERROR_-2':
            result.update(possible_cause='reply_context_or_proactive_window_rejected', cause_verified=False,
                          recovery='Use configured personal-CLI recovery; only authentication errors require login. Keep the rejected attempt.')
    attempt['result'] = result
    save(access, attempt_path, attempt)
    # Only a determinate context rejection can trigger one recovery. A timeout,
    # crash, auth error or media-upload error never resubmits the original message.
    if submitted and result.get('code') == 'BOT_BUSINESS_ERROR_-2' and recovery_enabled(state):
        from ilink_recovery import renew_context
        recovery_id = 'auto-' + hashlib.sha256(args.request_id.encode()).hexdigest()[:40]
        attempt['attempts'] = [dict(result)]
        attempt['phase'] = 'recovering'
        save(access, attempt_path, attempt)
        renewed = renew_context(access, root, state, recovery_id)
        result['native_recovery'] = renewed
        if renewed.get('ok') and renewed.get('fresh_for_current_send') is True and not renewed.get('replayed'):
            # Reserve the second submission before entering the API. If this
            # process dies here, replay returns unknown and cannot send again.
            msg['client_id'] = 'ncut-' + uuid.uuid4().hex
            msg['context_token'] = state['owner_context']['token']
            result = {**result, 'ok': False, 'code': 'BOT_SEND_OUTCOME_UNKNOWN',
                      'api_accepted': None, 'outcome_unknown': True,
                      'client_id': msg['client_id'], 'reply_context_used': True,
                      'reply_context_received_at': state['owner_context'].get('received_at'),
                      'submission_count': 2}
            result.pop('possible_cause', None)
            result.pop('cause_verified', None)
            result.pop('recovery', None)
            attempt.update(client_id=msg['client_id'], phase='resubmitting', result=result)
            save(access, attempt_path, attempt)
            try:
                value = request(state['baseurl'], 'sendmessage', token=state['bot_token'], body={'msg': msg})
                result.update(ok=True, code='BOT_SEND_ACCEPTED', api_accepted=True, outcome_unknown=False)
                if isinstance(value.get('message_id'), (str, int)):
                    result['server_message_id'] = value['message_id']
            except BotError as exc:
                unknown = (str(exc) in ('BOT_NETWORK_TIMEOUT', 'BOT_NETWORK_ERROR', 'BOT_INVALID_RESPONSE')
                           or str(exc).startswith('BOT_HTTP_5'))
                result.update(ok=False, code=str(exc), api_accepted=None if unknown else False,
                              outcome_unknown=unknown, message_submission_attempted=True)
            attempt['attempts'].append(dict(result))
        attempt.update(result=result, phase='finished')
        save(access, attempt_path, attempt)
    return result


def run(args, access):
    access.account_path(args.account)  # shared account alias validation
    root = access.STATE / 'bots' / args.account
    state_path, pending_path = root / 'account.json', root / 'login.json'
    if args.operation == 'download':
        from ilink_media import download
        return download(access, root, args.attachment_id, args.max_bytes)
    state, pending = read(access, state_path), read(access, pending_path)
    if args.operation == 'status':
        return local_status(state)
    if args.operation == 'recovery':
        from ilink_recovery import configure, renew_context
        if args.disable_native_recovery or args.native_chat:
            return configure(access, root, state, args.native_chat, args.disable_native_recovery)
        if args.renew:
            return renew_context(access, root, state, args.request_id)
        return {'ok': True, 'code': 'BOT_RECOVERY_STATUS', 'enabled': recovery_enabled(state),
                'configured': bool(state.get('native_recovery')), 'max_context_recoveries_per_send': 1}
    if args.operation == 'login':
        if state.get('bot_token') and not args.refresh:
            return {'ok': True, 'code': 'BOT_CREDENTIALS_PRESENT', 'login_verified': False,
                    'next': 'bot updates --account ' + args.account}
        if not args.refresh and pending and time.time() - pending.get('created_at', 0) < 300:
            return {'ok': False, 'code': 'BOT_SCAN_REQUIRED', 'qr_url': pending['qr_url']}
        value = request(BASE, 'get_bot_qrcode?bot_type=3',
                        body={'local_token_list': [state['bot_token']] if state.get('bot_token') else []})
        qr, content = nonempty(value, 'qrcode'), nonempty(value, 'qrcode_img_content')
        save(access, pending_path, {'qrcode': qr, 'qr_url': content, 'baseurl': BASE,
                                    'created_at': time.time()})
        return {'ok': False, 'code': 'BOT_SCAN_REQUIRED', 'qr_url': content,
                'next': 'bot finish --account ' + args.account}
    if args.operation == 'finish':
        if not pending or time.time() - pending.get('created_at', 0) >= 300:
            raise BotError('BOT_QR_EXPIRED')
        query = {'qrcode': pending['qrcode']}
        if args.verify_code_file:
            code = access.private_read(args.verify_code_file).strip()
            if not code.isdigit() or len(code) > 16:
                raise BotError('BOT_INVALID_VERIFICATION_CODE')
            query['verify_code'] = code
        value = request(pending['baseurl'], 'get_qrcode_status?' + urllib.parse.urlencode(query), timeout=35)
        status = value.get('status')
        if status == 'confirmed':
            new_state = {key: nonempty(value, key) for key in ('bot_token', 'ilink_bot_id', 'ilink_user_id', 'baseurl')}
            new_state['baseurl'] = api_origin(new_state['baseurl'])
            new_state['connected_at'] = access.now()
            if (state.get('ilink_bot_id') == new_state['ilink_bot_id']
                    and state.get('ilink_user_id') == new_state['ilink_user_id']):
                new_state.update({k: state[k] for k in ('cursor', 'pending', 'owner_context',
                                                       'native_recovery', 'last_update_poll') if k in state})
            save(access, state_path, new_state)
            pending_path.unlink()
            return {'ok': True, 'code': 'BOT_LOGIN_CONFIRMED', 'message_read_verified': False,
                    'scope': 'ClawBot channel only; not the personal WeChat inbox'}
        if status == 'scaned_but_redirect':
            pending['baseurl'] = api_origin('https://' + nonempty(value, 'redirect_host'))
            save(access, pending_path, pending)
        elif status in ('expired', 'verify_code_blocked'):
            pending_path.unlink()
        elif status == 'binded_redirect':
            if not state.get('bot_token'):
                raise BotError('BOT_BOUND_WITHOUT_LOCAL_CREDENTIALS')
            pending_path.unlink()
            return {'ok': True, 'code': 'BOT_ALREADY_BOUND', 'login_verified': False}
        elif status not in ('wait', 'scaned', 'need_verifycode'):
            raise BotError('BOT_UNKNOWN_LOGIN_STATUS')
        return {'ok': False, 'code': 'BOT_LOGIN_PENDING', 'status': status}
    if not state.get('bot_token'):
        raise BotError('BOT_LOGIN_REQUIRED')
    if args.operation == 'send':
        return send_owner(args, access, root, state)
    queue = state.get('pending', [])
    if not queue:
        poll_updates(access, root, state)
        queue = state['pending']
    selected, remaining = queue[:args.limit], queue[args.limit:]
    messages = [public_message(m) for m in selected]
    from ilink_media import cache_item
    for raw, public in zip(selected, messages):
        for index, (item, output) in enumerate(zip(raw.get('item_list', []), public['items'])):
            identity = json.dumps([state.get('ilink_bot_id'), raw.get('message_id'), index, item], sort_keys=True)
            attachment = cache_item(access, root, item, identity)
            if attachment:
                output['attachment_id'] = attachment
            elif item.get('type') not in (1, 2, 3, 4, 5):
                identifier = hashlib.sha256(identity.encode()).hexdigest()
                save(access, root / 'unrecognized' / (identifier + '.json'), item)
                output['raw_item_id'] = identifier
    state['pending'] = remaining
    # Cursor and remaining messages advance together only after a validated response.
    save(access, state_path, state)
    return {'ok': True, 'items': messages, 'remaining_buffered': len(remaining),
            'scope': 'ClawBot channel only', 'personal_inbox': False, 'automatic_reply': False,
            'desktop_required': False}


def main(argv, access):
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['login', 'finish', 'updates', 'send', 'download', 'status', 'recovery'])
    parser.add_argument('--account', default='me')
    parser.add_argument('--refresh', action='store_true', help='Explicitly request a new login QR')
    parser.add_argument('--native-chat', help='Configure the exact personal-WeChat ClawBot chat ID for bounded recovery')
    parser.add_argument('--disable-native-recovery', action='store_true')
    parser.add_argument('--renew', action='store_true', help='Exercise configured recovery once; requires a unique request ID')
    parser.add_argument('--verify-code-file', type=Path, help='Owner-only file containing the displayed pairing digits')
    parser.add_argument('--limit', type=int, default=20)
    content = parser.add_mutually_exclusive_group()
    content.add_argument('--text')
    content.add_argument('--text-file', type=Path, help='Private UTF-8 text file')
    content.add_argument('--file', type=Path, help='Send as a file attachment, including GIF or images')
    content.add_argument('--image', type=Path, help='Send as an image message')
    content.add_argument('--video', type=Path, help='Send as a video message')
    parser.add_argument('--attachment-id', help='Opaque attachment identifier returned by updates/send')
    parser.add_argument('--max-bytes', type=int, default=32 * 1024 * 1024)
    parser.add_argument('--request-id', help='Unique send operation ID; reuse it to inspect, never to resend')
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        raise ValueError('Use --limit between 1 and 100')
    if not 1 <= args.max_bytes <= 100 * 1024 * 1024:
        raise ValueError('Use --max-bytes between 1 and 104857600')
    try:
        access.account_path(args.account)
        root = access.STATE / 'bots' / args.account
        (access.STATE / 'bots').mkdir(parents=True, exist_ok=True, mode=0o700)
        (access.STATE / 'bots').chmod(0o700)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        # Status is a local snapshot; downloads read immutable references. Both
        # remain usable while a bounded poll holds the mutation lock.
        if args.operation in ('download', 'status'):
            return run(args, access)
        fd = os.open(root/'command.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BotError('BOT_ACCOUNT_BUSY') from None
            return run(args, access)
        finally:
            os.close(fd)
    except BotError as exc:
        return {'ok': False, 'code': str(exc)}
