---
id: personal-login
service: wechat
keywords: ["登录", "登陆", "扫码", "已登录", "过期", "重新登录"]
status: "not_connected"
evidence: "login --platform wechat captured the existing authenticated official client; fresh QR login and cold launch are unverified; WeCom entry missing"
runtime_verified_at: null
workflow: references/workflows/login.md
transport: "auth"
command: ["login", "--platform", "<wechat|wecom>"]
note: "默认伴随端尚未配置，当前只返回缺项；不唤起现有 Linux 客户端。学校业务用 login --platform school --service 教务/预约。"
---
# 本人登录入口

微信/企微原生登录默认 companion，目前明确返回未配置，不触碰现有手机/Linux 登录。仅用户明确选择本机窗口时使用 --transport current-desktop；这不是消息 API 登录。

学校业务用 `login --platform school --service 教务` / `预约`，本人完成后 `login finish` 自动恢复本机保存的目标。
