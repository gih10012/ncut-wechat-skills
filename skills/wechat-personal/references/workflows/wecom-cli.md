# 本人企业微信：免费独立 CLI

当前开发按本人 2026-10-01 批准的计划执行：独立开源 [wecom-linux-cli](https://github.com/gih10012/wecom-linux-cli)，由现有 skill 复用。只考虑免费路线，允许独立 Wine；Android 容器与鸿蒙通知接入暂缓。普通成员没有企业会话存档权限，官方机器人 `wecom-cli` 身份也不覆盖本人个人聊天，不使用它替代验收。

## 当前真实范围

已在本机安装 Wine 11.18 和官方下载的企业微信 5.0.11.6018，采用本人所有、0700 的独立 prefix，保留原 Windows 安装及资料。2026-10-01本人认证已完成，主界面显示学校会话。普通用户CLI已验证真实私聊/群聊、默认20条分页、无重复续页及指定会话全部已同步历史；完整中文、换行、emoji通过新GUI消息的独立CLI读回核对。消息、会话、联系人库及WAL通过校验和与SQLite完整性检查。媒体原始字段/引用完整保留；外部微信type101 PNG与企微原生type14 PNG/JPEG完整缓存原图已通过输入/导出字节一致及两端UI验收，按[原图导出契约](../capabilities/wecom/media-export.md)调用，不主动下载未缓存媒体。普通已安装 CLI 本人身份文字向授权的微信对应会话真实发送通过：两个独立读取端和两边窗口分别核对完整正文、单次收件、服务器ID；同ID重放不重发、正文冲突拒绝。双向文字收发已验收，手机确认先前的原生文件传输助手候选正常。三次正常托盘退出/重启均恢复配置账号、复用密钥及旧请求；各新进程原生构造预检通过，第三次之后新文字经接收端独立确认一条，关屏且未选中聊天亦可发送。两次计时约3.6秒达到原生预检，属于客户端重启、非整个Wine冷启动。5秒资源采样约4.4–5.6GiB PSS，空闲单核CPU约9–18%，一次发送窗口约20%；不是长期边界。2026-10-02普通原生CLI PNG与中文文件名JPEG各独立送达授权微信会话一条，两端窗口显示、缓存原图与输入一致、重放不重复及冲突拒绝通过；图片/文字构造预检未新增消息，51项CLI测试通过。中文文件名TXT/ZIP已由普通CLI发送各一条，个人微信下载字节一致、双方文件卡片显示；重放无新增，换文件拒绝，升级后旧PNG请求重放通过，58项测试通过。普通CLI动画GIF已由授权微信对应会话以type47单次收到，XML MD5/长度、双方动画显示与防重通过；65项测试及安装23个包文件校验通过。文章/小程序原生转发和各自修改标题/描述的自定义XML已独立微信收件、字段与防重验收，文章缩略图显示；小程序缩略图元数据为空，正常GUI及CLI均显示占位图，完整缩略图/点击待补。74项CLI测试及24个安装包文件一致检查通过。未缓存媒体、协议链接外部浏览器转换/中继、离线缺口与长期稳定性仍待验收，尚不配置常驻。

日常入口是 `wecom-linux`；本skill的`wecom`子命令仅调用已安装CLI一次，不切换身份或后端。缺少密钥时才捕获，不在每次正常读取前扫描进程。已配置的`me`绑定精确账号数据目录；不自动选择最大的数据库。详细本机路径、登录结果、私有日志和接续状态只保存于本机私有状态，不写入公共仓库。

2026-10-03追加：普通企微CLI私聊发起、按本轮令牌接听、计时连接、接通后播音、正常挂断及防重均通过，按[企微私聊控制](../capabilities/wecom/private-call-control.md)直接执行。两端安装call-play的生成音频独立录制匹配0.87/0.95、双端历史00:22，原路由/默认设备/临时模块恢复通过。109项CLI测试、29个source/wheel/installed包文件一致检查通过。正常托盘退出/客户端重启后，普通预加载19个系统DLL约5.24秒达到就绪，账号/历史保留，新进程入站接听与出站发起/连接后播音/挂断/防重通过；该轮没有重启整个Wine运行时。企微启动后入站测试先做`wecom-linux call preflight --account me`；目标没有附着view时用computer-use打开精确已授权会话再preflight，不能盲目换ID发起。主号个人微信保持原进程，不要求切小号。群通话/成员选择、整套Wine冷启动及长期稳定性继续开发。

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
wecom-linux send-file --account me --chat '精确chat_id' --file '/路径/中文文件.zip' --request-id '唯一ID'
wecom-linux send-sticker --account me --chat '精确chat_id' --sticker '/路径/表情.gif' --request-id '唯一ID'
wecom-linux send-status --request-id '原请求ID'
wecom-linux media export --account me --chat '精确chat_id' --message-id 123
```

快照对数据库/WAL各读两遍并验证元信息稳定；按实际密文校验和、盐值和提交标记合并有效提交，校验失败或不完整帧返回错误。其他WAL加密布局和非空回滚日志尚不支持，不能忽略后返回旧数据。跨库不是原子快照。消息分页绑定账号/会话，按时间和本地ID排序，排除第一页之后新插入的消息；新消息另开查询。`--all`不代表完整云端历史。未知类型不猜正文，保留全部原始字段/base64；媒体引用不证明媒体已查看。验证码、登录二维码、密钥、原始内存、消息正文和真实账号标识不提交；私有密钥与临时候选使用0700/0600，内存扫描回退通过管道逐块校验、不落盘。截图必要时发给本人ClawBot，发送前实际查看裁剪图。

文字发送按[文字契约](../capabilities/wecom/send-text.md)、PNG/JPEG按[图片契约](../capabilities/wecom/send-image.md)、TXT/ZIP按[文件契约](../capabilities/wecom/send-file.md)、动画GIF按[表情契约](../capabilities/wecom/send-sticker.md)执行。本人长期授权的微信/企微会话对保存于本机 `~/.local/state/ncut-wechat-skills/send-authorizations.json`；本次已核对名称后缀、精确ID及双向收发。授权不扩大到同名的内部自己聊天或其他联系人。

## 后续实际验收顺序

1. 完成本人认证，验证原 Windows 资料未变、手机和新客户端登录状态。必要本人操作经 ClawBot 联系，已有授权不重复询问。
2. 获取并验证本机消息密钥与真实结构，实现精确会话 ID、默认20条分页、cursor及全部已同步历史。核对私聊、群聊、中文、换行和媒体引用；同步历史边界与云端历史分别报告。
3. 验证新消息防重，覆盖前台、后台、窗口关闭、客户端重启和离线缺口；不以旧缓存查询代替新消息验收。
4. 验证本人身份 CLI 文字，再分别图片、文件、自定义表情、转发文章/小程序卡片及自定义XML；保持同 request-id 防重，接收端、本地读回和客户端显示分别记录。未授权的外部对象不作测试目标。
5. 2026-10-02本人调整：在微信/企微CLI中实现协议链接的通用转换或中继，使可转换的内容能在Edge/Chrome直接浏览；先用本人指定群中的真实链接验收。学校应用复用该入口或computer-use，不为学校业务增加专用CLI适配。保留已有ncut-web-api能力，动态OAuth票据与小程序启动页不冒充普通网页正文。
6. 至少三次已登录重启及空闲/发送 CPU、内存和启动测量后，由本人决定是否常驻。当前不创建 Linux 或 Wine 自启动，不启动独立后台接收器。

GUI 用于登录、发现及 CLI 无法完成的任务，不能把 GUI 发送当作原生 CLI 发送验收。本次企微开发探索限时已放宽，继续分阶段实测；日常其他缺项仍适用默认15分钟限制。

2026-10-03群入口追加：普通安装CLI完整读取空群语音成员选择窗443节点，并通过精确令牌调用正式取消按钮关闭；窗口打开时发起/目标预检/接听拒绝、无通话日志，独立群历史不变，旧令牌拒绝。119项CLI测试、原生编译与29个source/wheel/installed文件一致通过。复用[企微成员选择契约](../capabilities/wecom/group-call-selection.md)，精确成员ID、勾选/群邀请及群收音仍未完成。
