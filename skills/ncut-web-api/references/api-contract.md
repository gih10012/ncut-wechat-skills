# 可复用 API 能力与多步子流程

能力文件只保留实际调用需要的内容。扁平 frontmatter 用 JSON 数组/对象，供标准库脚本读取：

- `id/service/keywords`：紧密的业务能力与意图词。
- `status/evidence/runtime_verified_at`：区分 runtime_verified、source_verified、workflow_ready、not_connected；验证范围与时间真实。
- `transport`：http、auth、local、manual-ui 或 unavailable。截图/本机草稿不计入业务 API 成功。
- `command`：传给本 skill 脚本的参数数组；只用已存在命令，占位参数在 note 中解释。`note` 保留一两句决定调用行为的信息。
- `requests`：已观察的精确 method/path/effect/expect，身份要求可写 auth；供 request 校验。带动态路径的专用适配器在正文写实际 URL 来源，不把路径占位符登记为已验证路由。
- `workflow`：确需多步时链接一个子流程；默认检索只返回路径。

正文/子流程按下列顺序写，避免复制前端操作：

1. 输入及来源：用户选择、上一步响应、配置常量；不猜 resource_id、学期、账号 ID。
2. 认证：精确业务 origin、Cookie/header/原始 User-Agent，过期识别与登录入口；凭据只在私有状态文件。
3. 请求：METHOD + 完整 origin/path，query、form 或 JSON 及 Content-Type。
4. 响应映射：从哪些字段取下一步参数/最终数据，分页、时间范围、缺省字段的处理。
5. 验收：业务成功字段和数据语义，HTTP 200 或 JSON 可解析本身不够。
6. 副作用与失败：read/write、本机写入或远端提交、幂等键/回查方式；超时不盲重试提交。

例如课表：GET 控制页 → 提取实际学期和节次模式 → GET 课表片段 → 本地解析周次/单双周。HTML 是有效 HTTP 响应格式，不要求先改造出 JSON 接口。

脚本仅用于已重复的参数编排、解析或认证。新单接口优先复用 request，不另建项目、DSL、后台或爬虫。只有登录确实依赖界面才在认证资源记录必要操作；业务子流程不再重复登录页面步骤。
