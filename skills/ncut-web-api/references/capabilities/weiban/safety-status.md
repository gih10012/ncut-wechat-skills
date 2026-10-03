---
id: safety-education-status
service: weiban
keywords: ["安全微伴", "安全教育", "平安毓秀", "安全课程", "反诈考试", "补学"]
status: runtime_verified
evidence: "2026-09-21 used the owner's account to read three assigned projects, exact course/exam counts, scores and deadlines"
runtime_verified_at: "2026-09-21T23:08:00+08:00"
transport: http
command: ["safety", "status", "--account", "me", "--all"]
requests: [{"method":"POST","path":"/pharos/index/listStudyTask.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/project/showProgress.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/exam/listPlan.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/listCategory.do","effect":"read","expect":"json","auth":"X-Token"}]
note: "Read-only status is verified. Progress and exam writes have not been implemented or tested; future owner-authorized tasks use local discovery."
---

# 安全微伴完成状态

输入来自登录响应中实际返回的 `tenantCode`、`userId`，以及任务列表返回的 `userProjectId`；不猜项目 ID、考试计划或学期。`--all` 同时列出仍开放补学的往期项目，默认只返回当前开放项目。

认证使用 `https://weiban.mycourse.cn` 精确 origin 下的 `X-Token`。私有账号状态还保存该 token 对应的用户和学校 ID；不保存学号、默认密码、验证码或课程正文。接口返回 `detailCode=-105` 才按会话失效处理；其他非成功业务码保留业务原因。HTTP701是学习行为限制，停止请求并遵循原生页面说明，不重新登录循环重试。

2026-10-03登录续接补齐：`login --service 安全微伴` / `login finish --service 安全微伴` 已加入源码和离线回归。专用Chrome只从该精确origin的 `localStorage.user` 取 `token/userId/tenantCode`，分别存到认证头和 `service_data.weiban`；不读取含记住密码的 `default`。捕获时保留其他服务认证头、service_data与私有元数据，不能用重写空headers的方式清掉既有身份。保存后须用 `listStudyTask.do` 的成功业务码和 `studyTaskList` 数组验证；同日通过原生登录页恢复本人身份，捕获后真实读取到三期学习任务；新增续接已获运行验收。

依次只读调用任务列表、项目进度和考试计划。最终映射项目名称、起止日期、总进度、必修课程已完成数/总数，以及计入考核的考试完成数、成绩、剩余次数和合格分。业务成功需同时满足 HTTP 成功、JSON `code=0` 和预期数据结构。

这些请求没有远端写入。当前契约只实现状态查询；课程列表/开始与有限完成上报见独立[课程契约](safety-courses.md)；试卷准备、答题和交卷仍待验收。这是技术范围记录，不是对本人后续任务的永久限制。后续请求按SKILL.md的本人代理授权和局部发现流程处理，不单凭站点提示停止辅助任务。

本次任务入口：[《北方工大人注意，不做影响毕业》](https://mp.weixin.qq.com/s/VyYBwmvXZ0MujoaWZuaR5g)，2026-10-03已读取文字层，说明秋季课程开放至10月31日，课程后需在线考试及防范电信网络诈骗专题考试，合格分80、最多3次。正文末尾落款为2025年9月，与正文所述2026年不一致；项目学期、开放期、实际合格分和剩余次数均以本人平台实时响应为准。文章提供的默认密码提示不证明该账号仍使用默认密码。

同日已恢复登录并真实查询当前秋季项目：30门课程、两场考试（合格80、各3次），当前任务截止2026-10-31。考试参数userExamPlanId来自listPlan条目的id，examPlanId是另一字段，不能混用。课程完成始终以实际finished=1与项目进度读回确认；个人进展及恢复时间存本机私有状态，不在知识库记个人题目或成绩。
