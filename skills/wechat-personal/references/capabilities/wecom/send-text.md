---
id: wecom-send-text
service: wecom
keywords: ["企微发送", "企业微信发消息", "企微文字", "企业微信回复", "企微发送状态"]
status: "runtime_verified"
evidence: "2026-10-01 installed ordinary native CLI authorized external chat; independent WeChat recipient exact-once readback, both client UIs, server IDs and replay/conflict verification"
runtime_verified_at: "2026-10-01T20:28:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_native_ui_thread"
command: ["wecom", "send-text", "--account", "me", "--chat", "EXACT_CHAT_ID", "--text", "TEXT", "--request-id", "UNIQUE_REQUEST_ID"]
note: "先检查SKILL发送授权及本机send-authorizations.json；接受任意精确ID，不设后端授权白名单。已验收本人授权的微信对应会话文字；其他群聊另行验收，PNG/JPEG见独立图片契约。未知结果只查询原ID，不重发。"
---
# 企业微信本人身份文字

读取本人会话直接执行；写入先按主SKILL检查当前任务或适用的事先授权。本人长期授权的微信/企微对应会话可直接双向读写，精确ID、名称后缀及首次绑定证据留在本机授权登记；不把此授权扩展到同名内部自己聊天或其他联系人。

```sh
python3 "$WX" wecom send-text --account me --chat '精确chat_id' --text '完整文字' --request-id '唯一ID'
python3 "$WX" wecom send-status --request-id '原请求ID'
```

普通用户调用，不需sudo或键鼠输入。仅支持已校验SHA-256的官方Windows 5.0.11.6018、已配置的独立Wine prefix、精确账号及唯一未被调试的主进程。首次调用需要本机32位MinGW编译器。只读定位发送管理器 → 核对进程创建时间、窗口UI线程及当前账号 → 同一产物进行不发送的构造预检并校验完整正文 → 持久化请求状态 → UI线程原生调用一次。对象使用客户端分配器/析构；小型模块留到客户端退出，避免回调卸载竞态。

文字为1–3072个UTF-8字节、不含NUL，保留空白/换行/emoji；请求ID为4–80个ASCII字母数字或`._-`，首位字母数字。支持精确ID或唯一完整名称，同名须选ID。`FILEASSIST`是真实文件传输助手；内部自己的`S:`聊天是独立会话，不做目标改写。CLI没有授权收件人白名单。

同ID和相同参数返回已有结果，改变参数返回`REQUEST_ID_PAYLOAD_CONFLICT`。请求在原生提交前落盘并fsync；超时/中断保留`submission_unknown`，不能换ID或窗口重试。`send-status`只读取并依据返回的本地ID核对账号、会话、发送人、完整正文及非零服务器ID。`sent_local_server_id_verified`证明本地服务器回执；独立接收端与窗口显示是另行验收，不由函数返回或缓存缺失推断。`recipient_delivery_verified:false`表示该命令本身没有查询另一客户端，不抹去本机另存的独立接收端证据。

2026-10-01普通CLI向本人授权的微信对应会话文字发送已通过，两个独立读取端与窗口均完整显示且各一条/有服务器ID；反向个人微信CLI入站也通过。同ID重放没有重复，正文冲突拒绝。此前文件传输助手原生候选获本人手机正常确认。普通群聊、表情/卡片/XML、长期稳定性仍未单独验收；PNG/JPEG见[图片契约](send-image.md)，TXT/ZIP见[文件契约](send-file.md)。已具备发送授权无需因技术验收范围有限再次确认。支持范围、授权范围分别记录。

`UNSUPPORTED_CLIENT_BINARY_NO_NATIVE_CALL`：版本不匹配，不猜偏移或调用；`SEND_MANAGER_OR_ACCOUNT_NOT_VERIFIED`：核对现有客户端和精确账号；`submission_unknown`：查询原ID和对应接收端。不会自动换身份、重扫密钥或重发。请求正文和原生ID仅保存于本机0700/0600状态，不提交公共仓库。
