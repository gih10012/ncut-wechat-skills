---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信"]
exclude_keywords: ["企微", "企业微信", "ClawBot", "机器人"]
status: "not_connected"
transport: "unavailable"
workflow: references/workflows/messages.md
note: "原生发送尚未接通；当前Linux及第三方后端核对已记录，下一步需本人在线验证普通网页登录资格。已有本地定位/读回，数据库密钥不是服务端 token。"
---
# 消息发送

复用 conversations 定位和 read-messages 读回；仅补发送传输。以个人微信身份写入前必须取得本人明确授权或适用的事先授权，已有范围不重复询问；核对收件人、内容/类型与次数。超时先按会话/时间/内容读回再决定是否重试。ClawBot机器人身份发送走独立能力与长期授权，不能替代这里的验收。

2026-09-19候选核对与下一步见[第三方后端](../../workflows/onebot.md#2026-09-19按napcat同类后端复核)。当前Linux内部入口未取得外部调用契约；openwechat普通网页模式仅为待本人扫码验证的轻量候选。既没有登录成功，也没有发送命令可直接调用；不重复扩展逆向或枚举已排查项目。未接通状态题直接说明此边界，用户要求继续接入时再按现有证据推进。
