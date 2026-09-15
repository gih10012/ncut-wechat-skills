---
id: service-favorite
service: hall
keywords: ["收藏服务", "取消收藏", "服务收藏", "写请求验证", "验证POST", "v0验证"]
status: runtime_verified
transport: http
command: ["favorite", "show", "--account", "me", "--query", "<目录中的完整服务名称>"]
requests: [{"method":"POST","path":"/EIP/nonlogin/login/isLogin.htm","effect":"read","auth":true},{"method":"GET","path":"/EIP/resources/js/elobby/elobby.js","effect":"read","auth":true},{"method":"POST","path":"/EIP/nonlogin/elobby/portal/services/list.htm","effect":"read","expect":"json","auth":true}]
workflow: references/workflows/web-write.md
source_files: ["https://service.ncut.edu.cn/EIP/resources/js/elobby/elobby.js"]
source_sha256: "1e17cc9f49e22f5b4a3335a1c7a3498d6a6ca0f4a8333aa4f693102ac0f413cd"
runtime_verified_at: "2026-09-15T23:34:32+08:00"
evidence: "Authenticated school favorite yes/no POSTs; list isf confirmed change and restoration of original value. Two remote write requests; no reservation/application submitted."
note: "show 查询；已授权收藏用 set --value yes/no --allow-write；验证完整写链用 verify --allow-write，自动恢复原状态。完整服务名从 catalog 取得，账号登录可自动用已保存 SSO 换票。"
---
# 本人服务收藏与真实 POST 验证

查询：`favorite show --account me --query '完整服务名称'`。
写入：`favorite set --account me --query '完整服务名称' --value yes --allow-write`；取消改 no。
可恢复验证：`favorite verify --account me --query '完整服务名称' --allow-write`。

1. POST `/EIP/nonlogin/login/isLogin.htm`，空 body，文本 `true` 才算本人大厅登录。失败时 GET 当前服务目录页，解析 loginPageParam 的实际 SSO 地址；最多六次已登记 HTTPS origin 跳转，用 CookieJar 接收 Set-Cookie，再验证 isLogin。凭据不进日志，其他服务会话保留。
2. POST 服务列表，form `keyword=<完整名称>`；精确匹配唯一条目，得到动态 id 与 isf=0/1。不能固定一次会话中的 ID。
3. 写前 GET 当前 elobby.js，确认 fav/nofav 的路由仍是 `POST /EIP/elobby/{sid}/fav/yes.htm` 和 `POST /EIP/elobby/{sid}/fav/no.htm`。它们是空 body 的写请求，无需发明 JSON、CSRF 或 OPTIONS 预检。
4. 发送授权动作，再查列表该 ID 的 isf。HTTP200或空响应不是成功证据；读回与目标一致才成功。set 在状态已经一致时不发写请求。
5. verify 将状态反转、读回，然后无论测试读回是否失败都尝试恢复原值，再读回。已有收藏也必须恢复为已收藏。日志放私有 `write-checks/`，未恢复的旧日志阻止新验证；先依据记录恢复原值并核对，不盲重试。

此验证证明的是学校收藏写接口及恢复流程，不是实际订场或原生消息发送。
