# OneBot接入与已验证范围

本人明确要求普通微信好友/群聊收发优先；ClawBot只能作为补充，不是普通聊天验收的前置条件。

2026-09-21当前结论：Linux原生后端已将一次固定文字发送到文件传输助手，本人确认手机收到；这是后端首次个人身份投递证据，尚未经过OneBot。参数化原生发送、限时OneBot适配、其他收件人及媒体均待分别实测，不把此结果或下文ClawBot桥验收当成完整原生OneBot收发成功。`python3 "$WX" native send-status`可读取已有固定试验结果；正文和具体任务号仅私存。Linux历史未找到该条，当前本地回写未接入，不能据此重发。实现、状态命令与验收见[原生发送流程](native-send-port.md)。

个人微信身份向文件传输助手或ClawBot发送已有长期授权，不逐次询问；其他对象需本人明确口头授权或适用的事先授权，具体发送请求即为该范围授权。ClawBot机器人身份读写的长期授权保持。当前常驻服务仍暂缓，不因接入OneBot启动后台服务。下文为各轮历史证据，旧的未接通结论仅对应当时路线与范围。

## 限时原生文字入口

`scripts/native_onebot.py`已随skill安装，提供OneBot12 HTTP动作子集：`get_supported_actions`、`get_version`、`send_message`。当前只启用个人身份向filehelper发文字；没有事件接口和媒体动作，不是完整OneBot实现。标准HTTP及动作格式依据[HTTP通信](https://12.onebot.dev/connect/communication/http/)、[动作请求](https://12.onebot.dev/connect/data-protocol/action-request/)和[发送消息](https://12.onebot.dev/interface/message/actions/)。模拟后端的真实回环HTTP测试已通过，本人微信的OneBot调用尚待实测。

显式启动一次临时入口：

```bash
sudo python3 ~/.codex/skills/wechat-personal/scripts/native_onebot.py serve --duration 600 --max-sends 3
```

入口只监听127.0.0.1随机端口，600秒到期退出，最多接受3次新发送请求；Ctrl+C可结束。仅使用Python标准库与现有原生后端，不注册开机服务。端口及随机Bearer保存在本人`~/.local/state/ncut-wechat-skills/native-onebot-session.json`（0600），不要输出token。启动需要本机sudo权限，已有发送授权不需再次确认。

普通桌面账号通过stdin提交动作，`call`读取私有入口、禁用代理和重定向：

```bash
python3 ~/.codex/skills/wechat-personal/scripts/native_onebot.py call <<'JSON'
{"action":"send_message","params":{"detail_type":"private","user_id":"filehelper","message":[{"type":"text","data":{"text":"OneBot 原生文字测试"}}],"wechat.request_id":"replace-with-unique-ascii-id"},"echo":"optional-correlation"}
JSON
```

将`wechat.request_id`替换为4–80字符ASCII请求ID；`echo`只关联响应，不能代替防重ID。同ID同内容返回原结果；不同内容拒绝。成功响应的`message_id=wechat-local:<request-id>`是本地操作ID，`wechat.id_kind=local_request`明确其语义，微信客户端任务号另列`wechat.native_task_id`。成功仅表示原生往返验证、一次零错误回调及清理通过；`wechat.recipient_delivery_verified`单独记录接收端证据。

超时或回调不确定时禁止本会话继续发送，保留后端PID、request-id和结果路径，不自动重试、不强杀未完成GDB。通过`native send-status --request-id`和实际进程状态检查同一任务；状态文件写有`pending_backend`时下次启动拒绝覆盖，先核对该任务实际完成及客户端恢复情况，再处理旧会话记录。客户端仍会保留小型回调模块直到退出，不增加常驻接收服务。

## 普通微信候选核对

- [JustUndertaker/ComWeChatBotClient](https://github.com/JustUndertaker/ComWeChatBotClient)提供OneBot12，但项目已归档，明确支持Windows微信3.7.0.30；不匹配当前Linux4.1.1。
- [wx-11/MimicWX-Linux](https://github.com/wx-11/MimicWX-Linux)依赖Docker虚拟桌面、AT-SPI和键鼠输入；[smrwang/wechat-onebot-virtual-gateway](https://github.com/smrwang/wechat-onebot-virtual-gateway)也通过虚拟桌面UI发送，入站仍是受限的私聊Copy实验。这两条均不符合本轮轻量、日常业务不依赖UI的约束，未部署。
- [jessiongod/wechat-onebot-bridge](https://github.com/jessiongod/wechat-onebot-bridge)依赖Windows WeFlow及UIA发送，未部署。

这些核对没有证明普通好友/群聊的OneBot收发成功；Linux已有本地读取继续走native命令。

## 扩展协议及后端核对

按本人追加要求，继续检查OneBot11、OneBot12、Satori及多协议网关。以下是公开源码/部署说明核对，均不是本人账号运行验收。

| 项目 | 实际后端与本机适用性 |
| --- | --- |
| [lc-cn/onebots](https://github.com/lc-cn/onebots) | 提供OneBot11/12、Satori、Milky等出口，但微信适配分别是公众号和ClawBot；企微是自建应用、微信客服。多协议出口不增加普通聊天权限 |
| [satorijs/satori](https://github.com/satorijs/satori/blob/main/adapters/wecom/src/bot.ts) | 企微源码使用CorpID、Secret、AgentID和官方应用API；微信适配为公众号，未发现个人收件箱后端 |
| [alingalingling/Akasha-WeChat](https://github.com/alingalingling/Akasha-WeChat) | OneBot11；Windows WeFlow读取、UIA发送，不适用当前Linux环境 |
| [CMKH1337/Astrwechat](https://github.com/CMKH1337/Astrwechat) | OneBot11；Windows本地数据库/SSE读取及UIA发送，还含Electron桌面程序 |
| [Clov614/rikka-bot-wechat](https://github.com/Clov614/rikka-bot-wechat/blob/main/docs/onebot/README.md) | OneBot12；文档明确当前hook客户端不再支持Linux，实际adapter导入wcf-rpc-sdk；不能因历史openwechat标题判断当前Linux可用 |
| [WeChatPadPro/WeChatPadPro](https://github.com/WeChatPadPro/WeChatPadPro) | 普通微信Pad协议候选；公开仓库主要是部署和说明，发布包另取。README要求至少2GB内存并配置MySQL、Redis，未部署为本轮轻服务 |

企微Android/iPad候选的具体缺项见[企微消息](../capabilities/wecom/messages.md)。没有把“框架可在Linux运行”当成“其微信/企微后端可在Linux运行”；尚未找到同时满足当前环境、普通消息范围和轻量约束的新增可执行后端。

## QQ设备协议思路的适用性

本人进一步要求参照QQ手表端后端。已核对[MiraiGo设备类型](https://github.com/Mrs4s/MiraiGo/blob/master/client/internal/auth/device.go)与[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)：其OneBot接口之下还有QQ设备协议库，实现登录、会话和消息通信。可复用的设计是“独立设备协议后端→标准事件/API”，微信和企微仍需各自后端，不能直接改QQ设备类型获得微信登录。

- 普通微信的同类候选是Pad协议。除上述WeChatPadPro，[wechaty/puppet-padlocal](https://github.com/wechaty/puppet-padlocal)依赖PadLocal客户端及服务token；未取得token、未验证当前服务可申请或可用。[meteor-nb/Ipad860](https://github.com/meteor-nb/Ipad860)公开说明仍依赖来源未公开的`v08.dll`和Redis，不能因有Go源码就认定可直接在本机Linux运行。
- [AstrBot当前个人微信适配说明](https://github.com/AstrBotDevs/AstrBot/blob/master/docs/zh/platform/weixin_oc.md)明确使用`openclaw-weixin`、要求手机ClawBot插件；[客户端](https://github.com/AstrBotDevs/AstrBot/blob/master/astrbot/core/platform/sources/weixin_oc/weixin_oc_client.py)使用`ilink_bot_token`。它不是普通好友/群聊的Pad协议后端。
- 企微完整聊天尚未找到满足当前约束的公开可执行设备协议后端；普通成员也无会话存档权限。先前[Android通知转存](android-notifications.md)补充已因本人手机更正为原生鸿蒙而暂缓，不能将补充结果计为完整聊天成功。

## 已安装的补充测试

选用 [Foxerine/ilink-onebot](https://github.com/Foxerine/ilink-onebot/tree/290536f5bdae4075c9fa80d25b7ba2cea4c19d7e)，固定源码版本 `290536f5bdae4075c9fa80d25b7ba2cea4c19d7e`。其底层是ClawBot iLink，仅覆盖本人和机器人的会话，没有普通好友列表或群聊读取。

源代码及独立Python环境安装在本机 `~/.local/share/ncut-wechat-skills/ilink-onebot-trial/`，私人试验脚本/数据库/日志在 `~/.local/state/ncut-wechat-skills/onebot-trial/`。这些不是公共skill的生产依赖，也不在开机时启动。

安装实际遇到hatchling构建依赖下载超时；改为 `uv sync --no-dev --no-install-project`，从已审阅源码运行，55个运行依赖安装成功。试验只启动上游的OneBot WebSocket服务与有界轮询，没有启动媒体服务、完整机器人平台或自动扫码。只监听127.0.0.1并启用随机Bearer认证，独占原skill的账号锁、同步原游标，避免多个消费者争抢。

发送仅允许已绑定本人的ID、指定测试文字的一条回执；发送HTTP关闭自动重试，失败不会再发。收到真实指定测试文字之前不发送。私有凭证与context_token不输出或发布。

已实测：OneBot `get_version_info`、`get_status`、`get_login_info`通过；真实iLink轮询成功返回空增量批次。首次本机WebSocket连接受默认代理影响，显式 `proxy=None` 后连通。临时进程常驻内存约127MiB。空批次和元信息接口不代表消息收发验收成功，最终状态以同日验收记录为准。

## 本轮原生发送追加核对

[yincongcyincong/wechat_chatter](https://github.com/yincongcyincong/wechat_chatter/blob/main/onebot/readme.md)有OneBot文字/图片发送，但依赖macOS微信与Frida Gadget；[wechat-mac-hook-classic](https://github.com/xiaoguiwucan/wechat-mac-hook-classic)要求Apple Silicon/macOS及指定4.1.11.53构建。两者均不能直接用于当前Linux4.1.1。[wechat-shot-bridge](https://github.com/zhusinian/wechat-shot-bridge)确有Linux4.1.1.4进程内入口，但实现仅调用截图界面，没有消息发送后端；未部署或套用其偏移发送。

本轮已获准的验收是个人微信给文件传输助手发图片、给ClawBot发文字并由机器人接口检查入站。本机已准确定位filehelper，但会话查询没有找到ClawBot；发送后端尚未接通，两次个人身份发送均未执行。独立ClawBot机器人→本人文字已通过真实发送及本人收件确认，详见[发送契约](../capabilities/clawbot/send-text.md)，不能算普通OneBot完成。

## Linux客户端版本核对（2026-09-18）

本机包为`wechat-appimage 4.1.1-1`，desktop元数据为4.1.1；直接读取[Linux微信官网](https://linux.weixin.qq.com/)的当前HTML得到4.1.13，官方AppImage链接也正常响应。因此本机确实落后于官方发布，但官网未提供ClawBot支持说明，本轮未升级、未验证新版会话入口或原生发送后端。[腾讯仓库issue #167](https://github.com/Tencent/openclaw-weixin/issues/167)有其他用户报告跨设备ClawBot会话不显示，但它是用户报告、且涉及Mac，不能作为Linux新版必然支持或不支持的结论。

`ilink-onebot`已存在ClawBot适配；其send_private_msg仍以机器人身份发给绑定用户，get_friend_list/群聊动作不支持，不能用来从本人原生微信向ClawBot或filehelper发消息。

## 2026-09-19升级后的真实补充验收

本人将Linux微信更新至`wechat-appimage 4.1.13-3`并登录后，原native密钥继续有效，已定位`微信ClawBot`会话并读取双向历史。没有重捕密钥、重绑机器人或接管桌面。

复用前述固定版本ilink-onebot，临时启动仅监听127.0.0.1且带随机Bearer的WebSocket桥：第一轮真实iLink轮询收到本人升级后发送的文字，转换为OneBot消息事件；经真实WebSocket调用`send_private_msg`给绑定本人发送一条固定回执，返回retcode=0。随后从当前Linux客户端的ClawBot历史读到同文新回执，发送人确为该机器人，完成机器人通道的OneBot入站、发送与独立本地读回。

试验独占同一账号锁并同步游标，保留本人回复上下文；禁用发送自动重试。发送前已有尝试标记，后续不得直接重跑。临时进程已退出、16791端口关闭。试验没有创建常驻服务，也没有把额外桥接依赖加入主skill的日常调用链。新会话日常收发继续使用bot命令；历史/读回用native命令，无需旧试验脚本。

普通微信身份发送仍未接通：新版未观察到微信进程的TCP发送监听，D-Bus没有可调用的消息方法。二进制新增观察到`message::send_text_message`、`message::send_message`等内部字符串和抽象Unix IPC，但尚未取得外部调用、参数及认证契约，不能据字符串执行发送或把它写成可用API。本轮没有向filehelper发送图片，也没有代本人向ClawBot发送文字；真实入站来自本人升级后自己发送的消息。

另核对[lichaohuai/wechat-protocol-gateway](https://github.com/lichaohuai/wechat-protocol-gateway)：仓库明确只有接口调用示例，不提供后端代码、服务地址或凭证，不能直接部署验证。未因此注册第三方、联系他人或扩大企微支线。

## 2026-09-19按NapCat同类后端复核

本人要求优先寻找像[NapCatQQ](https://github.com/NapNeko/NapCatQQ)这样的实际协议端。筛选对象是能以本人身份给普通好友/群聊收发的后端，而不是只声明支持OneBot的上层平台。下面仍为公开源码/部署证据，不是本人账号登录与发送成功。

- [aixed/WeChat-Hook](https://github.com/aixed/WeChat-Hook)：确有客户端Hook DLL、HTTP文本/图片/XML发送接口及相关源码；当前README目标为Windows x64微信4.1.10.27，需加载version.dll。结构上是同类，但不适配现有Linux4.1.13；未改动客户端或运行DLL。
- [jwping/wxbot](https://github.com/jwping/wxbot)：明确包含好友/群聊文本、图片和文件API；其Linux部署依赖Docker/Wine和Windows微信，免注入版本说明为3.9.8.25，不是原生Linux微信后端，未部署。
- [ThePeppy/wechat-api-ipad](https://github.com/ThePeppy/wechat-api-ipad/tree/08c98614add19653388d76d821e84c7d6aa620d3)：有Go协议和newsendmsg组包源码，最后提交为2024-01-25；README列MySQL/Redis依赖，实际main.go强制初始化并Ping Redis，配置ServerName仍为7.0.12。未验证当前协议登录/收发或内存，不因源码公开就称可用。
- [openwechat](https://github.com/eatmoreapple/openwechat)：纯Go SDK，go.mod未列外部依赖，具有好友/群聊和文件/图片发送方法；实际走webwx接口，不是现有Linux客户端Hook。普通网页模式需要本人账号真实登录资格，尚未测试，不能把生成二维码当作收发成功。本人离开时不生成短期二维码或替换已有桌面会话。
- [WeChatPadPro](https://github.com/WeChatPadPro/WeChatPadPro/releases/tag/v2.01)：公开Linux amd64发行包v2.01为2025-08-22的861版本，README中的较新868指向赞助群；协议核心未在公开源码树中找到。[官方compose](https://github.com/WeChatPadPro/WeChatPadPro/blob/main/deploy/docker-compose.yml)同时启动MySQL8、Redis6及协议服务，README标最低2GB内存。文档中的ADMIN_KEY可在本地生成AuthKey，不能仅因有key就断言必须购买远程授权。包下载只取得部分数据，Range请求返回501，未完成包内配置/远程授权核验，未运行。上述依赖是官方部署要求，不是实测的最小运行要求。
- [Gewechat](https://github.com/Devo919/Gewechat)官方已声明停止服务、镜像及部署支持，公开树不含完整后端；旧调用SDK不能使其恢复。[GeWe API](https://doc.geweapi.com/doc-3146201)是另一条托管服务路线，供应商文档提供7天试用、Token、扫码节点和Webhook；还未取得本人试用账号，价格、当前登录及稳定性未验，不代注册或转交已有微信登录态。
- [WeChatFerry](https://github.com/lich0821/WeChatFerry)于2026-07-10归档，公开版本配套Windows微信3.9.12.51；Linux RPC客户端并不包含Linux微信发送后端。

本机Linux内部入口也已做有限静态复核：抽象Unix IPC观察到TOKEN/OPEN/CMD:show解析，没有定位到消息调用分发；FunctionCallManager相关内部发送注册没有对应动态导出或当前TCP监听。尚无外部调用契约，不在这些线索上扩展未验证注入工程。版本、哈希与定位证据仅私存；保持已有登录。

本轮有限探索结束，普通微信发送保持未接通。本人在线后已完成下节普通Web扫码实测，该路线当前被服务端拒绝。Windows Hook需要匹配的Windows微信环境，PadPro需要接受其依赖，GeWe需要本人选择供应商并取得试用凭证；这些条件变化后再继续对应路线，不重复枚举仓库，不提前部署常驻。候选选择遵循当前环境、轻量约束，不是对其可用性的保证。

## 2026-09-20普通Web扫码实测

本人在线配合后，按[openwechat源码](https://github.com/eatmoreapple/openwechat/tree/635e5561f3196cb6740f3ffcd36006fa84b61019)的普通Web登录链进行有界实测。本机无Go运行时，实际运行的是临时Python标准库探针，不是Go SDK。未使用Desktop模式、额外设备标识头或现有Linux客户端凭证。

两轮均取得真实二维码并收到扫码确认。第一轮响应解析异常，检查发现探针自动跟随跳转，与上游DefaultClient行为不一致；修正后第二轮保留原始响应。本人报告手机显示已登录网页版，但最终webwxnewloginpage返回HTTP200、text/html，正文明确提示暂不支持使用网页版微信。按响应实际编码解读后确认该拒绝；没有凭此手机提示把认证标为成功。

结果：普通网页登录当前不可用；未得到有效webwxinit会话，未执行已授权的filehelper文字/图片发送。临时探针已结束，私有材料只留本机，不纳入主skill运行依赖。明确拒绝后结束该路线；下次直接读取本子能力结论，不要求本人重复扫码。其他后端仍需单独实测。

## 2026-09-20 Linux PadPro真实启动及Hook移植

本人选择继续Linux并允许改造第三方项目后，完整取得官方v2.01 Linux861发行ZIP并校验目录。使用本机已有MariaDB12.3、Redis和发行二进制，在独立临时目录和隔离环境启动；没有使用本人的既有数据库、Redis、微信会话或开机服务。未使用原README要求的MySQL8镜像，实际兼容范围只到以下本地API。

实测数据库初始化与API监听成功；空账号启动时MariaDB、Redis、主服务合计RSS约172–179MiB，不能据此保证登录后的资源占用或稳定性。发行包内Swagger的`POST /admin/GenAuthKey1`可调用，但禁网及允许联网两次均最终返回Code300“授权服务暂时不可用”；未生成AuthKey、二维码或微信会话，未执行发送。二进制包含`AdminKeyServiceClient`及外部`adminkeyservice.knowhub.cloud`依赖，本机DNS解析成功。因此本地ADMIN_KEY配置不等于完全离线授权，也不能仅凭此失败断言必须付费。

运行时还发现该包未按HOST=127.0.0.1限制监听，API端口和固定MCP端口8098监听所有地址；停止试验后所有对应端口已关闭。再次试验必须使用网络隔离及明确的回环端口映射，不能只信任HOST配置。未部署常驻。

并行源码审查进一步定位了当前Linux的MMStartTask候选和Task拷贝函数。移植准备、实际观测工具及必须本人完成的系统权限步骤已沉淀为[原生发送移植子流程](native-send-port.md)。当时仅合成进程自测通过；此后真实提交与2026-09-21手机收件确认已补齐filehelper固定文字验收，OneBot和其他发送范围仍未通过。
