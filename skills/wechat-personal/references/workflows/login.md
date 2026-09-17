# 可跨会话续接的登录入口

学校业务直接 `login --platform school --service 教务`（或预约）。本人完成后 `login finish` 从私有 login.json 恢复目标，转交学校登录脚本验证并保存该业务会话；不代表微信/企微聊天登录。

`login --platform wechat` 默认 native，直接验证本机数据库读取，成功返回 `NATIVE_READ_READY` 和 `login_verified:false`；本地缓存可读不能证明客户端当前在线。缺密钥或数据库异常按 [本机读取](native-linux.md) 的具体错误处理，日常消息查询不预跑登录检查。`login --platform wecom` 返回 `WECOM_CLIENT_SETUP_REQUIRED`，不启动其他客户端。平台/服务/所选 transport 保存在本机，无需复制历史对话。

确需本人扫码时，用 `--transport current-desktop`；后续 `login finish` 复用该显式选择。这是窗口登录，不提供消息 HTTP 认证。仅在此分支看私有 image 判断登录页，必要扫码由本人完成；截图成功不等于登录验证。已测试复用已有客户端，冷启动/首次扫码仍未完整验收。

旧 `--transport companion` 保留兼容错误响应，已停止的伴随端不作为默认接入路线。
