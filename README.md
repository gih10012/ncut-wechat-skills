# NCUT / WeChat API Skills

面向 Codex 的两套轻量 skill：北方工业大学 Web/API，以及本人微信、企业微信与公众号信息。参考 EaseCation web-api 的工作方式：**检索已验证能力 → 直接调用；缺项 → 局部探索 → 实测 → 沉淀子能力**。新会话只需读取 skill，不依赖项目作者的聊天历史。

## 安装

```bash
git clone https://github.com/gih10012/ncut-wechat-skills.git ~/Github/ncut-wechat-skills
cd ~/Github/ncut-wechat-skills
python3 scripts/install.py
```

安装器将两套 skill 链接到 `~/.codex/skills/`，已有普通目录先备份。普通 HTTP 查询只需 Python 标准库；学校首次交互登录另需本机 Chrome 和 Node。登录态、验证码、私人结果均留在 `~/.local/state/`，不进入仓库。没有加密卷、容器或常驻爬虫依赖。

## 使用

对 Codex 直接说“查本周课表”“找今晚的空教室”“查羽毛球预约规则”，或给出一个新业务目标。没有现成子能力时，skill 应自行从服务注册表、目录、页面/客户端和已观察的请求继续探索，而非要求用户先提供 API。

- [学校 skill](skills/ncut-web-api/SKILL.md)：课表、成绩、空教室、预约日历和规则已真实调用验证。
- [微信／企微 skill](skills/wechat-personal/SKILL.md)：普通独立CLI已验证两端本人身份的会话/同步消息读取、文字、PNG/JPEG、中文文件名TXT/ZIP、动画GIF、公众号/小程序转发及自定义XML发送。个人微信另支持朋友圈动态/指定人完整缓存读取、分页与全部已加载历史；协议链接解析及精确HTTP等价页面的临时只读中继已在Chrome/Edge实测。各项格式、接收端、资源完整性与历史范围分别记录，不从一种格式或会话推定全部通过。
- ClawBot经iLink独立文字/文件/图片收发及语音下载已验证；明确`-2`拒绝时已配置个人微信CLI自动刷新、精确新入站核对后补发一次。普通发送不要求桌面微信在线，只有刷新需要主号在线；未知结果不自动重发。手机端不支持自定义表情。详见[自动恢复](skills/wechat-personal/references/capabilities/clawbot/recover-context.md)。
- 个人微信普通CLI私聊发起/接听/连接状态/接通后播放指定WAV/挂断及防重已实测；群成员选择与取消已实测，群邀请/挂断/接通/播音与企微CLI呼叫控制仍待验收。CLI无法完成的任务按既有授权用computer-use，先核对未知提交，避免重复操作。
- 子能力存放在 `references/capabilities/`；必要的多请求编排存放在 `references/workflows/`。它们是可检索的子 skill，不为每个 endpoint 新建顶层 skill。

## 版本与验收

| 阶段 | 验收目标 | 当前状态 |
| --- | --- | --- |
| v0 | Web 能力直接调用、缺项发现、真实验证、最小契约沉淀与再次复用 | 成绩发现与二次调用已实测，正常复用不改知识；9月19日独立上下文完成课表、成绩、重复查询、空教室及企微状态五题验收；范围见ACCEPTANCE.md |
| v1.a | 核实并尝试 Qclaw／微信官方机器人通道 | 已采用第三方 wechatbot-sdk 0.3.0，真实扫码绑定并读取本人测试文字；仅ClawBot通道；9月18日真实发送文字且本人确认收到 |
| v1.b | 本人微信/企微独立CLI与MCP入口 | 微信一次特权安装后的普通CLI原生发送、本地入库/UI及各格式分别验收；企微独立Wine CLI读取、原生发送和三次正常重启后新文字收件已验证。ClawBot独立收发、自动恢复与MCP防重通过；新CLI的OneBot入口仅旧请求重放验收，事件及新发送链路仍待分别验证 |
| 通话与协议网页 | 复用正常客户端并明确验收边界 | 个人私聊CLI控制和双向生成音频有独立证据；群选择/取消已实测，其余通话控制仍待验收。只读HTTP中继可用，通用小程序票据、客户端OAuth/JS SDK和完整资源兼容尚未验证 |
| 后续业务 | 具体微信链接、企微业务与学校 Web 等价入口 | 学校目录配对及部分身份/入口已验证；深链、完整企微清单、业务等价性和OAuth按实际需求接入 |

不把 HTTP 200、离线测试、UI 截图或已写文档当作真实业务成功；每个能力记录自己的验证范围。真实订场按本人明确或事先授权执行。个人微信身份向文件传输助手或ClawBot发送已有长期授权；其他对象需本人明确口头或事先授权，指定对象与内容的发送请求即为该范围授权。ClawBot机器人身份读写的长期授权保持。学校夜间失败须区分网络、认证、权限和业务开放时间。

