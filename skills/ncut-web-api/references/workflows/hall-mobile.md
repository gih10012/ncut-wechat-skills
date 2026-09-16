# 大厅移动业务复用学校 Web 身份

首次进入某个大厅移动业务：先调用 mobile-identity。若会话失效，执行 `login --service hall --account me`；它先验证大厅身份，尝试已保存学校 SSO 的 HTTP 换票，仅真正需要本人认证才打开登录。完成后重新调用身份接口。不要先要求企微扫码。

预请求是 `POST https://service.ncut.edu.cn/EIP/api/getUserAttributeForMobile.htm`，空body；返回非空 userId/userName才继续。2026-09-16实际取得本人身份，保存的SSO自动换票成功。接口只属于学校大厅，不能推广为所有企微应用的登录方式。

当前 `/EIP/weixin/weui/js/cooperate-main.js` 的 `showNewFormView` 明确定义移动路由 `#new/form/:flowKey`（或 `#new/form/new/:flowKey`）对应 Web 地址 `/EIP/cooperative/openCooperative.htm?flowKey=<同一key>`。因此从真实目录/卡片取得这种学校链接时，可以按源码映射到 Web 入口，再核对本人权限和实际业务名称；无需为这类路由启动小程序。仅支持这里观察的 new 类型，不把 draft/detail 当成新建，不猜其他业务路由。

表单后续接口仍按当前源码和业务参数验证。JS-SDK 签名、本人身份和具体业务权限是分别验证的步骤；已有学校SSO满足的页面不需要新增OAuth层，无替代的企微业务仍按自己的实际跳转链接入。
