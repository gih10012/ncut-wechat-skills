---
id: hall-service-search
service: hall
keywords: ["服务搜索", "搜索服务", "服务列表", "筛选服务"]
status: runtime_verified
evidence: "more.htm inline function search() -> post('/EIP/nonlogin/elobby/portal/services/list.htm', param)"
runtime_verified_at: "2026-09-14T00:14:13+08:00"
requests: [{"method":"POST","path":"/EIP/nonlogin/elobby/portal/services/list.htm","effect":"read","expect":"json","fields":["id","name","deptName"]}]
transport: "http"
command: ["request", "hall", "--capability", "hall-service-search", "--method", "POST", "--path", "/EIP/nonlogin/elobby/portal/services/list.htm", "--form", "keyword=<业务关键词>"]
note: "只读 POST，form keyword 来自用户查询，不需要 --allow-write。默认投影 id/name/deptName，最多 8 条。"
---
# 服务目录查询（只读 POST）

`request hall --capability hall-service-search --method POST --path /EIP/nonlogin/elobby/portal/services/list.htm --form keyword=成绩`

前端 param 包括 keyword/type/target/publisher/order/related/blisuse。只有已知筛选值才传入；普通文本查询只传 keyword。本接口查询目录，不提交申请，不需要 --allow-write。成功语义是目录条目列表（或当前前端使用的真实包装结构），JSON 解析成功本身不够。优先 catalog 的精简输出，避免把服务条目大量后台字段塞进上下文。

实测：空 keyword 返回 JSON 数组 64 条；可按 keyword 过滤。默认投影 id/name/deptName 并限制 8 条，保留 total_received/truncated。
