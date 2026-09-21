---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信", "原生发送", "文件传输助手发送", "发送状态", "个人身份发送", "给ClawBot发", "向ClawBot发", "给ClawBot发消息", "向ClawBot发消息"]
exclude_keywords: ["企微", "企业微信", "机器人身份"]
status: "partially_verified"
transport: "pinned_linux_native_client"
workflow: references/workflows/native-send-port.md
note: "2026-09-21本人确认手机收到原生身份向文件传输助手发送的固定文字；本地回写未接入。native send-status只读已有结果；native send参数路径、OneBot、其他收件人和媒体尚未实测，不能因一次验收标为通用可用。"
---
# 个人微信身份发送

2026-09-21本人确认手机文件传输助手收到此前Linux主动发送的固定文字。私有结果为`trial_finished`、`recipient_delivery_verified=true`：ppoll预检、网络服务链和原生请求往返检查通过，真实提交后收到一次零错误完成回调，回调对象已释放，客户端运行且已脱离调试器。这是首次原生个人身份文字投递验收；仅覆盖锁定Linux版本和该次filehelper文字。普通好友/群聊、个人身份向ClawBot发送、媒体及OneBot原生发送均需单独验收。

此次文字在Linux本地历史中未找到，当前发送适配尚未接入本地消息回写。手机收件确认与本地历史缺项分别记录，不能因此否定投递、重复发送或要求重新验收。

## 调用与状态

下文`$WX`为本skill的`scripts/wechat.py`绝对路径。先读取已有结果；这不会附加微信或发送消息：

```bash
python3 "$WX" native send-status
python3 "$WX" native send-status --request-id '原请求ID'
```

无request-id时读取已验收的固定试验。新增可传文字的入口如下，当前只面向filehelper；参数路径尚未在本人微信实际发送验收，不能把固定试验成功当作此命令每次成功：

```bash
sudo python3 "$WX" native send --text '消息文字' --request-id '本次唯一ID'
```

入口复用当前桌面微信唯一主进程和登录，默认目标为filehelper；底层`--recipient`可指定1–128字节的精确原生ID（ASCII字母、数字、`_.@-`），不接受显示名。其他目标尚未验收，执行前须满足下方授权规则并从已有会话读取精确ID。依赖匹配的二进制、系统GDB/GCC及本机调试权限；入口、前置检查和系统权限说明见[原生发送流程](../../workflows/native-send-port.md)。request-id须为4–80个ASCII字母、数字、点、下划线或连字符，首字符为字母或数字；文字为1–1024个UTF-8字节且不含NUL。一次操作固定使用一个request-id，相同正文、目标和模式的已有请求只返回记录，不重复提交；内容冲突拒绝。状态不确定先读同一ID及接收端，不删除防重记录或凭本地历史缺失重发。

`submission_entered`、客户端`task_id`和零错误回调均不单独代表送达；`recipient_delivery_verified`记录独立收件证据。`worker_pending`或`callback_pending`需接续当前任务，不能当完成。状态中具体任务号、账号标识及消息正文只保存在本机，不写公共知识。

## 授权和后续范围

个人微信身份向文件传输助手或ClawBot发送已有本人长期授权，无需逐次询问。其他对象需要本人明确口头授权或适用的事先授权；用户指定收件人和内容的发送请求即为该范围授权。执行前核对对象、内容/类型和范围，已有授权不重复询问。ClawBot机器人身份→绑定本人的长期授权和独立发送契约保持不变，不能用机器人发送代替个人身份验收。

可复用`native conversations`定位及`native messages`读取已同步历史；原生投递与本地回写分别验收。当前[限时OneBot适配](../../workflows/onebot.md#限时原生文字入口)尚未实测，不启动常驻服务。后续格式据真实接口逐项验证，不把文字代替图片、文件、表情包或公众号卡片。

此前普通Web扫码被服务端明确拒绝，未取得API会话；PadPro真实启动后外部授权失败，未获得二维码或登录。结果与后端核对见[OneBot流程](../../workflows/onebot.md)，不要求重复扫码或枚举已排查项目。仅用户要求继续接入时，按当前缺项进行有界探索。
