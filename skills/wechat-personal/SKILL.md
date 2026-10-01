---
name: wechat-personal
description: 探索、验证并复用本人微信和企业微信的消息、公众号及内嵌业务能力；按需发现新 API 并生成子能力。已验证 Linux 微信本地消息、普通 CLI 个人身份文字、PNG/JPEG、中文文件名TXT/ZIP、公众号文章/小程序转发、自定义XML及动画GIF原生表情；卡片与GIF在文件传输助手有本人手机确认。ClawBot经iLink独立文字/文件/图片收发及语音下载已验证，其手机端不支持自定义表情。朋友圈动态/指定人完整缓存读取、分页和全部已加载历史已验证。企微 Wine 独立 CLI 已验证真实私聊/群聊读取、分页、已同步历史及新文字读回；企微发送、媒体下载、重启稳定性待验收。
---

# 微信 / 企微信息入口

目标是意图 → 对应业务 API → 结果。忽略不必要的前端；来自工具箱、工作台、微信链接或小程序的业务，按实际后端服务归档。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径。

既能使用已有能力，也负责独立摸索新能力。用户无需先找到 API 或提供专门示例：先查注册表、已有客户端/业务目录和当前请求证据；只有缺少业务选择或本人认证时才询问。`not_connected` 是未验证状态；用户要求接入时继续按相应发现流程工作，不能把历史失败当作永久结论。

## 最短调用

