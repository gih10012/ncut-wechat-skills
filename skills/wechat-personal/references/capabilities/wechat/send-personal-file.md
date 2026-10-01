---
id: send-personal-file
service: wechat
keywords: ["微信发文件", "个人微信发文件", "个人身份发文件", "个人微信发送文件", "微信文件发送", "微信发ZIP", "微信中文文件名"]
exclude_keywords: ["机器人身份", "ClawBot机器人", "企微", "企业微信"]
status: "runtime_verified"
transport: "installed_linux_cli_queued_file_call"
command: ["native", "send", "--file"]
workflow: references/workflows/native-cli.md
note: "2026-10-01普通CLI以个人微信身份向ClawBot发送中文文件名TXT与ZIP，独立iLink各收到一条，文件名和下载字节一致，Linux UI正常；同ID重放未重新提交，改文件名或文字动作拒绝。"
---
# 个人微信文件发送

```bash
python3 "$WX" native send --recipient '精确chat_id' --file '/路径/文件.zip' --request-id '本次唯一ID'
python3 "$WX" native send-status --request-id '原ID'
```

也可直接用 `wechat-linux send-file --recipient '精确chat_id' --file '/路径/文件.zip' --request-id '本次唯一ID'`。输入为桌面用户可读的常规文件，1 字节到 10 MiB，原文件名最多 255 个 UTF-8 字节。CLI 接受相对路径并转换为绝对路径，服务私存文件快照，保留文件名；预检与提交绑定同一目标、客户端、文件名和字节哈希。文字、图片和文件参数互斥。空文件、大文件和其他尚未实测格式不由本契约保证。

CLI 接受任意精确会话 ID；发送授权按主 SKILL 判断。filehelper/ClawBot 已有长期授权，其他目标依据当前任务或适用的事先直接/间接授权。相同 ID、目标、文件名和字节只读返回旧结果；移动文件但保留文件名可复用，改名、改内容、改目标或发送动作拒绝。原文件已删除时用 send-status。未知结果保留原 ID，不换 ID 重发。

2026-10-01 从仓库外以普通用户运行系统服务发送中文文件名 TXT 与 ZIP 到 ClawBot。独立 iLink 各收到一条文件，下载文件名和字节均与输入一致；ZIP 解压完整性检查通过。Linux 聊天窗口显示完成的文件卡片，本地数据库各一条同名记录且有服务器 ID。两个 ID 的重放未改变原生产物内容或时间，改名和文字动作冲突拒绝，之后 iLink 没有新入站。

开发中清理曾把快照目录改为 600，导致一条测试文件异步上传中断；已修正为目录 700、文件 600，并用新中文文件请求完成上述验收，旧失败请求保留且未重发。私有快照需保留至客户端上传完成，不能在本地插入返回后立即删除或取消目录执行权限。

`ok` 只证明客户端提交完成，不等于上传或收件成功。默认 `local_history_filename_matches` 是新增同名类型 49 记录的候选数，`local_history_integrated` 可为 null；独立 UI、数据库服务器 ID 和接收端下载核验后才写私有确认。其他收件人、超过 10 MiB、原生表情包、卡片及 OneBot 文件动作仍需分别验收。
