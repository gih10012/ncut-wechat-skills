# Android企微通知补充（当前暂缓）

2026-09-18本人明确手机为原生鸿蒙，要求手机接入留待以后。本方案及安装/验收待办已暂缓，不再提示安装SmsForwarder，不启动接收；OpenHarmony方向以后按实际设备接口另行研究，不能假定Android APK可用。下文仅保留已实现的Android方案说明，完整企微聊天目标保留。

此入口只覆盖手机实际产生并展示的通知标题和文字，不含未通知的聊天、隐藏正文、原始媒体或历史收件箱。标题不能充当可信聊天ID。

手机侧使用 [SmsForwarder v3.5.0](https://github.com/pppscn/SmsForwarder/releases/tag/v3.5.0)。已核对该tag的 [NotificationService](https://github.com/pppscn/SmsForwarder/blob/v3.5.0/app/src/main/kotlin/cn/ppps/forwarder/service/NotificationService.kt) 及 [WebhookUtils](https://github.com/pppscn/SmsForwarder/blob/v3.5.0/app/src/main/kotlin/cn/ppps/forwarder/utils/sender/WebhookUtils.kt)：通过Android通知监听取得包名、标题和文字，Webhook支持JSON模板和自定义认证头。业务执行不使用聊天界面点击。

安装交接时先说明手机依赖：企微在本人手机上产生通知，SmsForwarder读取通知并推送，接收端保存，skill按需查询。手机无需一直亮屏，但要能正常接收企微通知并允许转发工具后台工作；服务器常开不能取代手机。同一局域网只是下文临时测试的条件，跨网和长期部署见[独立服务说明](../../../../BACKGROUND-RECEIVER.md)，当前尚未部署。本人询问原理或网络限制不代表配置已完成。

先查看电脑当前局域网地址，替换下例中的地址；只在同一可信局域网测试。使用已安装skill中的`wechat.py`：

```bash
python3 "$WX" notifications setup --account me --host 192.168.1.10 --port 16792
```

此命令只生成私有凭证和手机配置说明，返回`guide`文件路径；不启动服务。重复setup保留原token。说明中包含WebHook地址、认证头、JSON模板及`com.tencent.wework`包名规则。只开启企微APP通知转发，不开启短信、电话、远程控制或自动消除通知。手机通知使用权需本人在系统设置中完成。

本人设置完成、准备收取实际企微通知后，启动有界接收：

```bash
python3 "$WX" notifications serve --account me --seconds 300
```

只绑定setup时指定的私有IPv4地址，拒绝通配地址；默认300秒，最多900秒，到时退出。只接受带Bearer凭证的`POST /wecom/notifications`，校验来源包名和字段，限制请求体64KiB。同一组标题、文字和手机接收时间的重复投递只保存一次；这不是企微原生消息ID去重。归档为本机0600 SQLite，凭证及手机说明同样0600。`GET /health`只返回健康状态，没有HTTP历史读取接口。

无需接收服务在线即可读取已归档通知：

```bash
python3 "$WX" notifications list --account me --limit 20
```

或调用MCP `wecom_notifications`。返回固定标识`source=android_notification`、`complete_chat_history=false`、`personal_inbox_verified=false`。运行数据在`~/.local/state/wechat-personal/notification-inbox/<account>/`，不发布到仓库。

验收分开记录：本机HTTP、认证/过滤/重复投递测试和MCP调用已通过；手机安装、通知授权、实际企微通知投递与读回尚未完成。`/health`连通、模拟发送、空归档和离线测试都不证明实际企微新消息成功。本人离线时保存待办，返回后用提问卡片交接，不预先反复启动倒计时接收。
