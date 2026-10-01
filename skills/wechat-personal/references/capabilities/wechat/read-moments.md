---
id: read-moments
service: wechat
keywords: ["朋友圈", "朋友圈动态", "全部朋友圈", "完整朋友圈", "朋友圈历史", "朋友圈分页"]
exclude_keywords: ["指定人", "某人", "某个好友", "发朋友圈", "发布朋友圈"]
status: "runtime_verified"
evidence: "Linux 4.1.13 authenticated SNS snapshots, real feed GUI history loading, exact page/all ID agreement and complete XML parsing on 2026-10-01"
runtime_verified_at: "2026-10-01T13:23:00+08:00"
workflow: references/workflows/moments.md
transport: "local_sqlcipher_readonly_with_normal_client_gui_hydration"
command: ["native", "moments", "--account", "me", "--limit", "20"]
note: "默认20条分页，可用next_cursor续页或--all读取全部已加载历史；正文、媒体引用、点赞/评论与完整XML字段。新鲜/更早远端历史由computer-use在正常窗口加载，范围遵守微信可见权限，不把缓存末尾称为云端完整。"
---
# 朋友圈动态读取

只读`sns/sns.db`中的`SnsTimeLine`，复用现有私有密钥，HMAC验证后合并已提交WAL为内存快照；不调用发送函数、不附加调试器、不写源数据库。联系人来自独立快照，跨库不承诺同一事务。

默认20条，`--limit`1..100；`--cursor 'next_cursor'`继续同账号和筛选，`--all`返回当前缓存全部历史或游标之后全部历史。ID按无符号64位处理并以字符串输出，游标绑定账号/用户范围。每次读取为新的数据库快照，后续新增更近条目须从第一页读取；客户端删除旧缓存后不保证复现上次快照。

每条的`text`不截断，含作者、时间、内容类型、位置、全部`media`引用、客户端可见`likes`/`comments`及保留未知节点/属性的`details`；`--include-xml`提供原XML。`content_complete`描述字段解析完整性，不能证明媒体字节已下载、所有用户互动可见或远端历史完整。`media_bytes_included:false`，按需在微信窗口打开图片/视频查看。私有资源URL/密钥、XML和正文只留本机。

`cached_history_exhausted`只表示当前缓存末尾，`server_history_complete:false`、`server_sync_verified:false`明确区分远端状态。读取全部可见历史按[朋友圈工作流](../../workflows/moments.md)使用正常窗口加载，再读回；不把任何本地预览索引数量当作远端总数。缓存可能包括现在窗口已不展示的旧条目，归档须标明缓存来源。

失败：密钥缺失/失效复用native-linux流程；`DATABASE_BUSY`稍后只读重试。`MOMENTS_SCHEMA_UNSUPPORTED`需局部核对版本；`MOMENTS_CURSOR_INVALID`重新使用同范围的游标；坏XML保留该条ID、`content_complete:false`与`parse_error`，不得静默遗漏或宣称已读全文。未实现发布朋友圈。
