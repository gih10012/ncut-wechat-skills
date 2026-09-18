---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信"]
exclude_keywords: ["企微", "企业微信", "ClawBot", "机器人"]
status: "not_connected"
transport: "unavailable"
workflow: references/workflows/messages.md
note: "已有本地会话精确定位和读回能力；原生发送传输尚待发现和实测。数据库密钥不是服务端 token，不通过篡改数据库假装发送。"
---
# 消息发送

复用 conversations 定位和 read-messages 读回；仅补发送传输。以个人微信身份写入前必须取得本人明确授权或适用的事先授权，已有范围不重复询问；核对收件人、内容/类型与次数。超时先按会话/时间/内容读回再决定是否重试。ClawBot机器人身份发送走独立能力与长期授权，不能替代这里的验收。
