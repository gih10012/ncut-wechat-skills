---
id: read-messages
service: wechat
keywords: ["群消息", "微信消息", "聊天记录", "近期消息", "最近消息", "私聊", "读消息"]
exclude_keywords: ["企微", "企业微信", "ClawBot", "QClaw", "机器人"]
status: "runtime_verified"
evidence: "Linux owner database schema, authenticated pages and committed WAL; actual scoped recent group messages on 2026-09-16"
runtime_verified_at: "2026-09-16T12:47:47+08:00"
workflow: references/workflows/native-linux.md
transport: "local_sqlcipher_readonly"
command: ["native", "messages", "--account", "me", "--chat", "EXACT_CHAT_ID_OR_UNIQUE_NAME", "--limit", "20"]
note: "已验证 Linux 微信本地近期消息；先用 native conversations --query 定位。同名须选精确 chat_id。读取不改未读状态；覆盖此客户端已同步的数据，发送与企微另行接入。"
---
# 微信近期消息

前置：本账号一次捕获的数据库密钥。身份来自本机账号目录；不访问旧 wechatcopilot。

数据链：`SessionTable.username` 定位 → `Msg_<md5(username)>` → `Name2Id.rowid = real_sender_id` 得到发送人 → 联系人 `remark/nick_name`。仅查询命中会话，按时间倒序返回，上限50条。`--since` 为包含该秒的 Unix 时间，`--before` 为不包含该秒的上界；它不是无遗漏的逐条分页游标。

返回 `server_id` 为字符串以保留64位精度，含发送人、时间、类型、文字。WCDB zstd 正文有界解压；分享消息提取标题/链接，图片语音不做未请求的识别。每库返回快照时间和合并的 WAL 提交帧数；跨库不是同一事务。

`CHAT_NOT_UNIQUE`：查会话后选择精确 ID；`CHAT_HISTORY_NOT_LOCAL`：客户端没有该会话历史表；`DATABASE_BUSY`：源文件读取期间变化，稍后重试；`DATABASE_KEY_STALE`/`DATABASE_AUTH_FAILED` 才重新核对密钥。正文不能解压时该条有 `decode_error`，不可当作已读全文。
