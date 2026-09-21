---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信", "原生发送", "文件传输助手发送", "发送状态", "个人身份发送", "给ClawBot发", "向ClawBot发", "给ClawBot发消息", "向ClawBot发消息"]
exclude_keywords: ["企微", "企业微信", "机器人身份"]
status: "partially_verified"
transport: "pinned_linux_native_client"
workflow: references/workflows/native-send-port.md
note: "2026-09-21个人身份经OneBot向文件传输助手发送文字已获手机单次收件确认，中文、换行与emoji正常，同ID防重通过；共享参数化后端已实测，独立CLI写入未在本轮验收。其他对象、媒体、OneBot事件及本地回写未验收，通用发送保持partially_verified。"
---
# 个人微信身份发送

2026-09-21已验证锁定Linux版本的原生个人身份filehelper文字投递：此前固定试验及后续OneBot HTTP发送均有手机收件确认。OneBot调用共享参数化后端，完成回调一次、析构一次、存活回调零、错误为零，客户端继续运行且调试器已脱离；同ID重放未再次提交，本人确认只收到一条，中文、换行及emoji正常。可复用范围见[filehelper文字契约](send-filehelper-text.md)。普通好友/群聊、个人身份向ClawBot发送、媒体、OneBot事件及完整协议均需单独验收。

当前发送适配尚未接入Linux本地消息回写。手机收件确认与本地历史缺项分别记录，不能因历史缺失否定投递、重复发送或要求重新验收。

## 调用与状态

下文`$WX`为本skill的`scripts/wechat.py`绝对路径。先读取已有结果；这不会附加微信或发送消息：

```bash
python3 "$WX" native send-status
python3 "$WX" native send-status --request-id '原请求ID'
```

无request-id时读取已验收的固定试验。可传文字的CLI入口如下，默认面向filehelper；它与OneBot共用已实测的参数化后端，但独立CLI写入未在本轮执行，日常发送优先使用上述已验证契约：

```bash
sudo python3 "$WX" native send --text '消息文字' --request-id '本次唯一ID'
```

入口复用当前桌面微信唯一主进程和登录，默认目标为filehelper；底层`--recipient`可指定1–128字节的精确原生ID（ASCII字母、数字、`_.@-`），不接受显示名。其他目标尚未验收，执行前须满足下方授权规则并从已有会话读取精确ID。依赖匹配的二进制、系统GDB/GCC及本机调试权限；入口、前置检查和系统权限说明见[原生发送流程](../../workflows/native-send-port.md)。request-id须为4–80个ASCII字母、数字、点、下划线或连字符，首字符为字母或数字；文字为1–1024个UTF-8字节且不含NUL。一次操作固定使用一个request-id，相同正文、目标和模式的已有请求只返回记录，不重复提交；内容冲突拒绝。状态不确定先读同一ID及接收端，不删除防重记录或凭本地历史缺失重发。

`submission_entered`、客户端`task_id`和零错误回调均不单独代表送达；`recipient_delivery_verified`记录独立收件证据。`worker_pending`或`callback_pending`需接续当前任务，不能当完成。状态中具体任务号、账号标识及消息正文只保存在本机，不写公共知识。

## 授权和后续范围

个人微信身份向文件传输助手或ClawBot发送已有本人长期授权，无需逐次询问。其他对象需要本人明确口头授权或适用的事先授权；用户指定收件人和内容的发送请求即为该范围授权。执行前核对对象、内容/类型和范围，已有授权不重复询问。ClawBot机器人身份→绑定本人的长期授权和独立发送契约保持不变，不能用机器人发送代替个人身份验收。

可复用`native conversations`定位及`native messages`读取已同步历史；原生投递与本地回写分别验收。[限时OneBot适配](../../workflows/onebot.md#限时原生文字入口)的filehelper文字已实测，按需限时启动，不安装常驻服务。后续格式据真实接口逐项验证，不把文字代替图片、文件、表情包或公众号卡片。

此前普通Web扫码被服务端明确拒绝，未取得API会话；PadPro真实启动后外部授权失败，未获得二维码或登录。结果与后端核对见[OneBot流程](../../workflows/onebot.md)，不要求重复扫码或枚举已排查项目。仅用户要求继续接入时，按当前缺项进行有界探索。
