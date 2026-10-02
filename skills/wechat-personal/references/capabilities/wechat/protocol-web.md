---
id: wechat-protocol-web
service: wechat
keywords: ["微信协议网页", "微信链接转浏览器", "微信浏览器中继", "weixin链接", "小程序网页", "Chrome打开微信链接", "Edge打开微信链接"]
status: "runtime_verified"
evidence: "2026-10-02 installed personal and WeCom CLI bounded HTTP reading relays; owner-specified group mini-program post independently matched current native UI, full body and five unique comments in relay HTML; Chrome and Edge displayed body and scrolled through final comment section. Exact observed HTTP binding only; general opaque-ticket decoding and client JS/OAuth emulation unverified."
runtime_verified_at: "2026-10-02T14:22:00+08:00"
transport: "installed_cli_explicit_http_or_private_observed_binding_readonly_loopback_relay"
command: ["native", "web", "resolve", "--url", "ACTUAL_LINK"]
note: "先解析真实链接。已核对HTTP来源可在外部浏览器读取；CLIENT_REQUIRED用现有客户端观察对应HTTP入口或computer-use，不猜域名、不截取OAuth回调、不把小程序启动页当正文。"
---
# 微信 / 企微协议链接与外部浏览器

两套独立 CLI 共用相同的通用实现和本人私有绑定。日常无需 sudo。学校业务使用该入口或 computer-use，CLI 不添加学校专用适配。

```sh
python3 "$WX" native web resolve --url '真实链接'
python3 "$WX" native web resolve --url '真实链接' --probe
python3 "$WX" native web open --url '明确HTTP网页或含HTTP的webview链接' --browser chrome
python3 "$WX" wecom web open --url '明确HTTP网页或含HTTP的webview链接' --browser edge
python3 "$WX" native web relay --url '真实链接' --seconds 300 --browser chrome
python3 "$WX" wecom web relay --url '真实链接' --seconds 300 --browser edge
```

`resolve`默认仅解析，`--probe`才GET；`content_verified:false`或HTTP200不是业务成功。直接HTTP保留原URL及票据编码。微信/企微协议中唯一明确的`url/target_url/web_url/weburl`参数仅解码外层一次；没有HTTP目标的小程序票据和客户端动作返回`CLIENT_REQUIRED`。OAuth入口保留正常认证流程，不能把`redirect_uri`当已认证业务页。

小程序URL Link的静态启动信息可以读取名称、username、path和query；这不代表小程序正文可在浏览器运行。`weixin://dl/business/?t=...`不得直接换成短链域名猜目标。当前实例已用原客户端实际显示和真实HTTP响应核对对应帖子；新的不透明票据仍需局部观察。

观察到真实HTTP等价来源后，保存精确绑定：

```sh
python3 "$WX" native web bind --url '精确原协议链接' --target '实际HTTP来源' --target '另一个已观察的只读HTTP来源' --view json
```

默认配置`~/.local/state/wechat-web/bindings.json`为0600，两端共用；也可用`--bindings`指定私有配置。原链接以SHA256精确绑定，最多8个来源，不匹配新票据。绑定状态是调用者已观察配置，CLI不凭配置自行宣称业务验收。消息正文、本人身份、动态票据、请求证据只保存在私有状态，不写公共知识。

`relay`前台启动`127.0.0.1`随机端口和随机路径，立即输出`WEB_RELAY_READY`及本地URL；默认5分钟、最多1小时，Ctrl+C或到期关闭，无自启动。JSON完整嵌套字段/中文/换行不截断；text为完整文字；html为去掉脚本和样式的页面文字层。浏览器刷新重新GET，内容全部转义，HTTP写入不支持。它是只读浏览页面，不是完整交互网页、图片正文查看或通用小程序运行环境。浏览器`open`仅报告打开请求，仍须实际页面核对成功。

需现有HTTP身份时显式加`--session '/私有路径/session.json'`：本人所有0600文件，格式`{"origin":"https://实际域名","headers":{},"cookies":[],"user_agent":"实际UA"}`。cookies按域、路径、secure/有效期使用；自定义身份header必须声明精确origin，携带身份时跨域跳转拒绝，凭据不进浏览器HTML和请求日志。保存Cookie或更换UA不替代实际微信/企微OAuth或JS SDK能力；确实依赖客户端时沿用当前授权用computer-use。

已验收范围：指定微信群一条真实小程序帖子，原客户端正文/时间和HTTP业务成功字段一致，2条主回复加3条子回复的5个唯一ID/完整正文在只读页面中；Chrome与Edge显示正文及评论末尾，两套安装CLI可解析同一私有绑定并中继。未知小程序自动解票、登录迁移、JS SDK调用、交互提交和其他网站分别待验收。
