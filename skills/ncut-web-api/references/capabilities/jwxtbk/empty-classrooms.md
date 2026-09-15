---
id: empty-classrooms
service: jwxtbk
keywords: ["空教室", "空闲教室", "自习教室", "查教室"]
status: runtime_verified
transport: http
command: ["classrooms", "--account", "me", "--date", "YYYY-MM-DD", "--start", "HH:MM", "--end", "HH:MM"]
evidence: "Authenticated current query form and readonly POST queryJsjyxx; 2026-09-15 week 1 Tuesday, 571 rooms returned; occupancy flags matched current frontend rendering."
runtime_verified_at: "2026-09-15T22:22:02+08:00"
requests: [{"method":"GET","path":"/jiaowu/pkgl/llsykb/llsykb_find_jx0601_kx.htmlx","effect":"read","expect":"html","auth":true},{"method":"POST","path":"/jiaowu/kxjsgl/kxjsgl.do?method=queryJsjyxx","effect":"read","expect":"json","auth":true}]
note: "直接执行 classrooms，正常两次 HTTP；自动处理首次根路径换票。可选 --query 励学221、--campus 校本部、--limit 8；完整筛选后截断。空闲不代表现场无人或本人有借用权限。"
---
# 指定时间段的空教室

全部请求 origin 为 https://jwxtbk.ncut.edu.cn，使用本人会话与原 User-Agent。

`classrooms` 已封装以下查询及首次换票；正常使用只运行命令，不重新写脚本。`--output` 可把完整筛选结果保存到 `~/.local/state/ncut-web-api/` 下。它只有查询功能，没有借用提交入口。

1. GET `/jiaowu/pkgl/llsykb/llsykb_find_jx0601_kx.htmlx`。取隐藏 xnxqh 学期、zc 选项标注的真实日期范围、jcclass 的 data-value 和时间段（也有内联 jcarr JSON），以及查询函数的 jxzlid。校区从 xqbh 选项取值，校本部=01、延庆校区=02。
2. POST `/jiaowu/kxjsgl/kxjsgl.do?method=queryJsjyxx`，Content-Type application/x-www-form-urlencoded。表单：xnxqh、xqbh、jxlbh、jsbh、bjfh、rnrs、zc、xq、jc、jxzlid。未筛选楼/房间/人数时前三者相应为空，bjfh="="；xq 是 ISO 星期（周一1），jc 是相交大节代码的逗号连接。该 POST 只查占用，不进入 apply/教室借用申请。
3. success=true 且 xqmxList 中目标星期的 mxrq 与目标日期一致才使用 dataList。房间字段 jsid/jsmc/jslx/yxzws/xqid/zt；时段键是星期号+大节代码，例如 20910、21112。当前页面以值 "1" 表示占用，未出现该键表示无占用；缺少整个 dataList 或日期映射不算空闲。普通自习优先 jslx=普通教室、zt=1、yxzws>0；所有相交时段均无占用才推荐。后台分类可能把实验室列为普通教室，推荐时同时核对名称。

2026-09-15 的查询参数为 xnxqh=2026-2027-1、zc=1、xq=2、jc=0910,1112，覆盖实际两段 18:00–19:35 / 19:50–21:25；不是只查 18 点那一段。jxzlid 当时为 9B0B373BB2D24946B27C8895883F51A1，未来从当前表单取，不固定。

## 首次取得根路径教务会话

/jsxsd 的本科会话与根路径的各类课表会话要区分。表单明确返回认证失败或跳转时，最多换票一次：GET `/jsxsd/view/kbxx/kbcx/llsykb_frm.jsp`，取真实 frame/iframe src（含短期 token，不回显或写知识）；用 CookieJar 访问该同源 HTTPS `/Logon.do` URL，接收 Set-Cookie，再访问上面的空教室表单。不自动跟随未知跳转。查询验证成功后将 Cookie 合并到正常账号状态，保留 HttpOnly、SameSite、User-Agent 及其他服务会话；日常无需单独临时会话文件。此次已实际验证此纯 HTTP 换票链；不得猜 token 或调用其他账号身份。

`queryJszyqk` 的占用详情实测可返回其他周次的记录，不能以详情非空就推翻指定日期的占用标记。日常查询无需逐房间查详情。完整实测数据在本人私有 results 目录，不进入此契约。

## 教室借用权限证据

2026-09-15 18:23，仅 GET 当前页面 apply() 指向的 `/jiaowu/pkgl/jsjy/jsjy_add_new.htmlx`，当前账号收到 HTTP 200 的“出错页面”：您没有访问该功能的权限。应报告 `FORBIDDEN`，不解释成登录过期；没有取得保存接口契约，也没有提交申请。查询覆盖的大节可比用户请求更长，未来办理不能据此自动扩大借用时长。
