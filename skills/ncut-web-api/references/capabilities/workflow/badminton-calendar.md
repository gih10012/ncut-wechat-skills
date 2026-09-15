---
id: badminton-calendar
service: workflow
keywords: ["羽毛球", "球场", "订场", "场地余量", "可预约", "空场"]
status: runtime_verified
evidence: "Current authenticated reservation page and /reservation/site/resource/calendar; cookie validity depends on captured User-Agent"
runtime_verified_at: "2026-09-14T12:08:34+08:00"
requests: [{"method":"GET","path":"/reservation/site/resource/calendar","effect":"read","expect":"json","auth":true}]
workflow: references/workflows/badminton-reservation.md
transport: "http"
command: ["reservation", "calendar", "--account", "me", "--site", "596", "--date", "<YYYY-MM-DD>", "--limit", "8"]
note: "GET 时段余量；596 为学生一层羽毛球。保留登录时 User-Agent，e=OK 才成功；不提交预约。"
---
# 查看羽毛球场时段

`reservation calendar --account me --site 596 --date YYYY-MM-DD --limit 8`。596 当前实测标题为体育馆一层羽毛球预约（学生）；其他 site ID 必须从真实服务入口或当前页面确认，不复制旧脚本默认值。

query 为 id、collective=0、date={start_date,end_date} 的 JSON 字符串。业务成功是 e=OK，不能只看 HTTP 200。从 d.resource、d.time 和 d.data[日期][资源ID][时间段ID] 关联；状态 0 可约、1 未开放、2 已过期、3 约满、4 不可约，未知值按未知处理。返回公开时段/容量，不读取他人的预约者名单。

**已定位的认证例外**：同一组 Cookie 用浏览器原 User-Agent 返回 e=OK，换成通用脚本 User-Agent 返回 e=UN_AUTH。本人的状态文件必须带捕获时的 user_agent；正常请求保持该值，无需浏览器常驻或每次扫码。
