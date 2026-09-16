---
id: resolve-entry
service: hall
keywords: ["解析入口", "动态入口", "入口票据", "预约入口", "服务跳转", "fresh_entry_needed"]
status: runtime_verified
transport: http
command: ["catalog", "--resolve", "--account", "me", "--query", "EXACT_SERVICE_NAME"]
requests: [{"method":"GET","path":"/EIP/nonlogin/serviceHandleCenter/openService.htm","effect":"read","auth":true,"expect":"json"}]
workflow: references/workflows/resolve-entry.md
source_files: ["https://service.ncut.edu.cn/EIP/resources/js/elobby/elobby.js"]
source_sha256: "1e17cc9f49e22f5b4a3335a1c7a3498d6a6ca0f4a8333aa4f693102ac0f413cd"
runtime_verified_at: "2026-09-16T13:05:25+08:00"
note: "按目录完整服务名取得当次真实入口，经已有SSO跳转；票据只私存。预约页还查询详情核对site_id和名称，返回后续calendar命令。目录fresh_entry_needed先用此能力，不要求提供API或重新登录。"
---
# 按名称解析当前业务入口

`catalog --resolve --account me --query '目录完整服务名'`，不与 --cached/--alternatives 合用。动态sid来自当前精确名称查询，不能硬编码某次目录项ID。

实测“体育馆一层羽毛球预约（学生）”：大厅返回带token的当前入口 → workflow登录入口 → 学校SSO → workflow CAS回调 → 预约页；自动得到site_id，并用预约详情确认同一ID和名称。不打开浏览器，不提交预约。

“大教室预约”实测返回服务器tip，输出 SERVICE_UNAVAILABLE 并停止，不重复要求登录。其他服务要独立看自己的结果，不把这一权限结果推广到所有教室预约。
