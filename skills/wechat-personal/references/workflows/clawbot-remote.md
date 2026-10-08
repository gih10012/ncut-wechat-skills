# 显式绑定的独立接收器

普通 skill 安装不会启动接收器。本人在 2026-10-07 的个人助理部署中
显式选择云端作为唯一 iLink 轮询端，本机 CLI 通过私有 `bots/<account>/remote.json`
绑定到该控制账本。配置只包含 `control_url` 和 `token_file` 路径；必须为
本人持有的普通 0600 文件，token 留在私有文件，不进入代码、提示词或命令行。

- `bot status` 查看云端通道和 Leader 状态，既不续登也不消费消息。
- `bot updates` 读取已持久化归档，使用独立本机归档游标，不与云端争抢 iLink 游标。
- `bot send` 使用原 request_id 入队。`pending` 是排队，`accepted` 仅表示服务端受理；
  所有输出保留 `delivery_verified=false`，不能宣称手机已收到。
- 未知网络提交不自动重发；明确上下文拒绝仅在新上下文后最多一次恢复提交。
  首次远端入队前持久预留；重复 ID 仅查询原状态。查询不可达或没有记录仍为
  `outcome_unknown`，不换新 ID、不重新入队或上传。
  本机 native 刷新桥由独立服务持久预留，普通 CLI 不另开刷新轮询。
- 图片/文件等可沿用已有上传器，把私有媒体引用交给云端发送；这条远端媒体
  路线仍需单独真实验收。归档入站附件尚无与旧本机 attachment_id 缓存完整对接，
  不能将旧媒体契约的验收直接套用。
- 控制服务不可达时返回 `BOT_REMOTE_UNAVAILABLE_NO_LOCAL_FALLBACK`。
  不移除 remote.json、不启用第二个本地接收器，也不切换发送器。
- 重新扫码绑定须先协调唯一轮询权；普通账号 login/finish 被拒绝，避免两端身份分叉。

当前实现：[personal-assistant-mesh](https://github.com/gih10012/personal-assistant-mesh)。
主号桌面在线仅用于上下文需要刷新时；独立云端轮询和正常回复不依赖桌面在线。
跨夜收件、远端媒体和云端模型接管分别验收，不因服务 active 就算完成。
