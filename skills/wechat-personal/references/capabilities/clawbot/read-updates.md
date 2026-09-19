---
id: clawbot-updates
service: clawbot
keywords: ["ClawBot", "QClaw消息", "微信机器人消息", "机器人新消息"]
exclude_keywords: ["企微", "企业微信"]
status: "runtime_verified"
runtime_verified_at: "2026-09-17T23:06:29+08:00"
transport: "ilink_https_third_party_sdk"
command: ["bot", "updates", "--account", "me", "--limit", "20"]
workflow: references/workflows/clawbot.md
note: "第三方 wechatbot-sdk 0.3.0 已实测扫码绑定、接收本人测试文字与游标复用。仅机器人通道，不是个人微信或企微收件箱；单次长轮询，无自动回复。"
---
# ClawBot 新消息

来源：[corespeed-io/wechatbot](https://github.com/corespeed-io/wechatbot) Python SDK `wechatbot-sdk==0.3.0`，核对 [腾讯协议](https://github.com/Tencent/openclaw-weixin/blob/43675b66551d12d6853155a7869a50fb12a18a1e/docs/protocol.md)。QClaw 桌面产品与独立 iLink 接入是不同入口，本项目采用后者。

`POST /ilink/bot/getupdates`，origin 来自实际扫码响应的 `baseurl`，默认 `https://ilinkai.weixin.qq.com`；认证为私存 `bot_token`。请求体含上次的 `get_updates_buf` 和 SDK 构造的 `base_info`。首次游标为空；仅采用当前 `get_updates_buf`，不回退废弃的 `sync_buf`。

真实成功响应可以省略 `ret`/`errcode`；要求两者缺省或为0、`msgs` 为对象数组、`get_updates_buf` 为字符串。错误、畸形响应和超时不推进游标，不当作“没有消息”。合法空批次只证明本次无新消息。`-14` 需重新扫码；请求最长40秒，不自动无限轮询。

输出原始消息ID、时间、发送人及文字项；媒体引用私存并输出`attachment_id`，文件另有名称与大小，不返回下载凭证或 `context_token`。未知项私存供后续按实际协议补能力。下载命令及已验证的文件/图片/语音范围见[媒体契约](media.md)。`--limit` 为1–100；超出本次输出上限的消息与新游标一起原子私存，下次先取本地剩余批次。每账号排他锁避免并发推进游标。命令是增量读取，不承诺已取出的历史可重放。无需桌面微信在线。

2026-09-17已用本人扫码登录，通过上述第三方SDK真实读取本人在 ClawBot 中发送的测试文字。只读工具未调用发送、正在输入或自动回复接口；个人微信历史使用 `native messages`，企微原生消息另行接入。

2026-09-19本人配合发送文件、图片及无说话的语音，真实入站保存媒体引用并完成下载。语音项中的文字来自服务端，明确标为未验证转写，不能把附带文字当作本人确实说过的话。
