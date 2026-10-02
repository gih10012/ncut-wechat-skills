---
id: wechat-call-audio
service: wechat
keywords: ["通话播放音频", "语音通知", "指定音频", "企微通话音频", "通话麦克风路由"]
status: "runtime_verified"
command: ["native", "audio", "streams", "--pid", "<client_pid>", "--start-time", "<proc_start_time>"]
evidence: "2026-10-02 both installed ordinary CLIs passed actual isolated-stream PCM playback, restoration and no-playback replay. A normal GUI-connected WeCom/WeChat private call independently received source CLI Chinese speech in both directions (envelope correlations 0.88/0.93). Installed code matches reviewed source and wheels. Call control/group calls are separate."
transport: "existing_capture_stream_via_local_pulse"
note: "确认接通和参与人授权后播放；audio本身不发起/接听通话，不从输入流或本地播放推断对端送达。"
---

# 已接通通话的音频

先按[通话契约](voice-call.md)核对参与人授权与连接状态。个人微信可按[私聊CLI控制](private-call-control.md)发起/挂断，`call play`会先检查该通话连接再播放；接听、企微呼叫控制仍用computer-use。只有输入流、等待接听或“正在建立连接”不足，需连接计时或对端确认。audio基础命令不把任意音频流当作已接通通话。

个人端用`python3 "$WX" native audio ...`，企微端用`python3 "$WX" wecom audio ...`。桥接普通安装CLI，无需sudo；PID和`/proc/PID/stat`启动时间来自本轮真实客户端。

```sh
audio streams --pid CLIENT_PID --start-time PROC_START_TIME
audio play --pid CLIENT_PID --start-time PROC_START_TIME --source-output STREAM_ID --file /路径/notification.wav --request-id 本次唯一ID
audio status --request-id 原ID
audio recover --request-id 原ID
```

输入限PCM WAV、单/双声道、5分钟/32 MiB；其他格式先转换。生成音频不证明通知送达。命令需本机PulseAudio兼容服务、pactl与paplay，本机PipeWire已实测。企微skill桥接沿用播放进程自身有界生命周期，避免普通读取180秒超时强制终止。

输入绑定精确PID、启动时间、流索引/客户端/序号，临时转入独立虚拟输入；完成后恢复原设备并移除自建模块，不改默认输入/输出。流断开、静音、身份变化或手动改路由时停止，不碰替换流。同ID同音频/目标只返回旧结果；改内容/目标拒绝，未知状态不换ID重播。强制退出后先查原ID，再recover清理，清理不播放。记录在私有`~/.local/state/wechat-audio/`，不需常驻接收服务。

`playback_finished`只表示本地播放器完成，`remote_delivery_verified`和`call_connection_verified`保持false，agent按独立证据说明范围。此次双向对端音频和正常挂断、本机普通安装命令路由及source/wheel/安装一致性分别记录于私有voice-call状态。不能合并成完整通话CLI已实现。
