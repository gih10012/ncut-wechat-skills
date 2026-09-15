---
id: badminton-rules
service: workflow
keywords: ["预约规则", "订场规则", "羽毛球规则", "预约时间", "开放预约", "预约验证"]
status: runtime_verified
transport: http
command: ["reservation", "rules", "--account", "me", "--site", "596"]
requests: [{"method":"GET","path":"/reservation/site/resource/detail","effect":"read","expect":"json","auth":true}]
runtime_verified_at: "2026-09-15T22:26:49+08:00"
evidence: "Authenticated current resource detail, e=OK, id=596; server config anti_bot=1 and ServiceTimeRule window 12:00–17:00. No launch request."
note: "一次 GET 当前服务器配置；返回预约验证要求、提交窗口、限制和规则。预约窗口关闭、需验证、登录失效分别处理。公告与配置冲突时不猜实际可约日期，以实时日历/服务校验为准。"
---
# 羽毛球预约当前规则

GET `/reservation/site/resource/detail?id=596&collective=0`，原本人 workflow Cookie 与 User-Agent。成功须 e=OK、d.id 匹配输入，d.config.rule 数组及 anti_bot 结构有效。

`reservation rules` 提取 config.anti_bot、ServiceTimeRule、limit_info 及规则必要字段，保留 class/rule_type/roles；不回显完整配置和公告。返回的窗口是预约提交窗口，不是运动时段。未解释规则不能当作不存在，返回限制列表不能代替最终资格和余量校验。

2026-09-15 实测 anti_bot=1，提交窗口每天12:00–17:00。源页面包含需本人预约验证的检查；没有验证可跨日复用的验证码，不能声称无人值守抢场已可执行。不得自动替用户确认阅读须知或发送 resource/launch。
