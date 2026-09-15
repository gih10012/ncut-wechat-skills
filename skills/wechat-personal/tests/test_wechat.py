import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'scripts/wechat.py'
spec=importlib.util.spec_from_file_location('wechat_access',path);wx=importlib.util.module_from_spec(spec);spec.loader.exec_module(wx)

class WeChatTests(unittest.TestCase):
    def test_article_body_includes_text_after_self_closing_images_and_excludes_script(self):
        parser=wx.Article();parser.feed('<h1 id="activity-name">标题</h1><div id="js_content">开头<img data-src="https://example.test/a.png"/><p>正文</p><br/>结尾<script>do-not-read</script></div><footer>not-body</footer>')
        self.assertEqual(''.join(parser.title),'标题')
        text=''.join(parser.text)
        for wanted in ['开头','正文','结尾']:self.assertIn(wanted,text)
        for unwanted in ['do-not-read','not-body']:self.assertNotIn(unwanted,text)
        self.assertEqual(len(parser.images),1)

    def test_article_verification_page_is_not_success(self):
        with patch.object(wx.access,'fetch',return_value=({'ok':True,'status':200},b'<html>Verification required</html>')),contextlib.redirect_stdout(io.StringIO()) as out:
            wx.article(['--url','https://mp.weixin.qq.com/s/test'])
        self.assertEqual(json.loads(out.getvalue())['code'],'ARTICLE_BODY_UNAVAILABLE')

    def test_article_defaults_to_small_text_and_does_not_claim_inbox(self):
        raw=b'<div id="js_content">text<img src="https://example.test/a.png"/></div>'
        with patch.object(wx.access,'fetch',return_value=({'ok':True,'status':200},raw)),contextlib.redirect_stdout(io.StringIO()) as out:
            wx.article(['--url','https://mp.weixin.qq.com/s/test'])
        value=json.loads(out.getvalue());self.assertFalse(value['authenticated_inbox']);self.assertEqual(value['image_count'],1);self.assertEqual(value['image_urls'],[])

    def test_lifecycle_and_unapproved_send_do_not_run_backend(self):
        with patch.object(wx.subprocess,'run') as run:
            for argv in [['daemon','serve'],['accounts','remove'],['messages','commit-send','--transaction','t','--confirm']]:
                with self.assertRaises(ValueError):wx.client(argv)
        run.assert_not_called()

    def test_backend_failure_is_reported_without_retry_or_provisioning(self):
        result=type('Result',(),{'stdout':'{"ok":false,"error":{"code":"DAEMON_UNAVAILABLE"}}','returncode':1})()
        with patch.object(wx.Path,'is_file',return_value=True),patch.object(wx.subprocess,'run',return_value=result) as run,contextlib.redirect_stdout(io.StringIO()) as out:
            wx.client(['accounts','list'])
        self.assertEqual(run.call_count,1);self.assertFalse(json.loads(out.getvalue())['ok'])
        self.assertEqual(run.call_args.args[0][1:3],['accounts','list'])

if __name__=='__main__':unittest.main()
