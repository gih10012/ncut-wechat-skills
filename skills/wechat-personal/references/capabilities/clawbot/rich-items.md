---
id: clawbot-rich-items
service: clawbot
keywords: ["ClawBot表情包", "ClawBot公众号卡片", "机器人表情包", "机器人分享卡片"]
exclude_keywords: ["企微", "企业微信"]
status: "not_connected"
transport: "unverified"
workflow: references/workflows/clawbot.md
note: "本人2026-10-01确认ClawBot手机端不支持自定义表情，只能emoji。个人CLI向ClawBot的type47提交/服务器ID已取得，未取得iLink表情入站，不能宣称机器人表情可用；公众号卡片通道仍未接通。个人CLI向文件传输助手的GIF及卡片已另行验收。"
---
# 原生表情包与公众号分享卡片

ClawBot原生表情与公众号卡片通道保持未接通。2026-09-19本人配合验收时，明确两种均不能从当时微信客户端发给ClawBot；2026-10-01再次明确ClawBot手机端本身不支持自定义表情，只能emoji。这是本人报告的客户端限制，不是由空轮询推断接口不支持。无需反复要求本人重发同一种无法选择的内容。

2026-10-01个人CLI向ClawBot发送type47动画GIF取得服务器ID，本地原始XML的MD5/长度与输入一致，但没有对应iLink入站，且上述手机限制仍在。个人身份GIF向文件传输助手已由本人确认正常，见[个人表情契约](../wechat/send-personal-sticker.md)；文章/小程序转发及自定义XML向文件传输助手也已验收，见[转发契约](../wechat/forward-card.md)。这些分别证明个人发送能力，不证明ClawBot富消息协议或手机呈现。

当前公开iLink类型未定义这两种专用项；不能编造消息type或将普通图片、GIF附件、文本链接冒充原生类型。以后若客户端入口或协议有新证据，再按该证据局部探索；未知入站项会保留于私有`unrecognized/`供诊断。

普通文件、图片及语音下载见[媒体契约](media.md)，文件/图片发送见[发送契约](send-media.md)。这些已验证能力正常直接用，不因为富消息缺项而重新探索所有媒体。
