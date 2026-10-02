---
id: wecom-send-file
service: wecom
keywords: ["企微文件发送", "企业微信发文件", "企微TXT", "企微ZIP", "企微附件发送"]
status: "runtime_verified"
evidence: "2026-10-02 installed ordinary native CLI Chinese-filename TXT and ZIP independently received once in authorized personal WeChat peer; downloaded bytes equal inputs, both client file cards render, replay/conflict checks passed"
runtime_verified_at: "2026-10-02T09:50:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_native_ui_thread"
command: ["wecom", "send-file", "--account", "me", "--chat", "EXACT_CHAT_ID", "--file", "FILE_PATH", "--request-id", "UNIQUE_REQUEST_ID"]
note: "先检查发送授权；已实测本人授权微信对应会话的中文文件名TXT/ZIP。保留文件名和内容，1字节至10 MiB，未知结果只查原ID，不换ID或GUI重发。"
---
# 企业微信本人身份文件

先按主SKILL核对当前任务或事先发送授权；本人长期授权的精确微信/企微会话对可直接读写，不扩展到同名其他对象。普通用户调用已安装CLI，无需sudo、键鼠或亮屏。

```sh
python3 "$WX" wecom send-file --account me --chat '精确chat_id' --file '/路径/中文文件.zip' --request-id '唯一ID'
python3 "$WX" wecom send-status --request-id '原请求ID'
```

常规文件1字节至10 MiB，保留原文件名和完整内容；文件名UTF-8最多768字节，拒绝symlink及Windows非法文件名。已实测中文文件名TXT和ZIP；其他格式、内部企微会话与群聊分别验收。`send-file`发送附件，GIF用此命令是文件，不据此判原生自定义表情已支持。图片直接用[图片契约](send-image.md)。

支持已校验SHA-256的官方Windows 5.0.11.6018及已配置独立Wine账号，首次需要32位MinGW。输入先复制到0700/0600的私有`send-assets/`；原生对象深拷贝文件名和路径，预检核对序列化文件名/原始大小/路径及释放，再持久化防重记录并提交一次。副本在异步上传、命令退出及未知结果时保留。构造预检已内置，通常无需另跑；显式`send-file-preflight`使用同样参数但不发送。

同ID绑定文件名与内容哈希，改名、换内容或复用为图片/文字动作均拒绝；同ID相同文件只查询已有结果。超时/中断保持`submission_unknown`，查询原ID和接收端，不换ID或在窗口重试。成功核对账号、发送人、会话、原生返回本地ID、非零服务器ID，以及type15的文件名/MD5/大小。单命令的`recipient_delivery_verified:false`仅说明它没有查询另一客户端；独立验收证据另存。

2026-10-02已安装普通CLI TXT和skill→普通CLI ZIP各送达本人授权微信对应会话一条，下载文件名及字节完整一致，两边窗口均显示文件名和大小。同ID重放没有新增，换文件冲突拒绝；上一版本PNG请求升级后仍正常重放、不重发。文件/图片/文字构造预检均未新增消息，58项测试通过。此处是发送验收，不证明企微入站文件的主动下载；表情、转发卡片、自定义XML继续按企微工作流开发。私有路径、账号标识及详细消息证据不提交公共仓库。
