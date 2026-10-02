---
id: wecom-send-image
service: wecom
keywords: ["企微图片发送", "企业微信发图片", "企微PNG", "企微JPEG", "企微图片"]
status: "runtime_verified"
evidence: "2026-10-02 installed ordinary native CLI PNG and Chinese-filename JPEG; authorized personal WeChat recipient independently received each once, both UIs displayed them, cached originals matched inputs, replay/conflict checks passed"
runtime_verified_at: "2026-10-02T01:01:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_native_ui_thread"
command: ["wecom", "send-image", "--account", "me", "--chat", "EXACT_CHAT_ID", "--image", "IMAGE_PATH", "--request-id", "UNIQUE_REQUEST_ID"]
note: "先检查SKILL发送授权及本机send-authorizations.json；PNG/JPEG本人授权微信对应会话已实测，接受任意精确ID，不设授权白名单。未知结果只查原ID，不能换ID或GUI重发。"
---
# 企业微信本人身份图片

先按主SKILL检查当前任务或事先发送授权。本人长期授权的微信/企微对应会话可直接使用，精确ID与单位后缀保存在本机授权登记，不扩展到其他同名对象。

```sh
python3 "$WX" wecom send-image --account me --chat '精确chat_id' --image '/路径/图片.jpg' --request-id '唯一ID'
python3 "$WX" wecom send-status --request-id '原请求ID'
```

普通用户命令，不需sudo、键鼠或亮屏；支持已校验的官方Windows 5.0.11.6018及已配置独立Wine账号，首次需要32位MinGW。PNG/JPEG正规文件1字节至10 MiB，每边最多32768、总计最多6400万像素；扩展名须匹配格式。保留中文文件名，拒绝symlink及Windows非法文件名。`send-image-preflight`使用相同图片参数，仅核对原生构造/序列化及释放，不发消息；正常发送已自动执行预检，不需另跑。

CLI先复制输入到0700/0600的私有`send-assets/`，绑定文件名、内容哈希、格式和尺寸；原文件修改不会改变已提交的上传。副本保留到后续明确清理，不因命令结束或结果未知删除。账号/进程/线程及字节签名核对通过后，原生预检校验文件名、路径和尺寸，再将防重记录fsync并提交一次。使用客户端原生对象、字符串拷贝与异步引用；若无法确认异步所有权，则报告`native_handles_retained`并保留两个小型句柄至客户端退出，不猜测上传结束。

同ID同图片返回已有结果，改内容或文件名拒绝。超时/中断保持`submission_unknown`，只查原ID及接收端，不换ID或用窗口重试。成功状态核对精确账号、会话、发送人、本地ID、非零服务器ID及type14的文件名/MD5/大小/尺寸。`recipient_delivery_verified:false`仅说明该命令没有查询另一客户端；独立接收端验收另存。

2026-10-02普通已安装CLI的PNG与中文文件名JPEG各被本人授权微信对应会话独立收到一条，两端窗口完整显示；[原图导出](media-export.md)与输入逐字节一致。PNG同ID重放没有新增，替换图片冲突拒绝；51项CLI测试通过。此范围不包括普通群聊、外部入站JPEG、GIF表情或卡片/XML发送。TXT/ZIP见[文件契约](send-file.md)。技术范围与发送授权分别记录，已有授权不重复询问。私有路径、原生ID、正文及日志不提交公共仓库。
