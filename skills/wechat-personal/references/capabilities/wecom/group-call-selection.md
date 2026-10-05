---
id: wecom-group-call-selection
service: wecom
keywords: ["企微选择窗", "企微群语音控制", "企业微信群成员选择", "企微取消成员选择", "企微勾选联系人", "企微群预检", "企微打开群语音选择窗"]
status: "partially_verified"
command: ["wecom", "call", "inspect", "--account", "me"]
evidence: "2026-10-03 installed CLI verified complete group-picker read/cancel and call refusals. 2026-10-05 a read-only classic group picker yielded 13 exact native member IDs, all independently matched to local group membership. Installed ordinary CLI read a group-creation picker, excluded department metadata, selected the exact authorized external owner contact via normal COptionUI Activate, independently observed checked state and UI selected count, replayed selection read-only, deselected and normally canceled it; private start was refused before journaling. 125 CLI tests passed. Subsequent installed ordinary group-prepare opened the exact group voice picker, independently read two matching native group-ID strings, tracked picker status, replayed without reopening, refused a changed target, normally canceled and observed ended status; independent group history stayed unchanged. 129 CLI tests and 29 source/wheel/installed files matched. Further installed ordinary CLI acceptance verified an empty classic native selected-model snapshot, normal cancellation, open/ended status and read-only replay with unchanged group history; 132 tests and 30 source/wheel/installed files matched. Nonempty/off-screen runtime selection remains unverified. No group creation, invitation, remote join or group audio was performed."
transport: "version_bound_normal_duilib_member_picker"
note: "企微精确群语音选择窗打开/状态/防重、成员窗读取/取消及精确可见联系人勾选/取消勾选已由普通CLI实测；群语音页勾选、邀请提交、跨滚动完整选择、群连接和播音仍待验收。"
---

# 企微群成员选择

普通CLI可按精确群ID打开空的语音选择窗，读取/取消实际打开的成员选择窗，并勾选/取消勾选一个精确可见联系人；尚不能提交群邀请。联系人勾选的真实验收在建群选择窗完成，不等于群语音页提交验收。私聊通话按[私聊契约](private-call-control.md)调用，群整体按[通话契约](../wechat/voice-call.md)继续。保持电脑主号，不要求切小号；选中、邀请其他人须核对当前或事先授权。

```sh
wecom call inspect --account me
wecom call group-prepare --account me --chat 精确R群ID --request-id GROUP_PREPARE_ID
wecom call status --request-id GROUP_PREPARE_ID
wecom call selector-cancel --account me --selector-token 本轮selector_token
wecom call selector-select --account me --selector-token 本轮selector_token --member-id 精确原生用户ID --select
wecom call selector-select --account me --selector-token 本轮selector_token --member-id 精确原生用户ID --deselect
```

`inspect`把完整且已核验类型/归属的窗口放在`member_selectors`，与`incoming`和`active`分开。`selector_type`区分普通`CSelectUserFrame`和建群`CSelectUserFrame2`，字段包括会话标题、搜索文字、可见复选框数、节点数及`visible_members`。后者由正式`GetUserData/IsSelfSelected`读取原生用户ID和该复选框自身状态，不能使用会继承父状态的`IsSelected`。普通选择页的原生ID已与群数据库核对；建群页仅识别已验证的外部个人元数据格式，部门及其他未知格式不冒充用户ID。ID重复拒绝。

`group-prepare`要求精确`R:数字ID`及唯一正常附着会话view；缺view时用computer-use打开该精确会话再执行，不以同名标题代替。它完成本地DLL准备、原生目标预检，在开页前持久保存请求ID，再调用正常语音入口。新窗口的两处独立填入的原生配置字符串必须均为该精确群ID，返回`bound_group_chat/group_binding_verified`；此字段不证明完整选择或邀请提交。建群选择窗不返回群绑定。

请求成功为`member_selector_open`，`normal_voice_entry_verified=true`，`invitation_performed=false`；`status`跟踪原选择窗而非活动通话，正常关闭后变为`ended`。同ID只返回原记录，关闭后也不会重开；改群冲突。超时保留`group_prepare_unknown`，阻止新ID，先查原ID及实际窗口；不能从另一个新窗口推断旧请求结果。取消使用本轮`selector-cancel`，不是`hangup`；未知且未记录窗口时须独立核对结束后按私聊契约的`resolve --ended`解除本地未决，不把它变成邀请成功。

