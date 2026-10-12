---
id: library-database-resources
service: library
keywords: ["图书馆", "文献", "论文", "免费文献", "全文下载", "数据库导航", "知网", "万方", "维普", "IEEE", "ACM", "Elsevier", "Springer", "ProQuest", "原文传递", "BALIS"]
status: runtime_verified
runtime_verified_at: "2026-10-12T21:09:00+08:00"
transport: http
command: ["request", "library", "--capability", "database-resources", "--path", "/db/api/newDbsList", "--query", "sw=<数据库名称>", "--query", "trialFlag=true", "--limit", "3"]
requests: [{"method":"GET","path":"/db/api/newDbsList","effect":"read","expect":"json","required_fields":["code","data"]},{"method":"GET","path":"/db/cx/ipBlank","effect":"read","expect":"json","required_fields":["code","data"]}]
evidence: "2026-10-12 official index.js getDbs -> GET api/newDbsList; campus intranet=true returned code=1000 and 93 parent entries. Installed generic request verified sw=IEEE and sw=知网 with code=1000 and matching rows."
note: "已验证学校数据库目录查询；sw填知网/IEEE等数据库名称，不填论文题名。省略intranet返回校外VPN地址，校内地址须按正文先查IP判定。具体论文检索、机构认证和PDF下载继续按目标数据库办理，未在本能力验收。"
---
# 图书馆文献资源入口与目录查询

入口：[图书馆首页](https://lib.ncut.edu.cn/)；[数据库导航](https://lib.ncut.edu.cn/db/)。首页“毓秀搜索”是结合本馆订购数据库的统一文献检索；查具体论文优先在这里或相应数据库搜索题名、作者、DOI。

## 请求与结果

公开目录无需本人登录。GET `https://lib.ncut.edu.cn/db/api/newDbsList`，`sw`来自用户要找的数据库名称，`trialFlag=true`为官方前端使用的参数。前端还提供排序/分类参数，仅在确需这些筛选时查看当前页面。

成功须返回`code=1000`且`data`为符合查询词的数据库条目数组。generic request的`ok=true`只表示其通用检查通过，仍核对业务code。空数组表示未匹配，不代表学校没有其他文献资源。常用字段：`id/dbName/resTypeNames/languagesNames/procurementModesNames/trialEndTime/dbps/childs`。`dbps[].title/dbUrl`是当前访问方式和地址；部分父库在`childs`内列子库。详情页由实际返回的`id`生成`https://lib.ncut.edu.cn/db/detail?id=ID`。

前端先GET `/db/cx/ipBlank`，该接口实测成功结构为`code=1`、`data.status`为布尔值，再将`data.status`传为`intranet`。2026-10-12本机校内直连返回true；该值必须随当前网络读取，不固化为校内。实测省略`intranet`时，目录仍正常检索，但`dbps`默认给校外VPN地址；要查校内推荐链接，先`request library --capability database-resources --path /db/cx/ipBlank`，再给目录请求追加`--query intranet=true`或`intranet=false`，取值严格按当次判定。数据库访问优先使用网页按当前IP推荐的链接，校内入口与校外VPN入口分别验收。校内CLI请求受本机代理影响时，只为该次命令使用`env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY python3 "$NCUT" ...`直连，不修改全局设置。

## 已确认的学校资源（2026-10-12）

当天实时目录以下条目均标`procurementModesNames=正式`：

| 资源 | 详情ID | 用途 |
| --- | --- | --- |
| CNKI中国知网学术期刊（网络版） | 2 | 中文学术期刊全文 |
| CNKI中国知网博士论文全文数据库 | 3 | 博士论文 |
| CNKI中国知网优秀硕士学位论文全文数据库 | 4 | 硕士论文 |
| 维普中文期刊服务平台 | 34 | 中文期刊 |
| 万方学位论文全文数据库 | 103 | 中文学位论文 |
| IEEE Xplore Digital Library | 70 | 电气、电子、通信、计算机期刊与会议文献 |
| ACM美国计算机学会全文数据库 | 99 | 计算机期刊与会议文献 |
| Elsevier SDOL爱思唯尔电子期刊库 | 58 | 学校订购范围内ScienceDirect全文 |
| SpringerLink施普林格数据库 | 69 | 外文文献 |
| ProQuest博硕士论文全文数据库 | 74 | 外文学位论文 |

校内知网期刊入口当前为`https://kns.cnki.net/kns8s/?classid=YSTT4HG0`；硕博论文为`https://kns.cnki.net/kns8s/?classid=RMJLXHZ3`；IEEE为`https://ieeexplore.ieee.org/Xplore/home.jsp`。ACM、Elsevier、万方、维普的当前目录链接经过图书馆`/sso/api/auth/library/vpn358`，保留原始`dbps[].dbUrl`，不自行改写或猜SSO参数。

学校购买的是具体数据库/学科包/年份范围。Elsevier[官方说明](https://lib.ncut.edu.cn/db/detail?id=58)明确列出工程技术、计算机、数学、商管会计、经济金融和社会学科，并描述2003年以来747种期刊；这是该页面的说明，应以当次实际权限为准。检索索引如WOS、EI与全文库分开判断；能检索题录不保证能下载全文。

## 校外与其他获取路径

图书馆首页有“校外访问”；数据库详情按IP提供校外VPN链接。本次目录实测IEEE校外入口`https://ieeexplore-ieee-org.webvpn.ncut.edu.cn/`，知网条目给`https://kns-cnki-net-443.webvpn.ncut.edu.cn/kns8s/`下含原始classid的完整URL，以响应为准。[网信中心官方说明](https://cic.ncut.edu.cn/info/1040/2178.htm)记载学校WebVPN `https://webvpn.ncut.edu.cn/`可访问图书馆电子资源，支持统一认证及企业微信入口；该说明为2022年记录，本次没有验收校外登录或下载。

官网仍列“原文传递”和“开放获取资源→免费资源”。2026-10-12已观察并直连GET以下HTTPS栏目页；正文由前端动态加载，本次只确认栏目和入口，未核实最新服务收费规则：

- [原文传递](https://lib.ncut.edu.cn/engine2/m/0/5576358/6563788?p=1089377&t=13230194&currentBranch=1)
- [免费资源](https://lib.ncut.edu.cn/engine2/m/0/5576358/6563788?p=1089377&t=13230261&currentBranch=1)

2026年[学校图书馆活动通知](https://lib.ncut.edu.cn/engine2/d/28227607/6564093/0/5576664?p=1089377&t=13230255)仍安排BALIS原文传递宣传日。旧[图书馆手册存档](https://static.zxhnzq.com/xxsy/prod/file/20210108101542-9130.pdf)描述BALIS为我校读者免费提供原文传递，并给旧地址`http://202.112.118.46/balis/`；该旧地址和当前免费范围未实测，后续从现官网“原文传递”正常页面续查，不把旧说明等同当前办理成功。导航中的旧IP`202.204.27.7`当天直连无路由，使用已实测的`lib.ncut.edu.cn`对应HTTPS栏目路径。

## 验收边界与副作用

只读发现和目录查询；未创建读者账号、提交原文申请、验证出版商机构身份或下载具体论文。正式采购说明学校提供该资源，单篇是否含全文须在本人当前授权身份下确认。试用条目按真实截止日判断；不据首页列表中的过期试用条目宣称仍可用。
