---
id: clawbot-send
service: clawbot
keywords: ["ClawBot发送", "ClawBot发消息", "机器人给我发", "机器人发送", "ClawBot给我", "clawbot-send"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-09-18"
transport: "ilink_https_third_party_sdk"
command: ["bot", "send", "--account", "me", "--text", "<消息文字>", "--request-id", "<本次操作唯一ID>"]
workflow: references/workflows/clawbot.md
note: "已真实发送文字且本人确认收到；以ClawBot身份发给已绑定本人，读写已有长期授权。不是以个人微信身份给好友发消息。同一request-id不重复提交；接口成功与实际送达分开报告。"
---
# ClawBot 向本人发文字

来源：[腾讯发送实现](https://github.com/Tencent/openclaw-weixin/blob/main/src/messaging/send.ts)，底层使用已安装的 `wechatbot-sdk==0.3.0` 的 `ILinkApi.send_message`，每次一条，无自动回复或常驻服务。

`POST /ilink/bot/sendmessage`，origin和bot_token复用私存绑定；`msg.to_user_id`固定取该绑定的`ilink_user_id`，不接受任意收件人。`message_type=2`、`message_state=2`，单个type=1的text_item。每个新操作生成client_id；有本人入站context_token时私存复用，无上下文也可尝试（本次已实测送达）。不把绑定ID当作普通微信好友ID。

ClawBot读写已获本人长期授权，无需逐次确认。`--request-id`为1–80位字母、数字、下划线或短横线；同一操作始终复用同一ID，返回上次结果而不再次发送。正文可用`--text`或0600文件`--text-file`，最多16000 UTF-8字节。MCP同等入口为`clawbot_send(text, request_id, account="me")`。

发送前在账号`sends/`私存请求指纹与client_id，响应后保存结果，不存正文或上下文凭证。网络超时、错误响应或中断不能确定是否已送达时，不换新ID盲重试。`BOT_SEND_ACCEPTED`表示API受理，`server_message_id`存在时保留；返回的`delivery_verified=false`表示命令本身没有接收端读回能力。需要实际收件端证据才报告送达。

2026-09-18从已安装skill、以`/tmp`为工作目录真实调用，服务端返回消息ID；本人随后确认手机ClawBot收到对应文字。当天旧Linux版本尚未查询到ClawBot。9月19日升级至4.1.13后已能从本地历史读回该消息，以及新发出的OneBot回执；需要验收/排查时可选按[本地历史与读回](read-history.md)确认收件，电脑微信离线不阻断iLink收发；不能把CLI的`delivery_verified=false`误解为本地永远无法验证。本次不证明普通好友/群聊OneBot发送，也不证明代本人通过原生微信发送。