`visible_member_states_verified/member_identity_verified`仅证明返回的可见个人行，`selected_visible_member_ids`仅是其中已勾选的ID。`full_member_list_verified/selector_purpose_verified/selection_verified/call_connection_verified`仍false：可见行不覆盖滚动外成员，不代表完整已选列表或已提交邀请。

经典选择窗另返回`native_selected_member_ids/native_selected_member_count/native_selected_member_model_verified`。这在已核验UI线程读取客户端最终选择getter实际使用的两组有界原生向量，保留补充ID的去重合并语义，并核对成员类型、精确UID、前后字段不变及可见复选框状态一致；不是根据屏幕行数推算。模型不可核验时ID/人数为null、verified为false，区别于核验通过的空列表`[]/0`。建群`CSelectUserFrame2`布局不同，不能套用经典窗偏移，不返回该模型。

2026-10-05普通安装CLI真实空语音页返回核验通过的`[]/0`，正常取消、开页/结束状态、防重和群历史不变通过；132项CLI测试、原生编译及30个source/wheel/installed文件一致。离线C模型测试覆盖滚动外成员、补充ID合并、未知类型/重复身份、界限和读取变化，不能替代非空真实客户端验收。因此上述verified仅表示当前模型快照通过结构/身份核对，`selection_verified/selector_purpose_verified`仍false；非空及滚动外真实选择、语音页勾选和邀请提交仍待分别验收。

当正式取消控件、唯一“取消”文字和完整控件树均通过时，返回`cancel_control_verified=true`及`selector_token`。令牌绑定账号、进程创建时间、HWND/root/取消控件、本轮标题及已核验群ID；`selector-cancel`重新读取并核对令牌，在原UI线程通过正式DuiLib按钮方法取消，然后独立读取确认原窗口关闭。它只取消本地窗口，不发送邀请，无通话request-id；已关闭或变化的令牌拒绝。超时/未知结果不自动再按取消，先`inspect`核对真实窗口，必要时用computer-use正常取消。

`selector-select`先重新读取令牌和精确可见ID，绑定根窗口、唯一`WCheckbox/COptionUI`控件、完整原生元数据、旧状态及目标状态，只调用一次正常复选框`Activate`，随后独立读取新状态。已满足的状态返回`read_only=true`，不再反向切换。找不到可见ID、状态变化、类型/归属不符或结果未知不重试；先核对当前界面。此命令只改变本地勾选，绝不点击确定/完成、建群或发出邀请。

选择窗打开时，`start/answer/带目标preflight/resolve`拒绝继续；原生拨号/接听在动作前再检查，避免界面状态变化后的错误操作。无目标预检可做本地DLL准备，但不是呼叫成功。正常UI取消自行恢复niri显示电源/亮度；已有其他显示会话时拒绝。

依赖与私聊契约相同的官方5.0.11.6018、主程序/DuiLib/owl哈希、账号/进程/UI线程及控件类型核验。真实读回修正了非零偏移的非虚基类接口判断，保留完整树/父子关系/窗口归属和有界读取检查。原始窗口树和身份仅存本机私有状态，不公开群名称、成员或原始指针。

已验收：空的真实群语音选择窗完整443节点、可见13个原生ID均与群成员数据库一致；此前普通私聊发起、目标预检和接听均拒绝，未创建通话日志，正常取消及历史不变通过。建群选择窗的本人精确外部联系人由普通CLI勾选，原生状态和界面“已选择1个联系人”一致；同状态重放只读、取消勾选、正常取消及发起拒绝且无日志通过。没有点击完成、建立群或提交邀请，客户端无跟踪、显示恢复。

普通安装`group-prepare`另完成精确群开页、原生双字符串绑定、开页状态、同ID防重、改群冲突、正常取消及结束后防重；独立群历史逐条相同。129项CLI测试、原生编译及29个source/wheel/installed文件一致通过。

仍缺群语音选择窗内的勾选实测、非空及屏外完整选择实测、指定成员邀请提交、群连接判断及对端收音。不能以建群页勾选或私聊播音声称完整群通话已完成。
