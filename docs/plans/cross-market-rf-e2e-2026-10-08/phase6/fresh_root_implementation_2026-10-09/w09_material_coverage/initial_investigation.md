# W09 来源覆盖调查：初始盘点与 M3 交接

信息截止日 **2026-10-08**；调查日 2026-10-09。状态：**只读准备完成，W09 真实获取、全文消费与 M3 尚未完成**。

写集仅本报告与 [initial_inventory.json](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/fresh_root_implementation_2026-10-09/w09_material_coverage/initial_inventory.json)。JSON 保留真实 SourceRef、完整原件 SHA、物理路径、旧执行阶段、精确官方 URL、18 项交接任务和浏览时间；它是准备快照，不是第二套权威来源账本。没有改代码、配置、原件、来源事实、封存执行或共享 PWF；提交/发布/M3 排程归 MAIN。

## 1. 依据、数量与关键依赖

已读冻结 [IMPLEMENTATION.md](C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/fresh_root_remediation_2026-10-09/IMPLEMENTATION.md) W06/W09 以及同目录 issue_root_matrix.json 的 RC09/RC10。三家 fetch/storage/process 报告、scope、实际 document_matrix/source_ledger、requests/results/locators 和 reviewer 原件读取记录逐类比对，未修改旧文件。冻结 NOT_RUN 不是今天的工程状态。

| 公司 | 封存根目录 | 已有 SourceRef | 旧 matrix 条目 |
|---|---|---:|---:|
| 中微 688012 | [CN](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-cn-688012) | 6 | 13 |
| 腾讯 00700 | [HK](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-hk-00700) | 8 | 15 |
| Microsoft MSFT | [US](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-us-msft) | 10 | 18 |

合计 **24 个既有 SourceRef、31 个旧 ledger 条目、46 个旧 matrix 条目**。本次只读实算19份物理文件 SHA，其中17份匹配已用 SourceRef；另两份是中微FY24年报和不同版本的旧招股文件。不是24份原件全被本次 native reader 重开：没有再次启动 native prepare/reader/解析/摘要/预测，未重新定位的原件保留真实旧读取证明。旧 reviewer 读取不能算新 executor 已消费，全页解析也不能算全文条款已读。

MAIN 先报告 W06 独立 RED：标签/请求 A、原文+URL B 仍能 import/query/reuse。随后通知新源码 **90723304** 已交付，正在准备独立复审。本调查没有验收此修复；新材料不能成为绕过身份问题的办法。真实获取/事实更新/消费须使用 MAIN 复审后的 producer 和当前核验安装版本。

**复用原则：** M3 先查询当前配置的数据湖，以原件 SHA、身份、类型、期次定位已有文档，再走 SourceRef/registered-source 公共 preparation。缺公开日通过准确 primary 事件+同字节证据更新事实，不重下同文件；不同 SHA 不因文件名相似而合并。确实缺失才新隔离 attempt 一次有界采集，记录实际 usage；相同请求第二次证明复用。

## 2. 中微：已有资料与六项动作

### 既有原件

| 原件（完整 SHA/SourceRef 在 JSON） | 封存处理事实 |
|---|---|
| FY25 annual d64c4108…，9,165,875B/259页 | 原件读成功，旧付费摘要截断，没有可消费摘要 artifact。 |
| 2026H1 182e2062…，3,149,962B/210页 | 原件读成功，旧 zh-CN 预检失败，未调用模型。W01 工程修复不等于新公司消费。 |
| 2025H1 91ae4978…；2026Q1 ab7bb007… | 比较原件存在；Q1摘要公开读过，两处 span 用于六参数，选取 partial。 |
| 最终2019招股书19cdb41e…，11,211,796B/429页 | 历史业务/确认背景已读，不能当当前ASP/转化率实证。 |
| SEMI HTML 0c5481a9… | 已注册原件并实读；行业基准不是公司增速。 |

FY24 原件当前仍在 [中微公司：2024年年度报告.pdf](C:/Users/郑曾波/Dropbox/Stock/工业与信息化/电子/中微公司/中微公司：2024年年度报告.pdf)，14,285,291B/268页；本次整字节 SHA 为 **3273711fbb79fa6ee5e9a3b2f0eea7d5a1dfa0d305721c61e5af251f9addf399**，只读封面及第二页确认 issuer/FY24，没有全文读取或新资格断言。April17/18 公开日冲突仍未解决；签字、董事会、股东会材料、mtime 不算公开事件。

