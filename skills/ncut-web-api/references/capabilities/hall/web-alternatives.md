---
id: web-alternatives
service: hall
keywords: ["Web替代", "网页替代", "企微服务替代", "入口映射", "移动端入口", "企微工作台替代"]
status: runtime_verified
transport: http
command: ["catalog", "--alternatives", "--query", "<业务词>", "--limit", "8"]
requests: [{"method":"GET","path":"/EIP/nonlogin/elobby/service/more.htm","effect":"read","expect":"html"}]
runtime_verified_at: "2026-09-16T07:52:41+08:00"
evidence: "Current public catalog returned 64 services: 45 with visible Web entries, 39 with Web/mobile pairs from the same blArr action. This verifies catalog mappings, not business permissions or the full WeCom workbench."
note: "按目录同一 action 的 blpcurl/blmurl 配对，不按名称猜。默认最多8条；--cached 读私有缓存。动态票据链接不输出，fresh_entry_needed 表示需进一步解析；不能当作必须OAuth或没有Web替代。"
---
# 从学校目录找企微业务的 Web 入口

`catalog --alternatives --query '业务词'`。省略 query 时统计整个当前目录，但只输出 limit 条。

配对来自 `service[].blArr[]` 同一对象，分别取 blpcurl 与 blmurl；相同名字的不同 action 不交叉拼接。入口先验证为 HTTPS，并检查 query/fragment 中的 token/ticket/code 等动态参数，敏感入口不输出。若存在未输出入口，标 fresh_entry_needed，不能据此认定服务没有网页版。

same_business_verified=false 表示只核对了目录配对。真正替代须用本人登录验证两端指向同一业务对象、字段和权限，已停用或迁移条目也不能自动推荐。完整企微工作台清单尚未取得，64项公开服务不是完整企微覆盖率的分母。

2026-09-16 实测目录64项，45项含可显示 Web 入口，39项含 Web/移动配对，12项含需重新解析的入口。此计数是当次目录快照，不固定为永久值，也不保证未来登录可用。
