import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/notification_inbox.py'
spec = importlib.util.spec_from_file_location('notification_inbox', SCRIPT)
inbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inbox)


class NotificationIngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'notifications.sqlite'
        self.token = 'unit-test-ingest-token'
        self.server = inbox.make_server('127.0.0.1', 0, self.token, self.path)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .02})
        self.thread.start()
        self.payload = {'package': 'com.tencent.wework', 'title': '测试通知',
                        'text': '仅测试：引号 " 与换行\n第二行',
                        'phone_time': '2026-09-18 18:00:00.123'}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, payload=None, *, token=None, method='POST', path='/wecom/notifications', raw=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        body = raw if raw is not None else json.dumps(payload or self.payload).encode()
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + (self.token if token is None else token)}
        try:
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_http_ingest_unicode_and_retry_are_preserved_once(self):
        status, result = self.request(path='/wecom/notifications?timestamp=123')
        self.assertEqual(status, 200)
        self.assertFalse(result['duplicate'])
        self.assertTrue(self.request()[1]['duplicate'])
        data = inbox.read_notifications(self.path, 10)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['text'], self.payload['text'])
        self.assertEqual(data['source'], 'android_notification')
        self.assertFalse(data['personal_inbox_verified'])
        self.assertFalse(data['complete_chat_history'])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_changed_notification_is_not_discarded(self):
        self.request()
        changed = dict(self.payload, text='另一条通知', phone_time='2026-09-18 18:00:01.000')
        self.request(changed)
        data = inbox.read_notifications(self.path, 1)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['text'], '另一条通知')

    def test_authentication_and_package_filter_prevent_ingest(self):
        self.assertEqual(self.request(token='wrong')[0], 401)
        self.assertEqual(self.request(dict(self.payload, package='com.tencent.mm'))[0], 400)
        self.assertEqual(inbox.read_notifications(self.path, 10)['count'], 0)

    def test_invalid_and_oversized_payloads_leave_inbox_empty(self):
        for raw in [b'[]', b'null', b'{', b'\xff', b'{}', b'X' * (inbox.MAX_BODY + 1)]:
            status, _ = self.request(raw=raw)
            self.assertIn(status, [400, 413])
        self.assertEqual(self.request(dict(self.payload, phone_time='[receive_time]'))[0], 400)
        self.assertEqual(inbox.read_notifications(self.path, 10)['count'], 0)

    def test_http_has_no_archive_read_endpoint(self):
        self.request()
        status, body = self.request(method='GET')
        self.assertEqual(status, 404)
        self.assertNotIn('items', body)
        self.assertEqual(self.request(method='GET', path='/health')[0], 200)

    def test_empty_local_read_does_not_create_archive(self):
        missing = Path(self.temp.name) / 'missing.sqlite'
        self.assertEqual(inbox.read_notifications(missing, 10)['count'], 0)
        self.assertFalse(missing.exists())

    def test_insecure_archive_and_wildcard_binding_are_rejected(self):
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            inbox.read_notifications(self.path, 10)
        for host in ['0.0.0.0', '8.8.8.8', '224.0.0.1']:
            with self.assertRaises(ValueError):
                inbox.private_host(host)


if __name__ == '__main__':
    unittest.main()
