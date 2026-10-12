# 原版论文 PDF 获取与交付

2026-10-12本人明确偏好：尽量交付论文原版 PDF；最多另补资料说明、目录或总体概括 PDF。保存期刊/出版社返回的原始字节，仅命名和分类。论文、厂商技术论文和应用说明分别统计；新闻摘编不当作原始研究论文。私人文献包、联系人、聊天证据和临时下载令牌均留在本机，不提交公开仓库。

入口先用[学校图书馆资源契约](../capabilities/library/database-resources.md)。论文有原刊公开 PDF 时也可直接用出版社入口；公开原刊下载成功不代表学校付费数据库身份或下载权限已经验收。

## 已实测的公开原刊路径

- 《电子与封装》`https://ep.org.cn/`：封装、芯粒测试、半导体器件、光刻、刻蚀等中文原刊 PDF 已从当前正常页面取得；例如[硅转接板制造与集成技术综述](https://ep.org.cn/CN/10.16257/j.cnki.1681-1070.2024.0119)。
- 《高分子通报》[极紫外光刻胶综述](https://www.gfztb.com/zh/article/doi/10.14028/j.cnki.1003-3726.2022.12.002/)及《光学精密工程》[极紫外光学元件检测综述](https://ope.lightpublishing.cn/zh/article/doi/10.37188/OPE.20253317.2661/)：当次页面的`meta[name=citation_pdf_url].content`是当前原始 PDF 地址，不猜文章 ID 或自行把`lowqualitypdf`改成其他路由。该路径名称不等于页面字迹模糊，应实际渲染核对。
- 厂商原始资料可补充论文范围：TI 的`https://www.ti.com/lit/an/snoa286/snoa286.pdf`、`https://www.ti.com/lit/an/spra953d/spra953d.pdf`以及 Intel 的[先进封装技术资料](https://cdrdv2-public.intel.com/826148/Volume%206%20Intel%20Advanced%20Packaging%20Technology.pdf)均已验证是可打开原始 PDF。

《电子与封装》的实测请求链：

1. 从正常目录/检索响应的`a.txt_biaoti`取题名和稳定 DOI 页。高级检索页面`/CN/article/advancedSearch.do`及其`/js/front/advanced-search.js`明确观察到只读 POST `/CN/article/advancedSearchResult.do`，form `searchSQL=(主题词[Title])`。这是一套前端检索表达式；词来自本人任务，不另构造未观察的数据库语句。光刻和刻蚀按文题检索已返回对应论文。
2. PDF 按钮的`onclick`调用`lsdy1('PDF','实际articleId',...)`；ID从该按钮读取。当前`/js/download.js`明确观察到只读 POST `/CN/article/showArticleFile.do`，form `attachType=PDF&id=实际ID&json=true`，Referer为实际题名页。
3. 响应以`[json]`开头，去掉前缀再解析；仅`status=1`时GET返回的完整`pdfUrl`，沿用该正常请求的会话。购文/登录响应按实际要求办理，不伪造允许状态。URL中的一次性token不输出、不写进技能或公开清单；清单保存稳定题名页/DOI。
4. 2026-10-12这些国内原刊入口以本机直连成功；其他域名的代理方式按实际网络判断，不把校园网直连设置扩展为全部外网的永久配置。

## 原始文件与质量

核验`%PDF-`、`pdfinfo`能读取页数、页面可渲染、题名与原刊页相符。用SHA-256按内容去重，打包后再次核对包内原始字节。`Encrypted: yes`本身不等于不能阅读；有公开空口令可正常打开的原始 PDF 仍保留原文件，不移除保护、不改写文档。

部分原刊使用自定义字体编码，`pdftotext`出现乱码但渲染清晰；文字可复制和视觉可读分别记录，不据提取字符数宣称识别准确，也不把OCR文本替换成原版正文。首页、中间页和图表页按需要抽样；明显摘要、新闻摘编或无法打开的响应不充作全文。资料说明/目录注明年份、来源、页数与文件位置，原文正文保留不变。

多份资料按本人指定主题分类，只为实际交付生成轻量说明目录。发送复用[微信 skill](../../../wechat-personal/SKILL.md)并核对精确收件人和当前任务授权；大包超过普通 CLI 已验收大小时用正常微信窗口，等待上传完成后读回相同文件记录，不凭发送点击或初始本地插入宣称完成。
