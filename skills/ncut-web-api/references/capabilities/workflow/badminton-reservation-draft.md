---
id: badminton-reservation-draft
service: workflow
keywords: ["预订任务", "预约任务", "抢羽毛球", "抢场", "任务草稿", "验证任务"]
status: runtime_verified
evidence: "Local disabled draft persisted atomically, reread and checked; no school write or scheduler activation"
runtime_verified_at: "2026-09-14T12:06:37+08:00"
workflow: references/workflows/badminton-reservation.md
transport: "local"
command: ["task", "draft", "--account", "me", "--intent", "<用户任务意图>", "--key", "<唯一任务键>", "--validation-only"]
note: "仅写本机 disabled 草稿并回读；没有学校写请求、定时执行器或真实订场验收。"
---
# 创建可审阅的羽毛球预订任务草稿

`task draft --account me --intent '用户的任务意图' --key 唯一逻辑任务键 --validation-only`

本能力是**本地任务写入**，不是对学校发订场 POST，也不是运行中的抢场任务。保存 status=draft、enabled=false、validation_only=true；回读验证一致才成功。同一 account/key 的同内容重试返回原任务，不新增；同 key 不同内容拒绝。

查看 `task show ID` 或 `task list`。任务文件在 ~/.local/state/ncut-web-api/tasks，0600，不存在隐式执行器。真实预约还缺日期/时段/场馆、当前资源匹配、必要验证和实际订场授权；不能把这个草稿称为可执行或预约成功。
