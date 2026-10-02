---
id: wecom-protocol-web
service: wecom
keywords: ["企微协议网页", "企业微信链接转浏览器", "企微浏览器中继", "wxwork链接", "企业微信Chrome", "企业微信Edge"]
status: "runtime_verified"
evidence: "2026-10-02 ordinary installed WeCom CLI readonly loopback relay of an observed exact source binding displayed real post body and comment section in both Chrome and Edge; shared personal CLI implementation and installation verified; general client OAuth/JS SDK pages remain unverified."
runtime_verified_at: "2026-10-02T14:22:00+08:00"
transport: "installed_independent_wecom_linux_cli_readonly_http_relay"
command: ["wecom", "web", "resolve", "--url", "ACTUAL_LINK"]
note: "通用解析/只读中继已实测，严格按实际HTTP来源与私有绑定范围；不能凭HTTP200宣称企微免登或完整JS SDK兼容。"
---
# 企微协议链接与外部浏览器

使用同一[协议网页契约](../wechat/protocol-web.md)，将`native web`替换为`wecom web`。学校页面复用此通用入口或computer-use；不在CLI编写学校业务适配。默认不启动Wine或调试器，不需要sudo，无后台自启动。普通HTTP浏览器打开、明确HTTP参数解析和临时只读页面，与企微客户端认证/JS SDK调用分别核验。
