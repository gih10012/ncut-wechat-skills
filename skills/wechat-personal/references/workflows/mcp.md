# 按需 MCP 读取与ClawBot发送

`scripts/mcp_server.py` 使用 Python MCP SDK 的 stdio transport，仅在客户端调用时运行，不开放监听端口。工具调用相同的CLI，各来源的实际验收状态独立记录：

| 工具 | 来源 |
| --- | --- |
| `wechat_conversations` | 本人 Linux 微信本地会话与未读 |
| `wechat_messages` | 精确会话的已同步消息，最多50条 |
| `clawbot_send` | 以ClawBot身份向绑定本人发文字；长期授权，request_id防重复，实际送达已验证 |
| `clawbot_updates` | 第三方SDK读取ClawBot单批新消息，最长40秒 |
| `clawbot_send_media` | 本地文件/图片/视频发给绑定本人；文件/图片已发送且本人确认打开/显示正常；视频未实测 |
| `clawbot_download` | 按updates的入站attachment_id下载解密到私有目录；文件、图片、语音CLI及图片MCP下载已实测 |
| `wecom_notifications` | 本机Android企微通知归档；MCP调用已验证。本人手机为原生鸿蒙，通知接入已暂缓，真实投递未验证 |

安装额外依赖并注册：

```bash
uv pip install --python ~/.local/share/ncut-wechat-skills/bot-venv/bin/python -r skills/wechat-personal/requirements-mcp.txt
codex mcp add wechat-personal -- ~/.local/share/ncut-wechat-skills/bot-venv/bin/python ~/.codex/skills/wechat-personal/scripts/mcp_server.py
```

本机注册与真实MCP调用分别验证；修改配置不意味着当前已运行的对话会热加载工具。未加载时直接使用同等CLI，无需再登录。收到错误按所属能力处理，不启动新微信实例或聊天窗口自动化。

本MCP封装复用现有账号，未另行用OneBot登录。OneBot本身不是微信客户端；第三方适配器与实际后端核对见[OneBot尝试](onebot.md)。尚未取得匹配当前Linux环境并保留既有登录的普通消息发送后端证据，原生发送保持未接通。

2026-09-18新增发送后，真实stdio客户端已列出5个工具；使用同一发送操作ID调用`clawbot_send`返回已成功请求的结果且`replayed=true`，未重发。手机送达由本人确认，读回能力仍按来源区分。

4.1.13升级后，`wechat_messages(chat="微信ClawBot")`也可读取本机ClawBot双向历史。验收/排查时可选在`clawbot_send`后用此工具查新消息，核对正文、时间及机器人发送人；日常发送不要求本地微信在线或本地读回，`clawbot_updates`只消费服务端入站增量，不能代替发送后收件端读回。

2026-09-19新增媒体后，真实stdio客户端已列出7个工具；`clawbot_send_media`复用已发送图片的request_id返回`replayed=true`与原受理结果，没有再次上传/发送。媒体发送总超时75秒，下载50秒；超时后先检查原操作记录，不新建ID重试。文件/图片显示已获本人确认，下载验证范围见[媒体契约](../capabilities/clawbot/media.md)。
