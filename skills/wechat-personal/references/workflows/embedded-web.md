# 按具体业务接入 HTTP

已有服务：知识命中 → 用已保存的该域会话发请求 → 验证业务字段 → 返回结果。学校业务走 ncut-web-api；其他域登记到本 skill 的 services.json 和 capabilities/<service>。

找学校 Web 替代时先运行配套 `ncut.py catalog --alternatives --query '业务词'`。它直接从目录同一 action 的 Web/mobile 字段配对；再验证本人权限和业务对象是否一致。dynamic/fresh_entry_needed 不是没有网页版的证据。该目录只是已知学校服务范围，不能当作完整企微工作台清单。

动态入口继续用 `ncut.py catalog --resolve --account me --query '完整服务名'`。该流程已实测复用学校SSO打开学生羽毛球预约并取得真实site_id；会话过期先重走该入口，再查询日历。服务器明确返回tip时按权限/业务不可用处理，不要求重复登录。

首次缺项：

1. 从真实链接/消息卡片/已观察的入口确定业务域；页面、工具箱和小程序只是入口，不猜 OAuth 参数或域名。
2. 先看相关表单/接口定义/已有请求证据，首轮最多两个相关资源；仅确需认证或捕获请求时用一次本人正常操作。
3. 记录精确 METHOD/origin/path、query/body、参数来源、业务成功字段和最小结果投影。用本人该域会话完成一次实际请求验证后才标 runtime_verified。
4. 多步写“请求 A → 响应字段映射 → 请求 B”，稳定后优先复用 request；只为重复的编排/解析加小脚本。格式见 [API 契约](../../../ncut-web-api/references/api-contract.md)。

可独立复用的业务 Cookie/header 通过 `session import --account ALIAS --file 私有state.json` 保存，格式见 [会话格式](../../../ncut-web-api/references/workflows/session.md)。OAuth code/ticket 和客户端即时凭据不能固定进知识。每次仍需客户端签名的接口明确标注依赖；没有已验证的取得方式就报告这一缺项，不伪造接口或迁移到通用客户端适配。

正常命中不重新打开工作台。403 与登录失效区分；只读 POST 标 read，真正提交按当前用户授权和契约执行，结果不确定先回查。

## 学校移动页的已观察边界

2026-09-16，学校 `/EIP/weixin/weui/cooperate.html` 通过 RequireJS 主模块 `js/cooperate-main` 加载 `native-weixin`；相应 `js/native-weixin.js` 定义 `GET /EIP/weixin/jssdkapi.htm`，query `url` 为当前页面地址。响应 appId/timestamp/nonceStr/signature 交给 wx.config。这是客户端 JS-SDK 签名配置，不能当作本人 OAuth 登录、通用企微 token 或聊天权限；本次仅验证源码契约，没有把签名值写入知识。

同一次验证中，已保存学校 SSO 自动换票后，学生邮箱申请的 Web 入口能够返回“新建事项”页面，未发送申请提交请求；这证明该 Web 入口可以访问，尚未证明移动端字段/权限完全等价。

后续2026-09-16实测：大厅移动页 `POST /EIP/api/getUserAttributeForMobile.htm` 可直接复用学校SSO会话返回本人userId/userName，无需企微扫码；已沉淀 [移动身份子能力](../../../ncut-web-api/references/capabilities/hall/mobile-identity.md) 和 [移动路由转Web流程](../../../ncut-web-api/references/workflows/hall-mobile.md)。真正只有企微身份可用的业务，仍需从其实际 OAuth 跳转链取得 corp/app、redirect_uri、scope、state 和回调契约；不要将上述 jssdkapi 硬套为 OAuth 接口。
