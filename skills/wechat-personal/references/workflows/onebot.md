# OneBot轻量尝试（2026-09-18）

本人明确要求普通微信好友/群聊收发优先；ClawBot只能作为补充，不是普通聊天验收的前置条件。

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
