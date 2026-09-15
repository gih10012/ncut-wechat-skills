---
id: personal-timetable
service: jwxtbk
keywords: ["课表", "课程安排", "今天上课", "明天上课", "上什么课", "当前学期", "本周课"]
status: runtime_verified
evidence: "Authenticated jsxsd/xskb/xskb_list.do controls -> framework/mainV_index_loadkb_10009.jsp; parsed 24 schedule entries and 1 untimed course"
runtime_verified_at: "2026-09-14T12:06:40+08:00"
requests: [{"method":"GET","path":"/jsxsd/xskb/xskb_list.do","effect":"read","expect":"html","auth":true},{"method":"GET","path":"/jsxsd/framework/mainV_index_loadkb_10009.jsp","effect":"read","expect":"html","auth":true}]
workflow: references/workflows/personal-timetable.md
transport: "http"
command: ["timetable", "--account", "me", "--week", "current"]
note: "两次 GET；实际学期/节次由响应取得。本周用 --week current，全学期去掉该选项，某天用 --date YYYY-MM-DD。AUTH_REQUIRED 才执行 login --service 教务。"
---
# 本科个人课表

直接 `timetable --account me`。指定日期用 `--date YYYY-MM-DD`；本周用 `--week current`。正常命中只做两次 HTTP：读取实际学期/节次模式，再读取全周次课表片段。日期筛选在本地按学校周历、课程周次和单双周完成，避免日期特定片段的慢响应。

`--output ~/.local/state/ncut-web-api/results/文件.json` 保存完整个人结果，只回显摘要与文件位置。不要把真实课程、老师、教室、学号写进此能力。

认证来自本人本科教务 Cookie，不传入固定学号。新门户 jwxt.ncut.edu.cn 与本科系统 jwxtbk.ncut.edu.cn 不是同一个 origin。登录恢复才执行关联流程；会话有效时不打开浏览器、不查菜单、不重新解析打包 JS。
