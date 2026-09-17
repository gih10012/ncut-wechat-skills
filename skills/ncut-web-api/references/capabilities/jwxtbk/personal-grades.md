---
id: personal-grades
service: jwxtbk
keywords: ["成绩", "查分", "课程分数", "学期成绩", "平时分", "期末分"]
status: runtime_verified
transport: http
runtime_verified_at: "2026-09-16T21:43:36+08:00"
evidence: "Current undergraduate menu -> cjcx_frm iframe -> cjcx_query form -> authenticated read-only cjcx_list POST; nonempty course/score rows and requested semester verified"
command: ["grades", "--account", "me"]
requests: [{"method":"GET","path":"/jsxsd/kscj/cjcx_query","effect":"read","expect":"html","auth":true},{"method":"POST","path":"/jsxsd/kscj/cjcx_list","effect":"read","expect":"html","auth":true}]
note: "默认从学校实际学期选项由近到远查询，返回最近有成绩的学期；--term 用返回的 available_terms[].id。有效会话下直接 HTTP；AUTH_REQUIRED 才执行 login --service 教务。"
---
# 本科个人成绩

`grades --account me`；指定学期加 `--term 实际学期ID`。结果包含学期、课程编号/名称、学校原始成绩、学分，以及页面实际提供的平时/期末成绩和考试性质。不自行计算绩点，不合并补考/重修记录。`--output ~/.local/state/ncut-web-api/results/grades.json` 保存私人结果，只回显摘要。

认证复用本人 `jwxtbk.ncut.edu.cn` 会话，不传固定学号。首次发现依据当前学生首页的“课程成绩”菜单 `/jsxsd/kscj/cjcx_frm`，其 iframe 指向查询页；正常调用无需再次访问菜单、首页或前端 JS。

1. GET `https://jwxtbk.ncut.edu.cn/jsxsd/kscj/cjcx_query`。解析 `kscjQueryForm` 的真实学期选项、表单默认值，并确认脚本中的查询 action 仍为 `/jsxsd/kscj/cjcx_list`。
2. 表单 POST 到该 action，Content-Type 为 `application/x-www-form-urlencoded`。`kksj` 取实际学期 ID，`xsfs=all` 保留全部考试记录；`kcmc/kcxz/kcsx/mold` 等沿用表单默认值，未勾选复选框不提交。这是只读查询，无需 `--allow-write`。
3. 解析 `dataList` 表头和课程行，校验每行学期与请求一致。最新学期有记录时共两次 HTTP；若有效空表，再查上一个实际学期。指定学期为空时直接返回 `GRADES_EMPTY`，不替换学期。

未知学期返回 `GRADES_UNKNOWN_TERM` 和实际选项。缺少表单、表头、课程或成绩，或服务忽略学期筛选时返回明确错误；登录、权限和网络失败立即停止，不解释为“没有成绩”。只读结果不能证明选课、成绩申诉或其他写入能力可用。

探索参考：[csuhan/csugo](https://github.com/csuhan/csugo) 展示了同类 `jsxsd` 成绩页解析方式，但其学校和接口版本不同。此能力的入口、参数及结果以北方工大本次实际请求为准，未复用其登录方法或部署框架。
