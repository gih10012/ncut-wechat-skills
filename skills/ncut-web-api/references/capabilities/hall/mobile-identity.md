---
id: mobile-identity
service: hall
keywords: ["移动页身份", "移动表单登录", "大厅移动身份", "getUserAttributeForMobile"]
status: runtime_verified
transport: http
command: ["request", "hall", "--capability", "mobile-identity", "--method", "POST", "--path", "/EIP/api/getUserAttributeForMobile.htm", "--account", "me"]
requests: [{"method":"POST","path":"/EIP/api/getUserAttributeForMobile.htm","effect":"read","expect":"json","auth":true,"fields":["userId","userName"],"required_fields":["userId","userName"]}]
workflow: references/workflows/hall-mobile.md
source_files: ["https://service.ncut.edu.cn/EIP/weixin/weui/js/model/global/global-user-model.js"]
source_sha256: "55f4958e3ad4851519fac3ae8bc8a5ba18b5f3d1e96ebd4f45cf85e2c1a74a83"
runtime_verified_at: "2026-09-16T12:56:46+08:00"
note: "大厅移动表单的本人身份预请求，空body只读POST。已用学校SSO会话实测，无需企微扫码；userId和userName均非空才确认身份。仅覆盖service.ncut.edu.cn大厅，不是企微聊天授权。"
---
# 大厅移动表单本人身份

当前前端 `global-user-model.getUserInfo()` 与 `model/cooperate/common/current-user-model.load()` 均调用本接口。空 body POST，使用本人的 service.ncut.edu.cn Cookie；成功响应是 JSON，即使 Content-Type 为 text/html。只投影 userId/userName，其他身份属性不用于普通摘要。

验证必须同时具有非空 userId 与 userName；业务错误或空身份不能仅凭HTTP200算成功。失效先复用大厅 SSO 续接，见关联流程。只读身份接口不需要 --allow-write，也不是 v0 远端写入证明。
