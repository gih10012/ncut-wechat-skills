# Linux 微信本地消息：可复用读取

2026-09-19升级复查：本人已更新到`wechat-appimage 4.1.13-3`并登录，原密钥和命令继续有效，无需重新捕获。文件传输助手读取正常，新增可查询的`微信ClawBot`会话已读到双向历史及实际新发送回执；见[ClawBot历史](../capabilities/clawbot/read-history.md)。此成功不包含原生发送。

正常调用无需 sudo、浏览器或重新登录：

```bash
python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/wechat.py native conversations --account me --query '群名' --limit 5
python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/wechat.py native messages --account me --chat '上一步chat_id' --limit 20
```

此读取链已于2026-09-16在本人 Linux 客户端验证：16个数据库密钥全部匹配；真实会话列表195项；指定群近期文字、发送人、时间成功返回，并观察到合并6个有效 WAL 提交帧。一次有界消息查询约0.15秒（本机观测，不保证其他数据量）。覆盖本机已同步数据；发送和企微不在此验收范围。

## 首次准备与故障处理

依赖 Python 3.11+（SQLite deserialize）、`requirements-native.txt` 中的 pycryptodome，以及系统 libzstd。依赖已可用时直接执行，不重复安装。只做 HTTP/公众号读取无需这些可选依赖。

`native status --account me` 实际读取会话库，检查当前可用性；`native_keys.py status` 仅检查进程和密钥文件存在。只有首次无密钥，或数据库盐/HMAC证明确实失效时，才进行一次捕获：

```bash
sudo python3 /ABSOLUTE/PATH/TO/wechat-personal/scripts/native_keys.py capture --account me
```

脚本只打开归属原桌面用户的微信进程内存，只读 fd 建立后永久降回本人权限。默认最多读取256MiB、15秒，不改变 ptrace 全局设置、不暂停/注入进程、不重启客户端。候选密钥须通过数据库首页 HMAC；不保存内存转储。多账号时不猜账号。

密钥保存在 `~/.local/state/wechat-personal/native-keys/me.json`（0600，父目录0700），不进入仓库。成功输出仅数量和路径；capture 的 `native_messages_verified:false` 表示捕获动作没有查询消息，随后使用 native 命令验证。密钥不是服务端登录 token，不能直接用于发送。

## 读取链和一致性

`native_db.py` 对所需数据库及 WAL 做有上限的只读内存快照；读取前后大小、inode和纳秒修改时间须一致，最多尝试3次，持续变化返回 DATABASE_BUSY。每库总输入上限256MiB。验证 WAL 代次、累计校验和和提交边界，只合并最新已提交页；忽略旧代次尾部和未提交事务，损坏的当前帧报错。逐个非零页 HMAC 校验后解密，在内存 SQLite 中 query_only 查询；不写明文副本或聊天索引，不持有客户端写锁。联系人、会话、消息库分别取快照，不承诺跨库原子性。

`native_messages.py` 仅处理已观察的 schema。默认最多10条、最高50条，单条正文有界；消息以客户端已同步记录为准。压缩正文不能处理时逐条标 decode_error；媒体仅标类型。没有实时推送或云端完整历史保证。

格式依据：[SQLCipher 设计](https://www.zetetic.net/sqlcipher/design/)、[SQLite WAL 格式和读算法](https://www.sqlite.org/fileformat2.html#walformat)，候选密钥形态参考 [WCDB raw-key 观察](https://github.com/328336690/wechat-decrypt)。兼容性以本机 HMAC、实际 schema 和消息查询验证为准。
