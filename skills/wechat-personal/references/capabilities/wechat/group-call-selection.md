---
id: wechat-group-call-selection
service: wechat
keywords: ["微信群成员选择", "群通话预检", "指定群成员", "群语音CLI", "群聊呼叫"]
status: "partially_verified"
command: ["native", "call", "group-prepare", "--pid", "<client_pid>", "--start-time", "<proc_start_time>", "--chat", "<group_id>", "--member", "<member_id>"]
evidence: "2026-10-03 source and installed ordinary commands selected exactly one or two authorized members and canceled without invitation. Installed two-member start, normal hangup and same-ID replay then passed; independently synced group history has one start and one end with nonzero server IDs. Unverified group connection blocked play without creating an audio journal. 172 tests, one skipped; 23 source/wheel/installed package files identical. Remote join/group audio and WeCom group controls remain unverified."
transport: "normal_qt_atspi_and_niri_keyboard"
note: "指定群成员选择/取消、邀请/正常挂断/防重已实测；群连接仍未可靠核对，call play拒绝群播音。"
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

`start`使用相同检查，再按一次正常“完成”。ID绑定排序后的成员集合，冲突拒绝、重放不拨号；未知结果按[私聊控制](private-call-control.md)检查原请求，不换ID重试。搜索和逐成员核对的UI期限按1–8个成员有界增加，避免20秒私聊期限在“完成”前终止群选择。普通CLI双成员邀请及正常挂断已真实通过，但群状态仍为`group_connection_unverified`，`call play`拒绝群播音；本地计时或输入流不能证明所邀成员接通。

2026-10-03先实测源码单成员、双成员选择；普通安装skill从另一私聊导航到本人测试群、仅选两个授权小号，再取消并确认关闭，预检没有邀请。后续普通CLI双成员邀请、正常挂断与同ID不重拨通过，独立历史一条发起/一条结束且服务器ID非零；群play明确拒绝、未创建音频日志。前轮20秒超时留下选择窗口，正常取消、独立确认已结束并resolve原ID后，才验证修复后的新操作。没有登录小号或改变主号；未取得对端加入/收音，不将邀请/挂断算作完整群通话完成。
