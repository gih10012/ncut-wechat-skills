---
id: wecom-group-call-selection
service: wecom
keywords: ["企微选择窗", "企微群语音控制", "企业微信群成员选择", "企微取消成员选择"]
status: "partially_verified"
command: ["wecom", "call", "inspect", "--account", "me"]
evidence: "2026-10-03 installed ordinary CLI read a complete 443-node empty normal group voice picker, kept it separate from incoming/active calls, refused private start/target preflight/answer while it was open, and activated the verified normal cancel button. Independent group history remained unchanged, no member selected or invited; closed/stale token refused. 119 CLI tests, native compilation and 29 source/wheel/installed file equality passed. Exact member ID binding, selected-state control, CLI group invitation and remote join/audio remain unfinished."
transport: "version_bound_normal_duilib_member_picker"
note: "企微成员选择窗完整读取和正常取消已由普通CLI实测；精确成员选择、群邀请、群连接和播音仍待实现。"
---

# 企微群成员选择

目前可复用的普通CLI能力是读取、取消实际打开的成员选择窗；还不能用CLI打开群语音选择、指定成员或提交群邀请。私聊通话按[私聊契约](private-call-control.md)调用，群整体按[通话契约](../wechat/voice-call.md)继续。本人要求保持电脑主号，不要求切小号；选中、邀请其他人须核对当前或事先授权。

```sh
wecom call inspect --account me
wecom call selector-cancel --account me --selector-token 本轮selector_token
```

`inspect`把完整且已核验类型/归属的窗口放在`member_selectors`，与`incoming`和`active`分开。字段包括会话标题、搜索文字、当前可见复选框数及节点数；仅为界面读数，不能据名字推出精确成员ID，也不能把复选框数量当已选人数。`selector_purpose_verified/member_identity_verified/selection_verified/call_connection_verified`保持false；同种正常窗口用于多种成员选择，不靠标题猜测已提交邀请。

当正式取消控件、唯一“取消”文字和完整控件树均通过时，返回`cancel_control_verified=true`及`selector_token`。令牌绑定账号、进程创建时间、HWND/root/取消控件和本轮标题；`selector-cancel`重新读取并核对令牌，在原UI线程通过正式DuiLib按钮方法取消，然后独立读取确认原窗口关闭。它只取消本地窗口，不发送邀请，无通话request-id；已关闭或变化的令牌拒绝。超时/未知结果不自动再按取消，先`inspect`核对真实窗口，必要时用computer-use正常取消。

选择窗打开时，`start/answer/带目标preflight/resolve`拒绝继续；原生拨号/接听在动作前再检查，避免界面状态变化后的错误操作。无目标预检可做本地DLL准备，但不是呼叫成功。正常UI取消自行恢复niri显示电源/亮度；已有其他显示会话时拒绝。

依赖与私聊契约相同的官方5.0.11.6018、主程序/DuiLib/owl哈希、账号/进程/UI线程及控件类型核验。真实读回修正了非零偏移的非虚基类接口判断，保留完整树/父子关系/窗口归属和有界读取检查。原始窗口树和身份仅存本机私有状态，不公开群名称、成员或原始指针。

已验收：空的真实群语音选择窗完整443节点；打开时普通私聊发起、目标预检和接听均拒绝，未创建通话日志；普通CLI正常取消返回`activated=true/selector_closed_observed=true`；独立群历史逐条不变，未选中或邀请成员；旧令牌再次调用被拒绝，客户端保持无跟踪，显示恢复。仍缺精确原生成员ID绑定、可验证的已选状态、指定成员邀请提交、群连接判断及对端收音。不能以本项读取/取消或已通过私聊播音声称群通话已完成。
