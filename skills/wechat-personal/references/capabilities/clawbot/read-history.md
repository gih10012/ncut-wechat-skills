---
id: clawbot-history
service: clawbot
keywords: ["ClawBot历史", "ClawBot 历史", "ClawBot聊天记录", "ClawBot 聊天记录", "微信ClawBot", "ClawBot读回", "ClawBot 读回", "机器人历史"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-09-19"
transport: "local_sqlcipher_readonly"
command: ["native", "messages", "--account", "me", "--chat", "微信ClawBot", "--limit", "20"]
workflow: references/workflows/clawbot.md
note: "Linux微信4.1.13升级后已真实读取ClawBot双向会话和新发送回执。复用已有本机密钥，无需重新登录；仅当前客户端已同步历史，不消费机器人增量游标。"
---
# ClawBot 本地历史与收件端读回

2026-09-19在本人已升级并登录的Linux微信`wechat-appimage 4.1.13-3`上验证：原数据库密钥仍可用，`native conversations --query ClawBot`定位到名称为`微信ClawBot`、ID以`@weclaw`结尾的会话。用唯一名称或返回的精确chat_id读取，不将iLink的`@im.bot`/`@im.wechat` ID拼成此ID。

读取命令与[本机消息](../wechat/read-messages.md)共用。实际读到了本人发给机器人的文字、升级前机器人发给本人的文字，以及升级后新发送的OneBot回执。当前能力覆盖已同步的本地历史，不依赖旧私有试验脚本，不要求再次捕获密钥。

发送后的验证：在该会话里寻找发送时间之后新增、正文完全一致且`sender_id == chat_id`的机器人消息；排除本人发送的同文消息、旧回执及`truncated=true`。可用`--max-chars 3000`核对较长文字；超出读取上限不能宣称全文相符。接收端消息ID与iLink发送响应ID曾观察到不同，不能要求两者相等。

本地未同步或找不到消息时只报告“API已受理、收件端未确认”，不盲重发。本地读回与本人确认都是验收/排查手段，不是日常收发的必要步骤；电脑微信离线时按iLink响应报告结果，不阻断发送或重复请求本人确认。读回成功只证明机器人→本人链路，不证明已能以个人微信身份向好友或ClawBot发送。
