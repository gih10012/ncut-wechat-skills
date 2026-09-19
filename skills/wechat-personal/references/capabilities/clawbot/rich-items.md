---
id: clawbot-rich-items
service: clawbot
keywords: ["ClawBot表情包", "ClawBot公众号卡片", "机器人表情包", "机器人分享卡片"]
exclude_keywords: ["企微", "企业微信"]
status: "not_connected"
transport: "unverified"
workflow: references/workflows/clawbot.md
note: "2026-09-19本人实测报告：当前微信客户端无法向ClawBot发送原生表情包和公众号卡片；没有对应入站样本，也没有原生发送成功证据。保留目标，不把图片/GIF文件或文章链接当作卡片/表情包验收。"
---
# 原生表情包与公众号分享卡片

这两种目标保持未接通。2026-09-19本人配合验收时，明确两种均不能从当前微信客户端发给ClawBot；这是本人报告的客户端限制，不是由空轮询推断接口不支持。无需反复要求本人重发同一种无法选择的内容。

当前公开iLink类型未定义这两种专用项；不能编造消息type或将普通图片、GIF附件、文本链接冒充原生类型。以后若客户端入口或协议有新证据，再按该证据局部探索；未知入站项会保留于私有`unrecognized/`供诊断。

普通文件、图片及语音下载见[媒体契约](media.md)，文件/图片发送见[发送契约](send-media.md)。这些已验证能力正常直接用，不因为富消息缺项而重新探索所有媒体。
