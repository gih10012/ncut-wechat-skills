---
name: wechat-personal
description: 探索、验证并复用本人微信和企业微信的消息、公众号及内嵌业务能力；新上下文可从现有客户端、服务入口和请求证据接入新 API 并生成子能力。当前已验证公众号和部分学校 Web，原生消息仍待接通。
---

# 微信 / 企微信息入口

目标是意图 → 对应业务 API → 结果。忽略不必要的前端；来自工具箱、工作台、微信链接或小程序的业务，按实际后端服务归档。下文 `$WX` 是本 skill 的 `scripts/wechat.py` 绝对路径。

既能使用已有能力，也负责独立摸索新能力。用户无需先找到 API 或提供专门示例：先查注册表、已有客户端/业务目录和当前请求证据；只有缺少业务选择或本人认证时才询问。`not_connected` 是未验证状态；用户要求接入时继续按相应发现流程工作，不能把历史失败当作永久结论。

## 最短调用

- 给出公众号链接：`python3 "$WX" article --url '真实链接' --max-chars 6000`。结果仅覆盖页面文字层，图片正文按需读取。
- 学校信息：直接使用同套 [ncut-web-api](../ncut-web-api/SKILL.md) 的课表、场地余量或对应接口；不先启动微信/企微。
- 其他业务：`python3 "$WX" knowledge --query '具体需求'` 返回命中的命令、接口、状态和契约路径，默认不展开子流程。`command` 是脚本参数数组，按用户输入替换占位符。命中真实可用契约就 `request`，正常结果即结束；细节仅按能力 ID 加 `--details` 或读对应文件。
- 原生群消息/私聊：先读取命中能力和 [消息接入](references/workflows/messages.md)，核对当前客户端/会话或可调用接口。现有记录仍为 `not_connected`；接入任务须独立探索并验证收发，不能拿公众号或截图代替。保留手机和 Linux 登录，避免把一次消息请求扩大成容器工程。

新内部网页按 [业务 API 接入](references/workflows/embedded-web.md) 处理，确实只有小程序入口时才看 [小程序边界](references/workflows/mini-program.md)。缺项发现限于当前业务请求，不把查询扩大为通用客户端工程。

优先级：v0 通用 Web 写请求与预请求/读回示例；v1 本人消息收发和公众号；v2 实际观察到的微信深链；v3 先从学校 Web 寻找企微服务的等价入口，无替代再处理该业务的 OAuth。不能因为目录名称相同就认定数据和权限等价。

## 登录与本机状态

业务会话在 `~/.local/state/wechat-personal/accounts/`，0700/0600；与学校 skill 共用标准库 HTTP/检索模块，两者一起安装。普通业务请求不依赖旧 wechatcopilot、加密卷、Android 容器或常驻服务。

学校登录：`login --platform school --service 教务`（或预约），本人完成后 `login finish`；平台/服务保存在本机。微信/企微原生登录 `login --platform wechat|wecom` 默认保留手机与 Linux 登录及桌面，目前明确返回伴随端未配置，不能声称已能生成可用二维码。只在登录任务需要时读 [认证入口](references/workflows/login.md)。

旧客户端和当前窗口工具只作显式人工诊断入口；普通能力查询不召回其操作流程，不自动启用。用户明确要求使用现有 Linux 窗口时才读 [窗口读取](references/workflows/visible-wechat.md)，且只说明当前一屏覆盖范围。

## 记录已打通的 API

按 [共享契约格式](../ncut-web-api/references/api-contract.md) 写业务域、method/path、query/body 参数来源、会话来源、返回字段和成功/失败判断。多步子流程写请求 A → 从响应取值 → 请求 B；不写“打开工具箱点第几项”，不另建大量顶层 skill。动态 code/ticket 不写成永久入口，不保存 token 或消息正文。

`runtime_verified` 只标实际成功的范围；源码线索、接入流程、本地草稿和客户端截图各自标明。正常命中不重验全平台、不写知识。发送/提交须在用户明确授权范围内；当前没有原生聊天发送成功的证据。详见 [验收记录](references/verification.md)。
