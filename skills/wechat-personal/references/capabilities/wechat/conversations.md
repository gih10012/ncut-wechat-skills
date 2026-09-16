---
id: conversations
service: wechat
keywords: ["会话", "未读", "找群", "联系人", "最近聊天", "微信群"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-09-16T12:47:29+08:00"
transport: "local_sqlcipher_readonly"
command: ["native", "conversations", "--account", "me", "--query", "NAME_OR_ID", "--limit", "10"]
workflow: references/workflows/native-linux.md
note: "当前 Linux 微信本地会话列表、名称检索、未读数和摘要。省略 --query 列最近会话；--unread 过滤未读。取得 chat_id 后 native messages 精确读取。"
---
# 会话定位

读取当前 `session/session.db` 的 `SessionTable`，与 `contact/contact.db` 的备注/昵称配对。按 sort_timestamp 排序，匹配用户名或显示名；过滤隐藏会话后再限制条数。普通调用返回最多10项，上限50项，每项摘要最多160字。

实测195个会话，返回真实名称、未读数和最近时间。不改变未读计数，不打开窗口，不证明所有手机历史已同步。
