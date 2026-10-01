---
id: read-user-moments
service: wechat
keywords: ["指定人朋友圈", "某人朋友圈", "某个好友朋友圈", "个人朋友圈", "好友朋友圈", "相册历史"]
exclude_keywords: ["发朋友圈", "发布朋友圈"]
status: "runtime_verified"
evidence: "Exact author filtering and normal Linux album loading to an explicit one-month visibility footer, with 48 full local entries read back on 2026-10-01"
runtime_verified_at: "2026-10-01T13:16:00+08:00"
workflow: references/workflows/moments.md
transport: "local_sqlcipher_readonly_with_normal_client_gui_hydration"
command: ["native", "moments", "--account", "me", "--user", "EXACT_USER_ID_OR_UNIQUE_FULL_NAME", "--limit", "20"]
note: "指定人默认20条，--cursor续页，--all读取其全部已加载历史；未缓存历史使用computer-use打开本人可见的好友相册加载。遵守展示时间/权限限制，旧缓存及置顶历史单独说明。"
---
# 指定人的朋友圈

调用`native moments --user '精确微信用户ID或唯一完整联系人名称'`；同名或无法精确匹配返回`MOMENTS_USER_NOT_UNIQUE`，不自动选择。返回`user_id`作为后续稳定筛选依据。已知精确联系人ID没有缓存时返回空列表，不据此判定此人没有朋友圈。

分页、全部历史、完整字段、XML、快照与失败判断沿用[动态读取契约](read-moments.md)。游标不能混用于动态流、另一账号或另一用户。未读标记不因CLI查询改变；正常GUI浏览可能改变客户端自身浏览状态。

需要新鲜或全部可见历史时用computer-use在当前微信打开该联系人资料的朋友圈入口，确认可见作者/资料身份，再按[朋友圈工作流](../../workflows/moments.md)逐页加载和CLI读回。明确记录仅展示一个月/半年、无权限、没有更多等实际窗口边界，置顶旧帖不证明普通旧帖可见。48条实测包含本机此前留存旧缓存，不把它们都称为当前窗口可见；没有绕过访问范围或发起新设备登录。
