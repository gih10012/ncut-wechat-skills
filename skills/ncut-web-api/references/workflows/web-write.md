# Web POST 写入：新上下文可复用的请求链

先从用户意图确定目标和允许的副作用，读取匹配契约；缺项时从实际表单、前端调用或接口定义取得当前 method/path/body。POST 也可能只读，必须按服务语义分类。下面是写入子能力的结构，不是通用授权。

## 预请求 → 提交 → 读回

1. 读取本人身份和目标当前状态。已登录其他校园服务不证明本服务身份有效；原会话能够换票时直接续接。
2. 如果当前源码确实需要 CSRF、初始化表单、验证码或版本号，先调用相应预请求，从实际响应提取当次值，放在私有状态/请求体文件中。无需这些字段的接口不凭空增加预请求；也不为模仿浏览器自动发送 OPTIONS。
3. 构造精确 JSON 或 form。普通 API 用 `request --body-file` / `--form`；重复的多请求步骤再封装短命令。服务要求 application/x-www-form-urlencoded 时不能把 JSON 对象直接作为原始 body。变量名、必填/可空/枚举和嵌套 JSON 字符串必须源于当前接口。
4. 执行已授权写请求；检查业务成功字段，再 GET/查询 POST 读回对应对象。遇到网络超时或非幂等结果不明，先读回，不能盲重发。
5. 验证用途优先选能恢复的本人状态，保存操作前状态并确认恢复；实际订场和发消息只有在目标与内容获授权时执行。mock、本地草稿、dry-run 都单独标注，不算远端写入。

## 示例：学校服务收藏

当前页面源码的流程是 POST `nonlogin/login/isLogin.htm` → POST `elobby/{实际服务ID}/fav/yes.htm`；取消为 `fav/no.htm`。从本人服务列表的 `isf` 读前后状态。前端动态 ID 来自目录响应，不能写死某个人的历史对象；完整示例的验证状态以对应能力文件为准。

## 示例：羽毛球订场的前置验证

读当前资源配置与日历 → 选择实际 resource_id/period_id/date → 必要时 GET slide-captcha 取得当次挑战，由本人完成验证后 POST slide-captcha-check → POST resource/launch → 查询本人预约记录。验证码和一次性签名不进子 skill；没有完成验证码与真实订场就只标 source_verified。

旧 crawler 的 launch 使用 form：`data` 是包含 resource_id、period、number 的 JSON 字符串，另有 collective、captcha。它是参考线索；最新前端可能增加 data_colle、code 或其他字段，执行前必须局部核对。旧 `/api/tasks` 会创建可执行排程，不能用它冒充无副作用的验证草稿，也不需要为了复用此请求再启动整套 crawler。

## 总结为子 skill

能力分片填 method/path/effect、参数类型与来源、认证/预请求 workflow、成功字段、读回/恢复接口和 source 证据。只在真实业务和读回成功后标 runtime_verified。另一次新会话应仅凭该分片和已有私有登录态复现，不能依赖这次对话中的 ID 或临时脚本。
