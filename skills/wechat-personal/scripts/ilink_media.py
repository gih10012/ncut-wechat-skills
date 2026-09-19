"""Bounded iLink encrypted media transfer, independent of desktop WeChat."""
import asyncio
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.parse

from ilink import BotError, api_origin, read, save

CDN = 'https://novac2c.cdn.weixin.qq.com/c2c'
KINDS = {2: 'image', 3: 'voice', 4: 'file', 5: 'video'}


def cdn_url(value):
    p = urllib.parse.urlsplit(value)
    if (p.scheme != 'https' or not p.hostname or not p.hostname.endswith('.weixin.qq.com')
            or p.username or p.password or p.port not in (None, 443) or p.fragment):
        raise BotError('BOT_UNTRUSTED_MEDIA_ORIGIN')
    return value


def transfer(coro):
    from aiohttp import ClientError
    from wechatbot.errors import ApiError, MediaError
    try:
        return asyncio.run(asyncio.wait_for(coro, 45))
    except BotError:
        raise
    except ApiError as exc:
        raise BotError('BOT_AUTH_REQUIRED' if exc.is_session_expired else 'BOT_MEDIA_API_ERROR') from None
    except TimeoutError:
        raise BotError('BOT_MEDIA_TIMEOUT') from None
    except (ClientError, OSError):
        raise BotError('BOT_MEDIA_NETWORK_ERROR') from None
    except (MediaError, ValueError, KeyError, TypeError, AttributeError):
        raise BotError('BOT_INVALID_MEDIA_RESPONSE') from None


async def upload_async(state, data, kind, filename):
    import aiohttp
    from wechatbot.crypto import encrypt_aes_ecb, encode_aes_key_base64
    from wechatbot.protocol import ILinkApi
    api = ILinkApi(bot_agent='NCUTSkills/1.0')
    aes_key, filekey = os.urandom(16), os.urandom(16).hex()
    ciphertext = encrypt_aes_ecb(data, aes_key)
    info = await api.get_upload_url(api_origin(state['baseurl']), state['bot_token'],
        filekey=filekey, media_type={'image': 1, 'video': 2, 'file': 3}[kind],
        to_user_id=state['ilink_user_id'], rawsize=len(data),
        rawfilemd5=hashlib.md5(data).hexdigest(), filesize=len(ciphertext),
        no_need_thumb=True, aeskey=aes_key.hex())
    url = info.get('upload_full_url')
    if not url:
        param = info.get('upload_param')
        if not isinstance(param, str) or not param:
            raise BotError('BOT_MEDIA_UPLOAD_URL_MISSING')
        url = api.build_cdn_upload_url(CDN, param, filekey)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as session:
        async with session.post(cdn_url(url), data=ciphertext, allow_redirects=False,
                                headers={'Content-Type': 'application/octet-stream'}) as response:
            if response.status != 200:
                raise BotError('BOT_MEDIA_UPLOAD_HTTP_' + str(response.status))
            param = response.headers.get('x-encrypted-param')
            if not param:
                raise BotError('BOT_MEDIA_DOWNLOAD_REFERENCE_MISSING')
    media = {'encrypt_query_param': param, 'aes_key': encode_aes_key_base64(aes_key), 'encrypt_type': 1}
    if kind == 'image':
        return {'type': 2, 'image_item': {'media': media, 'mid_size': len(ciphertext)}}
    if kind == 'video':
        return {'type': 5, 'video_item': {'media': media, 'video_size': len(ciphertext)}}
    return {'type': 4, 'file_item': {'media': media, 'file_name': filename, 'len': str(len(data)),
                                    'md5': hashlib.md5(data).hexdigest()}}


def upload(state, data, kind, filename):
    return transfer(upload_async(state, data, kind, filename))


def cache_item(access, root, item, identity):
    kind = KINDS.get(item.get('type'))
    if not kind:
        return None
    content = item.get(kind + '_item')
    if not isinstance(content, dict) or not isinstance(content.get('media'), dict):
        return None
    identifier = hashlib.sha256(identity.encode()).hexdigest()
    value = {'kind': kind, 'content': content}
    save(access, root / 'media' / (identifier + '.json'), value)
    return identifier


async def download_async(record, max_bytes):
    import aiohttp
    from wechatbot.crypto import decode_aes_key, decrypt_aes_ecb
    content = record['content']; media = content['media']
    key = decode_aes_key(content.get('aeskey') or media['aes_key'])
    url = media.get('full_url') or CDN + '/download?' + urllib.parse.urlencode(
        {'encrypted_query_param': media['encrypt_query_param']})
    chunks, size = [], 0
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as session:
        async with session.get(cdn_url(url), allow_redirects=False) as response:
            if response.status != 200:
                raise BotError('BOT_MEDIA_DOWNLOAD_HTTP_' + str(response.status))
            async for chunk in response.content.iter_chunked(65536):
                size += len(chunk)
                if size > max_bytes + 16:
                    raise BotError('BOT_MEDIA_TOO_LARGE')
                chunks.append(chunk)
    data = decrypt_aes_ecb(b''.join(chunks), key)
    if len(data) > max_bytes:
        raise BotError('BOT_MEDIA_TOO_LARGE')
    if record['kind'] == 'file':
        if content.get('len') is not None and len(data) != int(content['len']):
            raise BotError('BOT_MEDIA_SIZE_MISMATCH')
        if content.get('md5') and hashlib.md5(data).hexdigest() != content['md5'].lower():
            raise BotError('BOT_MEDIA_HASH_MISMATCH')
    return data


def download(access, root, identifier, max_bytes):
    import re
    if not identifier or not re.fullmatch('[a-f0-9]{64}', identifier):
        raise BotError('BOT_ATTACHMENT_ID_REQUIRED')
    record = read(access, root / 'media' / (identifier + '.json'))
    if not record:
        raise BotError('BOT_ATTACHMENT_NOT_CACHED')
    data = transfer(download_async(record, max_bytes))
    name = record['content'].get('file_name', '')
    suffix = Path(name).suffix.lower()
    if record['kind'] == 'image':
        suffix = '.png' if data.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if data.startswith(b'\xff\xd8\xff') else '.gif' if data.startswith((b'GIF87a', b'GIF89a')) else '.image'
    if not re.fullmatch(r'\.[a-z0-9]{1,10}', suffix):
        suffix = {'image': '.image', 'video': '.mp4', 'voice': '.silk'}.get(record['kind'], '.bin')
    directory = root / 'downloads'; directory.mkdir(mode=0o700, exist_ok=True); directory.chmod(0o700)
    target = directory / (identifier + suffix)
    fd, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {'ok': True, 'path': str(target), 'kind': record['kind'], 'file_name': name,
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'attachment_id': identifier, 'desktop_required': False}