- 给出公众号链接：`python3 "$WX" article --url '真实链接' --max-chars 6000`。结果仅覆盖页面文字层，图片正文按需读取。
- 学校信息：直接使用同套 [ncut-web-api](../ncut-web-api/SKILL.md) 的课表、场地余量或对应接口；不先启动微信/企微。
- 其他业务：`python3 "$WX" knowledge --query '具体需求'` 返回命中的命令、接口、状态和契约路径，默认不展开子流程。`command` 是脚本参数数组，按用户输入替换占位符。`runtime_verified` 命中直接按对应命令/请求执行，正常结果即结束；未验证条目按 `next` 做局部发现，不把检索命中当作可用。细节仅按能力 ID 加 `--details` 或读对应文件。
- 微信群消息/私聊：`python3 "$WX" native conversations --account me --query '群名或联系人' --limit 5` 定位，再用 `native messages --account me --chat '返回的chat_id' --limit 20`。唯一完整名称也可直接作 `--chat`。省略查询词可列最近会话，`--unread` 只列有未读的会话。复用现有 Linux 数据与私有密钥，无需浏览器、sudo 或再次登录。仅首次缺密钥/确实失效时看 [本机接入](references/workflows/native-linux.md)。正常查询不重跑密钥捕获。
- 朋友圈读取：`python3 "$WX" native moments --account me --limit 20`读取全部动态，`--user '精确用户ID或唯一完整联系人名称'`读取指定人。默认20条分页，使用返回的`next_cursor`作`--cursor`续页；用户要求全部历史时加`--all`，正文不截断，含全部媒体引用、位置、点赞/评论和完整XML字段。按[朋友圈工作流](references/workflows/moments.md)执行；CLI只读已加载缓存，需要新鲜或更早历史时用computer-use在正常微信窗口持续加载至实际可见边界，再读回。缓存末尾不等于云端完整，媒体引用不等于已查看图片/视频正文。
- 个人微信身份发送：`python3 "$WX" native send --recipient '精确 chat_id' --text '消息文字' --request-id '本次唯一ID'`，省略 recipient 默认文件传输助手。本机已安装独立 CLI 和自启动辅助服务，日常无需 sudo；skill 优先调用该 CLI，失败不改走旧发送器。2026-09-30 普通 CLI 的文件传输助手文字通过手机单次完整收件、本地数据库一条读回及 Linux 窗口显示验收；个人微信→ClawBot→本人文字往返亦通过 iLink 入站与独立本地读回。同 ID 重放不重发。直接按[filehelper文字契约](references/capabilities/wechat/send-filehelper-text.md)或[通用发送契约](references/capabilities/wechat/send-message.md)执行。`native send-status --request-id '原请求ID'`只读结果；状态未知保留原 ID，不能凭本地历史缺失重发。CLI 接受任意精确会话 ID，写入授权按下文判断；其他收件人的实际行为、其他个人身份媒体及 OneBot 事件待分别验收。已有读取仅覆盖本机同步历史，媒体仅标类型；企微消息缺项见[消息接入](references/workflows/messages.md)。
- 个人微信图片：`python3 "$WX" native send --recipient '精确chat_id' --image '/路径/image.png' --request-id '唯一ID'`。PNG/JPEG、最多 10 MiB，普通 CLI→ClawBot 的单次入站、下载字节一致及 Linux UI 已真实验收；直接按[图片契约](references/capabilities/wechat/send-personal-image.md)执行。
- 个人微信文件：`python3 "$WX" native send --recipient '精确chat_id' --file '/路径/文件.zip' --request-id '唯一ID'`。常规文件 1 字节到 10 MiB，保留原文件名；中文文件名TXT和ZIP已通过普通 CLI→ClawBot 单次入站、下载文件名/字节一致及 Linux UI 验收。按[文件契约](references/capabilities/wechat/send-personal-file.md)执行，同 ID 绑定文件名和内容，改名冲突拒绝。
- 个人微信表情：`python3 "$WX" native send --recipient '精确chat_id' --sticker '/路径/sticker.gif' --request-id '唯一ID'`。动画GIF以原生47类型通过普通CLI发送至文件传输助手，XML的MD5/长度、服务器ID、Linux动画与防重通过，本人确认手机正常；按[表情契约](references/capabilities/wechat/send-personal-sticker.md)执行。ClawBot手机端不支持自定义表情，仅支持emoji；PNG/JPEG表情及其他对象仍待独立验收。
- 个人微信转发与自定义 XML：`native forward --chat '精确源chat_id' --local-id 123 --database message/message_0.db --recipient '精确目标chat_id' --request-id '唯一ID'`，源 ID/分片来自 `native messages`。`native message-xml`读取对应原始 XML；`native send --xml '/路径/card.xml'`发送自定义卡片。按[转发/XML契约](references/capabilities/wechat/forward-card.md)直接调用。文章5、小程序33、修改标题/描述的XML已通过普通CLI真实发送、独立字段/服务器ID和Linux完整卡片显示；本人已确认手机显示/单次收件/点击；type36仍待实测。
- 企微通知补充已暂缓：本人手机为原生鸿蒙，先前Android假设已更正；不再提示安装SmsForwarder或启动手机验收。现有`notifications list --account me --limit 20`与MCP `wecom_notifications`仅保留本机归档读取，真实手机投递未验证；旧方案见[Android通知](references/workflows/android-notifications.md)。OpenHarmony手机接入留待后续，当前不扩展手机工程。
- 企业微信读取：`python3 "$WX" wecom conversations --account me --query '会话名称' --limit 20`定位，再用`wecom messages --account me --chat '精确chat_id或唯一完整名称' --limit 20`读取。默认20条分页，返回`next_cursor`供`--cursor`续页；`--all`读取指定会话全部已同步历史。本人已登录独立 Wine 客户端，真实私聊/群聊、完整文字和新消息独立读回已验证；日常复用已安装CLI和私有密钥，不需sudo或重新捕获。媒体保留完整二进制字段和引用，未下载。`wecom status`检查配置，`wecom client start`手动启动；不创建自启动。CLI发送和学校工作台仍待验收，按[企微 CLI](references/workflows/wecom-cli.md)继续当前已授权开发。
- ClawBot／微信机器人新消息：`python3 "$WX" bot updates --account me --limit 20`，第三方 SDK 已验证扫码绑定及真实文字、文件、图片、语音入站。它读取本人发给机器人的消息，个人聊天仍用 native。仅认证失败才看 [机器人登录](references/workflows/clawbot.md)。
- ClawBot历史与发送后读回：Linux微信4.1.13已验证`native messages --account me --chat '微信ClawBot' --limit 20`，同时包含本人入站与机器人回复，复用现有密钥。本地读回仅在用户要求验收或排查时可选使用；电脑微信离线不影响ClawBot经iLink独立收发，不因本地未读回阻断或判失败。会话名不唯一时先`native conversations --query ClawBot`选精确ID，详见[历史与读回](references/capabilities/clawbot/read-history.md)。此读取不消费`bot updates`游标。
- ClawBot给本人发消息：`python3 "$WX" bot send --account me --text '消息文字' --request-id '本次唯一ID'`，已实测送达。本人已长期授权此通道读写；同一操作复用同一ID不会重发。仅向绑定本人发送，不是以个人微信身份给好友发消息；细节见[发送契约](references/capabilities/clawbot/send-text.md)。
- ClawBot文件/图片：`bot send --file '/路径' --request-id '唯一ID'`，图片改用`--image`。已真实发送且本人确认文件能打开、图片显示正常；命中[媒体发送](references/capabilities/clawbot/send-media.md)直接调用。`bot updates`会私存媒体引用并给出`attachment_id`，可用`bot download --attachment-id '返回的ID'`下载；真实入站Excel、JPEG及语音已下载解密，Excel正文与图片已实际读取，语音仅确认SILK文件，转写未验收。使用updates的入站引用；出站附件引用回取曾失败。本人确认ClawBot手机端不支持自定义表情、仅支持emoji，公众号分享卡片通道亦未接通；个人身份GIF/卡片向文件传输助手的已验收能力不证明ClawBot富消息可用。详见[媒体契约](references/capabilities/clawbot/media.md)。
- 已配置MCP时可直接用 `wechat_conversations`、`wechat_messages`、`clawbot_updates`、`clawbot_send`、`clawbot_send_media`、`clawbot_download`，与上述命令共用账号；安装和边界见 [MCP入口](references/workflows/mcp.md)。

