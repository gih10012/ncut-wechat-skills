import asyncio
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ilink
import ilink_media


class MediaDownloadTests(unittest.TestCase):
    def download(self, data, content, maximum=100):
        class Response:
            status = 200
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def iter_chunked(self, size):
                yield data
            @property
            def content(self): return self
        class Session(Response):
            def __init__(self, **kwargs): pass
            def get(self, url, **kwargs):
                self_url.append(url)
                if kwargs['allow_redirects'] is not False:
                    raise AssertionError('Media downloads must not follow redirects')
                return Response()
        self_url = []
        fake_http = SimpleNamespace(ClientSession=Session, ClientTimeout=lambda **kw: None)
        fake_crypto = SimpleNamespace(decode_aes_key=lambda k: b'key', decrypt_aes_ecb=lambda d, k: d)
        with patch.dict(sys.modules, {'aiohttp': fake_http, 'wechatbot.crypto': fake_crypto}):
            result = asyncio.run(ilink_media.download_async({'kind': 'file', 'content': content}, maximum))
        return result, self_url

    def media(self, **extra):
        return dict(media={'aes_key': 'private-key', 'encrypt_query_param': 'private-reference'}, **extra)

    def test_binary_data_and_declared_integrity(self):
        data = b'\x00\xff\x10binary'
        result, urls = self.download(data, self.media(len=str(len(data)), md5=hashlib.md5(data).hexdigest()))
        self.assertEqual(result, data)
        self.assertEqual(len(urls), 1)

    def test_wrong_size_or_hash_rejected(self):
        for value in (self.media(len='99'), self.media(md5='0'*32)):
            with self.subTest(value=value), self.assertRaises(ilink.BotError):
                self.download(b'bytes', value)

    def test_ciphertext_and_plaintext_limits(self):
        for length in (101, 117):
            with self.subTest(length=length), self.assertRaisesRegex(ilink.BotError, 'BOT_MEDIA_TOO_LARGE'):
                self.download(b'x'*length, self.media(), maximum=100)

    def test_full_url_checked_before_network(self):
        item = self.media(); item['media']['full_url'] = 'https://example.com/private'
        with self.assertRaisesRegex(ilink.BotError, 'BOT_UNTRUSTED_MEDIA_ORIGIN'):
            self.download(b'x', item)


if __name__ == '__main__':
    unittest.main()