Dropbox 中微半导体招股说明书.pdf 为9,533,198B、SHA **3a9eb0ce69ecdbbdcc8c187f53c0c90ebf54ec9f4760486426318b9b1bc37b6c**，不同于已用最终IPO **19cdb…**。不能替代它。

| ID | M3 动作 | 成功证据/保留的未知 |
|---|---|---|
| CN-01 | 复用 FY24，查准确官方事件及同SHA；由W06既有事实API追加版本，再读产品史 | 原件不改、不重复GET；准确公开日或明确unknown。 |
| CN-02 | 重找2026-08-25官方IR DOCX精确URL，查重后一次采集/入库；W05原语言DOCX解析/精选摘要 | 旧观察只有mirror DOCX线索，未保存literal official URL；不能造链接或称已获取。整份实质Q/A、条件、目标期与业务进展给locator。 |
| CN-03 | 查SSE Sep10真实分页正文/公开API或正式export，保留完整页/顺序/线程、连接Q/A并归属688012 | 缺页具名；用户提问与公司回答分开，不借其他公司答案。 |
| CN-04 | 找众硅交易最终注册报告、购买/补充/补偿协议、实施通知；按条款价值查重获取 | H1p176–177控制/承诺摘要不等于完整协议；核对对价、补偿、控制、收入目标口径、履约时点及全部修订。 |
| CN-05 | 年报March31到Oct8的演示/战略/重要公告及发行资料区间发现、读正文、materiality | 普通格式套话可注明理由跳过；FY25可转债“不适用”不能推断此后没有。2026Q3未公开不猜。 |
| CN-06 | 修后复用annual/H1及最终IPO：native选择→摘要→公共读→实际use；新attempt修正IPO引用 | 真实 [registered-ipo-v2.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-cn-688012/execution/requests/registered-ipo-v2.json) 已存在，旧matrix指向不存在registered-ipo.json；只能新记录supersession，不改旧封存。 |

