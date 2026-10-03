---
id: wecom-messages
service: wecom
keywords: ["企微消息", "企业微信消息", "企微读取", "企业微信读取", "企微聊天记录", "企业微信私聊", "企微群聊", "企微全部历史"]
status: "runtime_verified"
evidence: "2026-10-01 logged-in official Wine client; verified real DB/WAL and private/group pages; exact new Chinese/newline/emoji GUI message independently read by CLI"
runtime_verified_at: "2026-10-01T18:57:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_readonly"
command: ["wecom", "messages", "--account", "me", "--chat", "EXACT_CHAT_ID_OR_UNIQUE_NAME", "--limit", "20"]
note: "先用wecom conversations定位；默认20条分页，--cursor续页，--all读取指定会话全部已同步历史。读取不修改客户端数据或未读；消息读取返回完整媒体引用，已缓存原图另按media export导出，发送见各格式契约。"
---
# 企业微信本人会话读取

先使用`wecom conversations --account me --query '名称' --limit 20`选择精确ID；名称唯一时可直接作`--chat`，同名返回`AMBIGUOUS_CHAT_NAME_USE_EXACT_ID`。后端接受任意精确会话ID，读取本人账号内的已同步数据，无需sudo、会话存档权限或再次登录。

数据链：已配置精确账号目录 → 稳定复制并校验`message.db`、`session.db`、`user.db`及WAL → 解码并检查完整性 → 会话、发送人和消息正文。普通查询复用已有私有密钥；仅缺失或校验确实失败时处理密钥捕获，不能把每次读取变成进程扫描。

按`send_time,message_id`倒序默认20条；`next_cursor`绑定账号/会话并保留首次查询的最大本地ID，续页排除随后插入的消息。`--all`返回此会话全部已同步行，云端未同步数据不在范围内；跨库快照不是原子事务。返回服务器/发送人ID为字符串，保留64位精度。已观测文字字段保留全部空白、换行和emoji；未知类型返回完整原始二进制base64与字段，不把猜测文本当作全文。消息查询不自动下载或识别媒体，已缓存原图按[原图导出](media-export.md)另行读取。

`ACCOUNT_NOT_CONFIGURED`：按工作流核对已有本机配置，不猜账号目录；`DATABASE_KEY_MISMATCH`：核对源库与私有密钥；`DATABASE_CHANGED_DURING_SNAPSHOT`：读取期间实际变化，稍后重新读取；WAL校验或不完整错误：保留证据并局部排查，不删除WAL或返回忽略它的旧消息。正常读取没有发送副作用。普通CLI原生文字、图片、文件、GIF和转发/XML发送已按各格式分别验收，按[文字发送契约](send-text.md)或对应格式契约执行，不能从读取成功推定新的收件人投递。原生文件传输助手ID是`FILEASSIST`，内部与自己聊天的`S:自己的ID_自己的ID`是另一会话，不互相改写。
