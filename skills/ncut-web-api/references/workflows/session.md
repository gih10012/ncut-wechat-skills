# 一次登录，后续直接调用

跨会话先用 `login status` 读取已保存的目标服务；有待登录任务时才查询现存专用浏览器。输出 `qr_expired` 表示学校认证 iframe 的二维码已失效，需本人在窗口刷新并扫码，或改用学校密码/短信登录；`business_page_or_unknown` 仍须 `login finish` 做真实接口验证。没有待登录任务时不探测浏览器，也不为普通查询运行 status。

## 不依赖会话历史的入口

- `python3 "$NCUT" login --service 教务`：默认账号 me；有效登录直接返回 LOGIN_READY，失效时打开现有私有 Chrome profile。预约用 `--service 预约`。需要明确打开窗口时加 `--open`，不会退出原账号。
- 用户在真实页面完成登录/短信验证，然后回复“已登录”。运行 `python3 "$NCUT" login finish`，自动读取 `~/.local/state/ncut-web-api/login-pending/me.json` 中的目标服务，捕获 Cookie 与 User-Agent 并验证对应只读接口。教务需要门户换票时按已记录菜单自动续接；验证成功后关闭专用浏览器。
- `login status` 只返回是否有待续接登录和本地状态，不探测所有站点。正常业务查询不先执行 login。网络故障不会自动变成反复登录；未知服务未验证时不能宣称 LOGIN_READY。
- 若同时有学校和微信待登录且“已登录”指代不清，只询问是哪个窗口，不要求重述任务或账号配置。

2026-09-14 已完成这条入口的真实验收：本人登录后，`login finish` 自动点击“本科生 → 选课&课表 → 学生个人课表”，保存会话，返回 LOGIN_READY 并关闭专用浏览器。关闭后再次直接 HTTP 读取当周课表成功。切换“本科生”是新登录后的必要步骤，不能直接在默认本研公共服务页找本科菜单。

正常读取不打开浏览器。`session status --account me` 只看本地是否保存，不反复检查所有站点。当前普通会话状态在 ~/.local/state/ncut-web-api/accounts/me.json，目录 0700、文件 0600，包含 Cookie、精确 origin 的认证头（如有）和捕获时 user_agent。

首次或过期时，本机已有 Chrome + Node 可直接使用：

```bash
node scripts/browser-session.mjs open me jwxt
node scripts/browser-session.mjs status me
node scripts/browser-session.mjs capture me
node scripts/browser-session.mjs close me
```

open 使用独立的私有 Chrome profile；不会修改用户平常的默认浏览器资料。本人在页面完成学校登录/MFA，agent 完成业务导航；进入所需业务并核对身份后 capture。capture 保存 cookies 与该浏览器 User-Agent，只回显数量/无敏感参数页面路径，不证明业务已成功。实际接口读取成功才算验收。close 关闭这个专用浏览器，普通 HTTP 查询继续可用。

有图形会话时首次登录弹出窗口。无图形环境可用已有会话纯 HTTP；`open ... --headless` 仅用于已有可用登录资料或受控诊断，不声称它自动完成人工 MFA。未使用外部设备作为运行节点，也不要求新容器/加密卷。

其他本人浏览器状态可通过 `session import --account me --file /私有目录/state.json` 导入。兼容 Playwright cookies；可选 `headers` 为精确 origin 对认证/CSRF头的映射，`user_agent` 应保留该会话真实浏览器值。localStorage/sessionStorage token 只有在请求已证明其用法后才映射到 header，不能猜 token 字段。临时导入文件需 0600，用完删除自身临时文件。

**预约平台特例已实测**：workflow 的同一 Cookie 在原浏览器 User-Agent 下 e=OK，换用通用脚本 User-Agent 则 e=UN_AUTH。不要因为这个异常反复登录；保留 user_agent 就能直接 HTTP 调用。

HTTP 客户端不自动跟随任何重定向，防止 bearer/请求体错误转发。CAS ticket 流转在登录浏览器中完成，然后 capture。服务若轮换 Cookie/token，恢复该目标页面并重新捕获；私有响应不存进知识库。

实现依据：[Chrome 独立调试资料目录](https://developer.chrome.com/blog/remote-debugging-port)、[Chrome DevTools Storage 协议](https://chromedevtools.github.io/devtools-protocol/tot/Storage/)。这里的 profile 只是普通本机文件夹，不是虚拟卷。

2026-09-15 修复：专用 Chrome 重开会丢弃会话 Cookie。新窗口现在先开空白页，将账号文件中有效且属于学校域的 Cookie 恢复后再访问入口；已有窗口只补缺失项，保留其新 Cookie。本次补回缺失 SSO Cookie 后无需本人再次认证即进入教务并完成 finish。`login start` 不再将单纯开窗标为需要用户登录；只有实际认证页未恢复时才交接。4 项 Cookie 恢复行为测试通过。
