---
name: wechat-personal
description: 探索、验证并复用本人微信和企业微信的消息、公众号及内嵌业务能力；按需发现新 API 并生成子能力。已验证 Linux 微信本地消息、第三方 SDK 的 ClawBot 收发文字、公众号和部分学校 Web；原生发送与企微消息待接通。
---

# 微信 / 企微信息入口

目标是意图 → 对应业务 API → 结果。忽略不必要的前端；来自工具箱、工作台、微信链接或小程序的业务，按实际后端服务归档。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径。

既能使用已有能力，也负责独立摸索新能力。用户无需先找到 API 或提供专门示例：先查注册表、已有客户端/业务目录和当前请求证据；只有缺少业务选择或本人认证时才询问。`not_connected` 是未验证状态；用户要求接入时继续按相应发现流程工作，不能把历史失败当作永久结论。

## 最短调用

- 给出公众号链接：`python3 "$WX" article --url '真实链接' --max-chars 6000`。结果仅覆盖页面文字层，图片正文按需读取。
- 学校信息：直接使用同套 [ncut-web-api](../ncut-web-api/SKILL.md) 的课表、场地余量或对应接口；不先启动微信/企微。
- 其他业务：`python3 "$WX" knowledge --query '具体需求'` 返回命中的命令、接口、状态和契约路径，默认不展开子流程。`command` 是脚本参数数组，按用户输入替换占位符。`runtime_verified` 命中直接按对应命令/请求执行，正常结果即结束；未验证条目按 `next` 做局部发现，不把检索命中当作可用。细节仅按能力 ID 加 `--details` 或读对应文件。
- 微信群消息/私聊：`python3 "$WX" native conversations --account me --query '群名或联系人' --limit 5` 定位，再用 `native messages --account me --chat '返回的chat_id' --limit 20`。唯一完整名称也可直接作 `--chat`。省略查询词可列最近会话，`--unread` 只列有未读的会话。复用现有 Linux 数据与私有密钥，无需浏览器、sudo 或再次登录。仅首次缺密钥/确实失效时看 [本机接入](references/workflows/native-linux.md)。正常查询不重跑密钥捕获。
- 个人微信身份发送、企微消息：当前未接通。仅当前任务确实需要时按 [消息接入](references/workflows/messages.md) 检查局部新证据；不启动整个平台接入工程。已有读取覆盖当前客户端已同步的本地消息，不保证云端完整历史；图片、语音、视频仅标类型。
- 企微通知补充已暂缓：本人手机为原生鸿蒙，先前Android假设已更正；不再提示安装SmsForwarder或启动手机验收。现有`notifications list --account me --limit 20`与MCP `wecom_notifications`仅保留本机归档读取，真实手机投递未验证；旧方案见[Android通知](references/workflows/android-notifications.md)。OpenHarmony手机接入留待后续，当前不扩展手机工程。
- ClawBot／微信机器人新消息：`python3 "$WX" bot updates --account me --limit 20`，第三方 SDK 已验证扫码绑定与实际接收文字。它读取本人发给机器人的消息，个人聊天仍用 native。仅认证失败才看 [机器人登录](references/workflows/clawbot.md)。
- ClawBot历史与发送后读回：Linux微信4.1.13已验证`native messages --account me --chat '微信ClawBot' --limit 20`，同时包含本人入站与机器人回复，复用现有密钥。本地读回仅在用户要求验收或排查时可选使用；电脑微信离线不影响ClawBot经iLink独立收发，不因本地未读回阻断或判失败。会话名不唯一时先`native conversations --query ClawBot`选精确ID，详见[历史与读回](references/capabilities/clawbot/read-history.md)。此读取不消费`bot updates`游标。
- ClawBot给本人发消息：`python3 "$WX" bot send --account me --text '消息文字' --request-id '本次唯一ID'`，已实测送达。本人已长期授权此通道读写；同一操作复用同一ID不会重发。仅向绑定本人发送，不是以个人微信身份给好友发消息；细节见[发送契约](references/capabilities/clawbot/send-text.md)。
- ClawBot文件/图片：`bot send --file '/路径' --request-id '唯一ID'`，图片改用`--image`。上传、API受理和本地消息出现已实测，接收端打开效果待确认。`bot updates`会私存媒体引用并给出`attachment_id`，可用`bot download --attachment-id '返回的ID'`下载；当前CDN真实回取失败，下载尚未验收。表情包、公众号分享卡片保留目标，不能把普通图片/链接替代算作完成。详见[媒体契约](references/capabilities/clawbot/media.md)。
- 已配置MCP时可直接用 `wechat_conversations`、`wechat_messages`、`clawbot_updates`、`clawbot_send`、`clawbot_send_media`、`clawbot_download`，与上述命令共用账号；安装和边界见 [MCP入口](references/workflows/mcp.md)。

