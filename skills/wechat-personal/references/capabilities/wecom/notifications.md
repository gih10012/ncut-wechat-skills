---
id: wecom-notifications
service: wecom
keywords: ["企微通知", "企业微信通知", "手机通知转存"]
status: "not_connected"
transport: "android_notification_webhook"
command: ["notifications", "list", "--account", "me", "--limit", "20"]
workflow: references/workflows/android-notifications.md
note: "本人同意的通知补充入口已实现，本机HTTP与MCP通过；手机实际投递尚未验收。只读取通知展示的文字，不是完整企微聊天或历史。"
---
# 企微通知补充读取

来源为本人Android手机上的SmsForwarder，而非企业会话存档、企业应用或企微原生消息API。通知接收端使用Python标准库，默认限时300秒；正常读取无需网络服务在线。

首次配置、手机规则及实际验收见[流程](../../workflows/android-notifications.md)。只有手机实际企微通知进入本机并读回一致，才能将本条目的通知范围标为`runtime_verified`；完整企微消息条目保持独立状态。
