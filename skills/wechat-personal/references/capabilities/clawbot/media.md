---
id: clawbot-media
service: clawbot
keywords: ["ClawBot下载", "ClawBot读取文件", "ClawBot读图片", "ClawBot语音", "机器人下载"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-09-19"
transport: "ilink_https_third_party_sdk"
command: ["bot", "download", "--account", "me", "--attachment-id", "<updates返回的attachment_id>"]
workflow: references/workflows/clawbot.md
note: "真实入站Excel、JPEG及语音已下载解密；Excel已解析、图片已打开、语音为有效SILK。先updates取得attachment_id再下载，不重做探索；语音转写未经验证。机器人发出的附件引用回取曾失败，不与入站下载混淆。"
---
# ClawBot 媒体

读写长期授权，仅发给绑定本人。所有命令直接使用iLink/CDN，无需桌面微信在线，无常驻进程。每次最多上传/下载32MiB，可通过`--max-bytes`调至最高100MiB；这是本地资源界限，不是微信平台承诺。

```bash
python3 "$WX" bot send --file '/实际文件路径' --request-id '本次唯一ID'
python3 "$WX" bot send --image '/实际图片路径' --request-id '另一个唯一ID'
python3 "$WX" bot updates --limit 20
python3 "$WX" bot download --attachment-id 'updates返回的attachment_id'
```

`--file`、`--image`、`--video`与文字参数互斥，单条发送。视频具有实现但未实测。相同操作ID返回已有结果、不重传；内容改变必须视为新的操作。上传失败不会提交消息。消息提交结果不明时不得换ID盲重试。发送返回`api_accepted`与可能的服务端消息ID，不能据此承诺附件在接收端可打开。

来源：[腾讯媒体类型](https://github.com/Tencent/openclaw-weixin/blob/main/src/api/types.ts)、[上传实现](https://github.com/Tencent/openclaw-weixin/blob/main/src/cdn/upload.ts)、[CDN地址构造](https://github.com/Tencent/openclaw-weixin/blob/main/src/cdn/cdn-url.ts)。复用SDK AES-128-ECB/PKCS7实现，申请上传地址→加密上传→以附件引用发送。优先使用服务端完整URL，否则使用协议CDN拼接方式；URL限定微信HTTPS域名，不跟随重定向。

入站图片、文件、视频、语音若有媒体引用，`updates`私存凭证并返回不透明`attachment_id`；下载后返回本地路径、字节数与SHA-256。文件还校验服务端提供的长度和MD5。附件落在`~/.local/state/wechat-personal/bots/<account>/downloads/`，目录0700、文件0600；媒体密钥只在私有`media/`，不出现在工具结果。下载得到文件后再按实际格式读取内容，不能把文件名识别算作读完正文。

未知协议项保存在同账号`unrecognized/`，只输出`raw_item_id`和未支持标志，避免悄悄丢弃后宣称只支持文字。原生表情包/公众号分享卡片的客户端限制及未接通状态另见[富消息边界](rich-items.md)。GIF图片/文件、文章链接都不能冒充原生表情包或原生分享卡片验收。

2026-09-19实测：从已安装skill、`/tmp`目录发送无隐私测试TXT与PNG，均返回消息ID，本人确认文件能打开、图片正常显示，[发送能力](send-media.md)已通过。按这些出站引用回取CDN曾HTTP400，不能据此判断入站下载失败，也不换ID重发已送达内容。本地历史仅本次可选诊断，不是发送依赖。

随后通过真实iLink入站收到本人发送的Excel、JPEG、语音。从`updates`返回的引用直接下载解密全部成功：Excel通过长度/MD5校验并实际解析工作表与单元格，JPEG实际打开查看，语音为有效SILK头。真实stdio MCP `clawbot_download`也下载同一JPEG，SHA-256与CLI一致。本人确认语音没有说话，因此只验证音频文件接收，不宣称语音识别正确；服务端附带转写标注`transcription_verified=false`。视频下载及所有格式兼容性未验收。

下载读取私存附件引用并原子写本地文件，不消费游标，允许与有界`updates`轮询同时执行；无需等待接收锁释放，也不依赖桌面微信。凭证缺失/过期/下载报错按实际错误处理，不重复扫码或盲重发。
