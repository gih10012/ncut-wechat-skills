---
id: clawbot-send-media
service: clawbot
keywords: ["ClawBot文件", "ClawBot图片", "机器人文件", "机器人图片", "ClawBot发文件", "ClawBot发图片"]
exclude_keywords: ["企微", "企业微信", "下载", "读取", "表情包", "卡片"]
status: "runtime_verified"
runtime_verified_at: "2026-09-19"
transport: "ilink_https_third_party_sdk"
command: ["bot", "send", "--account", "me", "--file", "<本地文件路径>", "--request-id", "<本次操作唯一ID>"]
workflow: references/workflows/clawbot.md
note: "文件与PNG已真实发送，API返回消息ID，本人确认文件能打开、图片正常显示。已验证发送直接调用，不重做探索；仅ClawBot向绑定本人，不是个人微信身份发送。视频、原生表情包及分享卡片未验收。"
---
# ClawBot 向本人发送文件与图片

文件使用上方命令，图片改用`--image`；MCP为`clawbot_send_media(path, request_id, kind="file"或"image", account="me")`。已有长期授权，无需再问。命中后直接执行，正常结果不重新探索下载通道或要求桌面微信在线。

协议、资源上限、凭证位置与错误判断见[媒体契约](media.md)。同一业务操作始终复用同一request_id，不因超时或下载失败重发；机器人发送使用独立iLink，与原生身份授权分开。

2026-09-19实测TXT与PNG发送受理，本地历史出现对应消息；本人随后确认文件能打开、图片正常显示。此证据证明这两项发送链路，不证明所有文件格式、视频、入站下载、原生表情包或公众号卡片。未来普通发送仍不要求逐条收件确认或本地读回。