v0 示例：[服务收藏](skills/ncut-web-api/references/capabilities/hall/service-favorite.md)、[写入预请求与读回](skills/ncut-web-api/references/workflows/web-write.md)。`favorite verify` 真实改变本人收藏并恢复，必须在获准验证时使用 `--allow-write`；不会订场或提交申请。

读取路径：[现有 Linux 微信的一次性密钥读取](skills/wechat-personal/references/workflows/native-linux.md)。首次只读本人微信进程，匹配数据库HMAC后私存密钥；不重登录或改全局ptrace设置。后续`native conversations/messages`直接复用，普通读取无需sudo，仅覆盖已同步数据。原生发送已使用客户端真实消息创建/入库流程，普通CLI日常无需sudo，调用与防重见[通用发送契约](skills/wechat-personal/references/capabilities/wechat/send-message.md)。本地读回、UI显示和对端收件分别核对，未知结果不能换ID重发。原生读取需Python 3.11+、pycryptodome和系统libzstd。

个人微信优先已安装独立CLI；企微采用免费官方客户端的独立Wine环境和[开源CLI](https://github.com/gih10012/wecom-linux-cli)，日常读取/发送复用私有密钥与请求记录，无需sudo。不需要Windows主机常驻，尚未启用企微自启动；冷启动通话和长期稳定性未验收。付费WorkPro不作为当前方案。新能力先查已有契约和相关GitHub实现，缺项才核对真实接口。日常探索累计上限15分钟，等待本人认证不计入；已授权的个人媒体和企微开发例外保留。正常UI控制、原生API和对端验收分别记录。

ClawBot安装、登录与有界读取见 [第三方SDK入口](skills/wechat-personal/references/workflows/clawbot.md)；按需启动的stdio MCP见 [MCP入口](skills/wechat-personal/references/workflows/mcp.md)。机器人通道不会自动取得本人其他聊天；个人微信读取继续复用已登录的Linux客户端，不另开设备会话。

此前准备的[Android企微通知转存](skills/wechat-personal/references/workflows/android-notifications.md)已暂缓：手机实际为原生鸿蒙，不再要求安装SmsForwarder。本机通知归档不代表真实手机投递；OpenHarmony手机接入留待后续。当前企微原生聊天读取使用独立CLI，不依赖手机转发。

本人也允许后续部署一个与主 skill 解耦的轻量后台接收服务，可放在常开服务器或本机；独立说明见 [BACKGROUND-RECEIVER.md](BACKGROUND-RECEIVER.md)。常驻实现与部署暂缓，普通使用与安装 skill 不自动启动服务。

最新追加的独立 Linux CLI 辅助服务已获一次安装、自启动及日常普通命令的授权；它与暂缓的后台接收器分别处理。[开源 CLI](https://github.com/gih10012/wechat-linux-cli)已作为开发预览发布，独立安装包真实读取及临时 Unix 服务检查通过；特权系统服务已部署并启用自启动，普通CLI文字、PNG/JPEG和中文文件名TXT/ZIP发送及Linux本地显示已分别验收，公众号/小程序转发与自定义XML的服务器回包/Linux卡片显示、本人手机单次显示与点击亦通过；原生动画GIF在文件传输助手也有本人手机确认，其他格式各自验收。接续见[独立 CLI](skills/wechat-personal/references/workflows/native-cli.md)。

## v0 验收交接

- 新增 [成绩查询契约](skills/ncut-web-api/references/capabilities/jwxtbk/personal-grades.md)：现有菜单/表单发现 → 真实只读 POST → 解析学期及课程成绩 → 再次直接调用。发现到真实验证约13分钟；二次调用结果一致，知识文件未改变。
- 修正未接通能力的检索后续指引、微信平台与读取能力状态、学校 HTTP 200 登录失效页与已知登录跳转识别。已有课表和跨两组节次的空教室查询已实测复核。
- 本机命令与相关自动测试已验证；9月19日按本人并行授权，由独立上下文代理完成 [新对话验收问题](ACCEPTANCE.md) 中五项只读执行/分流。另发现并修正ClawBot复合提问的分项检索指引，独立复核通过。此结果不代表全部业务或未接通消息后端已通过。

## 开发

```bash
python3 -m pip install -r skills/wechat-personal/requirements-native.txt
python3 -m unittest discover -s skills/ncut-web-api/tests
python3 -m unittest discover -s skills/wechat-personal/tests
node --test skills/ncut-web-api/tests/test_browser_session.mjs
```

仅提交代码、公共接口契约和去隐私示例。修改后做相关验证并及时 commit/push；正常 API 命中不改知识库。见 [AGENTS.md](AGENTS.md)。MIT License。
