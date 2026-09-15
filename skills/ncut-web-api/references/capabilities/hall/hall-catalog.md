---
id: hall-catalog
service: hall
keywords: ["服务", "入口", "办理", "目录", "邮箱", "预约", "查学校", "成绩单"]
status: runtime_verified
evidence: "https://service.ncut.edu.cn/EIP/nonlogin/elobby/service/more.htm; inline vjson and service[].blArr[]"
runtime_verified_at: "2026-09-14T00:14:13+08:00"
requests: [{"method":"GET","path":"/EIP/nonlogin/elobby/service/more.htm","effect":"read","expect":"html"}]
transport: "http"
command: ["catalog", "--query", "<业务关键词>", "--limit", "8"]
note: "公开 GET，按关键词筛选真实办理入口；目录命中不等于个人业务查询已打通。"
---
# 按需求查学校服务与办理入口

直接 `catalog --query '关键词' --limit 8`，无需登录。脚本解析同页真实目录、按关键词本地过滤，输出服务名、部门、实际办理入口。办理入口可能有副作用，查目录不自动跟进办理。

完整列表保存在 references/catalog.json，仅首次或目录实际变化时更新；不要为查询读整个 JSON。`catalog --cached` 显式用旧目录并返回验证时间。没有结果先用更短的业务词；空目录/HTML 结构改变视为异常，不能报告“学校没有这些服务”。