新内部网页按 [业务 API 接入](references/workflows/embedded-web.md) 处理，确实只有小程序入口时才看 [小程序边界](references/workflows/mini-program.md)。缺项发现限于当前业务请求，不把查询扩大为通用客户端工程。

单项新能力最多探索15分钟实际工作时间；切换路线不重置，等待本人认证不计入。到点报告证据、缺项和后续选项。界面仅用于必要登录和接口发现，日常能力通过 HTTP、已有命令或本机数据执行。长期路线图留在仓库 README，不自动串行推进。

## 发送授权

以本人个人微信身份执行写请求（含 OneBot）前，必须有本人明确授权或适用的事先授权；核对收件人、内容/类型和范围，已有授权不重复询问。接通发送能力本身不代表授权任意发送。ClawBot 通道的读和写已有本人长期授权，无需逐次确认；当前发送仅面向已绑定本人。两种身份的授权不能混用。

当前任务先完成微信，再继续企微。WorkPro 仅在实测可用、稳定且免费或价格低时考虑；未完成这些验证前不宣称可用。

## 登录与本机状态

业务会话在 `~/.local/state/wechat-personal/accounts/`，0700/0600；与学校 skill 共用标准库 HTTP/检索模块，两者一起安装。普通业务请求不依赖旧 wechatcopilot、加密卷、Android 容器或常驻服务。

本人允许以后增加与主 skill 解耦的轻量常驻接收器，部署在服务器或本机；当前暂缓实现与部署，普通查询不启动或管理它。仅处理部署需求时读[独立服务说明](../../BACKGROUND-RECEIVER.md)。

学校登录：`login --platform school --service 教务`（或预约），本人完成后 `login finish`；平台/服务保存在本机。`login --platform wechat` 默认检查现有本地读取，返回的 `NATIVE_READ_READY` 不证明客户端在线或远端登录有效；日常查询直接 native，不预查登录。确需本人扫码时使用显式 `--transport current-desktop`，只在登录任务需要时读 [认证入口](references/workflows/login.md)。企微原生入口仍未配置。

旧客户端和当前窗口工具只作显式人工诊断入口；普通能力查询不召回其操作流程，不自动启用。用户明确要求使用现有 Linux 窗口时才读 [窗口读取](references/workflows/visible-wechat.md)，且只说明当前一屏覆盖范围。

## 记录已打通的 API

按 [共享契约格式](../ncut-web-api/references/api-contract.md) 写业务域、method/path、query/body 参数来源、会话来源、返回字段和成功/失败判断。多步子流程写请求 A → 从响应取值 → 请求 B；不写“打开工具箱点第几项”，不另建大量顶层 skill。动态 code/ticket 不写成永久入口，不保存 token 或消息正文。

`runtime_verified` 只标实际成功的范围；源码线索、接入流程、本地草稿和客户端截图各自标明。正常命中不重验全平台、不写知识。发送/提交遵守上面的身份与授权规则；当前没有原生聊天发送成功的证据。详见 [验收记录](references/verification.md)。
