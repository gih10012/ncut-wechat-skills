---
id: send-filehelper-text
service: wechat
keywords: ["文件传输助手发文字", "文件传输助手发消息", "文件传输助手发送文字", "文件传输助手发送消息", "OneBot文件传输助手", "OneBot原生文字"]
exclude_keywords: ["发图片", "发文件", "发送图片", "发送文件", "语音", "表情包", "公众号卡片"]
status: "runtime_verified"
runtime_verified_at: "2026-09-21"
transport: "local_onebot12_http"
command: ["onebot", "call"]
workflow: references/workflows/onebot.md
note: "已通过本人Linux微信真实OneBot调用发送filehelper中文多行文字，手机确认只收到一条且emoji正常；相同请求ID不重发。call从stdin读动作JSON，复用限时本机入口；入口未运行时需一次本机sudo启动，不重找后端。仅文字和filehelper，不含事件、媒体或其他对象。"
---
# 个人身份向文件传输助手发文字

已通过安装后的OneBot12 HTTP发送动作及原生后端完成实际发送，本人确认手机收到一条且换行、Unicode表情正常。一次零错误完成回调、回调释放和微信继续运行均已核对。同请求ID重放得到原结果，原生记录内容及修改时间不变，服务发送计数仍为1；同ID改正文被拒绝。范围只到当前匹配的Linux版本、filehelper文字和已列动作，不代表完整OneBot协议或其他对象/格式可用。

个人身份向filehelper已有长期授权，正常命中直接调用。下文`$WX`为本skill的`scripts/wechat.py`绝对路径。`python3 "$WX" onebot call`从stdin读取：

```json
{"action":"send_message","params":{"detail_type":"private","user_id":"filehelper","message":"消息文字","wechat.request_id":"unique-ascii-request-id"}}
```

文字为1–1024个UTF-8字节、不能包含NUL，也可用text消息段数组。每次操作选择新的4–80位ASCII请求ID（首位字母或数字，其余可含`._-`），同一操作始终复用它；`echo`仅关联响应。不要用新ID重复发送结果不确定的同一条消息。

`call`自动从本人0600私有会话文件读取回环端点及Bearer，无需输出凭证。若返回无活动入口，当前需本机运行一次`sudo python3 "$WX" onebot serve --duration 600 --max-sends 3`；发送授权已有，缺少的是系统调试权限。服务在10分钟后退出，不安装后台常驻。启动、状态位置和超时处理见[限时入口](../../workflows/onebot.md#限时原生文字入口)。

`status=ok`仅在原生往返、一次零错误回调、回调释放及调试器清理通过后返回。`message_id`是本地请求ID，原生任务号另列，不能当服务器消息ID。`wechat.recipient_delivery_verified`是该请求独立收件证据，正常新请求可能为false，不因此重发；本项验收已另获本人确认。只读查询原生记录用`python3 "$WX" native send-status --request-id '原请求ID'`。

当前适配未写回Linux本地发送历史，不能凭历史缺少该条判断失败。若需要个人身份向其他目标或发送媒体，读取[通用发送状态](send-message.md)，逐项按证据推进。
