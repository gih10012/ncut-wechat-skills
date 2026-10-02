"""Refresh one bound ClawBot context through the installed personal CLI, without a daemon."""
import hashlib
import json
import re
import subprocess
import time
import uuid

import ilink
import native_cli


def configure(access, root, state, chat, disabled=False):
    if disabled:
        state.pop('native_recovery', None)
    else:
        ilink.nonempty(state, 'ilink_user_id')
        ilink.nonempty(state, 'ilink_bot_id')
        if not isinstance(chat, str) or not re.fullmatch(r'[A-Za-z0-9_-]+@weclaw', chat):
            raise ilink.BotError('BOT_RECOVERY_EXACT_CLAWBOT_CHAT_REQUIRED')
        if not native_cli.available():
            raise ilink.BotError('BOT_RECOVERY_NATIVE_CLI_REQUIRED')
        state['native_recovery'] = {'enabled': True, 'native_chat': chat,
                                   'ilink_user_id': state['ilink_user_id'],
                                   'ilink_bot_id': state['ilink_bot_id'],
                                   'configured_at': access.now()}
    ilink.save(access, root / 'account.json', state)
    return {'ok': True, 'code': 'BOT_RECOVERY_CONFIGURED', 'enabled': ilink.recovery_enabled(state),
            'message_send_performed': False, 'max_context_recoveries_per_send': 1}


def matches_refresh(message, state, text):
    return (message.get('from_user_id') == state.get('ilink_user_id')
            and message.get('to_user_id') == state.get('ilink_bot_id')
            and not message.get('group_id') and message.get('message_type') == 1
            and isinstance(message.get('context_token'), str) and bool(message['context_token'])
            and any(item.get('type') == 1 and isinstance(item.get('text_item'), dict)
                    and item['text_item'].get('text') == text for item in message.get('item_list', [])))


def renew_context(access, root, state, request_id):
    if not request_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request_id):
        raise ilink.BotError('BOT_SEND_REQUEST_ID_REQUIRED')
    if not ilink.recovery_enabled(state):
        return {'ok': False, 'code': 'BOT_NATIVE_RECOVERY_NOT_CONFIGURED', 'automatic_retry': False}
    config = state['native_recovery']
    fingerprint = hashlib.sha256(json.dumps([state['ilink_bot_id'], state['ilink_user_id'],
                                             config['native_chat']]).encode()).hexdigest()
    path = root / 'renewals' / (request_id + '.json')
    previous = ilink.read(access, path)
    if previous:
        if previous.get('fingerprint') != fingerprint:
            raise ilink.BotError('BOT_RECOVERY_REQUEST_ID_CONFLICT')
        # Even an accepted old renewal cannot authorize a fresh send now: the
        # context may have expired again. Replays are inspection, never refresh.
        return {**previous.get('result', {'ok': False, 'code': 'BOT_NATIVE_RECOVERY_INTERRUPTED'}),
                'replayed': True, 'fresh_for_current_send': False, 'automatic_retry': False}
    native_id = 'bot-renew-' + hashlib.sha256(request_id.encode()).hexdigest()[:40]
    text = 'ClawBot 自动刷新 ' + uuid.uuid4().hex
    record = {'fingerprint': fingerprint, 'native_request_id': native_id, 'created_at': access.now()}
    ilink.save(access, path, record)  # reserve before the native write
    result = {'ok': False, 'code': 'BOT_NATIVE_RECOVERY_FAILED', 'request_id': request_id,
              'native_request_id': native_id, 'context_refreshed': False,
              'desktop_required_for_recovery': True, 'automatic_retry': False}
    try:
        native = native_cli.send_text(text, native_id, config['native_chat'], timeout=120)
        result['native_status'] = native.get('code') or native.get('status')
        result['native_submission_entered'] = native.get('native_submission_entered')
        result['native_local_history_integrated'] = native.get('local_history_integrated')
        # A caller timeout can leave the service still working. Observe the
        # exact nonce once, but never issue another native send to guess success.
        if not native.get('ok') and native.get('native_submission_entered') is False:
            result['code'] = 'BOT_NATIVE_RECOVERY_SEND_FAILED'
        else:
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                try:
                    messages = ilink.poll_updates(access, root, state,
                                                  timeout=min(20, max(.1, deadline - time.monotonic())))
                except ilink.BotError as exc:
                    if str(exc) in ('BOT_POLL_TIMEOUT', 'BOT_NETWORK_TIMEOUT'):
                        continue
                    raise
                saved_identity = state.get('owner_context', {}).get('message_fingerprint')
                context_from_this_poll = any(
                    saved_identity == hashlib.sha256(json.dumps(message, sort_keys=True).encode()).hexdigest()
                    for message in messages)
                if (context_from_this_poll and
                        any(matches_refresh(message, state, text) for message in messages)):
                    result.update(ok=True, code='BOT_NATIVE_CONTEXT_REFRESHED', context_refreshed=True,
                                  fresh_for_current_send=True)
                    break
                if not messages:
                    time.sleep(min(1, max(0, deadline - time.monotonic())))
            else:
                result['code'] = 'BOT_NATIVE_RECOVERY_INBOUND_NOT_OBSERVED'
    except (ilink.BotError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result.update(code=str(exc) if isinstance(exc, ilink.BotError) else 'BOT_NATIVE_RECOVERY_LOCAL_ERROR',
                      error_type=type(exc).__name__)
    result['completed_at'] = access.now()
    record['result'] = result
    ilink.save(access, path, record)
    return result
