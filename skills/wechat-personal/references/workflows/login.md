# 可跨会话续接的登录入口

学校业务直接 `login --platform school --service 教务`（或预约）。本人完成后 `login finish` 从私有 login.json 恢复目标，转交学校登录脚本验证并保存该业务会话；不代表微信/企微聊天登录。

原生微信/企微：`login --platform wechat` / `wecom` 默认 companion，目前返回 `COMPANION_LOGIN_NOT_CONFIGURED`。不自动启动 Linux 客户端、伴随端容器或旧后台；保留手机及 Linux 的现有登录与桌面。平台/服务/所选 transport 保存在本机，无需复制历史对话。

只有用户明确选择本机窗口时，用 `--transport current-desktop`；后续 `login finish` 复用该选择。这是窗口登录/视觉诊断，不提供消息 HTTP 认证。仅在此分支看私有 image 判断登录页或当前会话，必要扫码由本人完成；截图成功不等于登录验证。已测试复用已有客户端，冷启动/首次扫码仍未完整验收。

2026-09-15：伴随端实验已停止，默认路径不再引导开启模拟器/容器或排查点击适配。先获得某一业务所需的可复用认证证据，再考虑针对性接入。
