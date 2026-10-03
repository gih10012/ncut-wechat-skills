---
id: safety-education-courses
service: weiban
keywords: ["安全微伴课程", "安全教育学习", "安全微课", "安全课程完成", "课程材料"]
status: runtime_verified
evidence: "2026-10-03 owner's assigned autumn project: category/course reads and native SDK completion independently read back; standalone start/finish CLI completed a second mcwk course."
runtime_verified_at: "2026-10-03T19:16:00+08:00"
transport: http
command: ["safety", "courses", "--account", "me", "--project", "USER_PROJECT_ID"]
requests: [{"method":"POST","path":"/pharos/usercourse/listCategory.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/listCourse.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/study.do","effect":"write","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/getCourseUrl.do","effect":"read","expect":"json","auth":"X-Token"}]
note: "Use the assigned project/course IDs. Listing/start are verified; completion had limited success but batch starts triggered a one-hour platform lock. Read this contract before course writes; code=0 response alone is insufficient, and unresolved submissions continue in the native page."
---

# 安全微伴课程

2026-10-03观察到：批量登记多门开始学习后，部分完成请求返回code=0却仍finished=2，随后平台HTTP701，原生页面明确暂停学习1小时、解锁后按原方式重新进入（刷新提示页无效）。该完成适配器只能视为有限验收，不能宣称整套批量学习稳定可用。逐门开始、阅读/观看/互动、完成并读回后再进入下一门；不能先批量start再finish。发生701即停止所有请求，按实际页面等待；不修改身份、网络或票据规避限制。

`safety status --account me --all` 给出本人任务的 `project_id`。课程列表先验证任务归属，POST `listCategory.do`，form含 `tenantCode/userId/userProjectId/chooseType=3`；对每个返回的 `categoryCode` POST `listCourse.do` 加该字段。不可省略categoryCode猜全量列表。`resourceId`映射为course_id，`userCourseId`映射为user_course_id，`finished=1`完成、2未完成；不猜UUID。

```bash
python3 "$NCUT" safety courses --account me --project USER_PROJECT_ID
python3 "$NCUT" safety course start --account me --project USER_PROJECT_ID --course COURSE_ID
# 实际读取材料、观看视频或办理原生页面互动以后：
python3 "$NCUT" safety course finish --account me --project USER_PROJECT_ID --course COURSE_ID --reviewed
```

start检查本人归属和source=1，POST `study.do`（远端登记开始学习）→ POST `getCourseUrl.do`（读课程URL）。返回去除私有query的material_url，完整URL和开始状态存 `~/.local/state/ncut-web-api/safety/ACCOUNT/PROJECT/USER_COURSE.json`，0600。材料可能为HTML图片正文、交互页或视频，标题/HTML200不证明读取过内容，不能仅下载后自动声明reviewed。

认证仍用weiban精确origin的X-Token；材料URL目前只验收 `https://mcwk.mycourse.cn`。动态URL由平台实际返回，不是永久入口。当前SDK `https://mcwk.mycourse.cn/js/sdk.js` 的原生finish逻辑是GET JSONP `https://weiban.mycourse.cn/pharos/usercourse/v2/USER_COURSE_ID.do`，参数 `userCourseId/tenantCode/callback`。这个动态路由由专用适配器从已分配课程构造，不登记成通用request固定路径。JSONP只解析JSON，不执行服务端脚本。SDK若提供uniqueNo、验证码check、不同source或新路径，按实际证据扩展；不能伪造票据或跳过验证。

finish需要已登记的对应课程记录和实际材料reviewed声明；csCapt为true/未知时返回USE_NATIVE_CAPTCHA_FLOW，使用原生页面完成验证。已完成课程跳过提交。每次完成请求后重新查该分类，匹配精确userCourseId且finished=1才报告成功；HTTP200、code=0或已调用SDK都不能单独作完成判据。提交前保存submission_started_at；网络超时/未知响应先读回，不盲重发。后续finish调用只读回，仍未完成返回USE_NATIVE_COMPLETION_FLOW，转原生页面处理；重新start不会覆盖未决提交记录。不要凭空设定站点需要的时长，或伪造播放、学习时长。全项目最终使用showProgress.do，课程和两场考核均完成且项目达到100%才算整个任务完成。

个人材料、题目、截图和成绩只放本机私有状态。临时UI或OCR用于真实办理和内容读取，不建立新的爬虫项目/后台服务。考试契约单独验证，课程完成不代表考试已通过。
