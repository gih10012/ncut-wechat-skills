"""Optional private mesh routing. Installing a skill never enables a receiver."""
import hashlib
import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('BOT_REMOTE_REDIRECT_BLOCKED')


def credentials(config, access):
    if (not isinstance(config, dict) or not isinstance(config.get('control_url'), str)
            or not isinstance(config.get('token_file'), str) or not config['token_file']):
        raise ValueError('BOT_REMOTE_INVALID_CONFIG')
    base = config['control_url'].rstrip('/')
    try:
        parsed = urllib.parse.urlsplit(base)
        port = parsed.port
    except ValueError:
        raise ValueError('BOT_REMOTE_UNTRUSTED_ORIGIN') from None
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or port is not None and not 1 <= port <= 65535 or
            (parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1')))):
        raise ValueError('BOT_REMOTE_UNTRUSTED_ORIGIN')
    token = access.private_read(Path(config['token_file'])).strip()
    if not token or any(char.isspace() for char in token):
        raise ValueError('BOT_REMOTE_INVALID_TOKEN')
    return base, token


def request(config, access, endpoint, body=None):
    base, token = credentials(config, access)
    req = urllib.request.Request(base + endpoint,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(req, timeout=15) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('BOT_REMOTE_RESPONSE_TOO_LARGE')
            value = json.loads(data)
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException):
        raise ValueError('BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK') from None
    if not isinstance(value, dict):
        raise ValueError('BOT_REMOTE_INVALID_RESPONSE')
    return value


def send_status(config, access, request_id, replayed=False, attachment_id=None):
    try:
        value = request(config, access, '/v1/notify/status', {'request_id': request_id})
        status = value.get('status')
        if (status not in ('pending', 'submitting', 'accepted', 'rejected', 'unknown', 'waiting_auth')
                or value.get('id', request_id) != request_id):
            raise ValueError('BOT_REMOTE_INVALID_RESPONSE')
    except ValueError:
        # A missing authority record is not proof that the reserved submit did
        # not reach it. Inspect the original ID; never quietly submit it again.
        return {'ok': False, 'code': 'BOT_REMOTE_SEND_OUTCOME_UNKNOWN',
                'request_id': request_id, 'outcome_unknown': True, 'replayed': replayed,
                'delivery_verified': False, 'automatic_retry': False}
    result = dict(value, ok=status not in ('rejected', 'unknown'),
                  code='BOT_REMOTE_SEND_' + status.upper(), request_id=request_id,
                  outcome_unknown=status in ('unknown', 'submitting'), replayed=replayed,
                  delivery_verified=False, automatic_retry=False)
    if attachment_id:
        result['attachment_id'] = attachment_id
    return result


def submit(config, access, root, request_id, payload, endpoint, attachment_id=None):
    fingerprint = hashlib.sha256(json.dumps([config['control_url'].rstrip('/'), endpoint, payload],
                                           sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    journal = root / 'remote-sends' / (request_id + '.json')
    if journal.exists():
        previous = json.loads(access.private_read(journal))
        if not isinstance(previous, dict) or previous.get('fingerprint') != fingerprint:
            raise ValueError('BOT_REQUEST_ID_CONFLICT')
        return send_status(config, access, request_id, True, attachment_id)
    # This records the immutable operation before entering even the idempotent
    # authority enqueue. A crash or ambiguous response never triggers a re-POST.
    access.private_write(journal, json.dumps({'fingerprint': fingerprint}))
    try:
        request(config, access, endpoint, dict(payload, request_id=request_id))
    except ValueError:
        return {'ok': False, 'code': 'BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK',
                'request_id': request_id, 'outcome_unknown': True,
                'delivery_verified': False, 'automatic_retry': False}
    return send_status(config, access, request_id, attachment_id=attachment_id)


def run(args, access, root, config):
    # Validate the private remote binding before an upload or other effect.
    credentials(config, access)
    if args.operation == 'status':
        value = request(config, access, '/v1/status')
        return {'ok': True, 'code': 'BOT_REMOTE_STATUS', 'source': 'mesh', 'desktop_required': False,
                'leader': value.get('leader'), 'channel_error': value.get('channel_error'), 'outbox': value.get('outbox')}
    if args.operation == 'updates':
        cursor_path = root / 'remote-read-cursor.json'
        cursor = json.loads(access.private_read(cursor_path)).get('cursor', 0) if cursor_path.exists() else 0
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            raise ValueError('BOT_REMOTE_INVALID_CURSOR')
        value = request(config, access, '/v1/inbox', {'after': cursor, 'limit': args.limit})
        if (not isinstance(value.get('next_cursor'), int) or isinstance(value['next_cursor'], bool)
                or value['next_cursor'] < cursor or not isinstance(value.get('items'), list)
                or not all(isinstance(item, dict) for item in value['items'])):
            raise ValueError('BOT_REMOTE_INVALID_RESPONSE')
        access.private_write(cursor_path, json.dumps({'cursor': value['next_cursor']}))
        return dict(value, ok=True, code='BOT_REMOTE_UPDATES', scope='ClawBot mesh archive',
                    personal_inbox=False, automatic_reply=False)
    if args.operation == 'send' and not any(getattr(args, k, None) for k in ('file', 'image', 'video')):
        text = access.private_read(args.text_file) if args.text_file else args.text
        if not isinstance(text, str) or not text.strip() or len(text.encode()) > 16000:
            raise ValueError('BOT_TEXT_REQUIRED_OR_TOO_LARGE')
        if not args.request_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.request_id):
            raise ValueError('BOT_REQUEST_ID_REQUIRED')
        return submit(config, access, root, args.request_id, {'text': text}, '/v1/notify')
    if args.operation == 'send':
        if not args.request_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.request_id):
            raise ValueError('BOT_REQUEST_ID_REQUIRED')
        path = args.image or args.video or args.file
        if not path.is_file() or not 0 < path.stat().st_size <= args.max_bytes:
            raise ValueError('BOT_INVALID_MEDIA_FILE_OR_SIZE')
        with path.open('rb') as stream:
            data = stream.read(args.max_bytes + 1)
        if len(data) > args.max_bytes:
            raise ValueError('BOT_MEDIA_TOO_LARGE')
        kind = 'image' if args.image else 'video' if args.video else 'file'
        fingerprint = hashlib.sha256(json.dumps([kind, path.name, hashlib.sha256(data).hexdigest()]).encode()).hexdigest()
        record_path = root / 'remote-uploads' / (args.request_id + '.json')
        if record_path.exists():
            record = json.loads(access.private_read(record_path))
            if record.get('fingerprint') != fingerprint:
                raise ValueError('BOT_REQUEST_ID_CONFLICT')
            if not record.get('item'):
                if isinstance(record.get('result'), dict) and not record['result'].get('outcome_unknown'):
                    return dict(record['result'], replayed=True)
                return {'ok': False, 'code': 'BOT_REMOTE_UPLOAD_UNKNOWN_NO_RETRY',
                        'request_id': args.request_id, 'outcome_unknown': True,
                        'delivery_verified': False, 'automatic_retry': False, 'replayed': True}
        else:
            from ilink_media import upload, cache_item
            state = json.loads(access.private_read(root / 'account.json'))
            access.private_write(record_path, json.dumps({'fingerprint': fingerprint}))
            try:
                item = upload(state, data, kind, path.name)
            except (ValueError, ImportError) as exc:
                # The durable upload reservation is retained even if its
                # outcome cannot be established. It is never silently retried.
                code = 'BOT_SDK_INSTALL_REQUIRED' if isinstance(exc, ImportError) else str(exc)
                result = {'ok': False, 'code': code if code.startswith('BOT_') else 'BOT_REMOTE_UPLOAD_UNKNOWN_NO_RETRY',
                          'request_id': args.request_id,
                          'outcome_unknown': code not in ('BOT_AUTH_REQUIRED', 'BOT_SDK_INSTALL_REQUIRED', 'BOT_UNTRUSTED_API_ORIGIN'),
                          'delivery_verified': False, 'automatic_retry': False}
                access.private_write(record_path, json.dumps({'fingerprint': fingerprint, 'result': result}))
                return result
            record = {'fingerprint': fingerprint, 'item': item,
                      'attachment_id': cache_item(access, root, item, 'remote:' + args.request_id)}
            access.private_write(record_path, json.dumps(record))
        return submit(config, access, root, args.request_id, {'items': [record['item']]},
                      '/v1/notify/media', record.get('attachment_id'))
    return None
