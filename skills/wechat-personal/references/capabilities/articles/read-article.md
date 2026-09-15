---
id: read-article
service: articles
keywords: ["公众号", "文章链接", "mp.weixin.qq.com", "推文", "读文章"]
status: runtime_verified
evidence: "Live GET of mp.weixin.qq.com/s/3N8Cyu-y8EB2A0Px6d5Cng; title and text/image counts independently cross-checked"
runtime_verified_at: "2026-09-14T00:19:34+08:00"
transport: "http"
command: ["article", "--url", "<真实公众号文章链接>", "--max-chars", "6000"]
note: "GET 用户给出的 mp.weixin.qq.com/s 链接；提取标题/文字/图片数。图片正文需另读，不代表个人微信登录或消息收件箱。"
---
# 读取指定公众号文章

`article --url '真实文章链接' --max-chars 6000`。

只允许 mp.weixin.qq.com/s 的真实文章 URL；提取 activity-name/js_content；默认只输出文字与图片数量，需图片时加 --images N（最多 8）。没有文字或图片正文（验证页、失效文章等）返回 ARTICLE_BODY_UNAVAILABLE，不把 HTTP 200 当文章成功，不自动无限重试。

结果标记 authenticated_inbox:false，不代表本人微信收件箱，也不代表历史消息完整。图片 URL 是页面观察到的地址，不自动下载或转发。

实测文章《迎新专栏｜一键开启NCUT建筑之旅》以图片为主：文字层为回顾/制作信息，12 张正文图片。脚本明确 text_layer_only:true；需要图片中的建筑介绍时继续视觉读取，不能只看文字层就总结全部文章。公众号 HTML 常超过 2 MB，本命令上限为 8 MB，输出仍按 max-chars 和 images 限制。
