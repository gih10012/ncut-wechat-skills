---
id: send-personal-media
service: wechat
keywords: ["个人微信媒体", "个人身份媒体发送"]
exclude_keywords: ["机器人身份", "ClawBot机器人", "企微", "企业微信"]
status: "partially_verified"
transport: "installed_linux_cli_distinct_native_media_requests"
workflow: references/workflows/native-cli.md
note: "普通CLI个人身份PNG/JPEG、中文文件名TXT/ZIP、公众号文章/小程序转发、自定义XML及动画GIF原生表情分别已实测。GIF手机确认在文件传输助手；ClawBot手机端不支持自定义表情。其他格式和目标各自记录，不扩大验收范围。"
---
# 个人身份媒体

PNG/JPEG 已通过普通 CLI、ClawBot 独立下载字节对比和 Linux UI 验收，直接按[图片契约](send-personal-image.md)执行。中文文件名TXT/ZIP见[文件契约](send-personal-file.md)；公众号文章、小程序33及自定义XML见[转发契约](forward-card.md)，本人手机显示与点击已确认；原生动画GIF见[表情契约](send-personal-sticker.md)，文件传输助手手机正常。ClawBot手机端不支持自定义表情，机器人通道的富消息状态另行记录。filehelper/ClawBot 测试与媒体发送已有长期授权，其他对象按主 SKILL 当前或适用的事先直接/间接授权执行。

2026-09-30 的正常 UI 图片观察曾获得真实请求类及字段值，旧静态候选和过滤不匹配；两次附加均安全清理。之后定位到实际图片工厂、公共路径字段及引用生命周期，2026-10-01 完成不发送的排队构造预检、私有真实发送，再接入并部署普通 CLI。历史观察缺项不能再作为图片主动发送的当前结论；更早的同步协程入口仍保持禁用。

尚未验收的格式继续分别核对客户端工厂、真实负载字段、上传与所有权，先做对应不发送的构造预检，再通过唯一 ID 的普通 CLI 发送。分别检查本地显示、类型和接收端内容；不要只修改图片/文字类型伪造新格式。当前专项目标由本人明确放宽探索时间，继续到实测可用；其他日常缺项仍按主 SKILL 默认限时。私有证据和接续在本机 state，正常业务入口不依赖旧 PID、私有一次性脚本或对话历史。
