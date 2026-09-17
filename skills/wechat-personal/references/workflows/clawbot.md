# ClawBot 与第三方 SDK

已选 [corespeed-io/wechatbot](https://github.com/corespeed-io/wechatbot)，只使用底层 `ILinkApi`，由本 skill 管理有界调用、私有账号、游标和错误。没有安装整套 QClaw/OpenClaw，没有开自动回复或常驻网关。

一次安装（仓库根目录执行）：

```bash
uv venv ~/.local/share/ncut-wechat-skills/bot-venv
uv pip install --python ~/.local/share/ncut-wechat-skills/bot-venv/bin/python -r skills/wechat-personal/requirements-bot.txt
```

日常命令沿用 `python3 "$WX" bot updates --account me --limit 20`，入口自动使用独立环境；已有登录直接读取，不再生成二维码。

仅缺凭证或认证失效时：

1. `python3 "$WX" bot login --account me`；若明确需要重新绑定，加 `--refresh`。已有凭证返回 `BOT_CREDENTIALS_PRESENT`，这不证明远端仍在线。
2. `qr_url` 是当前二维码内容，可本地用 `qrencode` 生成图片或在本人手机打开；二维码约数分钟有效。显示后立即运行 `bot finish --account me`，每次最多35秒。`wait/scaned` 表示仍待本人，`scaned_but_redirect` 自动保存官方返回的微信域名用于下次查询。本人等待不计入主动探索时间。
3. `need_verifycode` 时使用本人手机显示的数字，保存到0600私有文件，传 `--verify-code-file /私有路径`；不猜数字、不写入公共知识。`expired` 停止当前二维码；本人在场时再显式刷新。
4. `BOT_LOGIN_CONFIRMED` 后，先让本人给已绑定 ClawBot 发测试文字，再执行 `bot updates` 验证内容。扫码成功和空批次不能代替消息读取实测。

凭证、二维码和增量游标在 `~/.local/state/wechat-personal/bots/<account>/`，权限0700/0600。默认SDK方法无消息发送；后续若扩展发送，仍须按具体目标与正文授权，不自动启用示例 echo bot。

GitHub选型（2026-09-17）：`photon-hq/qclaw-wechat-client` 已归档；`nightsailer/wechat-clawbot` 提供MCP/网关但文档基线仍为上游2.1.1；`epiral/weixin-bot` 是另一个轻量SDK。选用的SDK源码具有新版POST二维码、数字校验与直接底层方法，已在本机真实验证。第三方封装不会自动取得个人微信全部聊天权限。
