---
id: wecom-private-call-control
service: wecom
keywords: ["企微CLI接听", "企业微信私聊呼叫", "企微CLI挂断", "企微来电", "企微接通后播音", "企微通话预检"]
status: "runtime_verified"
command: ["wecom", "call", "inspect", "--account", "me"]
evidence: "2026-10-03 installed ordinary CLI start and skill-bridged incoming answer, connected PCM playback, normal hangup and replay guards verified against the owner's desktop WeChat. Installed call playback independently reached both opposite clients, envelope correlations 0.87/0.95 and both histories 00:22. One normal client restart retained account/history and verified new-process incoming/outgoing controls after ordinary 19-module warmup; entire Wine runtime not restarted. 109 CLI tests and native compilation passed; 29 source/wheel/installed files identical. Group calls and long-term stability are separate."
transport: "version_bound_normal_duilib_ui_thread"
note: "企微普通CLI私聊发起/接听/连接后播音/挂断已实测；精确来电令牌不证明原生联系人ID，群成员选择和群通话另待实现。"
---

# 企微私聊通话控制

先按[通话授权](../wechat/voice-call.md)核对参与人。以下参数经本skill的`wecom`入口传给已安装`wecom-linux`，不需sudo、源码PYTHONPATH或私有试验脚本。

```sh
wecom call inspect --account me
wecom call preflight --account me --chat 精确私聊ID
wecom call start --account me --chat 精确私聊ID --request-id CALL_ID
wecom call answer --account me --invitation-token 当前令牌 --request-id ANSWER_ID
wecom call status --request-id CALL_ID
wecom call play --request-id CALL_ID --file /路径/通知.wav --audio-request-id AUDIO_ID --wait-seconds 30
wecom call hangup --request-id CALL_ID
```

发起目标为`S:ID_ID`私聊ID，读取接受任意会话的规则保持，通话目标没有授权白名单。`start`须有对应精确会话的正常附着view；返回`ONE_CACHED_ATTACHED_CHAT_VIEW_REQUIRED_OPEN_TARGET_IN_CLIENT`时，沿用已授权范围用computer-use打开该精确会话、核对名称/后缀，再做`preflight --chat`。不能改传同名的其他聊天。普通CLI可读取/取消成员选择窗，并按精确可见联系人ID勾选/取消勾选，按[企微成员选择契约](group-call-selection.md)执行；勾选实测在建群页，群邀请尚未实现。普通及建群选择窗都在`inspect.member_selectors`单独返回，不视为来电或连接；打开时拨号、接听、目标预检及resolve拒绝，先核对本轮令牌正常取消。

依赖本人已登录的官方5.0.11.6018独立Wine客户端，主程序与DuiLib/owl哈希、账号、进程创建时间、UI线程、控件类型和窗口均核对；版本变化拒绝，不复用旧偏移。首次本机编译需32位MinGW。原生助手只调用客户端正常UI handler或正式导出的DuiLib控件方法；小模块保留到客户端退出以避免回调卸载竞态。不是猜测原生VoIP引擎ABI，也不通过消息发送接口假造通话。

`inspect/status`只读实际控件，不呼叫或接听。`preflight`还在UI线程用版本核验的正常CRT解析器预加载19个系统DLL，规避已观察到的语音组件加载锁循环；这是本地准备，`read_only=false`但`invitation_performed=false`。客户端启动后、入站通话测试前先做无目标`preflight`；`start/answer`自身也执行准备。冷启动/长期稳定性按真实验收记录区分，不将预检视为连接成功。正常UI动作自行begin/wake/end并恢复niri电源/亮度，有其他显示会话时拒绝；CLI不足时沿用主skill的computer-use规则。

接听先`inspect`取本轮唯一来电的令牌，核对授权后调用`answer`。令牌绑定账号、进程创建时间、HWND/root/接听控件和完整来电caption；名字含富文本后缀，不能据同名推断原生精确ID，`caller_identity_verified=false`。本人两端已核对的对应会话互测由精确出站请求关联到来电；其他来电另核对上下文与授权。

ID在发出邀请/接听/挂断前私存到`~/.local/state/wecom-linux-cli/calls/`。同ID不再次操作，改目标/令牌冲突拒绝；结果未知保留原ID并阻止新请求，先读status和实际窗口/历史，独立确认结束后用`wecom call resolve --request-id 原ID --ended`解除本地未决记录。resolve不呼叫、不重播、不把未知邀请改为已送达。挂断绑定原通话窗口和控件，不能挂断另一轮通话。

`call play`等原私聊窗口的真实计时、对端标签和正式挂断控件，最多等待120秒；“已接通”短提示消失不影响判断。“正在呼叫”、不完整树、重复状态标签、群布局、仅有输入流均不满足。自动选择原客户端唯一活动且未静音的输入流，独立音频ID与PCM/5分钟/32MiB/恢复规则按[音频契约](../wechat/call-audio.md)。skill沿用CLI自身等待/播放/恢复生命周期，不使用普通读取180秒强制超时。`call_connection_verified_before_playback`只表示播放前GUI连接检查；音频原语的对端字段仍为false，送达须独立验收。同音频ID结束后重放返回原记录，播放前绑定原进程/流/内容，冲突拒绝。

2026-10-03实际范围：普通CLI企微发起、个人普通CLI接听，双方连接后分别用各自`call play`注入6秒生成中文通知，仅录制隔离的接收输出，匹配0.87/0.95，双端独立历史均为00:22。企微CLI正式挂断，个人端确认原窗口结束；恢复原流、默认输入/输出、清除全部临时模块通过。企微同ID发起/播音不重做；个人端结束后的`call play`拒绝已结束handle、音频status保留完成结果，没有新播放。另由个人CLI发起，企微通过普通skill桥接按本轮令牌接听、等待接通播音、正常挂断，接听/音频防重通过。没有切小号或重启个人微信主号。

同日正常托盘退出并启动企微，新进程普通预加载19个系统DLL约5.24秒到就绪，账号/历史保留；新进程入站接听、连接后播音、正常挂断与防重通过。出站会话view未打开时预检明确拒绝，computer-use打开已核对的对应会话后，普通CLI新进程发起、接通后播音、正常挂断及防重亦通过。此次没有重启整个Wine运行时，也不证明长期无人值守通话稳定。

随后本人主号手机真实接听企微普通CLI呼叫并确认收到6秒通知，无需桌面接听或切小号；正常结束、音频恢复及临时模块清理通过。本人反馈旧eSpeak语音不自然、过响，改用[归一化神经语音生成](../wechat/speech-synthesis.md)。第二次电话显示对方未接听，未播音且已结束/清理，新语音WAV样例另经ClawBot发送后本人确认正常并要求不再打电话。样例听感已确认，新的电话播音没有发生，不继续拨号验收。
