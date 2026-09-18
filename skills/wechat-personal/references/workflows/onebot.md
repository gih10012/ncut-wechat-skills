# OneBot轻量尝试（2026-09-18）

目标仍区分普通微信好友/群聊与ClawBot通道，不能用后者证明前者已接通。

## 普通微信候选核对

- [JustUndertaker/ComWeChatBotClient](https://github.com/JustUndertaker/ComWeChatBotClient)提供OneBot12，但项目已归档，明确支持Windows微信3.7.0.30；不匹配当前Linux4.1.1。
- [wx-11/MimicWX-Linux](https://github.com/wx-11/MimicWX-Linux)依赖Docker虚拟桌面、AT-SPI和键鼠输入；[smrwang/wechat-onebot-virtual-gateway](https://github.com/smrwang/wechat-onebot-virtual-gateway)也通过虚拟桌面UI发送，入站仍是受限的私聊Copy实验。这两条均不符合本轮轻量、日常业务不依赖UI的约束，未部署。
- [jessiongod/wechat-onebot-bridge](https://github.com/jessiongod/wechat-onebot-bridge)依赖Windows WeFlow及UIA发送，未部署。

这些核对没有证明普通好友/群聊的OneBot收发成功；Linux已有本地读取继续走native命令。

## 已安装的补充测试

选用 [Foxerine/ilink-onebot](https://github.com/Foxerine/ilink-onebot/tree/290536f5bdae4075c9fa80d25b7ba2cea4c19d7e)，固定源码版本 `290536f5bdae4075c9fa80d25b7ba2cea4c19d7e`。其底层是ClawBot iLink，仅覆盖本人和机器人的会话，没有普通好友列表或群聊读取。

源代码及独立Python环境安装在本机 `~/.local/share/ncut-wechat-skills/ilink-onebot-trial/`，私人试验脚本/数据库/日志在 `~/.local/state/ncut-wechat-skills/onebot-trial/`。这些不是公共skill的生产依赖，也不在开机时启动。

安装实际遇到hatchling构建依赖下载超时；改为 `uv sync --no-dev --no-install-project`，从已审阅源码运行，55个运行依赖安装成功。试验只启动上游的OneBot WebSocket服务与有界轮询，没有启动媒体服务、完整机器人平台或自动扫码。只监听127.0.0.1并启用随机Bearer认证，独占原skill的账号锁、同步原游标，避免多个消费者争抢。

发送仅允许已绑定本人的ID、指定测试文字的一条回执；发送HTTP关闭自动重试，失败不会再发。收到真实指定测试文字之前不发送。私有凭证与context_token不输出或发布。

已实测：OneBot `get_version_info`、`get_status`、`get_login_info`通过；真实iLink轮询成功返回空增量批次。首次本机WebSocket连接受默认代理影响，显式 `proxy=None` 后连通。临时进程常驻内存约127MiB。空批次和元信息接口不代表消息收发验收成功，最终状态以同日验收记录为准。
