---
id: visible-wechat-window
service: wechat
keywords: ["当前微信窗口", "微信窗口截图", "visible-wechat-window"]
status: runtime_verified
evidence: "Existing official Linux WeChat tray activated; niri captured its window and actual personal service notifications were visually read"
runtime_verified_at: "2026-09-14T17:16:24+08:00"
workflow: references/workflows/visible-wechat.md
transport: "manual-ui"
command: ["desktop", "capture", "--show"]
note: "仅用户明确选择使用本机微信窗口时调用；当前一屏的视觉读取，不是消息 API，不作为普通消息查询回退。"
---
# 读取本人微信当前可见内容

用户已要求优先独立伴随端，保留现有手机及 Linux 登录与桌面。此能力只在当前任务明确选择 Linux 客户端时使用；不作为普通消息任务的默认回退。

`python3 "$WX" desktop capture --show` 返回一个私有图片路径；用 `view_image` 读取该图片，再按用户目标提取内容。截图成功不是文本提取或登录成功；必须实际查看，判断是扫码页、加载页还是本人会话。

真实验收：官方微信已登录，可读“服务通知”中的本人通知卡片。仅代表当前可见内容，`complete:false`，不含未加载的聊天历史。没有验证自动搜索/切换群、发送消息或小程序内部读取。

依赖本机已有 niri；隐藏窗口通过系统 Python dbus 激活已有微信托盘。没有新增服务。当前窗口不存在时只允许一次唤出，失败后需要用户打开目标会话，不重建旧消息后台。
