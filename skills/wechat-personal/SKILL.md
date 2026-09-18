---
name: wechat-personal
description: 探索、验证并复用本人微信和企业微信的消息、公众号及内嵌业务能力；按需发现新 API 并生成子能力。已验证 Linux 微信本地消息、第三方 SDK 的 ClawBot 收消息、公众号和部分学校 Web；原生发送与企微消息待接通。
---

# 微信 / 企微信息入口

目标是意图 → 对应业务 API → 结果。忽略不必要的前端；来自工具箱、工作台、微信链接或小程序的业务，按实际后端服务归档。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径。

既能使用已有能力，也负责独立摸索新能力。用户无需先找到 API 或提供专门示例：先查注册表、已有客户端/业务目录和当前请求证据；只有缺少业务选择或本人认证时才询问。`not_connected` 是未验证状态；用户要求接入时继续按相应发现流程工作，不能把历史失败当作永久结论。

## 最短调用

- 给出公众号链接：`python3 "$WX" article --url '真实链接' --max-chars 6000`。结果仅覆盖页面文字层，图片正文按需读取。
- 学校信息：直接使用同套 [ncut-web-api](../ncut-web-api/SKILL.md) 的课表、场地余量或对应接口；不先启动微信/企微。
- 其他业务：`python3 "$WX" knowledge --query '具体需求'` 返回命中的命令、接口、状态和契约路径，默认不展开子流程。`command` 是脚本参数数组，按用户输入替换占位符。`runtime_verified` 命中直接按对应命令/请求执行，正常结果即结束；未验证条目按 `next` 做局部发现，不把检索命中当作可用。细节仅按能力 ID 加 `--details` 或读对应文件。
- 微信群消息/私聊：`python3 "$WX" native conversations --account me --query '群名或联系人' --limit 5` 定位，再用 `native messages --account me --chat '返回的chat_id' --limit 20`。唯一完整名称也可直接作 `--chat`。省略查询词可列最近会话，`--unread` 只列有未读的会话。复用现有 Linux 数据与私有密钥，无需浏览器、sudo 或再次登录。仅首次缺密钥/确实失效时看 [本机接入](references/workflows/native-linux.md)。正常查询不重跑密钥捕获。
- 微信发送、企微消息：当前未接通。仅当前任务确实需要时按 [消息接入](references/workflows/messages.md) 检查局部新证据；不启动整个平台接入工程。已有读取覆盖当前客户端已同步的本地消息，不保证云端完整历史；图片、语音、视频仅标类型。
- 企微通知补充：`python3 "$WX" notifications list --account me --limit 20`，或MCP `wecom_notifications`。仅本人Android通知的本机归档，不覆盖完整聊天。接收端与MCP已本机测试，真实手机通知尚待验收；首次设置见[Android通知](references/workflows/android-notifications.md)。
- ClawBot／微信机器人新消息：`python3 "$WX" bot updates --account me --limit 20`，第三方 SDK 已验证扫码绑定与实际接收文字。它读取本人发给机器人的消息，个人聊天仍用 native。仅认证失败才看 [机器人登录](references/workflows/clawbot.md)。
- 已配置MCP时可直接用 `wechat_conversations`、`wechat_messages`、`clawbot_updates`，与上述命令共用账号；安装和边界见 [MCP入口](references/workflows/mcp.md)。

新内部网页按 [业务 API 接入](references/workflows/embedded-web.md) 处理，确实只有小程序入口时才看 [小程序边界](references/workflows/mini-program.md)。缺项发现限于当前业务请求，不把查询扩大为通用客户端工程。

单项新能力最多探索15分钟实际工作时间；切换路线不重置，等待本人认证不计入。到点报告证据、缺项和后续选项。界面仅用于必要登录和接口发现，日常能力通过 HTTP、已有命令或本机数据执行。长期路线图留在仓库 README，不自动串行推进。

## 登录与本机状态

业务会话在 `~/.local/state/wechat-personal/accounts/`，0700/0600；与学校 skill 共用标准库 HTTP/检索模块，两者一起安装。普通业务请求不依赖旧 wechatcopilot、加密卷、Android 容器或常驻服务。

本人允许以后增加与主 skill 解耦的轻量常驻接收器，部署在服务器或本机；当前暂缓实现与部署，普通查询不启动或管理它。仅处理部署需求时读[独立服务说明](../../BACKGROUND-RECEIVER.md)。

学校登录：`login --platform school --service 教务`（或预约），本人完成后 `login finish`；平台/服务保存在本机。`login --platform wechat` 默认检查现有本地读取，返回的 `NATIVE_READ_READY` 不证明客户端在线或远端登录有效；日常查询直接 native，不预查登录。确需本人扫码时使用显式 `--transport current-desktop`，只在登录任务需要时读 [认证入口](references/workflows/login.md)。企微原生入口仍未配置。

旧客户端和当前窗口工具只作显式人工诊断入口；普通能力查询不召回其操作流程，不自动启用。用户明确要求使用现有 Linux 窗口时才读 [窗口读取](references/workflows/visible-wechat.md)，且只说明当前一屏覆盖范围。

## 记录已打通的 API

按 [共享契约格式](../ncut-web-api/references/api-contract.md) 写业务域、method/path、query/body 参数来源、会话来源、返回字段和成功/失败判断。多步子流程写请求 A → 从响应取值 → 请求 B；不写“打开工具箱点第几项”，不另建大量顶层 skill。动态 code/ticket 不写成永久入口，不保存 token 或消息正文。

`runtime_verified` 只标实际成功的范围；源码线索、接入流程、本地草稿和客户端截图各自标明。正常命中不重验全平台、不写知识。发送/提交须在用户明确授权范围内；当前没有原生聊天发送成功的证据。详见 [验收记录](references/verification.md)。
