---
id: wecom-messages
service: wecom
keywords: ["企微消息", "企业微信消息", "企微聊天记录", "企业微信私聊", "企微群聊", "企微全部历史"]
status: "runtime_verified"
evidence: "2026-10-01 logged-in official Wine client; verified real DB/WAL and private/group pages; exact new Chinese/newline/emoji GUI message independently read by CLI"
runtime_verified_at: "2026-10-01T18:57:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_readonly"
command: ["wecom", "messages", "--account", "me", "--chat", "EXACT_CHAT_ID_OR_UNIQUE_NAME", "--limit", "20"]
note: "先用wecom conversations定位；默认20条分页，--cursor续页，--all读取指定会话全部已同步历史。读取不修改客户端数据或未读；媒体仅完整引用，发送另行验收。"
---
# 企业微信本人会话读取

先使用`wecom conversations --account me --query '名称' --limit 20`选择精确ID；名称唯一时可直接作`--chat`，同名返回`AMBIGUOUS_CHAT_NAME_USE_EXACT_ID`。后端接受任意精确会话ID，读取本人账号内的已同步数据，无需sudo、会话存档权限或再次登录。

数据链：已配置精确账号目录 → 稳定复制并校验`message.db`、`session.db`、`user.db`及WAL → 解码并检查完整性 → 会话、发送人和消息正文。普通查询复用已有私有密钥；仅缺失或校验确实失败时处理密钥捕获，不能把每次读取变成进程扫描。

按`send_time,message_id`倒序默认20条；`next_cursor`绑定账号/会话并保留首次查询的最大本地ID，续页排除随后插入的消息。`--all`返回此会话全部已同步行，云端未同步数据不在范围内；跨库快照不是原子事务。返回服务器/发送人ID为字符串，保留64位精度。已观测文字字段保留全部空白、换行和emoji；未知类型返回完整原始二进制base64与字段，不把猜测文本当作全文。媒体引用尚未下载或识别。

`ACCOUNT_NOT_CONFIGURED`：按工作流核对已有本机配置，不猜账号目录；`DATABASE_KEY_MISMATCH`：核对源库与私有密钥；`DATABASE_CHANGED_DURING_SNAPSHOT`：读取期间实际变化，稍后重新读取；WAL校验或不完整错误：保留证据并局部排查，不删除WAL或返回忽略它的旧消息。正常读取没有发送副作用。CLI发送尚未接通，不能将GUI发现阶段的发送记录当作CLI发送验收。
