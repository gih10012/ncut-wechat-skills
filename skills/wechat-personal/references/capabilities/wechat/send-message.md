---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信", "原生发送", "文件传输助手发送", "发送状态", "个人身份发送", "给ClawBot发", "向ClawBot发", "给ClawBot发消息", "向ClawBot发消息"]
exclude_keywords: ["企微", "企业微信", "机器人身份"]
status: "partially_verified"
transport: "installed_linux_cli_queued_client_call"
command: ["native", "send"]
workflow: references/workflows/native-cli.md
note: "CLI接受任意精确会话ID；写入授权由skill/agent判断。普通CLI系统服务实际部署；filehelper文字经手机及Linux显示验收，个人微信与ClawBot文字往返通过；其他对象、个人身份媒体与OneBot事件待验收，不设后端收件人授权白名单。"
---
# 个人微信身份发送

CLI 的读取和文字写入接受任意精确原生会话 ID，包括私聊和群聊。调用 agent 按主 SKILL 判断发送授权；不能把目前验收的 filehelper、ClawBot 范围变成后端白名单，也不能因某目标未实测而自动再次询问已具备的授权。

本机系统辅助服务已安装，以桌面 UID 加 CAP_SYS_PTRACE 运行；普通命令无需 sudo。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径：

```bash
python3 "$WX" native conversations --account me --query '联系人或群名' --limit 5
python3 "$WX" native send --recipient '返回的精确chat_id' --text '消息文字' --request-id '本次唯一ID'
python3 "$WX" native send-status --request-id '原请求ID'
```

发送目标不能用显示名，省略 recipient 默认为 filehelper。精确 ID 为 1–128 个 ASCII 字母、数字或 `_.@-`；文字为 1–1024 个 UTF-8 字节且不含 NUL。request-id 为 4–80 个 ASCII 字符，首位字母或数字，其余可含 `._-`。同一操作固定一个 ID，相同目标/正文只读取已有结果，冲突拒绝。调用失败、超时或本地历史缺失均不自动重试，不切换旧发送后端；先读取原 ID 和接收端。

普通 CLI 的 filehelper 文字已通过本人手机一条完整收件、独立本地数据库读回一条及 Linux 窗口显示确认，见[文件传输助手契约](send-filehelper-text.md)。2026-09-30 个人微信 CLI→ClawBot 的文字被 iLink 精确收到，机器人回执在 Linux 本地数据库独立读回，两方向各一条且有服务器 ID；同 ID 重放未改变原生产物。ClawBot 的 Linux UI 未单独获得本人确认，其他好友/群的实际发送仍未分别验收。技术缺项和授权范围各自记录。

`ok` 仅证明客户端提交调用完成；`local_history_integrated` 是本地数据库证据，`recipient_delivery_verified` 是独立接收端证据，均不推定 Linux UI。pending 任务须接续同一操作，不能当完成。具体账号、正文和消息 ID 只留本机。

向文件传输助手或 ClawBot（含测试、媒体、OneBot）已有长期授权。向其他对象写入需要当前任务授权或适用的事先直接/间接授权，例如指定对象与内容、委托回复、已授权工作流；按实际范围执行，无需重复询问。读取本人会话直接执行。ClawBot 机器人→绑定本人是另一身份，长期读写授权保持，不能用机器人发送代替个人身份验收。

个人身份图片、文件、表情包及公众号卡片尚未实现或验收；逐项定位真实客户端入口及上传/对象生命周期，不能把文字、链接或机器人媒体代作完成。OneBot 当前仅提供限时私聊文字动作子集和已列元信息动作，事件、群动作及媒体动作仍缺项；这属于协议适配范围，CLI 不因它限制群聊目标。详见[OneBot流程](../../workflows/onebot.md)。
