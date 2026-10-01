---
id: send-personal-image
service: wechat
keywords: ["个人微信发图片", "个人身份发图片", "个人微信发送图片", "微信图片发送", "个人微信PNG", "个人微信JPEG"]
exclude_keywords: ["机器人身份", "ClawBot机器人", "企微", "企业微信"]
status: "runtime_verified"
transport: "installed_linux_cli_queued_image_call"
command: ["native", "send", "--image"]
workflow: references/workflows/native-cli.md
note: "2026-10-01普通CLI以个人微信身份发PNG/JPEG给ClawBot，独立iLink各收到一条且下载字节与原文件一致；Linux UI显示。图片同ID防重及动作冲突拒绝通过。其他原生媒体另行验收。"
---
# 个人微信图片发送

先解析精确会话 ID，再以普通用户调用：

```bash
python3 "$WX" native send --recipient '精确chat_id' --image '/路径/image.png' --request-id '本次唯一ID'
python3 "$WX" native send-status --request-id '原ID'
```

同一入口也可直接用 `wechat-linux send-image --recipient '精确chat_id' --file '/路径/image.jpg' --request-id '本次唯一ID'`。支持 PNG/JPEG、单个常规文件最多 10 MiB；CLI 接受相对路径并转换为绝对路径，服务按文件字节判断格式，以桌面用户读取并私存快照。预检与发送匹配同一精确目标、客户端 PID/启动时间及图片哈希。中文路径可用，图片与文字参数互斥。

任意精确会话 ID 均可作为目标，授权由 agent 按主 SKILL 判断；filehelper/ClawBot 已有长期授权，其他目标依据当前任务或适用的事先直接/间接授权。同 ID/目标/图片字节只读返回旧结果，换文件名不会再次发送；内容、对象或发送动作冲突拒绝。状态未知用原 ID 检查，不换 ID 重发。原文件已删除时可直接查询 send-status，不需要图片文件。

2026-10-01 独立系统服务离线更新后，从仓库外普通用户运行 PNG、JPEG 真实发送到 ClawBot。iLink 分别收到一条图片，下载后的字节与原文件完全一致；Linux 聊天窗口显示对应图片，本地数据库各新增一条图片消息并有服务器 ID。PNG 同 ID 重放原生产物内容和时间未变，改成文字动作返回 REQUEST_ID_CONFLICT。另有私有排队 PNG→filehelper 经本地数据库及 Linux UI 验收，手机收件尚未本人确认；不能把该私有试验称为普通 CLI filehelper 图片手机验收。

`ok` 是客户端提交完成，默认类型读回只给 `local_history_type_matches` 和单一候选的本地/服务器 ID，不能证明图片字节，故 `local_history_integrated` 可为 null。独立 UI/接收端核验后才更新私有确认。图片媒体引用下载、原生文件、表情包及公众号卡片不由这条契约证明。
