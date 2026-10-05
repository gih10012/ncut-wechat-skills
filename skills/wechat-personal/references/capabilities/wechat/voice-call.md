---
id: wechat-voice-call
service: wechat
keywords: ["微信语音通话", "微信群通话", "邀请通话成员", "接通后播放音频", "企业微信语音通话", "企微群通话"]
status: "partially_verified"
evidence: "2026-10-02 normal GUI private call and both directions of source CLI speech verified, histories 04:20 and correlations 0.88/0.93. 2026-10-03 both installed CLIs private start/answer/connected play/hangup and replay guards verified; independently recorded installed call-play audio correlations 0.87/0.95, both histories 00:22. Personal installed group selection/cancellation and selected two-member invitation/hangup/replay passed; independent history has one start/end, unverified group playback refused. WeCom installed CLI complete empty group picker inspection and normal cancellation verified without selection/invitation or history changes. 2026-10-05 installed WeCom group-prepare opened the exact group voice picker with matching native configuration strings, status/replay/conflict/cancel/ended guards and unchanged history. Exact visible selection was tested in a creation picker. Remote group join/audio and WeCom voice-picker selection/invitation remain unverified."
transport: "normal_qt_duilib_private_ui_and_cli_audio"
note: "两端普通CLI私聊发起/接听/连接后播音/挂断及双向对端音频已实测；个人指定群成员选择/取消、邀请/挂断/防重已实测，企微精确群选择窗开页/状态/防重、读取/取消及建群页精确联系人勾选已实测，群连接/播音与企微指定成员邀请仍待完成。"
---

# 微信与企微语音通话

两端普通CLI私聊控制按[个人私聊契约](private-call-control.md)与[企微私聊契约](../wecom/private-call-control.md)直接调用，封装正常Qt/DuiLib界面。来电提示不暴露精确联系人ID，令牌只绑定本轮实际邀请，接听授权另核对。个人群选择/取消按[群成员选择契约](group-call-selection.md)调用，邀请/正常挂断/防重已实测；企微精确群选择窗开页/状态/防重、读取/取消与可见联系人勾选按[企微成员选择契约](../wecom/group-call-selection.md)调用，勾选实测在建群页。群连接/自动播音、企微群语音页指定成员邀请仍未完成。本人已委托继续开发，按主SKILL已有授权执行；本人两端对应会话和两个小号的精确身份在私有授权登记。邀请其他成员须有当前任务或事先授权，不能默认呼叫整个群。当前不要求切小号，以免挤掉电脑主号。

2026-10-02实测：个人Linux微信的正常语音菜单可以发出邀请；本次对应企微会话没有接通，双方历史为“对方无应答/未接听”，时长零。企微Wine客户端选择语音后主窗口消息队列不响应，读取线程控制状态显示UI等待DLL加载锁、持锁线程等待同一组件临界区，疑似锁循环。此次挂起已恢复登录态、历史和原生构造预检，旧发送记录均已成功，无待完成发送。不能据此推定所有企微客户端永久不支持通话，也不能继续在已挂起窗口盲目重试。

后续在精确客户端UI线程预先解析该组件19个系统DLL后，正常企微呼叫成功且窗口保持响应；当时为私有试验，2026-10-03已加入普通`wecom call preflight/start/answer`。企微电话图标可直接发起语音，电脑微信来电提示可接听/拒绝。最初正常接听、计时4分钟后挂断，独立type50历史显示“通话时长04:20”。原始XML的duration节点仍为0，不能仅用此节点判断未接通，应结合显示文字、实际计时和音频证据。

同次通话双向播放生成中文通知，隔离发送方输入和接收方输出，仅录制生成音频；语音包络与原文件相关系数0.88/0.93。默认麦克风/扬声器及已有虚拟设备保持原样，临时模块/录制流已清理。普通安装audio命令另通过双频路由、恢复和同ID不重播。之后个人普通CLI完成真实发起及接听、连接状态、等待接通再播生成音频、挂断及防重；当时企微用正常窗口操作，独立历史00:11/00:12，这两轮没有重新录制对端。两端已安装`audio streams/play/status/recover`，按[音频契约](call-audio.md)使用。

继续实现时分别核对呼叫目标、实际选中的群成员、邀请提交、接通状态、指定音频输入、对端收音及正常挂断。音频仅在确认接通后播放；输入流绑定客户端实际进程身份，使用独立临时虚拟输入，完成后恢复原流并清理。生成或转换音频不证明它进入通话。用户授权的私信通知可在通话确实不可用时按现有发送契约执行，保存原请求ID；不要每次轮询失败都重复通知。

原始身份、通话历史、线程状态和本机音频试验存于私有状态。代码和契约按实际通过的范围更新，不将媒体发送、语音消息或公费电话冒充本项通话能力。

2026-10-03手机追加：本人无需切小号，使用主号手机接听普通企微CLI呼叫，连接后播放6秒生成通知、正常结束、路由恢复和临时模块清理通过；本人经ClawBot确认听到，但反馈旧eSpeak声音不自然、过响。随后采用[自然语音生成命令](speech-synthesis.md)，神经语音文件已实际生成且无数字削波；第二次呼叫显示对方未接听、未进入播放，正常结束并清理。新音色随后作为WAV样例经ClawBot发送，本人确认声音正常并要求不再拨号；记样例听感通过，新神经语音电话播出和群收音仍无实际证据。

2026-10-03本人停止切小号进行手机验收，并明确保持正常启动微信、不再调整自动登录；不能因“就当成功了”改写未实测项。普通个人CLI从另一个私聊开始的群双成员选择/取消已通过，无新邀请。企微正式控件getter/Activate经类型与归属核对后沉淀为已安装CLI；私聊发起、接听、计时连接、播音、正常挂断和防重均通过，错view预检拒绝，钩子移除且进程保持无跟踪。两端普通call-play输出独立录制匹配0.87/0.95，两边历史00:22；音频全部清理。企微启动后先做普通预加载，客户端正常重启后的入站与出站控制亦通过。群连接/对端收音、企微群控制和长期稳定性继续单独验收。

同日群控制追加：原20秒UI超时留下成员选择窗，没有新群通话历史；正常取消、确认无活动通话后resolve旧ID，再修复按成员数增加的有界期限。普通安装CLI从另一私聊的选择/取消预检通过；随后仅邀两个授权成员、正常挂断、同ID不重拨通过，独立同步历史为一条发起/一条结束、服务器ID非零。群play拒绝且未创建音频日志。没有小号登录或主号切换，群对端加入/收音仍未验收。
