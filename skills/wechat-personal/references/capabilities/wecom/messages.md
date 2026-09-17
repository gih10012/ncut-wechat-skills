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