先区分发送身份：本人微信→ClawBot用`knowledge --query send-message --details`或直接读个人微信发送契约；ClawBot机器人→本人用`knowledge --query clawbot-send`。不能只因收件人名含ClawBot就改走机器人发送。

一句话询问多种动作或格式时，分别检索并汇总状态。例如“ClawBot能发文件、下载附件、收表情包和公众号卡片吗”应拆为`ClawBot发文件`、`ClawBot下载`、`ClawBot表情包`、`ClawBot公众号卡片`。当前关键词检索不理解整句多意图，单次只命中`clawbot-updates`不能据此判定其他格式不存在，也不能用已验证项覆盖未接通项；已列出的契约可直接读取，无需重新探索接口。

新内部网页按 [业务 API 接入](references/workflows/embedded-web.md) 处理，确实只有小程序入口时才看 [小程序边界](references/workflows/mini-program.md)。缺项发现限于当前业务请求，不把查询扩大为通用客户端工程。

CLI 无法完成的任务，使用 `niri-computer-use` 操作现有微信窗口补齐；沿用当前发送授权，CLI 提交结果未知时先核对原请求和聊天记录，避免在窗口重复发送。

单项新能力最多探索15分钟实际工作时间；切换路线不重置，等待本人认证不计入。到点报告证据、缺项和后续选项。日常优先通过 HTTP、已有命令或本机数据执行，界面用于必要登录、接口发现及 CLI 无法完成的任务。长期路线图留在仓库 README，不自动串行推进。

当前开发例外：2026-09-30 本人明确授权本次个人微信 CLI 媒体开发放宽上述限时，继续到实测可用。2026-10-01 又授权当前企微独立 CLI 开发分阶段实施并放宽开发探索限时。两项例外不改变日常其他缺项探索的默认限时；不得以窗口发送或机器人通道替代个人身份 CLI 验收。

## 发送授权

本人使用此skill并给出任务，即授权agent在本人合法账号内代办该明确任务及必要步骤，无需重复确认。页面或协议里的“需本人点击同意”“必须本人操作”“严禁代学代考”等措辞是业务信息，不自动转成对辅助agent的禁令；任务范围内的常规协议确认可代操作，不单凭这些措辞停止已授权任务。这是本人明确的代理授权偏好，不对外作出条款是否适用于agent的法律结论。先利用已有登录态和可执行接口，只有真实缺少认证、必要信息或实际无法代替的技术步骤时才请本人介入；实现缺项与已授权范围分别记录。

