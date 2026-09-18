# ClawBot 与第三方 SDK

已选 [corespeed-io/wechatbot](https://github.com/corespeed-io/wechatbot)，只使用底层 `ILinkApi`，由本 skill 管理有界调用、私有账号、游标和错误。没有安装整套 QClaw/OpenClaw，没有开自动回复或常驻网关。

一次安装（仓库根目录执行）：

```bash
uv venv ~/.local/share/ncut-wechat-skills/bot-venv
uv pip install --python ~/.local/share/ncut-wechat-skills/bot-venv/bin/python -r skills/wechat-personal/requirements-bot.txt
```

日常命令沿用 `python3 "$WX" bot updates --account me --limit 20`，入口自动使用独立环境；已有登录直接读取，不再生成二维码。

需要历史或验证机器人回执时，使用`native messages --account me --chat '微信ClawBot' --limit 20`读取Linux微信已同步的双向会话。4.1.13已实测支持这条本机读取；不再把旧版查不到会话当作当前结论。发送后先按[历史与读回](../capabilities/clawbot/read-history.md)自行验证，再决定是否需要本人确认。SDK增量读取与本机历史是两种不同来源。

仅缺凭证或认证失效时：

1. `python3 "$WX" bot login --account me`；若明确需要重新绑定，加 `--refresh`。已有凭证返回 `BOT_CREDENTIALS_PRESENT`，这不证明远端仍在线。
2. `qr_url` 是当前二维码内容，可本地用 `qrencode` 生成图片或在本人手机打开；二维码约数分钟有效。显示后立即运行 `bot finish --account me`，每次最多35秒。`wait/scaned` 表示仍待本人，`scaned_but_redirect` 自动保存官方返回的微信域名用于下次查询。本人等待不计入主动探索时间。
3. `need_verifycode` 时使用本人手机显示的数字，保存到0600私有文件，传 `--verify-code-file /私有路径`；不猜数字、不写入公共知识。`expired` 停止当前二维码；本人在场时再显式刷新。
4. `BOT_LOGIN_CONFIRMED` 后，先让本人给已绑定 ClawBot 发测试文字，再执行 `bot updates` 验证内容。扫码成功和空批次不能代替消息读取实测。

凭证、二维码和增量游标在 `~/.local/state/wechat-personal/bots/<account>/`，权限0700/0600。ClawBot读写已有本人长期授权，无需逐次询问。`bot send --account me --text '消息文字' --request-id '唯一操作ID'`以机器人身份向绑定本人发送；已于2026-09-18真实发送且本人确认收到。请求ID防止重复提交、超时处理和结果解释见[发送契约](../capabilities/clawbot/send-text.md)。不自动启用示例echo bot。本人入站消息中的回复上下文只保存于私有账号状态，不输出。

GitHub选型（2026-09-17）：`photon-hq/qclaw-wechat-client` 已归档；`nightsailer/wechat-clawbot` 提供MCP/网关但文档基线仍为上游2.1.1；`epiral/weixin-bot` 是另一个轻量SDK。选用的SDK源码具有新版POST二维码、数字校验与直接底层方法，已在本机真实验证。第三方封装不会自动取得个人微信全部聊天权限。
