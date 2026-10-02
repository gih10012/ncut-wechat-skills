---
id: wechat-private-call-control
service: wechat
keywords: ["微信私聊呼叫", "CLI语音通话", "CLI挂断", "接通后自动播音", "打开通话联系人"]
status: "runtime_verified"
command: ["native", "call", "inspect", "--pid", "<client_pid>", "--start-time", "<proc_start_time>"]
evidence: "2026-10-02 installed ordinary CLI originated an owner-authorized private call, observed connection, played generated Chinese speech after connection, and normally hung up; same-ID replay did not invite again. Source CLI history independently reports 00:47, and unique aliases/external-contact namespace navigation passed. 149 tests pass, one skipped; 23 installed package files match reviewed source/wheel. WeCom acceptance still used normal GUI."
transport: "normal_qt_atspi_and_niri_keyboard"
note: "个人微信正常GUI控制的CLI封装；原生VoIP API、CLI接听、企微呼叫控制及群成员邀请尚未完成。"
---

# 个人微信私聊呼叫控制

先按[通话授权与范围](voice-call.md)核对目标。使用本轮真实微信PID和`/proc/PID/stat`启动时间；命令都由已安装CLI执行，无需sudo，不重启原生发送服务。

```sh
native call inspect --pid CLIENT_PID --start-time PROC_START_TIME
native call open --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确联系人ID
native call start --pid CLIENT_PID --start-time PROC_START_TIME --chat 精确联系人ID --request-id CALL_ID
native call status --request-id CALL_ID
native call play --request-id CALL_ID --file /路径/通知.wav --audio-request-id AUDIO_ID --wait-seconds 30
native call hangup --request-id CALL_ID
```

`open`不呼叫；`start`验证所选账号数据库在指定进程中打开、联系人完整名称在对应个人/企业联系人命名空间唯一，并核对窗口标题后，操作正常语音菜单。GUI未暴露原生精确ID；同命名空间重名时拒绝，改用computer-use独立核对。搜索结果/标题更新需等待真实异步变化，不能直接按旧列表位置呼叫。`open`可导航群聊，`start`目前拒绝群聊；不能借此绕过群成员选择。

GUI控制依赖niri、wtype、系统Python的GI/libatspi、正常Qt辅助接口和已安装的niri-computer-use显示会话助手。沿用同一桌面焦点。CLI自行begin/wake/end并验证屏幕电源/亮度；已有其他显示会话时拒绝，先结束本人agent的会话后再调用。inspect/status不唤醒屏幕；无辅助接口或程序身份变化时停在此入口，按主skill用computer-use。

每个ID绑定账号、精确目标、PID和启动时间，重复只返回旧记录。挂断绑定原Qt对象路径/总线、niri窗口ID和进程身份，拒绝控制另一通话。未知结果保留原ID，先读status和实际窗口/历史；独立确认已结束后才用`native call resolve --request-id 原ID --ended`解除未决记录。resolve不呼叫、不重播，不把未知邀请结果改成已送达。私有状态为`~/.local/state/wechat-calls/`。

`call play`仅当原通话窗口出现连接计时及挂断控件才播放，可等待0–60秒；等待邀请、仅有输入流或“正在连接”均不满足。使用独立音频请求ID，多个输入流时显式指定`--source-output`；格式、防重和恢复按[音频契约](call-audio.md)。`call_connection_verified_before_playback`只报告播放前的GUI状态；音频结果的对端送达字段仍为false。这轮普通CLI控制/播放验收没有重新录制接收端；此前独立双端录制的0.88/0.93证据另行保留，不能混称本轮又做了一次对端音频验收。

本能力已验证个人微信发起到本人企微对应会话，接收端仍由computer-use接听。CLI接听、企微呼叫/挂断/选成员及群聊通话仍按[总体通话契约](voice-call.md)继续，不将私聊已交付范围扩大为完整两端通话控制。
