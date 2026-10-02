---
id: wechat-voice-call
service: wechat
keywords: ["微信语音通话", "微信群通话", "邀请通话成员", "接通后播放音频", "企业微信语音通话", "企微群通话"]
status: "partially_verified"
evidence: "2026-10-02 normal GUI private call and independent history report 04:20; generated Chinese speech reached both opposite clients with envelope correlations 0.88/0.93. Installed personal call open/start/status/play/hangup and replay also passed against normal GUI WeCom acceptance. CLI acceptance, WeCom call control and selected-member group calls remain unimplemented."
transport: "gui_private_call_and_cli_audio"
note: "正常窗口私聊/双向音频及个人CLI呼叫/状态/播放/挂断已实测；CLI接听、企微控制和群成员选择仍在开发。"
---

# 微信与企微语音通话

个人普通CLI现有私聊`call open/start/status/play/hangup/resolve`，按[私聊控制契约](private-call-control.md)调用；它封装正常Qt界面，未使用原生VoIP API。接听、企微呼叫控制及群成员邀请仍在开发。本人已委托继续实现；用正常窗口做接口发现，按主SKILL已有授权执行。本人两端对应会话和两个小号的精确身份在私有授权登记。邀请其他成员须有当前任务或适用的事先授权；选择指定成员，不能默认呼叫整个群。没有精确群选择时先推进已授权私聊及音频。

2026-10-02实测：个人Linux微信的正常语音菜单可以发出邀请；本次对应企微会话没有接通，双方历史为“对方无应答/未接听”，时长零。企微Wine客户端选择语音后主窗口消息队列不响应，读取线程控制状态显示UI等待DLL加载锁、持锁线程等待同一组件临界区，疑似锁循环。此次挂起已恢复登录态、历史和原生构造预检，旧发送记录均已成功，无待完成发送。不能据此推定所有企微客户端永久不支持通话，也不能继续在已挂起窗口盲目重试。

后续在精确客户端UI线程预先解析该组件19个系统DLL后，正常企微呼叫成功且窗口保持响应；预加载仍是私有开发试验，没有普通CLI入口，不宣称重启后通话已稳定。企微电话图标可直接发起语音，电脑微信来电提示可接听/拒绝。正常接听、计时4分钟后挂断，独立type50历史显示“通话时长04:20”。原始XML的duration节点仍为0，不能仅用此节点判断未接通，应结合显示文字、实际计时和音频证据。

同次通话双向播放生成中文通知，隔离发送方输入和接收方输出，仅录制生成音频；语音包络与原文件相关系数0.88/0.93。默认麦克风/扬声器及已有虚拟设备保持原样，临时模块/录制流已清理。普通安装audio命令另通过双频路由、恢复和同ID不重播。之后个人普通CLI又完成真实发起、连接状态、等待接通再播生成音频、挂断及防重；接收端由企微正常窗口接听，此轮没有重新录制对端。两端已安装`audio streams/play/status/recover`，按[音频契约](call-audio.md)使用；接听、企微控制及群成员选择尚待完成。

继续实现时分别核对呼叫目标、实际选中的群成员、邀请提交、接通状态、指定音频输入、对端收音及正常挂断。音频仅在确认接通后播放；输入流绑定客户端实际进程身份，使用独立临时虚拟输入，完成后恢复原流并清理。生成或转换音频不证明它进入通话。用户授权的私信通知可在通话确实不可用时按现有发送契约执行，保存原请求ID；不要每次轮询失败都重复通知。

原始身份、通话历史、线程状态和本机音频试验存于私有状态。代码和契约按实际通过的范围更新，不将媒体发送、语音消息或公费电话冒充本项通话能力。
