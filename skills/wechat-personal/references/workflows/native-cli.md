# 独立 Linux CLI

确定性的 Linux 微信数据库读取和原生控制已抽到独立[开源 wechat-linux-cli](https://github.com/gih10012/wechat-linux-cli)。skill 保留账号选择、意图路由、业务发现和发送授权。本机已真实安装自启动系统辅助服务，普通用户无需 sudo；`$WX native …` 和限时 OneBot 适配优先委托 `/usr/local/bin/wechat-linux`。只有未安装时保留旧入口，某次写入失败或超时绝不自动切换发送器。

## 日常调用

```bash
wechat-linux status
wechat-linux conversations --query '联系人或群名' --limit 5
wechat-linux messages --chat '精确 chat_id' --limit 20
wechat-linux service-status
wechat-linux send-text --recipient '精确 chat_id' --text '消息文字' --request-id '本次唯一ID'
wechat-linux send-image --recipient '精确 chat_id' --file '/路径/image.png' --request-id '图片唯一ID'
wechat-linux send-status --request-id '原请求ID'
wechat-linux inspect-pending
```

读取只覆盖本机已同步历史，使用现有私有密钥；普通查询不重新捕获。CLI 接受任意精确私聊/群聊 ID，写入授权由调用 agent 根据主 SKILL 判断。filehelper 和 ClawBot 长期授权，其他目标按当前任务或适用的事先直接/间接授权执行，已有授权不重复询问。未实测目标与授权缺失分别处理。

发送先做不发送消息的排队构造预检，再在同一 PID/启动时间调用客户端真实消息创建入口。服务串行执行，未知结果没有自动重试。同 ID/正文/目标返回原结果，冲突拒绝，既有低层 ID 仍保留防重。结果、确认及读取来自不同证据；客户端返回成功不等于接收端确认，数据库记录不推定 UI。用原 ID 接续 pending，不换 ID 重发或删除记录。

## 实际验收

2026-09-30 已通过一次私有排队高层 filehelper 发送，并完成系统服务安装、自启动启用及普通 CLI filehelper 真实发送。本人分别确认手机只收到一条、中文/换行/emoji 完整、Linux 窗口显示；数据库独立读回一条并取得服务器 ID。普通服务同 ID 防重、冲突拒绝及排队任务清理通过。

个人微信 CLI→ClawBot 的真实文字被 iLink 精确收到，ClawBot 回执在 Linux 本地数据库独立读回；两方向各一条且有服务器 ID。同 ID 重放没有新原生调用，工作产物内容和修改时间未变。普通用户限时 OneBot→安装服务的已有请求 HTTP 重放亦通过，未据此宣称一次新的 HTTP 提交验收。其他对象、文件/表情包/卡片、OneBot 事件、部署后的新密钥采集及长期稳定性未以文字验收覆盖。

首次安装器及私有离线更新实际运行过；更新保留旧包、等待当前任务安全结束，再替换代码并检查服务。公共安装器仍只支持首次安装。任意目标修正包已实际安装：安装清单、新 wheel 与安装的 16 个包文件一致，重启后的服务健康、CAP_SYS_PTRACE 及既有请求读取均通过。更新脚本曾在重启后的即时检查报错，独立核验确认部署完成；已补入只读就绪等待，不再次要求 sudo。

## 部署与数据

安装器默认只输出计划，`--apply` 才创建系统文件。构建和依赖下载在普通用户阶段执行，root 离线安装已校验 wheel；具体流程及启停见[CLI 服务说明](https://github.com/gih10012/wechat-linux-cli/blob/feature/highlevel-preflight/docs/service.md)。本机工程位于本人的 GitHub 工作目录下 `wechat-linux-cli/`。

| 位置 | 用途 |
| --- | --- |
| `/opt/wechat-linux-cli/` | root 所有的代码、复制解释器、旧/新 wheel 和安装清单 |
| `/usr/local/bin/wechat-linux` | 普通用户命令 |
| `/etc/systemd/system/wechat-linux-cli@<UID>.service` | 桌面 UID/GID，唯一能力 CAP_SYS_PTRACE，自启动 |
| `/run/wechat-linux-cli-<UID>/control.sock` | 本机控制；目录 0700、socket 0600，双方核对 UID |
| `~/.local/state/wechat-linux-cli/service/` | pending 及后端结果 |
| `~/.local/state/wechat-linux-cli/native-highlevel/` | 排队预检、请求、防重结果和独立确认 |
| `~/.local/state/wechat-linux-cli/native-send/` | 低层旧请求，存在更早目录时继续使用原位置 |
| `~/.local/state/wechat-personal/native-keys/` | 私有读取密钥，0600 |

服务 SIGTERM 等待原生调用结束；unit 不超时强杀 GDB，不自动重启。pending 或停止未完成时保留进程及记录，核对现有任务。回调模块留到客户端退出，不因任务完成卸载。发送后的单次空闲采样约 12 MiB、1 个任务，未承诺长期上限。独立后台消息接收器仍暂缓。

## 继续开发

旧同步协程入口曾导致客户端崩溃，保持关闭，不重试旧脚本。当前使用经真实验收的客户端任务排队、活动协程引用和生命周期检查；不直接写数据库伪造发送记录。版本签名、对象/回调生命周期和对应真实验收须同时满足后再开新入口。

`scripts/native_highlevel_probe.py` 是有界的高层只读观察工具，曾串起正常窗口文字请求→初始入库→本地 ID→回包更新；它不等于主动发送预检。新增 `observe --kind image --seconds 60` 区分公共请求字段和数据库消息类型，严格过滤实际观察到的图片类。两轮真实 UI 图片观察安全脱离，四个断点各命中一次，但旧过滤没有关联事件；已据真实请求类/字段值修正。合成 GDB 的字段区分、关联、无正文读取、SIGPIPE 处理及脱离通过，修正后的真实关联仍未验收；图片主动发送随后已通过普通 CLI 验收。它只读取生命周期字段，不调用发送函数；附加权限仍需本机 sudo。媒体继续开发需验证专用请求、上传及对象生命周期，不能仅修改文字请求类型。私有接续在本机 `next-actions.md`、`CONTEXT-PROOF-20260930.md` 和原生产物中；账号、正文、捕获与任务 ID 不发布。

2026-10-01 图片入口已接入普通 CLI 并真实部署。PNG/JPEG→ClawBot 均经单次 iLink 入站下载、字节一致、Linux UI 显示及本地新增图片记录验收；图片同 ID 防重及跨动作冲突拒绝通过。详见[图片契约](../capabilities/wechat/send-personal-image.md)。上文修正探针尚未重新做完整真实关联，仍是单独的观察器状态，不能据此否定后续主动图片验收。文件、表情包及卡片仍需各自验收。
