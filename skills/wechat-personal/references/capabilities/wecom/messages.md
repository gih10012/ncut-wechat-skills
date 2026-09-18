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

本人随后已完成一次性只读元信息检查：确认既有Android目录内存在消息/会话数据库，相关文件不是明文SQLite，尚未取得可读正文或新消息同步证据。具体路径、数量、时间和检查结果只保存在本机。无需再次要求同一检查；Waydroid仍保持停止。

本人确认历史与新消息都需要，先尝试接收后续新消息。旧缓存检查不代替此目标，现有扫码状态和既有手机登录继续保留。

2026-09-18按本人“轻服务、稍微尝试”的要求补查：

- [Hoshinonyaruko/Finance_Wechat_Group_Chatbot_OnebotApi](https://github.com/Hoshinonyaruko/Finance_Wechat_Group_Chatbot_OnebotApi)明确要求企业认证和会话存档API；不是普通企微账号扫码即可读取的服务。本机未持有该企业级权限，未部署Java/Python双进程栈。
- 官方 [WecomTeam/aibot-node-sdk](https://github.com/WecomTeam/aibot-node-sdk)提供智能机器人长连接；npm版本1.0.7的包展开约0.5MB，直接依赖仅ws、axios和eventemitter3。它是轻服务候选，但认证仍需机器人Bot ID/Secret，消息范围限于机器人接收的事件，不能读取本人既有全部聊天。本机未安装WeCom CLI，也没有其已保存凭证。没有新建企业或机器人来代替个人消息目标。

2026-09-18本人要求扩大第三方及机器人协议检索后的源码核对：

- [OneBots企微适配器](https://github.com/lc-cn/onebots/blob/master/adapters/adapter-wecom/README.md)公开说明其目标是企业自建应用；代码调用`message/send`与`appchat/send`。其OneBot11/12等出口不改变应用消息范围。客服另用`adapter-wecom-kf`，也不是本人同事/群聊收件箱。
- [Satori企微适配器](https://github.com/satorijs/satori/blob/main/adapters/wecom/src/bot.ts)同样使用企业应用身份，未发现普通成员聊天接入实现。
- [gtsigner/wework-hook-example](https://github.com/gtsigner/wework-hook-example)有Android Xposed消息收发示例，但README声明停止更新、支持企微2.7.2，不能证明当前客户端可用。
- [cctvz/wecome-ipad](https://github.com/cctvz/wecome-ipad)虽然有Go代码，[HTTP封装](https://github.com/cctvz/wecome-ipad/blob/main/util/http/http.go)的`BASE_URL`为空，二维码和登录控制器只是转发到外部API；未提供真实协议后端，也没有消息接收实现可供本机试跑。
- [weworkipad/weworkipad](https://github.com/weworkipad/weworkipad)及[musi66/wework_robot](https://github.com/musi66/wework_robot)当次完整仓库树均只有README。功能宣传不等于可安装后端，未交付账号给这些服务。
- [xlrpa/FlowBot](https://github.com/xlrpa/FlowBot)说明其Android实现依赖无障碍界面自动化；不符合当前日常消息能力不依赖UI的约束，未安装。

以上只是适配器范围和依赖核对，未验收企微新消息。本人进一步确认只有普通成员权限、无法开通会话内容存档，因此该路线当前不可用，不再要求管理员开通。继续接入需要可执行且匹配现有环境的个人消息后端；不再重复要求缓存元信息检查，也不把企业应用/机器人测试改名为个人聊天成功。
