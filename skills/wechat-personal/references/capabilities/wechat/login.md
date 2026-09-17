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
note: "微信默认检查现有本机读取，不启动窗口；本机读取成功不是远端登录验证。确需扫码才显式选择 current-desktop。企微原生入口未配置；学校业务用 login --platform school --service 教务/预约。"
---
# 本人登录入口

微信默认 native，验证本机数据库读取并保留现有手机/Linux 登录；不能由本地缓存推断远端在线。企微返回具体缺项。确需本机扫码时使用 --transport current-desktop；后续 login finish 复用这一显式选择。旧 companion 仅保留兼容错误入口，不作为默认路线。

学校业务用 `login --platform school --service 教务` / `预约`，本人完成后 `login finish` 自动恢复本机保存的目标。
