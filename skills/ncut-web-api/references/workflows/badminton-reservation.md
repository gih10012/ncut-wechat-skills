# 羽毛球 API 与本地验证草稿

输入：用户给出的日期、场馆和时段。已验证学生一层 site=596；其他 ID 从实际入口取得。查询不需要预先打开预约页面。

## 查询时段

GET `https://workflow.ncut.edu.cn/reservation/site/resource/calendar`，query：`id=<site>`、`collective=0`、`date=<JSON 字符串 {"start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD"}>`。

身份为本人 workflow 域 Cookie，并保留登录时捕获的 User-Agent；同 Cookie 换成通用 UA 曾返回 UN_AUTH。成功要求 e=OK 和 d.time/d.resource/d.data 结构有效。从 d.resource 取 resource_id/name，从 d.time 取 period_id/str_time，再关联 d.data[date][resource_id][period_id]。状态 0 可约、1 未开放、2 已过期、3 约满、4 不可约；num/total 保留原语义，不自行解释为占用人数。

直接 `reservation calendar --account me --site 596 --date YYYY-MM-DD`。AUTH_REQUIRED 时用 `login --service 预约` 恢复该服务身份，不循环重试。规则发生变化再局部查当前说明，不固定旧公告。

## 验证任务写入

`task draft --account me --intent '用户意图' --key UNIQUE_KEY --validation-only`：原子写本机 JSON 后回读，status=draft、enabled=false、validation_only=true。同 account/key 同内容幂等，异内容拒绝。没有学校写请求，也没有调度执行器。

## 远端订场尚未验收

先 `reservation rules --account me --site 596` 读当前配置。2026-09-15 本人 GET detail 实测 anti_bot=1、提交窗口12:00–17:00；日历在窗口外仍可读，不等于能提交。需本人预约验证的依赖尚未打通为可复用流程。规则/公告的日期范围文字有差异，不猜可预约范围；以实时日历和服务资格校验为准。

历史源码中 POST `/reservation/site/resource/launch` 的 form 为 `data=<JSON 数组 [{resource_id,period:[{date,period_id}],number:1}]>`、collective、captcha。这是历史线索，当前未列入可执行写能力；captcha 须来自真实验证流程。

真正提交须有用户明确目标、当次资源/时段/规则验证及实际认证，结果不确定先查本人预约。旧项目 POST /api/tasks 会创建可执行任务，不能拿它测试 disabled 草稿。当前不得声称已部署自动抢场或已验证学校写 API。
