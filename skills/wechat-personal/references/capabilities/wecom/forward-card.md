---
id: wecom-forward-card
service: wecom
keywords: ["企微转发", "企业微信转发公众号", "企微小程序转发", "企业微信自定义XML", "企微自定义XML", "企微XML", "企微卡片"]
status: "runtime_verified"
evidence: "2026-10-02 installed ordinary native CLI article5 and mini-program33 forwards plus edited title/description XML each independently received once by authorized personal WeChat peer; identity/page, Chinese/newline/emoji, server IDs and replay verified; complete mini thumbnail and click-through unverified"
runtime_verified_at: "2026-10-02T13:20:00+08:00"
workflow: references/workflows/wecom-cli.md
transport: "installed_independent_wecom_linux_cli_native_ui_thread"
command: ["wecom", "forward", "--account", "me", "--chat", "EXACT_SOURCE_CHAT_ID", "--message-id", "SOURCE_MESSAGE_ID", "--recipient", "EXACT_TARGET_CHAT_ID", "--request-id", "UNIQUE_REQUEST_ID"]
note: "先检查目标写入授权。文章与小程序卡片原生转发/编辑XML已实测；文章预览完整，小程序缩略图为空，完整资源与点击待补。未知结果只查原ID，不换ID或GUI重发。"
---
# 企业微信卡片转发与自定义 XML

先按主SKILL核对发送授权。读取本人历史直接执行；长期授权的精确对应会话对可双向验证，不扩大至其他同名人。普通安装CLI，无需sudo、键鼠或亮屏。

```sh
python3 "$WX" wecom messages --chat '精确源chat_id' --limit 20
python3 "$WX" wecom forward --chat '精确源chat_id' --message-id 123 --recipient '精确目标chat_id' --request-id '唯一ID'
python3 "$WX" wecom message-xml --chat '精确源chat_id' --message-id 123
python3 "$WX" wecom send-xml-preflight --chat '精确目标chat_id' --xml '/私有路径/card.xml'
python3 "$WX" wecom send-xml --chat '精确目标chat_id' --xml '/私有路径/card.xml' --request-id '另一唯一ID'
python3 "$WX" wecom send-status --request-id '原ID'
```

源必须是本机已同步的精确会话/消息ID，type13文章或type78小程序。转发保留完整原生protobuf字段，不把卡片改成纯文字链接。XML输出为`msg/appmsg`，文章type5、小程序type33，附带`wecom-native`的版本、原始base64及SHA256。它可能含原生分享/资源凭据，只保存在0600私有文件，不贴公共仓库或问题报告。

自定义XML为1..65536字节UTF-8、无NUL/DTD/实体声明。文章可改title/des/url/thumburl；小程序可改title/des/sourcedisplayname与weappinfo/weappiconurl，必须保留真实原卡片的appid、username、pagepath、type和完整`wecom-native`载荷，不能用其他应用的分享票据。未知原生字段保留，客户端可能规范化XML；任意XML标签、合并聊天记录、type36和无真实来源的小程序不在本契约内。

构造预检原生解析/序列化、核对完整字段与释放，成功后才持久化请求并提交一次。相同ID绑定目标、动作、原生内容与源消息身份或XML原始字节；换源、改XML、转发改直接XML均拒绝。源已删除或XML丢失时查询send-status，不换ID重试。不同动作/目标别名下的同一未知操作也阻止再次提交。CLI结果只证明己方原生提交及本地服务器ID，接收端/UI验收另存私有证据。

2026-10-02普通CLI原生转发文章与小程序33，以及各自编辑标题/描述的XML，授权微信对应会话各独立收到一条type49/app5或33；双方服务器ID非零，标题、描述、中文换行/emoji、小程序appid/username/pagepath核对通过。四个ID重放无新增，动作冲突拒绝。文章两端显示缩略图；小程序源缩略图元数据为空，正常GUI转发与CLI均显示占位图，完整缩略图及点击打开仍待补。74项CLI测试及已有格式v3原生预检通过。
