# 按具体业务接入 HTTP

已有服务：知识命中 → 用已保存的该域会话发请求 → 验证业务字段 → 返回结果。学校业务走 ncut-web-api；其他域登记到本 skill 的 services.json 和 capabilities/<service>。

首次缺项：

1. 从真实链接/消息卡片/已观察的入口确定业务域；页面、工具箱和小程序只是入口，不猜 OAuth 参数或域名。
2. 先看相关表单/接口定义/已有请求证据，首轮最多两个相关资源；仅确需认证或捕获请求时用一次本人正常操作。
3. 记录精确 METHOD/origin/path、query/body、参数来源、业务成功字段和最小结果投影。用本人该域会话完成一次实际请求验证后才标 runtime_verified。
4. 多步写“请求 A → 响应字段映射 → 请求 B”，稳定后优先复用 request；只为重复的编排/解析加小脚本。格式见 [API 契约](../../../ncut-web-api/references/api-contract.md)。

可独立复用的业务 Cookie/header 通过 `session import --account ALIAS --file 私有state.json` 保存，格式见 [会话格式](../../../ncut-web-api/references/workflows/session.md)。OAuth code/ticket 和客户端即时凭据不能固定进知识。每次仍需客户端签名的接口明确标注依赖；没有已验证的取得方式就报告这一缺项，不伪造接口或迁移到通用客户端适配。

正常命中不重新打开工作台。403 与登录失效区分；只读 POST 标 read，真正提交按当前用户授权和契约执行，结果不确定先回查。
