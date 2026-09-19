---
id: clawbot-media
service: clawbot
keywords: ["ClawBot文件", "ClawBot图片", "ClawBot下载", "机器人文件", "机器人图片", "ClawBot表情包", "ClawBot公众号卡片"]
exclude_keywords: ["企微", "企业微信"]
status: "partially_verified"
transport: "ilink_https_third_party_sdk"
command: ["bot", "send", "--account", "me", "--file", "<本地文件路径>", "--request-id", "<本次操作唯一ID>"]
workflow: references/workflows/clawbot.md
note: "文件和PNG上传、发送API受理及本地消息出现已验证；文件打开/图片渲染待本人确认。下载已实现但本次CDN回取HTTP400，尚未通过真实下载验收。原生表情包与公众号分享卡片保留目标，未接通。"
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

未知协议项保存在同账号`unrecognized/`，只输出`raw_item_id`和未支持标志，避免悄悄丢弃后宣称只支持文字。当前公开类型没有原生表情包/公众号分享卡片专用项，需真实入站样本再判断是否转换为图片、文件或文字；GIF图片/文件、文章链接都不能冒充原生表情包或原生分享卡片验收。

2026-09-19实测：从已安装skill、`/tmp`目录发送无隐私测试TXT与PNG，均返回消息ID，本地历史出现对应文件/图片项。按发送引用回取CDN均HTTP400，未取得明文字节；因此下载保持未验证，不能声称媒体全线跑通。本人离开期间未要求协助，文件能否打开、图片实际渲染以及真实入站媒体/卡片/表情包留待回来配合。本地历史仅本次可选诊断，不是发送依赖。
