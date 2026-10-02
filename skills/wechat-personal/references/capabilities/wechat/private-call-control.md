---
id: wechat-private-call-control
service: wechat
keywords: ["微信私聊呼叫", "CLI语音通话", "CLI接听", "微信来电", "CLI挂断", "接通后自动播音", "打开通话联系人"]
status: "runtime_verified"
command: ["native", "call", "inspect", "--pid", "<client_pid>", "--start-time", "<proc_start_time>"]
evidence: "2026-10-02 installed ordinary CLI private start and incoming answer each observed connection, played generated Chinese speech afterwards and normally hung up; same-ID replay did not dial or accept again. Incoming source/installed history reports 00:11/00:12. 157 tests complete, one skipped; 23 installed package files match reviewed source/wheel. WeCom calling and acceptance still use normal GUI."
transport: "normal_qt_atspi_and_niri_keyboard"
note: "个人微信正常GUI控制的CLI封装，私聊呼叫/接听/状态/播放/挂断已实测；原生VoIP API、企微呼叫控制及群成员邀请尚未完成。"
---

# 个人微信私聊呼叫控制

先按[通话授权与范围](voice-call.md)核对目标。使用本轮真实微信PID和`/proc/PID/stat`启动时间；命令都由已安装CLI执行，无需sudo，不重启原生发送服务。

```sh
native call inspect --pid CLIENT_PID --start-time PROC_START_TIME
native call open --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确联系人ID
native call start --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确联系人ID --request-id CALL_ID
native call answer --pid CLIENT_PID --start-time PROC_START_TIME --invitation-token OBSERVED_TOKEN --request-id ANSWER_ID
native call status --request-id CALL_ID
native call play --request-id CALL_ID --file /路径/通知.wav --audio-request-id AUDIO_ID --wait-seconds 30
native call hangup --request-id CALL_ID
```

`open`不呼叫；`start`验证所选账号数据库在指定进程中打开、联系人完整名称在对应个人/企业联系人命名空间唯一，并核对窗口标题后，操作正常语音菜单。GUI未暴露原生精确ID；同命名空间重名时拒绝，改用computer-use独立核对。搜索结果/标题更新需等待真实异步变化，不能直接按旧列表位置呼叫。`open`可导航群聊，`start`目前拒绝群聊；不能借此绕过群成员选择。

GUI控制依赖niri、wtype、系统Python的GI/libatspi、正常Qt辅助接口和已安装的niri-computer-use显示会话助手。沿用同一桌面焦点。CLI自行begin/wake/end并验证屏幕电源/亮度；已有其他显示会话时拒绝，先结束本人agent的会话后再调用。inspect/status不唤醒屏幕；无辅助接口或程序身份变化时停在此入口，按主skill用computer-use。

每个ID绑定账号、精确目标、PID和启动时间，重复只返回旧记录。挂断绑定原Qt对象路径/总线、niri窗口ID和进程身份，拒绝控制另一通话。未知结果保留原ID，先读status和实际窗口/历史；独立确认已结束后才用`native call resolve --request-id 原ID --ended`解除未决记录。resolve不呼叫、不重播，不把未知邀请结果改成已送达。私有状态为`~/.local/state/wechat-calls/`。

接听先用`inspect`读取唯一实际来电的`invitation_token`，核对当前任务或事先接听授权，再传给`answer`。令牌绑定本轮PID/启动时间、Qt总线/提示及接听控件路径、完整提示文字和对应niri提示窗口；用实际窗口尺寸区分同名主窗口，不使用旧截图坐标。提示结尾动画点不改变令牌，控件或窗口变化则拒绝；每个接听ID绑定令牌，同ID不接另一来电。接听提交后结果丢失记`accept_unknown`并阻止新ID，按上段确认已结束后解除。提示文字只显示名称，`caller_identity_verified`及`participants_verified`保持false；不能据名字相同推定精确联系人或自动接听未经授权的人。本轮由已核对身份的本人企微窗口发起，建立了独立测试关联。

`call play`仅当原通话窗口出现连接计时及挂断控件才播放，可等待0–60秒；等待邀请、仅有输入流或“正在连接”均不满足。使用独立音频请求ID，多个输入流时显式指定`--source-output`；格式、防重和恢复按[音频契约](call-audio.md)。`call_connection_verified_before_playback`只报告播放前的GUI状态；音频结果的对端送达字段仍为false。这轮普通CLI控制/播放验收没有重新录制接收端；此前独立双端录制的0.88/0.93证据另行保留，不能混称本轮又做了一次对端音频验收。

本能力已验证个人微信发起到本人企微对应会话，以及接听该企微正常窗口发起的来电；源码/普通安装接听的独立type50历史为00:11/00:12，均在连接后播放6秒生成通知并正常挂断，此轮没有重新录制对端。企微仍由computer-use发起/接听；企微CLI呼叫/挂断/选成员及群聊通话按[总体通话契约](voice-call.md)继续，不将私聊已交付范围扩大为完整两端通话控制。
