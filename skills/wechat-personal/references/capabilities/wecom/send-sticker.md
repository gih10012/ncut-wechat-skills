---
id: wecom-send-sticker
service: wecom
keywords: ["企微表情发送", "企业微信自定义表情", "企微GIF", "企微表情包", "企业微信动画表情"]
status: "runtime_verified"
evidence: "2026-10-02 installed ordinary native CLI animated GIF independently received once as personal WeChat type47; XML MD5/length and server IDs match, both UIs animate, replay and rename-conflict checks passed"
runtime_verified_at: "2026-10-02T12:34:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_native_ui_thread"
command: ["wecom", "send-sticker", "--account", "me", "--chat", "EXACT_CHAT_ID", "--sticker", "GIF_PATH", "--request-id", "UNIQUE_REQUEST_ID"]
note: "先检查发送授权；动画GIF已实测至本人授权微信对应会话。原生表情input29、微信type47，1字节至10 MiB；未知结果只查原ID，不换ID或GUI重发。"
---
# 企业微信本人身份 GIF 表情

先按主SKILL核对发送授权；本人长期授权的精确微信/企微会话对可直接读写，不扩大到其他同名对象。调用普通安装CLI，无需sudo、键鼠或亮屏。

```sh
python3 "$WX" wecom send-sticker --account me --chat '精确chat_id' --sticker '/路径/表情.gif' --request-id '唯一ID'
python3 "$WX" wecom send-status --request-id '原请求ID'
```

GIF文件1字节至10 MiB，拒绝symlink与Windows非法文件名；逻辑尺寸每边最多32768、总计6400万像素，最多2000帧，检查完整块边界与结束标记。已实测96×96三帧动画GIF发到本人授权的微信对应会话；其他会话、静态GIF、PNG/JPEG自定义表情仍需分别验收。`send-file`发GIF是附件，不代替本入口。

支持已校验SHA-256的官方Windows 5.0.11.6018和独立Wine账号。输入先私有复制并固定哈希；原生EmotionMessage有独立构造、共享控制块和析构，不复用FileMessage内存布局。内置预检核对完整序列化路径、尺寸、表情类型及释放，再持久化防重记录、提交一次；原生异步引用保留上传数据，副本在命令退出和未知结果时保留。显式`send-sticker-preflight`只构造，不发送。

同ID绑定文件名、内容哈希、格式、尺寸和帧数，相同输入只查询已有结果；改名、换内容或跨文字/图片/文件动作冲突拒绝。超时/中断保持`submission_unknown`，只查询原ID及接收端。发送成功核对账号、发送人、会话、本地返回ID、非零服务器ID，以及type29的MD5/尺寸/表情类型。单命令没有查询另一客户端，因此其`recipient_delivery_verified:false`与另存的独立验收证据分别解释。

2026-10-02普通安装CLI向授权微信对应会话送出一条GIF；独立微信读取为type47，XML MD5/长度匹配，双方窗口显示变化的动画帧。同ID重放未新增、改名拒绝；升级前TXT请求仍正常重放。己方临时原生引用释放后，客户端异步引用继续持有对象；构造预检不新增消息，65项测试通过，安装wheel的23个包文件逐字节一致。微信接收端表情缓存仍是加密数据，原始GIF导出尚未验证，不能以XML哈希推定已完成下载/解密。卡片转发、自定义XML按企微工作流继续开发。