[SSE活动入口](https://roadshow.sseinfo.com/activityDetails/40766)搜索预览声称**21家公司合计195条互动/65页每页3条**，预征集另29条/10页；**不是中微195条回答**。这些计数仍待真实原响应复核。本次 actual open 0行动态正文，未获取完整QA，也没猜API。先保留包括行政/结束发言的原始全量，再做公司归属与有用内容抽取。

众硅完整交易资料发现入口：[SSE项目](https://www.sse.com.cn/listing/renewal/ma/index_listing_detail.shtml?auditId=d111c13e8f884c24bc2e5008c6337657&bussinesType=1)、[Apr24报告候选](https://static.sse.com.cn/stock/disclosure/announcement/c/202604/688012_20260424_14Q8.pdf)、[Apr29报告候选](https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-04-29/688012_20260429_2YSG.pdf)。本次只见官方搜索发现及动态索引骨架，没有读候选PDF/完整协议，不能确认最终条款与公开日。

## 3. 腾讯：已有资料与六项动作

已有FY25/FY24年报 d19f1834…/70f52998…、Q1 ef3baa50…、26Q2/25Q2发布64d8d203…/8bf85e0c…，不应重复下载。FY25年报与26Q2摘要有公开使用但为partial。June9 GMTN 1cfbaab8…已保留664页原件/全页解析，实际重点读p24/40/41/46/62/220/227/246/276，不等于664页全条款审读。

H1英文 **4170f80ec8548ea2fb92ec04691a4b252a52de20941e48fb516baf3f98082639**、5,135,808B/122页和overview **a9b0a5d6c68d6ce70b38607b8604d12fc8a150de9dac8bd8dc8679249c586389**、1,676,729B/24页均原件完整，publication null、默认historical资格失败，未消费。不能因为zh H1 not_found再下同一英文报告。

| ID | M3 动作 | 成功证据/保留的未知 |
|---|---|---|
| HK-01 | 绑定官方Aug25 H1事件及已存E700同SHA，再W06追加事实→复用全文读 | 当前HKEX候选在债券counter40242；链接PDF尚未与E700比字节，日期没有修。 |
| HK-02 | 对已有overview找真实带日期event/archive及同SHA | URL的20260916、PDF创建时间、当前网页不算historical公开证明。 |
| HK-03 | 查询当前inventory，再一次获取真Q2 presentation | 精确官方URL已解析，本次浏览超时；987B HTML不是PDF，overview不是同一presentation。 |
| HK-04 | 真实00700 equity issuer June9–Oct8公告和有价值业务新闻分页/区间覆盖 | 当前firstpage Sep9–Oct9，Oct9排除，前序仍未遍历；债券counter不是全部equity公告。 |
| HK-05 | 复用GMTN，读取会影响业务约束的June10pricing/June17completion及supplements | 事件索引已见，PDF正文未在本次取得；资金/债务不当销售，不机械下载所有附件。 |
| HK-06 | W07能力校验后分清ET与官方original call/Q&A；修后复用年报/release摘要 | HK US-only ET限制具名，无录音转录新服务；已有annual/release不冒充call成功。 |

[HKEX候选索引](https://www1.hkexnews.hk/search/titlesearch.xhtml?category=0&lang=EN&market=SEHK&stockId=1000041953)原文列Aug25 16:53 interim event及June融资事件，尚无sameSHA证明；[腾讯结果页](https://www.tencent.com/investors/results/)的[Q2精确presentation链接](https://static.www.tencent.com/website-2026-upload/2Q26-earnings-PPT_20260812_1800-88b183.pdf) actual open超时；[公告页](https://www.tencent.com/investors/announcements/)仅firstpage。均不能称PDF/完整区间已获取或入库。

原call旧失败是schema/capability pre-HTTP，并非402/entitlement。CADPA两份真正HTML优先复用；NetEase旧浏览响应hash与publisher原HTML分开，原HTML GET超时。核心阅读包括游戏地区/确认节奏、广告量价、微信小店技术服务费完整证据组、AI采用转付费条件和限制；不是只有乐观目标。

## 4. Microsoft：已有资料与六项动作

FY25/FY24原件99d693f6…/43829a12…已读；FY26 Q1/Q2/Q3 c963d750…/a60bb6a0…/76945a2c…均已存在，旧独立reviewer公共reader实读，executor Q1失败、Q2/Q3未读，尚未消费。真实类型 regulatory_filing、form10-Q，不能为补标题重下载。

已有官方Q4 release8d63b8ea…、call HTML bdc90bf7…、metrics cf054968…和Sep2deck c02f4ea1…。call原文研究读成功，旧native parser失败；W05修复回放不等于新公司处理。deck15/16选择partial，旧guidance与Sep2更新关系须保留。原语言TXT4ac3b4f0…、66,324B来源URL/date均null，不能借官方HTML日期给不同字节补资格。

| ID | M3 动作 | 成功证据/保留的未知 |
|---|---|---|
| US-01 | W06复审后当前catalog查缺，再通过RF→FF→CWP一次exact FY26 10-K获取，再同请求复用 | 当前旧链无SHA/SourceRef；SEC主文件真实公开8,585,501B，不机械取36MBcomplete submission。真实usage连续，旧失败unknown不补零。 |
| US-02 | 复用正式regulatory_filing/10-Q Q1–Q3、实际prepare/open/extract/use | exact身份/FYQ/period/原SHA；不要用quarterly_report伪类别。 |
| US-03 | 复用完整481行official call、release/metrics/deck，重跑native业务组摘要/公共读/实际消费 | deck不能替代call；reported/CC、年度/季度、guidance supersession分开；ET US真实外部结果另记。 |
| US-04 | 获取最新Microsoft–OpenAI公开合同修订及material客户融资/履约资料 | 完整私约/cap/付款安排未知就保留unknown；融资、估值、采购承诺、当期确认收入分开。 |
| US-05 | latest annualJuly29–Oct8及baseline后相关合同变更的重要沟通区间覆盖 | Oct28季报实际结果在cutoff后；资本分配不强加收入预测。 |
| US-06 | 保留既有TXT、证明同版出处才资格复用；外部市场材料按materiality补原文 | SRG/AWS/Gartner partial browser text不是原HTML/SourceRef；没有价值就具体unused，免硬加provider。 |

[SEC exact index](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/0001193125-26-323660-index.htm)原文确认CIK789019、accession0001193125-26-323660、FY期末June30、July29公开/受理及primary文件大小。**这是可获取目标的公开事件证明，不是完整10-K已下载/入库/读完的证明**。

新发现的[2026-04-27微软官方修订](https://blogs.microsoft.com/blog/2026/04/27/the-next-phase-of-the-microsoft-openai-partnership/)涉及云合作、IP排他性及收入分享的方向/期限/上限；[2025-10-28 OpenAI旧协议说明](https://openai.com/index/next-chapter-of-microsoft-openai-partnership/)披露额外Azure采购承诺与股权估值。必须保留旧声明→新修订来源链，公开news并非完整私约，承诺/融资不可直接变成确认收入。两篇只读web正文已开，未下载HTML、未入库、未造SHA/SourceRef。

## 5. 已有接口与具体请求交接

| 场景 | 真实模板 | 使用方式 |
|---|---|---|
| 精确财报复用 | [annual2025.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-cn-688012/execution/requests/annual2025.json) | schema2.0、company/market/document_kind、exact FY/period/asof/reuse_only，经RF source_preparation→FF→CWP。 |
| 已登记非标准资料复用 | [registered-ipo-v2.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-cn-688012/execution/requests/registered-ipo-v2.json) | source_candidate+实际六字段SourceRef，经既有registered-source公共preparation；不新造DTO。 |
| 缺latest annual | [fy26-fetch.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-us-msft/execution/requests/fy26-fetch.json) | schema2.0，MSFT/US/annual_report/exactFY2026/form10-K/asof/fetch_if_missing，当前累计预算，不更改provider。 |
| 新official原件 | [prospectus-2026-compact-import-request.json](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/fresh-20261009T065028-hk-00700/execution/prospectus-2026-compact-import-request.json) | W04真实有界capture→official-source-import-request/1，以实际URL/bytes/MIME/SHA/receipt交CWP，W06查身份/期间/公开事件。没有字节不得编造请求。 |
| DOCX/分页QA | 发现→actual bounded capture→CWP raw/parse/locator→registered-source | W05 DOCX；QA先原响应页和顺序/线程完整，实不支持则具名原输入交MAIN，不能以snippet代替或另建ledger。 |

原scope记录的CLI为当前RF scripts/source_preparation.py，参数 **--company-wiki-catalog-config、--company-wiki-config、--filing-fetch-root**；M3用MAIN核验安装版本/当前配置，换新独占隔离根，按入口既有stdin/file机制提交这些真实形状。不能拿旧TEMP配置直接重跑、不能绕开W06、不能擅换模型/provider或增加预算。旧US请求40MiB只是上限；主文件8.59MB，本调查未消耗或提高额度。

每条新材料沿M3既有运行流程记录：旧sealed/newattempt、cutoff、公司身份、实际request、event/link、SourceRef/SHA或null、公开日证明/unknown、原文locator、parse、summary/public-read、materiality、actualuse或具体unused、外部限制/缺页、usage、supersedes。JSON每项给旧artifact定位、后续动作、原文检查点和完成证据。修正IPO指针仅新attempt追加。

## 6. 大节点验收与剩余未知

M3统一检查：已有原SHA保持/同请求无重复下载；来源身份/type/period/asof与sameSHA公开事实成立或诚实unknown；DOCX、issuer QA、完整H1、presentation、区间公告与交易/客户条款有原文或具名缺口；原语言parse→选择→summary→public read→真实claim/parameter use逐层留证。融资≠收入、产品市场覆盖≠收入份额、承诺≠完成、出货/部署≠验收确认，货币/单位/CC/期次正确。机械hash只证明字节，预测语义仍由大节点独立review审查。无逐材料人工许可、authorizationJSON/private-public/canary/新签收链。

仍未覆盖：CN准确official DOCXURL/原件、SSE全响应、完整交易条款、FY24公开日；HK H1/overview sameSHA-publication、真presentation、完整公告/call范围；US最新annual actual raw、可公开客户资金/履约条款、若干新native处理/消费。现清单不声称这些材料不存在或W09全绿。

Lam丢失旧GETbody不伪造恢复；只有peer检查仍material才新有界capture另记新SHA。CADPA原件复用，NetEase浏览表示不能当原HTML。无价值的一般格式材料可以有理由跳过，不强行增加provider。

本调查官方域名 **8search query/12open或click**，已到上限，未继续web。SSE0行动态body、腾讯presentation超时、kit不可访问、精确URL/公开日未知保留；网页返回正文不是完整PDF/DOCX/QA已获取/入库。

**FF/ET/provider API/paid API/LLM调用0；新下载/原件入库/事实断言0；生产代码与配置写入0。** 未创建测试TEMP/原件，不需要下载清理。报告写后 2026-10-09T18:20:48.054435+00:00 复核38个选定封存文本/请求和19个物理原件，57个文件SHA/size全部一致，原件变化0；24个SourceRef/18项交接结构成立。不声称全库再验。初次纳秒mtime经JS数字传输有精度丢失，已删除失真的mtime数字，因此不宣称精确mtime前后证明；这不影响独立SHA/size验证。恢复结果见JSON restoration。

