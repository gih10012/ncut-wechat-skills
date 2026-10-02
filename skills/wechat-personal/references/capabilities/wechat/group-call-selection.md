---
id: wechat-group-call-selection
service: wechat
keywords: ["微信群成员选择", "群通话预检", "指定群成员", "群语音CLI", "群聊呼叫"]
status: "partially_verified"
command: ["native", "call", "group-prepare", "--pid", "<client_pid>", "--start-time", "<proc_start_time>", "--chat", "<group_id>", "--member", "<member_id>"]
evidence: "2026-10-03 source and installed ordinary skill commands navigated from another chat, selected exactly one or two authorized members in the normal Qt selector, canceled and verified its closure without an invitation. 171 CLI tests completed, one skipped; all 23 installed package files match source/wheel. Group invitation, hangup, remote join and group audio remain unverified."
transport: "normal_qt_atspi_and_niri_keyboard"
note: "群成员选择与取消已实测；start提交实现仍待邀请/挂断验收，群连接未实现可靠核对，call play拒绝群播音。"
---

# 微信群通话成员选择

先按[通话授权](voice-call.md)核对精确群和每个邀请成员；不能默认邀请全群。读取会话/联系人定位精确ID，使用当前微信PID与启动时间。

```sh
native call group-prepare --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确群ID --member 精确成员ID --member 另一成员ID
native call start --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确群ID --member 精确成员ID --request-id GROUP_CALL_ID
native call status --request-id GROUP_CALL_ID
native call hangup --request-id GROUP_CALL_ID
```

`group-prepare`不邀请：核对账号数据库、唯一群标题及人数、缓存群成员、本人默认勾选；按精确ID对应的唯一名称勾选指定成员，再核对每个复选框、总数和未选成员。最后正常取消并验证原选择窗口关闭。支持1–8个不同的其他成员，缺失缓存、同名或窗口变化时拒绝；GUI不暴露原生ID，名称匹配不等于直接读取GUI精确ID。成员在正常列表中不可选时不会改邀其他人。

`start`实现使用相同检查，再按一次正常“完成”。ID绑定排序后的成员集合，冲突拒绝、重放不拨号；未知结果按[私聊控制](private-call-control.md)检查原请求，不换ID重试。此提交与群挂断尚未取得普通CLI实际邀请验收，调用前保留该状态。当前群状态为`group_connection_unverified`，`call play`拒绝群播音；本地计时或输入流不能证明所邀成员接通。

2026-10-03已实测源码单成员、双成员选择；普通安装skill在另一私聊开始，导航到本人测试群、仅选两个授权小号，然后取消并确认关闭。全程没有新通话邀请，不将选择成功算作接通、对端收音或群通话完成。本人已停止切小号进行手机验收，不主动要求再切号；待验收项如实保留。
