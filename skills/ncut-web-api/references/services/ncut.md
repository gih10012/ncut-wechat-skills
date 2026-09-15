# 服务事实与证据等级

2026-09-01 会话只提供历史线索；2026-09-14 的直接 HTTP 结果才是本次实测。不要把旧会话结论全部升级为可用能力。

- `hall`：公开办事目录在 `/EIP/nonlogin/elobby/service/more.htm`。HTML 内 `vjson = mini.decode('JSON')` 有完整目录；空数组初始化后才出现真正列表。查询由同页 `search()` POST `/EIP/nonlogin/elobby/portal/services/list.htm`，form 字段见能力分片。办理链接从每条 `service[].blArr[].blpcurl/blmurl` 取，不能按名称拼接。
- `ywtb`：当前根入口 302 到站内 `/manage/common/login/index`。后续历史观察为学校 CAS。根入口跳转只证明入口存在，不证明登录成功。
- `jwxt`：历史 `/config.js` 设置 `loginType=CAS`、`keepOwnLogin=false`，本地登录页不能当通用密码入口。2026-09-14 凌晨访问失败，原因不得泛化成永久关闭。
- `mobile-jw`：用户给的是 `/yjs-dist/#/moreMenu`。历史前端从 `#/casLogin?...&token=...` 把 token 存入 `sessionStorage.Token`，再请求身份；这既不能证明本科账号可用，也不能证明 `/auth/wxcp/getUserInfo` 可直接拼在域名后。API base 要从当前 serverconfig/请求验证。旧直登曾失败，不重复试相同密码。
- `sso`：旧测试账号密码通过后要求短信 MFA；这不等于当前已登录。不得在普通业务读取时反复触发短信。
- `webvpn`：校外内网入口，跟随实际门户链接；不猜 URL 编码。`mail` 是另一身份域，不传播学校密码。

账号、姓名、学号、token、真实课表与成绩不属于本文件。以上是历史调查记录；当前课表状态以文末的白天实测更新为准，成绩仍待实际需求验证。

## 2026-09-14 白天的实际更新

- jwxt 是“本研公共服务平台”；实际本科课表经页面菜单调用 jwToken 换票后进入 **jwxtbk.ncut.edu.cn**。本科主页 /jsxsd/framework/xsMainV_10009.htmlx 的本人欢迎信息已核对；课表读取已经实际成功。不要再只检查 jwxt 的旧 qsmart 配置。
- 本科课表采用两次 GET 与本地解析，详见 personal-timetable 能力；真实课表仅保存在账号私有 results 目录。
- workflow 一层学生羽毛球场 site=596 已核对页面标题和实时日历；会话绑定浏览器 User-Agent 的差异已实测确认。正常调用需要保存 user_agent，详见 badminton-calendar 能力。
- 旧服务目录学生场馆的 token 参数是入口参数；当前 catalog 的通用敏感参数过滤会省略该办理链接。具体预约能力已登记并验证实际落地点，不能把 entries=[] 解释为不存在该服务。
