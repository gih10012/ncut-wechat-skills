---
id: wecom-messages
service: wecom
keywords: ["企微消息", "企业微信消息", "企微聊天", "企业微信聊天"]
status: "not_connected"
transport: "unavailable"
workflow: references/workflows/messages.md
note: "本人企微原生消息待接入；Linux 微信数据库读取不覆盖企微。学校 Web 或企微 JS-SDK 签名也不证明消息权限。"
---
# 企微消息接入

先定位实际客户端或已授权接口，验证本人身份、会话列表和一个有界消息查询。不得把企业自建应用推送接口称为个人完整收件箱。

2026-09-17已检查的局部证据：

- 本人挂载Windows目录有WXWork 5.0.7.6005及两个账号数据目录，其中一个 `message.db` 当日更新。消息和会话库均非明文SQLite；看到文件不等于读取成功。
- [jiebao776/wxwork-decrypt](https://github.com/jiebao776/wxwork-decrypt) 提供wxSQLite3解密，但取钥依赖已登录Windows进程。当前Linux没有该进程或Wine；本人明确不接受Windows常驻。未运行其扫描器、未取得企微密钥，不让此路线成为运行前提。
- [zlz3907/wecom-mcp](https://github.com/zlz3907/wecom-mcp) 接的是智能表格；[kedoupi/wecombot-mcp](https://github.com/kedoupi/wecombot-mcp) 接的是群机器人，均不能证明本人收件箱可读。
- [lichaohuai/wecom-protocol-gateway](https://github.com/lichaohuai/wecom-protocol-gateway) 只有接口示例和展示页，明确未包含网关后端、服务地址或协议代码；未安装、未把账号交给未知服务。缺少可本地部署的真实实现。
- Android桥接也需实际可用的设备/会话；当次 `adb devices` 无已连接设备。尚未部署新的Android容器或手机自动化工程。

后续优先取得不依赖Windows常驻的可执行个人消息后端，并验证本人身份、会话与真实文字。单项探索累计上限沿用主skill；只有新证据或环境变化才继续该分支，不反复搜索上述已排除项目。

2026-09-18补充核对：

- 本机已有停止状态的Waydroid，并存在 `com.tencent.wework` 应用私有目录；目录权限为0700，当前用户不可读，无交互sudo要求密码。尚未确认其中是否有登录态或消息数据库；不能把目录存在记为读取成功。未启动容器、未新建手机登录、未更改目录权限。
- 官方 [WecomTeam/wecom-cli](https://github.com/WecomTeam/wecom-cli) 可在Linux运行，但其[命令参考](https://github.com/WecomTeam/wecom-cli/blob/main/docs/cli-reference.md)说明扫码绑定的是机器人凭证，消息示例是 `message aibot sessions list`；README仅列机器人近期对话推送。未发现其公开文档提供本人完整聊天读取，不能用该CLI替代本目标，也没有为了验收读取而创建机器人。

当前可交接的下一步是一次性只读检查既有Android企微缓存的数据库元信息，先确认是否存在可用本地消息，再决定是否值得继续；需要本人本机授权，不需要Windows常驻。该步骤本身不保证能解密，也不证明能持续同步。本人离线期间将授权事项记入本机待办，不重复生成登录二维码。

2026-09-18按本人“轻服务、稍微尝试”的要求补查：

- [Hoshinonyaruko/Finance_Wechat_Group_Chatbot_OnebotApi](https://github.com/Hoshinonyaruko/Finance_Wechat_Group_Chatbot_OnebotApi)明确要求企业认证和会话存档API；不是普通企微账号扫码即可读取的服务。本机未持有该企业级权限，未部署Java/Python双进程栈。
- 官方 [WecomTeam/aibot-node-sdk](https://github.com/WecomTeam/aibot-node-sdk)提供智能机器人长连接；npm版本1.0.7的包展开约0.5MB，直接依赖仅ws、axios和eventemitter3。它是轻服务候选，但认证仍需机器人Bot ID/Secret，消息范围限于机器人接收的事件，不能读取本人既有全部聊天。本机未安装WeCom CLI，也没有其已保存凭证。没有新建企业或机器人来代替个人消息目标。
