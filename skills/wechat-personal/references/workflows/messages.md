# 本人消息接入与缺项

Linux 微信本地读取已接通：正常需求直接用 `native conversations` 定位和 `native messages` 查询，见 [本机消息](native-linux.md)。身份、会话定位、正文解码和读回已可复用，不重新探索或捕获密钥。

2026-09-21个人身份经OneBot向文件传输助手发送文字已端到端验证；本人确认仅收到一条，中文、换行与emoji正常，同ID重放未重发。直接使用[filehelper文字契约](../capabilities/wechat/send-filehelper-text.md)。共享参数化后端已真实运行，独立`native send` CLI写入未在本轮验收；状态只读使用`native send-status --request-id '原请求ID'`。本地回写未接入，不能因Linux历史缺失否定手机投递或重发。

剩余缺项是其他原生收件人、OneBot事件、本地回写、媒体和企微消息，见[通用发送契约](../capabilities/wechat/send-message.md)。仅当前任务需要时，检查实际客户端、可调用工具或当前接口源码中的局部新证据；旧后台失效只排除该条路径。单项新能力累计探索15分钟即收束，报告证据与缺项，不重跑已有失败枚举。界面只用于登录和观察接口；不开发聊天窗口点击/输入作为业务发送路径，也不为补发送重建读取链、旧伴随端或容器。

2026-09-16当前 Linux 4.1.1 发送探索：没有观察到属于微信的监听TCP/Unix发送服务；可遍历的D-Bus仅托盘和菜单，辅助功能总线返回连接拒绝。二进制出现 `micromsg.SendMsgRequestNew` 与 `/cgi-bin/micromsg-bin/newsendmsg` 只证明内部符号存在，未获得请求序列化和认证契约，不能裸HTTP调用或据此标已接通。本地可精确定位 filehelper，但未发送测试消息。再次接入优先寻找当前版本新增证据，避免重复同一轮枚举。

已排除的版本错配例子：[jwping/wxbot](https://github.com/jwping/wxbot) 的Linux路径是Docker/Wine运行Windows3.9；[lmclmc/linux-wechat-hook](https://github.com/lmclmc/linux-wechat-hook) 要求旧1.0测试版。它们不证明本机4.1.1可直接使用，不自动替换或降级现有客户端。

收消息：从真实会话列表取得会话 ID，再读取有上限的近期消息，核对实际来源和时间。发送：当前原生入口仅支持filehelper文字；扩展其他目标时根据用户指定对象定位同一会话ID，执行前核对目标与内容。个人身份向filehelper和ClawBot已有长期授权；其他对象须本人明确口头或事先授权，具体发送请求即为其范围授权。返回任务号和零错误回调不单独证明投递，收件端证据另行记录；超时先读同一request-id的状态和接收端，不因本地历史缺失自动重发。没有实际运行或收件证据的范围不能宣称验收通过。

认证、会话定位、读取、发送各自有可复用接口才拆成子能力；共同的本机会话取得方式只写一个 workflow。独立设备登录只在证明能保留用户现有设备会话后采用；若需要本人扫码，先完成可交接的最小登录入口，再请本人操作。

2026-09-18本人要求再尝试轻量OneBot；已核对的普通微信后端及ClawBot桥接实测见 [OneBot尝试](onebot.md)。普通好友/群聊的发送仍未接通，不把机器人桥接当作完整原生收发。

2026-09-19当时按新版4.1.13复查：本地读取和ClawBot会话读回正常，补充OneBot机器人通道收发通过；原生发送仍缺外部可调用契约。内部`message::send_text_message`字符串及Unix IPC仅为线索，不是已验证API。随后原生入口及filehelper文字OneBot发送已接通，当前范围以本页开头及[原生发送流程](native-send-port.md)为准；历史候选见[OneBot记录](onebot.md)，不重复4.1.1的版本判断。
