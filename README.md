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

- [学校 skill](skills/ncut-web-api/SKILL.md)：课表、空教室、预约日历和规则已真实调用验证。
- [微信／企微 skill](skills/wechat-personal/SKILL.md)：Linux 微信本地近期消息、会话检索和公众号文字层已验证；发送与企微消息待接通。
- 子能力存放在 `references/capabilities/`；必要的多请求编排存放在 `references/workflows/`。它们是可检索的子 skill，不为每个 endpoint 新建顶层 skill。

## 版本与验收

| 阶段 | 验收目标 | 当前状态 |
| --- | --- | --- |
| v0 | 通用发现、总结、复用；真实 Web POST 写入并读回；必要预请求示例 | 收藏 POST → 读回 → 取消 POST → 确认恢复已实测；已保存换票及写入子能力 |
| v1 | 本人微信／企微消息接收、发送；公众号文章读取 | 文章与 Linux 微信本地消息读取可用；微信发送、企微消息待实测 |
| v2 | 微信内链接与深链读取 | 待实现；scheme 以实际客户端为准 |
| v3 | 企微服务与学校 Web 替代映射；无替代时处理本人 OAuth 授权 | 学校目录配对、移动页复用学校SSO取得本人身份已实测；完整企微清单、业务等价性和OAuth待验收 |

不把 HTTP 200、离线测试、UI 截图或已写文档当作真实业务成功；每个能力记录自己的验证范围。真实订场、消息发送等操作仍按用户当次授权的目标执行。学校夜间失败须区分网络、认证、权限和业务开放时间。

v0 示例：[服务收藏](skills/ncut-web-api/references/capabilities/hall/service-favorite.md)、[写入预请求与读回](skills/ncut-web-api/references/workflows/web-write.md)。`favorite verify` 真实改变本人收藏并恢复，必须在获准验证时使用 `--allow-write`；不会订场或提交申请。

v1 读取路径：[现有 Linux 微信的一次性密钥读取](skills/wechat-personal/references/workflows/native-linux.md)。该工具需要本人本机授权，只读本人微信进程，匹配数据库 HMAC 后私存密钥；不重登录或改全局 ptrace 设置。16个数据库密钥和实际近期消息读取已验证；后续 `native conversations` / `native messages` 直接调用，普通读取不再需要 sudo。当前仅覆盖本机已同步数据，发送仍待验收。原生读取另需 Python 3.11+、pycryptodome 和系统 libzstd，见该流程。

## 开发

```bash
python3 -m pip install -r skills/wechat-personal/requirements-native.txt
python3 -m unittest discover -s skills/ncut-web-api/tests
python3 -m unittest discover -s skills/wechat-personal/tests
node --test skills/ncut-web-api/tests/test_browser_session.mjs
```

仅提交代码、公共接口契约和去隐私示例。修改后做相关验证并及时 commit/push；正常 API 命中不改知识库。见 [AGENTS.md](AGENTS.md)。MIT License。
