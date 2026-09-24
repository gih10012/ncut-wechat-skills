# 独立 Linux CLI 接续

按本人要求，确定性的 Linux 微信数据库读取和原生控制已抽到独立[开源 `wechat-linux-cli`](https://github.com/gih10012/wechat-linux-cli) 开发预览。skill 保留账号选择、意图路由、业务发现和授权范围。当前尚未全面切换：既有日常读取与已验证的 OneBot 入口继续使用，不能因为代码已抽出就宣称新服务写入已验收。

本机工程位于本人的 GitHub 工作目录下 `wechat-linux-cli/`；部署说明为该项目 `docs/service.md`，安装器为 `src/wechat_linux_cli/install.py`。安装器默认只输出计划，`--apply` 才写入 `/opt`、命令和 systemd unit，并启用自启动。

2026-09-24已实际验证：最新 wheel 与源码一致；普通用户离线安装后，从仓库外以隔离 Python 模式读取现有账号成功；临时 Unix 服务 health、无权限拒绝、SIGTERM退出及 socket 清理通过。原生调用的合成 GDB 生命周期、读取与安装器共56项测试通过（1项仅CI root场景跳过），公开仓库最新CI成功。这些证据不覆盖 CAP_SYS_PTRACE 系统服务部署、真实密钥采集或新服务发送。

目标日常命令：

```bash
wechat-linux status
wechat-linux conversations --query '群名或联系人' --limit 5
wechat-linux messages --chat '精确 chat_id' --limit 20
wechat-linux service-status
wechat-linux send-status --request-id '已有请求ID'
```

发送通过 Unix socket 请求已安装的辅助服务，服务以桌面 UID 加 `CAP_SYS_PTRACE` 运行，使用 root 所有的安装代码。读取继续直接用现有私有密钥；已有发送 request ID 保留在原私有目录，不迁移或清空防重记录。发送授权、身份和对象范围仍按主 SKILL 执行。

实际系统安装仍需本机 sudo，当前会话的非交互 sudo 要求密码。可审阅的安装计划已生成；在本地显示修复路径进一步确定后，由本人在终端执行 `docs/service.md` 的一次性安装命令。不把缺少 sudo 密码当成缺少发送授权。

本地显示的缺项已缩小到客户端自己的消息生命周期：初始创建 → 客户端 DB 插入/取得本地 ID → 替换发送上下文中的消息对象 → 网络提交 → 回包更新及通知。底层网络发送已获手机收件确认，但此前绕过前半段。2026-09-24 本人 Linux 窗口的高层只读探针把同一条文件传输助手文字的业务请求、初始入库、本地ID分配、回包更新串联起来：初始ID 0 → 本地ID 57 → 状态2及服务器ID，原生更新参数 `update_type=1, notify=1`。四个事件均在同一原生线程，探针安全脱离；实际 UI 调用栈经过 `0x708a0c0 → 0x64d57c0 → 0x64c7bd0`。此前本人已确认正常窗口发送在Linux窗口持续显示且仅一条。这些是正常窗口发送的实测基线，**不是 CLI 原生发送的修复验收**。实际 `TextMessageHandler` 不走先前误认为通用文字 sender 的断点。静态副本也已找到 JSON 文字业务请求汇入该入库链的路径，但主动调用的线程、对象及回调生命周期尚未运行验证；不得用直接 SQL 补写或仅刷新界面作为修复。

仅在继续本地显示修复时，`scripts/native_highlevel_probe.py` 可做有界、只读的高层请求→入库→本地ID→更新关联观察。它已通过合成 GDB 测试、固定 ELF 签名核对及上述一次真实观察；不要把探针或现有低层发送标为本地显示已修复。

私有当前证据与待本人协助事项位于 `~/.local/state/ncut-wechat-skills/next-actions.md`；详细静态报告位于该目录的 `source-review/hook-port/local-history-analysis/REPORT-20260921.md`。只有继续此开发任务才读取这些材料，不让普通查询重新展开逆向工作。