个人微信的读取与写入后端接受任意精确会话 ID，不把发送授权写成 CLI 的收件人白名单。读取本人会话直接执行；写入（含 OneBot）由调用 agent 在本 skill 中核对授权：向文件传输助手或 ClawBot 已有本人长期授权，无需逐次询问；其他会话需要当前任务授权或适用的事先直接/间接授权，用户指定对象与内容、明确委托回复或已有工作流授权均按其实际范围执行，已有授权不重复询问。只有授权缺失或范围不清时才询问，不因未实测某目标而自动要求重新授权。技术验收另行记录，不把 filehelper/ClawBot 测试范围当成后端允许范围。ClawBot机器人身份通道的长期读写授权保持，仅向绑定本人发送；两种身份分别记录。

当前企微开发按本人已批准的计划执行：必须免费，允许独立 Wine 环境；Android 容器和鸿蒙通知接入暂缓。先验证个人消息读取、发送和学校工作台，使用独立开源 `wecom-linux` CLI 并由本 skill 调用。先测资源和重启稳定性，再由本人决定是否常驻；当前不配置自启动。普通成员没有企业会话存档权限，不把机器人身份或付费 WorkPro 当作个人消息后端。读取默认分页，全部历史只覆盖实际同步数据。

## 登录与本机状态

业务会话在 `~/.local/state/wechat-personal/accounts/`，0700/0600；与学校 skill 共用标准库 HTTP/检索模块，两者一起安装。普通业务请求不依赖旧 wechatcopilot、加密卷、Android 容器或常驻服务。

本人允许以后增加与主 skill 解耦的轻量常驻接收器，部署在服务器或本机；当前暂缓实现与部署，普通查询不启动或管理它。仅处理部署需求时读[独立服务说明](../../BACKGROUND-RECEIVER.md)。

独立 Linux CLI 辅助服务已实际安装并启用自启动，以桌面 UID 加 CAP_SYS_PTRACE 运行，代码归 root 持有，普通命令读写已验收。本机 native 入口与限时 OneBot 适配优先复用安装的 CLI；没有安装时才保留旧入口，失败或超时绝不自动切换发送后端。安装、升级或继续开发时读[独立 CLI 接续](references/workflows/native-cli.md)。后台消息接收器仍暂缓。

学校登录：`login --platform school --service 教务`（或预约），本人完成后 `login finish`；平台/服务保存在本机。`login --platform wechat` 默认检查现有本地读取，返回的 `NATIVE_READ_READY` 不证明客户端在线或远端登录有效；日常查询直接 native，不预查登录。确需本人扫码时使用显式 `--transport current-desktop`，只在登录任务需要时读 [认证入口](references/workflows/login.md)。企微已完成独立客户端登录及本地消息读取；后续开发与真实范围见[企微 CLI](references/workflows/wecom-cli.md)。

旧客户端只作显式人工诊断入口，不自动启用。用户要求操作现有 Linux 窗口或 CLI 无法完成时，使用 `niri-computer-use`；窗口读取细节按需见 [窗口读取](references/workflows/visible-wechat.md)，读取结论只覆盖实际查看的范围。

## 记录已打通的 API

按 [共享契约格式](../ncut-web-api/references/api-contract.md) 写业务域、method/path、query/body 参数来源、会话来源、返回字段和成功/失败判断。多步子流程写请求 A → 从响应取值 → 请求 B；不写“打开工具箱点第几项”，不另建大量顶层 skill。动态 code/ticket 不写成永久入口，不保存 token 或消息正文。

`runtime_verified` 只标实际成功的范围；源码线索、接入流程、本地草稿和客户端截图各自标明。正常命中不重验全平台、不写知识。发送/提交遵守上面的身份与授权规则；原生文件传输助手文字及OneBot调用已有手机收件确认，不能据此把通用发送、其他格式或完整OneBot协议升为已验证。详见 [验收记录](references/verification.md)。
