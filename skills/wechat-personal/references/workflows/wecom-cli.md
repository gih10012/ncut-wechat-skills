# 本人企业微信：免费独立 CLI

当前开发按本人 2026-10-01 批准的计划执行：独立开源 [wecom-linux-cli](https://github.com/gih10012/wecom-linux-cli)，由现有 skill 复用。只考虑免费路线，允许独立 Wine；Android 容器与鸿蒙通知接入暂缓。普通成员没有企业会话存档权限，官方机器人 `wecom-cli` 身份也不覆盖本人个人聊天，不使用它替代验收。

## 当前真实范围

已在本机安装 Wine 11.18 和官方下载的企业微信 5.0.11.6018，采用本人所有、0700 的独立 prefix，保留原 Windows 安装及资料。2026-10-01本人认证已完成，主界面显示学校会话。普通用户CLI已验证真实私聊/群聊、默认20条分页、无重复续页及指定会话全部已同步历史；完整中文、换行、emoji通过新GUI消息的独立CLI读回核对。消息、会话、联系人库及WAL通过校验和与SQLite完整性检查。媒体原始字段/引用完整保留；外部微信type101 PNG与企微原生type14 PNG/JPEG完整缓存原图已通过输入/导出字节一致及两端UI验收，按[原图导出契约](../capabilities/wecom/media-export.md)调用，不主动下载未缓存媒体。普通已安装 CLI 本人身份文字向授权的微信对应会话真实发送通过：两个独立读取端和两边窗口分别核对完整正文、单次收件、服务器ID；同ID重放不重发、正文冲突拒绝。双向文字收发已验收，手机确认先前的原生文件传输助手候选正常。三次正常托盘退出/重启均恢复配置账号、复用密钥及旧请求；各新进程原生构造预检通过，第三次之后新文字经接收端独立确认一条，关屏且未选中聊天亦可发送。两次计时约3.6秒达到原生预检，属于客户端重启、非整个Wine冷启动。5秒资源采样约4.4–5.6GiB PSS，空闲单核CPU约9–18%，一次发送窗口约20%；不是长期边界。2026-10-02普通原生CLI PNG与中文文件名JPEG各独立送达授权微信会话一条，两端窗口显示、缓存原图与输入一致、重放不重复及冲突拒绝通过；图片/文字构造预检未新增消息，51项CLI测试通过。文件/表情/卡片发送、未缓存媒体下载、学校工作台、离线缺口与长期稳定性仍待验收，尚不配置常驻。

日常入口是 `wecom-linux`；本skill的`wecom`子命令仅调用已安装CLI一次，不切换身份或后端。缺少密钥时才捕获，不在每次正常读取前扫描进程。已配置的`me`绑定精确账号数据目录；不自动选择最大的数据库。详细本机路径、登录结果、私有日志和接续状态只保存于本机私有状态，不写入公共仓库。

```sh
wecom-linux status
wecom-linux client start
wecom-linux keys capture --database '/私有prefix/drive_c/实际数据库.db'
wecom-linux db inspect --database '/私有prefix/drive_c/实际数据库.db' --key-file '/私有密钥.json'
wecom-linux conversations --account me --query '会话名称' --limit 20
wecom-linux messages --account me --chat '精确chat_id' --limit 20
wecom-linux messages --account me --chat '精确chat_id' --cursor '上页next_cursor'
wecom-linux messages --account me --chat '精确chat_id' --all
wecom-linux send-text --account me --chat '精确chat_id' --text '文字' --request-id '唯一ID'
wecom-linux send-image --account me --chat '精确chat_id' --image '/路径/图片.jpg' --request-id '唯一ID'
wecom-linux send-status --request-id '原请求ID'
wecom-linux media export --account me --chat '精确chat_id' --message-id 123
```

快照对数据库/WAL各读两遍并验证元信息稳定；按实际密文校验和、盐值和提交标记合并有效提交，校验失败或不完整帧返回错误。其他WAL加密布局和非空回滚日志尚不支持，不能忽略后返回旧数据。跨库不是原子快照。消息分页绑定账号/会话，按时间和本地ID排序，排除第一页之后新插入的消息；新消息另开查询。`--all`不代表完整云端历史。未知类型不猜正文，保留全部原始字段/base64；媒体引用不证明媒体已查看。验证码、登录二维码、密钥、原始内存、消息正文和真实账号标识不提交；私有密钥与临时候选使用0700/0600，内存扫描回退通过管道逐块校验、不落盘。截图必要时发给本人ClawBot，发送前实际查看裁剪图。

文字发送按[文字契约](../capabilities/wecom/send-text.md)、PNG/JPEG按[图片契约](../capabilities/wecom/send-image.md)执行。本人长期授权的微信/企微会话对保存于本机 `~/.local/state/ncut-wechat-skills/send-authorizations.json`；本次已核对名称后缀、精确ID及双向收发。授权不扩大到同名的内部自己聊天或其他联系人。

## 后续实际验收顺序

1. 完成本人认证，验证原 Windows 资料未变、手机和新客户端登录状态。必要本人操作经 ClawBot 联系，已有授权不重复询问。
2. 获取并验证本机消息密钥与真实结构，实现精确会话 ID、默认20条分页、cursor及全部已同步历史。核对私聊、群聊、中文、换行和媒体引用；同步历史边界与云端历史分别报告。
3. 验证新消息防重，覆盖前台、后台、窗口关闭、客户端重启和离线缺口；不以旧缓存查询代替新消息验收。
4. 验证本人身份 CLI 文字，再分别图片、文件、表情及卡片；保持同 request-id 防重，接收端、本地读回和客户端显示分别记录。未授权的外部对象不作测试目标。
5. 学校工作台先复用 [ncut-web-api](../../../ncut-web-api/SKILL.md) 已验证业务接口；只有实际缺项才在企微入口局部发现。登录页面或动态 ticket 不是永久业务 API，不扩大到通用办公平台。
6. 至少三次已登录重启及空闲/发送 CPU、内存和启动测量后，由本人决定是否常驻。当前不创建 Linux 或 Wine 自启动，不启动独立后台接收器。

GUI 用于登录、发现及 CLI 无法完成的任务，不能把 GUI 发送当作原生 CLI 发送验收。本次企微开发探索限时已放宽，继续分阶段实测；日常其他缺项仍适用默认15分钟限制。
