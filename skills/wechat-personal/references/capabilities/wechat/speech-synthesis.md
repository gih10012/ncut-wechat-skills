---
id: wechat-speech-synthesis
service: wechat
keywords: ["文字转语音", "免费TTS", "自然中文语音", "生成通知音频", "晓晓", "企微语音生成"]
status: "runtime_verified"
command: ["speech", "synthesize", "--text", "<通知文字>", "--output", "<私有绝对路径.wav>"]
evidence: "2026-10-03 live Edge voice catalog and Xiaoxiao synthesis verified. Installed skill command executed from /tmp produced 8.112-second mono16k PCM, peak -6.652dBFS, zero clipped samples; six guards passed. Phone receipt of earlier eSpeak audio was confirmed, but owner rejected its quality. Owner confirmed the neural WAV sample sounds normal through ClawBot and requested no further calls. The neural phone trial was unanswered; no neural phone playback is claimed."
transport: "edge_read_aloud_online_and_local_ffmpeg"
note: "无API Key生成自然中文PCM WAV，两端call play可使用；文件生成、样例听感与通话送达分别验收。"
---

# 生成通话通知语音

```sh
python3 "$WX" speech synthesize --text '需要你处理的内容已发送到微信私信，请有空查看。' --output "$HOME/.local/state/wechat-personal/notification.wav"
```

长文字或私有正文使用`--text-file /私有路径/text.txt`，UTF-8，最多1200字符。默认`zh-CN-XiaoxiaoNeural`中文女声、语速-5%；可用`--voice zh-CN-YunxiNeural`或`--rate -10`调整。依赖`uvx`和`ffmpeg`，首次运行由uvx缓存固定`edge-tts==7.2.8`及依赖，无sudo或新后台服务。本机已真实安装并验收；新机器缺依赖返回`SPEECH_REQUIRES_UVX_AND_FFMPEG`。

[edge-tts上游](https://github.com/rany2/edge-tts)使用微软Edge在线朗读接口，不需要API Key、Windows或运行Edge。实际文字会发到在线朗读服务；它不是带服务承诺的Azure开发者API，不登记为永久免费或长期稳定。此次没有创建付费云资源。可用声音按上游`uvx --from edge-tts==7.2.8 edge-tts --list-voices`查询；换声后仍需实测。

文件生成后归一至约-22 LUFS、目标真峰值-6 dBFS，输出16kHz/16bit/单声道PCM WAV，最多5分钟。返回时校验格式、完整帧、时长、峰值、SHA256及无数字削波；文件0600，文本/MP3中间件在私有临时目录并清理。已有文件或软链接拒绝覆盖，云端/转换失败不发布半成品，不输出含原文的云端错误。

先核对[通话授权与连接](voice-call.md)，再将输出路径传给个人`native call play`或企微`wecom call play`；通话ID和音频ID沿用原调用规则。生成文件不会呼叫、发送、播放或证明对端听到。需要分享样例时用已授权的文件发送命令。本人主号手机已确认收到之前的生成音频，但认为旧eSpeak声音不自然、过响；新的神经语音文件峰值/完整性通过，经ClawBot作为WAV文件发送后本人确认样例正常并要求停止电话验收。样例听感已确认；第二次电话未接听，不能标记新的电话播音已发生。尊重本人停止进一步电话验收的指示，保留主号登录。
