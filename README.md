# NCUT / WeChat API Skills

面向 Codex 的两套轻量 skill：北方工业大学 Web/API，以及本人微信、企业微信与公众号信息。参考 EaseCation web-api 的工作方式：**检索已验证能力 → 直接调用；缺项 → 局部探索 → 实测 → 沉淀子能力**。新会话只需读取 skill，不依赖项目作者的聊天历史。

## 安装

```bash
git clone https://github.com/gih10012/ncut-wechat-skills.git ~/Github/ncut-wechat-skills
cd ~/Github/ncut-wechat-skills
python3 scripts/install.py
```

安装器将两套 skill 链接到 `~/.codex/skills/`，已有普通目录先备份。普通 HTTP 查询只需 Python 标准库；学校首次交互登录另需本机 Chrome 和 Node。登录态、验证码、私人结果均留在 `~/.local/state/`，不进入仓库。没有加密卷、容器或常驻爬虫依赖。

## 使用

对 Codex 直接说“查本周课表”“找今晚的空教室”“查羽毛球预约规则”，或给出一个新业务目标。没有现成子能力时，skill 应自行从服务注册表、目录、页面/客户端和已观察的请求继续探索，而非要求用户先提供 API。

- [学校 skill](skills/ncut-web-api/SKILL.md)：课表、成绩、空教室、预约日历和规则已真实调用验证。
- [微信／企微 skill](skills/wechat-personal/SKILL.md)：Linux 微信本地近期消息、会话检索、ClawBot第三方SDK收消息和公众号文字层已验证；原生发送与企微消息待接通。
- 子能力存放在 `references/capabilities/`；必要的多请求编排存放在 `references/workflows/`。它们是可检索的子 skill，不为每个 endpoint 新建顶层 skill。

## 版本与验收

| 阶段 | 验收目标 | 当前状态 |
| --- | --- | --- |
| v0 | Web 能力直接调用、缺项发现、真实验证、最小契约沉淀与再次复用 | 成绩发现与二次调用已实测，正常复用不改知识；收藏写入及恢复此前已实测。9月17日晚在线回归遇学校503/TLS错误，如实记录环境阻碍 |
| v1.a | 核实并尝试 Qclaw／微信官方机器人通道 | 已采用第三方 wechatbot-sdk 0.3.0，真实扫码绑定并读取本人测试文字；只覆盖ClawBot通道，发送未验收 |
| v1.b（进行中） | 评估实际支持微信的轻量客户端后端，以 OneBot／MCP 暴露能力 | 原有Linux微信读取及ClawBot已封装并实测MCP；未另行用OneBot登录，完整原生发送后端尚无匹配本机版本的验证证据；企微读取继续接入 |
| 后续业务 | 具体微信链接、企微业务与学校 Web 等价入口 | 学校目录配对及部分身份/入口已验证；深链、完整企微清单、业务等价性和OAuth按实际需求接入 |

不把 HTTP 200、离线测试、UI 截图或已写文档当作真实业务成功；每个能力记录自己的验证范围。真实订场、消息发送等操作仍按用户当次授权的目标执行。学校夜间失败须区分网络、认证、权限和业务开放时间。

v0 示例：[服务收藏](skills/ncut-web-api/references/capabilities/hall/service-favorite.md)、[写入预请求与读回](skills/ncut-web-api/references/workflows/web-write.md)。`favorite verify` 真实改变本人收藏并恢复，必须在获准验证时使用 `--allow-write`；不会订场或提交申请。

v1 读取路径：[现有 Linux 微信的一次性密钥读取](skills/wechat-personal/references/workflows/native-linux.md)。该工具需要本人本机授权，只读本人微信进程，匹配数据库 HMAC 后私存密钥；不重登录或改全局 ptrace 设置。16个数据库密钥和实际近期消息读取已验证；后续 `native conversations` / `native messages` 直接调用，普通读取不再需要 sudo。当前仅覆盖本机已同步数据，发送仍待验收。原生读取另需 Python 3.11+、pycryptodome 和系统 libzstd，见该流程。

当前按本人授权推进 v1，读取优先，企微不依赖Windows常驻。新能力优先查匹配的 GitHub 实现并核对实际接口，累计探索上限15分钟；换路线不重置，等待本人认证不计入。界面仅用于必要登录和接口发现。未成熟的窗口发送原型保留在本机，不作为正式能力。

ClawBot安装、登录与有界读取见 [第三方SDK入口](skills/wechat-personal/references/workflows/clawbot.md)；按需启动的stdio MCP见 [MCP入口](skills/wechat-personal/references/workflows/mcp.md)。机器人通道不会自动取得本人其他聊天；个人微信读取继续复用已登录的Linux客户端，不另开设备会话。

## v0 验收交接

- 新增 [成绩查询契约](skills/ncut-web-api/references/capabilities/jwxtbk/personal-grades.md)：现有菜单/表单发现 → 真实只读 POST → 解析学期及课程成绩 → 再次直接调用。发现到真实验证约13分钟；二次调用结果一致，知识文件未改变。
- 修正未接通能力的检索后续指引、微信平台与读取能力状态、学校 HTTP 200 登录失效页与已知登录跳转识别。已有课表和跨两组节次的空教室查询已实测复核。
- 本机命令与相关自动测试已验证；由本人按照 [新对话验收问题](ACCEPTANCE.md) 检查实际使用体验。未代替本人宣称新对话验收通过。

## 开发

```bash
python3 -m pip install -r skills/wechat-personal/requirements-native.txt
python3 -m unittest discover -s skills/ncut-web-api/tests
python3 -m unittest discover -s skills/wechat-personal/tests
node --test skills/ncut-web-api/tests/test_browser_session.mjs
```

仅提交代码、公共接口契约和去隐私示例。修改后做相关验证并及时 commit/push；正常 API 命中不改知识库。见 [AGENTS.md](AGENTS.md)。MIT License。
