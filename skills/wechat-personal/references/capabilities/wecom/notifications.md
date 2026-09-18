---
id: wecom-notifications
service: wecom
keywords: ["企微通知", "企业微信通知", "手机通知转存"]
status: "not_connected"
transport: "android_notification_webhook"
command: ["notifications", "list", "--account", "me", "--limit", "20"]
workflow: references/workflows/android-notifications.md
note: "已按本人最新要求暂缓：手机为原生鸿蒙，先前Android假设已更正，不再提示安装SmsForwarder或手机验收。本机HTTP与MCP通过，实际投递未验证；不是完整企微聊天。"
---
# 企微通知补充读取

2026-09-18本人更正手机系统为原生鸿蒙，要求手机接入以后再说，后续再研究OpenHarmony方向。本条目当前暂缓，不能把检索命中当作安装或验收待办。

此方案原设计来源为Android手机上的SmsForwarder，而非企业会话存档、企业应用或企微原生消息API。通知接收端使用Python标准库，默认限时300秒；正常读取无需网络服务在线。代码保留，但没有原生鸿蒙适配。

原配置、手机规则及验收设计见[流程](../../workflows/android-notifications.md)，当前不执行。只有适用设备的实际企微通知进入本机并读回一致，才能将本条目的通知范围标为`runtime_verified`；完整企微消息条目保持独立状态。
