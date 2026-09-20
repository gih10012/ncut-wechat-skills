---
id: send-message
service: wechat
keywords: ["发消息", "发送消息", "微信发送", "回复微信"]
exclude_keywords: ["企微", "企业微信", "ClawBot", "机器人"]
status: "not_connected"
transport: "unavailable"
workflow: references/workflows/messages.md
note: "原生发送尚未接通；普通网页登录实测被拒，Linux PadPro已启动但外部授权失败。已准备Linux发送入口观测工具，需本人本机sudo及手动测试；已有本地定位/读回。"
---
# 消息发送

复用 conversations 定位和 read-messages 读回；仅补发送传输。以个人微信身份写入前必须取得本人明确授权或适用的事先授权，已有范围不重复询问；核对收件人、内容/类型与次数。超时先按会话/时间/内容读回再决定是否重试。ClawBot机器人身份发送走独立能力与长期授权，不能替代这里的验收。

2026-09-19候选核对见[第三方后端](../../workflows/onebot.md#2026-09-19按napcat同类后端复核)。当前Linux内部入口未取得外部调用契约；没有发送命令可直接调用。未接通状态题直接说明此边界，用户要求继续接入时再按现有证据推进，不重复扩展逆向或枚举已排查项目。

2026-09-20本人实际扫描普通Web登录二维码并确认，手机显示已登录网页版；最终登录接口却返回明确的“不支持使用网页版微信”HTML，未取得有效API会话，未执行发送。详见[普通Web实测](../../workflows/onebot.md#2026-09-20普通web扫码实测)。因此普通Web路线不再等待重复扫码；需要服务端资格或实际后端条件变化后才重试。此结论不证明其他设备协议可用或不可用。

本人随后明确选择Linux并允许参考第三方Hook项目移植。PadPro公开Linux包已真实启动，但生成AuthKey时外部授权失败，尚无二维码或登录。Hook移植已有当前Linux静态入口和可执行的短时观测工具，步骤与边界见[原生发送移植](../../workflows/native-send-port.md)；需要系统调试权限进行真实观测后再确定发送对象，不把工具自测当发送成功。
