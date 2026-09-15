# 现有 Linux 微信：一次性密钥读取路径

目的：尝试复用本人现有客户端，避免重新登录或占用桌面。不适用于企微，也未验证消息发送。此路径当前是待本人实测的准备工具，不能标为消息已接通。

`python3 scripts/native_keys.py status` 仅检查本人进程和私有密钥文件是否存在，不证明已登录或密钥有效。

需要本机授权时，先让用户审阅 capture 脚本，再由本人在终端执行：

```bash
sudo python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_keys.py capture --account me
```

脚本只打开归属原桌面用户的微信进程内存，只读 fd 建立后即永久降回本人权限。默认最多读取256MiB、15秒，不改变 ptrace 全局设置、不暂停/注入进程、不重启客户端。只匹配 WCDB 原始密钥候选，并用对应数据库首页 HMAC 验证；不保存进程内存或聊天正文。仅匹配一个本机账号目录；多账号时先明确当前目标，不猜账号。

结果保存到 `~/.local/state/wechat-personal/native-keys/me.json`（0600，父目录0700），命令只输出数量和路径。零匹配时保留原文件；格式和 Linux 当前版本兼容性仍须实际验证。密钥并非微信通用登录 token，不能拿它直接调用服务端发消息。

格式依据：[SQLCipher 官方设计](https://www.zetetic.net/sqlcipher/design/)及[Windows WCDB raw-key 格式观察](https://github.com/328336690/wechat-decrypt)。Windows 格式观察仅支持候选格式；本工具用本人的真实数据库 HMAC 确认，不能据此宣称 Linux 已验证。

密钥捕获成功后，按最小必要范围读取会话库/联系人库的实际 schema，再接入限定会话和条数的消息读取。WAL 中可能有最新消息，读取链必须处理一致性，不能用旧数据库快照冒充实时消息。发送另需经过实际客户端/接口验收。
