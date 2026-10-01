---
id: wecom-media-export
service: wecom
keywords: ["企微图片下载", "企业微信图片", "企微缓存图片", "企微原图", "企微附件导出"]
status: "runtime_verified"
evidence: "2026-10-01 external type101 PNG and native type14 PNG; 2026-10-02 ordinary native CLI PNG/Chinese-filename JPEG; installed cached-original exports equal input bytes, both UIs display images"
runtime_verified_at: "2026-10-02T01:01:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_verified_original_cache"
command: ["wecom", "media", "export", "--account", "me", "--chat", "EXACT_CHAT_ID", "--message-id", "LOCAL_MESSAGE_ID"]
note: "已实测外部微信type101 PNG及企微原生type14 PNG/JPEG缓存原图导出；按消息原始大小/MD5校验，返回私有路径供查看。不主动下载，不用缩略图替代原图；外部type101 JPEG及其他媒体待分别验收。"
---
# 企业微信已缓存原图

先从`wecom messages`取得精确会话及`message_id`，然后执行上面的命令。读取本人对应会话直接执行，无需sudo、重新登录或内存扫描。接受已验证的外部微信图片type101及企微原生图片type14；`message_id`绑定精确chat，不能从另一会话取图。

数据链：消息库原图cache key、大小、MD5 → 同账号`CacheMapping`稳定快照及提交WAL → 该原图映射 → `Cache/Image`内对应文件 → 检查大小/MD5 → 私有`attachments/`副本及SHA256。缓存路径禁止越出账号或用symlink跳转；type14使用的绝对C:路径仅允许映射到配置Wine prefix内该账号的Image缓存。导出600原始PNG/JPEG，重复导出同一数据返回同一路径，不覆盖冲突产物。缓存映射key、远端媒体凭证不打印或写入公共仓库。

`ORIGINAL_IMAGE_NOT_CACHED_OPEN_IN_CLIENT`：先用computer-use在正常企微窗口打开这条图片加载原图，再重复读取/导出；不发送或重发消息。`CACHE_ORIGINAL_HASH_MISMATCH`、大小错误或路径越界：停止使用该文件，核对原消息及缓存。`MEDIA_TYPE_NOT_SUPPORTED_FOR_EXPORT`：当前类型未实现，不用文字或缩略图冒充图片/附件全文。

返回`source=verified_client_original_cache`、`original_hash_verified=true`、`thumbnail_used=false`，同时明确`remote_download_performed=false`。这证明本机完整原图导出；需看图片正文时实际打开返回路径。2026-10-01普通个人微信CLI发到本人授权企微对应会话的PNG已在两端显示，企微原图及安装CLI导出副本与输入逐字节一致。另有正常企微GUI向授权微信会话发出type14 PNG，对端独立读回一条且两端显示，原图导出与输入逐字节一致。该GUI发送不是原生CLI发送验收。2026-10-02普通原生CLI发送的PNG与中文文件名JPEG已在两端显示，其type14缓存原图导出均与输入逐字节一致；发送验收见[图片发送](send-image.md)。外部type101 JPEG、内部企微会话图片收发、文件、表情、卡片和主动获取未缓存远端原图仍待分别验收。原图导出与发送各自记录。
