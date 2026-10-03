---
id: wechat-call-audio
service: wechat
keywords: ["通话播放音频", "语音通知", "指定音频", "企微通话音频", "通话麦克风路由"]
status: "runtime_verified"
command: ["native", "audio", "streams", "--pid", "<client_pid>", "--start-time", "<proc_start_time>"]
evidence: "2026-10-02 both installed ordinary CLIs passed isolated-stream PCM playback, restoration and no-playback replay; a normal GUI-connected call independently received source CLI Chinese speech in both directions (0.88/0.93). 2026-10-03 installed call-play commands independently reached both opposite clients (0.87/0.95, histories 00:22) with exact restoration. Private call controls have separate contracts; group calls remain unverified."
transport: "existing_capture_stream_via_local_pulse"
note: "确认接通和参与人授权后播放；audio本身不发起/接听通话，不从输入流或本地播放推断对端送达。"
---

# 已接通通话的音频

先按[通话契约](voice-call.md)核对参与人授权与连接状态。个人按[个人私聊CLI](private-call-control.md)、企微按[企微私聊CLI](../wecom/private-call-control.md)发起/接听/挂断；两端`call play`先检查原通话连接再播放。只有输入流、等待接听或“正在建立连接”不足，需实际连接计时或对端确认。audio基础命令不把任意音频流当作已接通通话。

个人端用`python3 "$WX" native audio ...`，企微端用`python3 "$WX" wecom audio ...`。桥接普通安装CLI，无需sudo；PID和`/proc/PID/stat`启动时间来自本轮真实客户端。

```sh
audio streams --pid CLIENT_PID --start-time PROC_START_TIME
audio play --pid CLIENT_PID --start-time PROC_START_TIME --source-output STREAM_ID --file /路径/notification.wav --request-id 本次唯一ID
audio status --request-id 原ID
audio recover --request-id 原ID
```

输入限PCM WAV、单/双声道、5分钟/32 MiB；其他格式先转换。生成音频不证明通知送达。命令需本机PulseAudio兼容服务、pactl与paplay，本机PipeWire已实测。企微skill桥接沿用播放进程自身有界生命周期，避免普通读取180秒超时强制终止。

需要文字通知时先用[语音生成命令](speech-synthesis.md)得到归一化PCM WAV，再用对应原通话`call play`；无需复用旧私有试验脚本。主号手机已确认收到普通企微CLI播出的旧eSpeak通知，但反馈声音不自然、过响；新的晓晓语音已生成并限幅，WAV样例由本人确认正常；第二次电话未接听，本人要求不再拨号。不把文件试听或本地无削波推定为新的电话送达。

输入绑定精确PID、启动时间、流索引/客户端/序号，临时转入独立虚拟输入；完成后恢复原设备并移除自建模块，不改默认输入/输出。流断开、静音、身份变化或手动改路由时停止，不碰替换流。同ID同音频/目标只返回旧结果；改内容/目标拒绝，未知状态不换ID重播。强制退出后先查原ID，再recover清理，清理不播放。记录在私有`~/.local/state/wechat-audio/`，不需常驻接收服务。

`playback_finished`只表示本地播放器完成，音频原语的`remote_delivery_verified`和`call_connection_verified`保持false；`call play`另用`call_connection_verified_before_playback`表示真实UI检查，agent按独立证据说明范围。2026-10-03两端普通call-play命令的接收输出录制匹配0.87/0.95，两边历史00:22，正常挂断与原路由/默认设备/临时模块清理通过，证据私存。不能把私聊互测扩大为群连接或其他参与人已验收。
