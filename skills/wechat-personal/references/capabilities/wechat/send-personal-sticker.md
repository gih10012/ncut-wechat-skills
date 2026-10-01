---
id: send-personal-sticker
service: wechat
keywords: ["个人微信表情包", "个人身份表情包", "个人微信发GIF", "微信发送自定义表情", "微信原生表情包"]
exclude_keywords: ["机器人身份", "ClawBot机器人", "企微", "企业微信"]
status: "runtime_verified"
transport: "installed_linux_cli_queued_emoticon_call"
command: ["native", "send", "--sticker"]
workflow: references/workflows/native-cli.md
note: "2026-10-01普通CLI向文件传输助手发送原生type47动画GIF，独立XML的MD5/长度、服务器ID、Linux动画显示及同ID防重通过；本人确认手机文件传输助手正常。ClawBot手机端不支持自定义表情，仅支持emoji；不能作为GIF收件验收对象。PNG/JPEG表情及其他对象待独立验收。"
---
# 个人微信原生表情包

```bash
python3 "$WX" native send --recipient '精确chat_id' --sticker '/路径/sticker.gif' --request-id '本次唯一ID'
python3 "$WX" native send-status --request-id '原ID'
```

独立命令为 `wechat-linux send-sticker --recipient '精确chat_id' --file '/路径/sticker.gif' --request-id '本次唯一ID'`。这是客户端原生表情消息（47），与图片消息（3）、文件和文字 emoji 分别构造。输入为桌面用户可读的常规文件，1 字节到 10 MiB；按字节识别 GIF/PNG/JPEG，实际端到端验收仅覆盖动画 GIF。PNG/JPEG 表情不能据此称为已验收。普通使用无需 sudo。

服务先私存输入快照，再做绑定同一目标、字节哈希及客户端身份的不发送构造预检，随后让客户端自身解析表情、计算媒体信息并上传。任意精确会话 ID 均可传入，发送授权按主 SKILL 判断。相同 ID/目标/字节只读返回旧结果；改内容、对象或动作冲突拒绝。结果不明时检查原 ID，不换 ID 重发；原文件已移走可直接用 send-status。

2026-10-01 从仓库外以普通用户运行已安装 CLI，向文件传输助手发送三帧循环 GIF：本地新增一条 type47 消息、取得服务器 ID，原始 XML 的 MD5 和长度与输入一致，Linux 显示动画；本人确认手机文件传输助手正常。相同 ID 重放没有新原生调用，预检、发送及输入快照共42个产物的哈希/修改时间未变；换图片动作和改变表情字节均拒绝。

另一条发给 ClawBot 的原生 GIF 已取得服务器 ID，本地 XML 类型、MD5、长度一致，但 iLink 没有返回对应表情项。本人明确说明 ClawBot 手机端本身不支持自定义表情，只能使用 emoji。保留该次结果，不重发、不把客户端提交或空轮询当作 ClawBot 表情可用。文件传输助手验收证明个人身份 GIF 发送，不扩展到 ClawBot 富消息或其他对象。

默认 `ok` 仅表示客户端提交完成。`local_history_type_matches` 是类型候选，不能证明 GIF 字节或投递；独立 XML、UI 和本人确认另存私有 acceptance。原生表情不由机器人普通图片/GIF文件发送替代。
