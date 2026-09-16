# 目录项 → 当前票据 → 业务接口

1. 使用大厅已有会话；失败优先复用学校SSO换票，见服务收藏中的认证步骤。
2. POST `/EIP/nonlogin/elobby/portal/services/list.htm`，form `keyword=完整服务名`，精确且唯一地选取返回id。
3. GET `/EIP/nonlogin/serviceHandleCenter/openService.htm?sid=<该id>`。源码 `openServiceItem` 使用同一路径。needToLogin明确为真返回AUTH_REQUIRED；tip非空表示服务器限制/不可用，保留提示并停止；不能绕过提示直接使用旧目录URL。
4. 对返回url执行最多6跳的已注册HTTPS跳转，复用CookieJar，更新私有会话。带票据入口和最终URL存放在私有entries目录，普通结果只输出无query的路径和允许的业务参数，不把token写入知识。
5. 若落在已验证的workflow预约页，从实际query取得id，然后GET `/reservation/site/resource/detail?id=<id>&collective=0`，要求e=OK且详情id一致，再返回业务名称及后续calendar命令。其他落地页只标business_verified=false，继续按该业务的实际源码/API验证。

当前预约登录态过期而SSO仍有效时，可先用此命令重走真实服务入口，再重试原calendar/rules查询。不需要用户再扫码。只有SSO也确实无法续接才使用统一登录入口。

不把纯HTTP200、空壳页面或目录名称配对算业务成功。不自动打开未注册域或HTTP降级入口，不执行页面脚本，不提交表单；它是可复用的入口/认证流程，不是预约写入。
