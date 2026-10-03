---
id: safety-education-courses
service: weiban
keywords: ["安全微伴课程", "安全教育学习", "安全微课", "安全课程完成", "课程材料"]
status: runtime_verified
evidence: "2026-10-03 owner's assigned autumn project: category/course reads and native SDK completion independently read back; standalone course listing/start verified; completion now uses native pages and read-only verification."
runtime_verified_at: "2026-10-03T19:16:00+08:00"
transport: http
command: ["safety", "courses", "--account", "me", "--project", "USER_PROJECT_ID"]
requests: [{"method":"POST","path":"/pharos/usercourse/listCategory.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/listCourse.do","effect":"read","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/study.do","effect":"write","expect":"json","auth":"X-Token"},{"method":"POST","path":"/pharos/usercourse/getCourseUrl.do","effect":"read","expect":"json","auth":"X-Token"}]
note: "Use the assigned project/course IDs. Listing/start are verified; completion had limited success but batch starts triggered a one-hour platform lock. Read this contract before course starts; course completion stays in the native page and verify only reads its actual finished state."
---

# 安全微伴课程

2026-10-03观察到：批量登记多门开始学习后，部分完成请求返回code=0却仍finished=2，随后平台HTTP701，原生页面明确暂停学习1小时、解锁后按原方式重新进入（刷新提示页无效）。CLI直接完成适配器已撤除；此前的有限成功不能宣称整套批量学习稳定可用。逐门开始、阅读/观看/互动、完成并读回后再进入下一门；不能先批量start再finish。发生701即停止所有请求，按实际页面等待；不修改身份、网络或票据规避限制。

`safety status --account me --all` 给出本人任务的 `project_id`。课程列表先验证任务归属，POST `listCategory.do`，form含 `tenantCode/userId/userProjectId/chooseType=3`；对每个返回的 `categoryCode` POST `listCourse.do` 加该字段。不可省略categoryCode猜全量列表。`resourceId`映射为course_id，`userCourseId`映射为user_course_id，`finished=1`完成、2未完成；不猜UUID。

```bash
python3 "$NCUT" safety courses --account me --project USER_PROJECT_ID
python3 "$NCUT" safety course start --account me --project USER_PROJECT_ID --course COURSE_ID
# 在原生课程页实际完成阅读、视频、互动及课后题以后：
python3 "$NCUT" safety course verify --account me --project USER_PROJECT_ID --course COURSE_ID
```

start检查本人归属和source=1，POST `study.do`（远端登记开始学习）→ POST `getCourseUrl.do`（读课程URL）。返回去除私有query的material_url，完整URL和开始状态存 `~/.local/state/ncut-web-api/safety/ACCOUNT/PROJECT/USER_COURSE.json`，0600。材料可能为HTML图片正文、交互页或视频，标题/HTML200不证明读取过内容，不能仅下载后自动声明reviewed。

认证使用weiban精确origin的X-Token；材料URL目前只验收 `https://mcwk.mycourse.cn`，由平台实际返回，不能猜参数。课程资源既有旧版图文，也有通过额外JS记录翻页、互动及动态课后题的版本。SDK支持动态uniqueNo；静态HTML未出现它、csCapt=false，都不能证明完成链不需要这些原生步骤。必须通过实际课程页办理，不修改原生进度、时长或验证结果。

2026-10-03已用原生课程页完成互动与两道课后题，独立showProgress读回增加一门；这与先前单独SDK上报成功却读回未完成的条目不同。为避免误用，已撤除CLI直接完成上报；`course verify`只有读操作，返回finished和COURSE_FINISHED/COURSE_NOT_FINISHED。HTTP701停止请求并按原生页面等待解锁、重新进入；不是AUTH_REQUIRED。最终以showProgress.do核对课程与两场考核均完成、项目100%。

个人材料、题目、截图和成绩只放本机私有状态。临时UI或OCR用于真实办理和内容读取，不建立新的爬虫项目/后台服务。考试契约单独验证，课程完成不代表考试已通过。
