# 按需 MCP 读取

`scripts/mcp_server.py` 使用 Python MCP SDK 的 stdio transport，仅在客户端调用时运行，不开放监听端口。工具直接调用相同的已验证命令：

| 工具 | 来源 |
| --- | --- |
| `wechat_conversations` | 本人 Linux 微信本地会话与未读 |
| `wechat_messages` | 精确会话的已同步消息，最多50条 |
| `clawbot_updates` | 第三方SDK读取ClawBot单批新消息，最长40秒 |

安装额外依赖并注册：

```bash
uv pip install --python ~/.local/share/ncut-wechat-skills/bot-venv/bin/python -r skills/wechat-personal/requirements-mcp.txt
codex mcp add wechat-personal -- ~/.local/share/ncut-wechat-skills/bot-venv/bin/python ~/.codex/skills/wechat-personal/scripts/mcp_server.py
```

本机注册与真实MCP调用分别验证；修改配置不意味着当前已运行的对话会热加载工具。未加载时直接使用同等CLI，无需再登录。收到错误按所属能力处理，不启动新微信实例或聊天窗口自动化。

本MCP封装复用现有账号，未另行用OneBot登录。OneBot本身不是微信客户端：已检查的 `lc-cn/onebots` 微信适配器用于公众号，`Clov614/rikka-bot-wechat` 已归档且主要使用Windows注入；macOS版本Hook也不能用于当前Linux。未取得匹配当前Linux版本并保留既有登录的发送后端证据，故不宣称原生发送已接通。
