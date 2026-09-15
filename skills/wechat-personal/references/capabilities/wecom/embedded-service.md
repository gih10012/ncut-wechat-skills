---
id: embedded-service
service: wecom
keywords: ["工具箱", "工作台", "内部网页", "内嵌", "网页", "学校企微", "免登录", "OAuth"]
status: "workflow_ready"
evidence: "Per-service adapter procedure; no universal WeCom token API"
runtime_verified_at: null
workflow: references/workflows/embedded-web.md
transport: "http"
note: "按具体业务域复用会话/API；学校业务转 ncut-web-api。新域只做该接口的有限发现，尚未提供通用企微身份或任意内部网页访问。"
---
# 工具箱/工作台的业务网页接入

已验证业务域与登录态可通过共享 HTTP 客户端直接调用。首次接入必须取得真实入口与本人会话；当前没有“通用企微 token”或“任意网页已登录”的实现，不能声称已打通所有内部网页。
