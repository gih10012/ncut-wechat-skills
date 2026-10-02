---
id: clawbot-recover-context
service: clawbot
keywords: ["ClawBot断连", "ClawBot恢复", "ClawBot掉线", "ClawBot刷新", "机器人发不出", "BOT_BUSINESS_ERROR_-2", "clawbot-recover"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-10-03"
transport: "personal_cli_refresh_and_independent_ilink"
command: ["bot", "status", "--account", "me"]
workflow: references/workflows/clawbot.md
note: "个人微信CLI刷新→精确本人iLink新入站→机器人通知已真实验证；受控本地-2故障注入后的恢复使用真实CLI/网络，本地单条读回及重放防重通过。自然再次过期的完整自动恢复与长期稳定性仍待观察，不把-2直接当登录失效。"
---
# ClawBot 有界自动恢复

本机已为绑定本人配置个人微信ClawBot精确会话。普通`bot send`先走独立iLink；只有首次消息提交明确返回`BOT_BUSINESS_ERROR_-2`时，才自动经普通`wechat-linux send-text`发一条含唯一标记的“ClawBot 自动刷新”消息，再读取新iLink入站，取得有效的新回复来源后补发原通知一次。刷新与机器人通道读写都在本人长期授权内，已有配置直接复用，不要求本人手动发刷新消息，也不重新扫码机器人。文字与媒体共用这条恢复流程，媒体只上传一次。

`bot status --account me`不联网、不消费游标、不输出凭证；显示上下文接收时间、消息时间、最近成功更新查询及`native_recovery_enabled`。旧记录没有时间时返回null；`reply_context_validity=unknown`，有缓存不代表仍有效。空轮询或读取旧的本地分页不会更新上下文时间。输出页以外的新消息也参与选择最新本人上下文，非绑定收件人、其他发送人、群聊或其他机器人不能覆盖它。

首次在其他安装配置时，从`native conversations --query ClawBot`读取并核对本人绑定机器人的精确`@weclaw`会话，再运行：

```bash
python3 "$WX" bot recovery --account me --native-chat '从本人会话查询返回的精确ID'
```

配置绑定当前iLink用户与机器人ID，保存在账号私有状态，换绑定后不能继续使用旧配置。`bot recovery`检查配置，`--disable-native-recovery`关闭它；配置命令不发送消息。单独验收刷新可用`bot recovery --renew --request-id '本次唯一ID'`，这会真实发送一条刷新消息。本人明确要求不再切换小号验收；日常保持主号正常微信进程，不能为本功能退出、切换账号或重绑。

原通知使用一个外层request_id，首次拒绝及最后结果保留在`sends/`的`attempts`；刷新有独立`renewals/`记录和确定性的原生request_id。发送前写入记录，恢复后提交前写入未知结果。重复ID、进程中断、网络超时、HTTP 5xx或任何未知提交结果均不启动第二次刷新或再次提交；第二次仍拒绝时结束。`automatic_retry=false`指不再循环/重放提交，发生过一次恢复时另返回`native_recovery`及`submission_count=2`。

恢复中的读取保留所有入站与新游标，供下次普通`bot updates`输出，不能吞掉本人的业务消息。只接受本轮新查询中与刷新标记精确匹配、来自绑定本人、发给绑定机器人的私聊消息，并核对采用的上下文来自这批消息；只看到刷新本地入库、任意其他新消息或旧缓存不足以补发。自动刷新是控制消息，读取到它不用另行执行任务或回一条echo。

原生CLI调用最长120秒，之后最多35秒等待精确入站；没有常驻循环、定时保活或后台接收器。CLI缺失、主号未登录或刷新未到达时保留原拒绝及恢复错误。普通iLink读写不依赖桌面在线，只有这条刷新路径需要个人主号在线；先检查真实缺项，认证`-14`才走机器人登录。CLI提交未知时先查看其原请求，不能在GUI重发。CLI确实无法完成且原请求未进入时，agent可按已有授权用computer-use补齐，再取得精确新入站。

2026-10-03实际证据：原登录凭证下`updates`认证正常、通知返回`-2`，本人新消息后回复受理且本人确认手机收到。主号登录后，普通个人CLI自动刷新、iLink精确入站与机器人通知再次受理；受控本地注入一次`-2`后，后续所有CLI与网络调用均真实，约3.5秒完成恢复，本地独立读回一条通知，普通命令同ID重放不新增消息。新入站后的测试中，无缓存上下文和故意无效上下文也被API受理，说明不能把此次原因直接定为token过期；具体服务端条件与有效期未知。故障注入不冒充一次自然服务端拒绝，长期空闲后自动恢复仍需继续观察。本人手机确认适用于此前回复；本轮受控测试的收件证据是独立本地读回。
