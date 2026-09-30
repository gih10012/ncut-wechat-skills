---
id: send-filehelper-text
service: wechat
keywords: ["文件传输助手发文字", "文件传输助手发消息", "文件传输助手发送文字", "文件传输助手发送消息", "OneBot文件传输助手", "OneBot原生文字"]
exclude_keywords: ["发图片", "发文件", "发送图片", "发送文件", "语音", "表情包", "公众号卡片"]
status: "runtime_verified"
runtime_verified_at: "2026-09-30"
transport: "installed_linux_cli_queued_client_call"
command: ["native", "send", "--recipient", "filehelper"]
workflow: references/workflows/native-cli.md
note: "普通用户调用已安装 CLI 服务发送中文多行文字；本人确认手机一条且完整、Linux窗口显示；独立数据库读回一条。同ID重放不重发，冲突拒绝。OneBot旧路径有真实手机验收，新CLI适配另通过HTTP已有请求重放，未据此宣称新HTTP发送验收。"
---
# 个人身份向文件传输助手发文字

本机已安装独立 CLI 和特权辅助服务，正常发送不需要 sudo。本人长期授权向文件传输助手发送，命中直接调用。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径：

```bash
python3 "$WX" native send --recipient filehelper --text '消息文字' --request-id '本次唯一ID'
python3 "$WX" native send-status --request-id '原请求ID'
```

也可直接运行 `wechat-linux send-text --recipient filehelper --text '消息文字' --request-id '本次唯一ID'`。skill 优先委托安装的 CLI；某次调用失败或超时不会改用旧发送器。仅没有安装 CLI 时保留旧入口，旧发送入口需要本机调试权限，不能据此让已安装机器的日常操作使用 sudo。

文字为 1–1024 个 UTF-8 字节且不含 NUL。request-id 为 4–80 个 ASCII 字符，首位字母或数字，其余可含 `._-`。每次新操作用唯一 ID，同一操作始终复用它；同 ID、正文和目标只返回原结果，冲突拒绝。状态未知先读取原 ID 和接收端，不删除防重记录、不换 ID 重发。

`ok` 证明客户端提交调用完成，`local_history_integrated` 单独记录本地数据库证据，接收端与 Linux UI 分别确认。密钥缺失或读回不明确时字段可为 null，不据此重发。2026-09-30 普通 CLI 发送已获本人手机单次完整收件及 Linux 显示确认，数据库读回一条，服务防重与冲突拒绝通过。具体账号、正文和消息 ID 仅私存。

需要 OneBot 时按[限时 HTTP 入口](../../workflows/onebot.md#限时原生文字入口)启动普通用户适配；它复用安装的服务、不另部署常驻接收器。2026-09-21 旧原生 OneBot 路径已通过真实文字与手机验收；2026-09-30 新 CLI 适配通过普通用户 HTTP 已有请求重放，原生工作产物未变，尚未以此验证一次新的 HTTP 提交。两轮范围分开记录。

其他会话与媒体见[通用发送契约](send-message.md)。
