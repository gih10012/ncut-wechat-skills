---
id: school-login
service: jwxtbk
keywords: ["登录", "登陆", "扫码", "过期", "已登录", "认证", "重新登录"]
status: runtime_verified
evidence: "Real user login followed by login finish: undergraduate tab/menu handoff, cookie and User-Agent capture, protected timetable check, browser close; subsequent direct HTTP timetable read succeeded."
runtime_verified_at: "2026-09-14T18:27:49+08:00"
workflow: references/workflows/session.md
transport: "auth"
command: ["login", "--service", "教务"]
note: "仅首次/失效时登录；预约用 --service 预约。本人完成后 login finish，从本机状态续接。"
---
# 学校登录启动与跨会话续接

`python3 "$NCUT" login --service 教务`；预约平台用 `--service 预约`。用户完成页面登录后执行 `login finish`，目标服务从私有 pending 文件恢复。成功只以对应个人接口验证为准。

启动、过期识别、门户菜单自动续接、会话保存和关闭浏览器后的课表读取均已实测。遇到 SCHOOL_MENU_CHANGED 时读取当前门户局部菜单，不凭历史会话重建全部登录链。
