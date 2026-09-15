# 本人课表：两次 HTTP

入口：`timetable --account me [--week current | --date YYYY-MM-DD]`；去掉筛选选项取得整个当前学期。身份为本人 jwxtbk 域 Cookie，无固定学号。

1. GET `https://jwxtbk.ncut.edu.cn/jsxsd/xskb/xskb_list.do`。从 xnxq 下拉框唯一 selected 项取学期；从 kbjcmss 中 mrms=1 项取 kbjcmsid；学校 week 下拉框提供周起点。不得按月份猜学期或采用自然周号。
2. GET `https://jwxtbk.ncut.edu.cn/jsxsd/framework/mainV_index_loadkb_10009.jsp`。query：`rq=all`、`sjmsValue=<kbjcmsid>`、`xnxqid=<学期>`、`xswk=false`。保留该账号有效会话。
3. 直接解析 HTML：首列大节/时间，后七列周一至周日；格内多个 person-class 各自保留。按学校周历、课程周次及单双周本地筛选；tbXs 未排时段课程单列。

成功要求控制页学期/模式有效，片段符合实际课表结构。未知周次/列结构明确报错，不能静默漏课。日期特定渲染曾超时，已验证稳定路径是全周次片段加本地筛选。

仅 `AUTH_REQUIRED` 才 `login --service 教务`，本人完成后 `login finish`，再恢复本流程。登录的门户菜单、SSO 跳转由认证脚本处理；正常课表查询无 UI 步骤。
