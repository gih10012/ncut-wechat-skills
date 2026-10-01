---
id: forward-card
service: wechat
keywords: ["微信转发", "个人微信转发", "微信转发公众号", "转发公众号文章", "微信转发小程序", "转发小程序卡片", "微信自定义XML", "微信发XML", "微信卡片发送"]
exclude_keywords: ["机器人身份", "ClawBot机器人", "企微", "企业微信"]
status: "runtime_verified"
transport: "installed_linux_cli_queued_app_message"
command: ["native", "forward"]
workflow: references/workflows/native-cli.md
note: "2026-10-01普通CLI向文件传输助手真实转发公众号文章和type33小程序，修改标题/描述的自定义XML亦发送；独立XML字段、服务器ID与Linux完整卡片显示通过，同ID重放未再次提交。手机投递与点击、type36及其他收件人待独立确认。"
---
# 个人微信转发与自定义 XML

先用 `native conversations` 定位源会话，再用 `native messages --chat '精确源chat_id' --limit 20` 选择原消息的 `local_id` 与 `database`。读取直接执行，目的会话的写入授权按主 SKILL 判断；filehelper/ClawBot 长期授权，其他会话依据当前或适用的事先授权。

```bash
python3 "$WX" native forward --chat '精确源chat_id' --local-id 123 --database message/message_0.db --recipient '精确目标chat_id' --request-id '唯一ID'
python3 "$WX" native message-xml --chat '精确源chat_id' --local-id 123 --database message/message_0.db
python3 "$WX" native send --recipient '精确目标chat_id' --xml '/路径/card.xml' --request-id '另一唯一ID'
python3 "$WX" native send-status --request-id '原ID'
```

独立命令分别为 `wechat-linux forward`、`wechat-linux message-xml`、`wechat-linux send-xml --file …`。转发当前覆盖 appmsg 公众号文章（5）和小程序（33/36），实际客户端验收为文章5和小程序33；类型36已有解析路径，尚无真实验收。源消息必须在本机同步历史内。跨分片 ID 不唯一时明确指定 `database`，不自动选第一条。读取原始 XML 会返回本人消息正文，保存到本机私有文件，不上传或写入公共仓库。

自定义 XML 是桌面用户可读的 UTF-8 `msg/appmsg` 文件，1..65536字节，无NUL/DTD/实体声明。必须有支持的 `type` 与非空标题；小程序还需真实 `weappinfo/appid`、`username`、页面路径及可用资源元数据。客户端原生解析并构造分享消息，会规范化 XML；不保证未经客户端支持的任意标签原样传输。不可把纯文字 URL 当作卡片验收，也不可捏造 appid、分享票据或媒体参数。普通表情包、合并聊天记录与其他 XML 类型不由本契约保证。

预检和提交绑定同一目标、XML字节、源消息身份及客户端进程。相同请求 ID 只读返回旧结果；换源、换目标、改XML或改发送动作会冲突。直接发送与转发即使 XML 相同也有不同身份。源被删除/文件已移走时查 send-status，不换 ID 重发。

2026-10-01 普通用户在仓库外运行已安装 CLI：文章转发、小程序33转发、自定义文章标题/中文描述/换行/✅各生成一条本地消息并取得服务器ID；Linux UI均显示完整卡片。独立原始XML读回验证文章标题/URL/来源、小程序appid/username/pagepath及实际预览图引用、自定义标题/描述。三次相同ID重放未改变原生产物与私有快照，转发ID改为直接XML动作拒绝。

手机投递、手机点击打开、ClawBot卡片通道及其他收件人仍待独立确认。`ok`仅证明客户端提交完成；默认 `local_history_card_matches` 是标题/类型/URL匹配候选数，不自动证明完整XML、UI或投递。独立确认另存私有 acceptance，不改原始调用结果。
