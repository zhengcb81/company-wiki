# Findings：叙述性证据试点

## Requirements

- 财务报表标准数值可由外部清洗数据接口提供；优先处理行业、主营业务、新业务、出海、风险和运营驱动的叙述。
- 覆盖年报、半年报、季报、招股书、再融资文件、投资者关系材料及英文财报电话会议。
- 目标是 filing-fetch 在抓取公司文档时通过版本化 companion flow 调用 earnings-transcripts 的正式 adapter，电话会议英文 TXT 统一登记在 company-wiki；不翻译，做来源锚定的选择与摘要。此处描述目标，不表示当前已有 MCP tool 或已完成集成。
- 仅维护本计划目录，不改变现有项目计划、生产数据或 Worker 状态。

## Prior Read-only Findings

- 现有 source catalog 数据库约 46.27 GiB、约 2720 万 EvidenceSpan；高基数的全量切片及其 JSON/索引是首要排查对象，不能简单归因于 PDF 原件或仅仅归因于重复正文。精确空间分解尚未完成。
- 现有 section_extractor 只针对少数财报/招股书章节；投资者关系、再融资等高价值类型不在默认目标集合。
- earnings-transcripts 存量 43 份英文 TXT，约 2.44 MB，分属 6 家公司；原文混有网站编辑摘要和电话会议逐字稿，至少有两种版式、若干说话人/转写异常。
- 跨项目职责：company-wiki 提供可追溯来源和版本化导出；StockWiki 持有投资研究状态；revenue-forecast 消费驱动证据；StockWiki/RF 是否消费本试点叙述包须分别通过其真实 reader/adapter 合同。invest-quick-scan 只使用可选的实体/证券身份映射，不消费文档、原文或叙述摘要。

## E2E Isolation Findings (2026-09-27)

- 项目已有局部验收断言和临时目录要求，但 G1–G4 大节点原先没有统一的端到端运行生命周期与清理后基线证明。补充一个隔离 E2E 计划，将完整链路集中在既有大节点，而不是每张小卡重复复核。
- earnings-transcripts 当前入口为 Python CLI；其 output 参数不能证明配置目录、cache、log、lock 也已隔离。因此真实下载 E2E 必须注入隔离 config/staging，并证明所有副作用都落在 run-id 根目录；否则只运行 fake provider contract test。
- 稳妥的恢复方法是固定 fixture 只读、每次唯一 run-id、所有临时输出限制到新增运行子目录，测试后只删除本次创建的内容，再逐项比对测试目录前后文件树。禁止通配符清理和对公司原始数据目录做全量 46 GiB 快照。
- 跨仓 schema 只读核对发现：StockWiki 的严格 Source Provider v1 与 pilot `narrative-evidence-selection-bundle/0.2.0` 不同构；StockWiki provider 配置当前 disabled。G2a 必须等待 owner 批准并用其真实 reader/adapter 做隔离 E2E，不能以本仓 harness 代替；quick-scan 的 G2b 仅测试 optional identity mapping。

## Transcript Acquisition Contract Findings (2026-09-27)

- 当前 `ALL_TOOLS` 中没有 earnings-transcripts MCP tool；`Projects/earnings-transcripts/earnings-transcripts/scraper.py` 是现有 CLI。`--output` 只改 transcript 文件路径；`main()` 仍从脚本目录载入固定 config，并初始化 transcript/log 目录、日志、single-instance lock、cache。CLI 默认翻译，必须带 `--no-translate` 才跳过；`--quarters` 表示最近 N 季，不是可验证的精确 fiscal-period 请求。直接把当前 CLI 当隔离 provider 会留下共享副作用风险。
- 当前 `filing-fetch/scripts/fetch_filing.py::resolve_filing()` 走 verified identity → company-wiki resolve/ensure，仅返回单份 filing handle；`filing_contracts.py::validate_request()` 对 schema 1.2 严格拒绝未知字段，未实现 related transcript 调用或复合结果。安装/项目 `SKILL.md` 写 request schema 1.1、SKILL v1.4.0，而同目录代码写 request schema 1.2、`SKILL_VERSION=1.2.0`；集成前需由该接口 owner 指明真实活动合同，不能据技能文案推断代码行为。只读 `git status` 因目录 ownership protection 未能取得状态，本轮没有尝试更改 safe.directory。
- Transcript writer 会给 transcript content 前置生成式 header；FMP response 把 `url` 设为 `FMP API`，不是可验证 HTTPS URL。因此新的 canonical 保存不能直接把该 CLI 输出当 provider 原始响应；应定义正文/元数据分离、精确期次、真实来源 URL，分别核验 provider-payload hash 与 company-wiki canonical TXT hash。
- 结论：G1e 需增加**独立上游 transcript acquisition contract gate**（filing-fetch 新版 request/response + earnings-transcripts 可注入、无翻译、精确 period、隔离副作用 adapter）。此 gate 与 RF `I-05-C/I-06-A` 下游 producer/consumer 冻结不同；它允许先完成 acquisition 集成，而 G2 consumer、shared producer/Worker 仍必须等 RF G0。当前没有把 fake CLI 或本仓 parser harness冒充真实 acquisition E2E 的依据。

## Sample Register

样本根路径：PDF 为 `C:/Users/郑曾波/Projects/company-wiki/companies/`；TXT 为 `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcripts/`。文件哈希是只读计算值；表内只展示前 12 位，完整值可按文件重新计算。

| 编号/类别 | 相对路径或文件名 | 页/行 | 大小 | SHA-256 前 12 位 | 试点用途 |
|---|---|---:|---:|---|---|
| P01 年报 | `中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf` | 259 页 | 9,165,875 B | `d64c410832f2` | 大量财务表与业务讨论混排 |
| P02 半年报 | `中微公司/raw/financial_reports/中微公司：2025年半年度报告.pdf` | 188 页 | 6,361,468 B | `91ae4978b694` | 中期进展与期间增量 |
| P03 季报 | `中微公司/raw/financial_reports/中微公司：2026年第一季度报告.pdf` | 15 页 | 217,264 B | `ab7bb0076b2a` | 小文件中财务与业务信息相邻 |
| P04 招股书 | `中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf` | 429 页 | 11,211,796 B | `19cdb41e03b2` | 基线业务、技术与风险 |
| P05 可转债 | `三角防务/raw/research/三角防务：1-1西安三角防务股份有限公司创业板向不特定对象发行可转换公司债券募集说明书.PDF` | 302 页 | 18,858,880 B | `2ea34bcb188f` | 项目用途、产能和阶段，首封面无可提文字 |
| P06 定向增发 | `三角防务/raw/research/三角防务：西安三角防务股份有限公司向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF` | 191 页 | 5,595,592 B | `cd803fe9528f` | 募集投向与注册稿状态 |
| P07 投资者关系 | `万润股份/raw/research/万润股份：投资者关系活动记录表20260515.pdf` | 6 页 | 153,851 B | `221467c15a24` | 套话与具体业务问答混合；有跨页问答 |
| P08 投资者关系 | `万润股份/raw/research/万润股份：投资者关系活动记录表20250430.pdf` | 13 页 | 236,281 B | `4455d6f099f5` | 密集业务问答 |
| P09 格式制度 | `中微公司/raw/investor_relations/中微公司：投资者关系管理办法（2025年8月）.pdf` | 7 页 | 167,252 B | `76e146985388` | 应跳过业务切片的负例 |
| P10 会议通知 | `八方股份/raw/research/八方股份：关于召开2025年年度暨2026年第一季度业绩说明会的通知.pdf` | 3 页 | 95,673 B | `823b2bdee3b6` | 文件名含“业绩说明会”但正文不含会议问答的负例 |
| T01 新版 TXT | `MSFT/MSFT_Q4_2026_earnings_call.txt` | 340 行 | 66,324 B | `4ac3b4f0fa1b` | 网站摘要与逐字稿并存、说话人冒号样式 |
| T02 旧版 TXT | `NVO/NVO_Q4_2024_earnings_call.txt` | 604 行 | 66,597 B | `d00e2a4537b8` | `Prepared Remarks`/`Questions & Answers`、说话人独立行 |

只读 catalog 基线：P04 已有 `normalized` 和 `sections` artifact，22,458 个 evidence spans；P05/P06 均被归入 `document_kind=other` 且没有解析产物；P07/P09 为 `investor_relations` 且当前无解析产物。P01–P04 的匹配记录为 `retired`，但 P04 仍有历史解析产物；这些查询不代表最新可消费状态。试点按原文直接读取，不以 `retired` 等同于文件缺失。

## Pilot Evidence

### 方法和证据范围

使用 PyMuPDF 1.26.7 只读打开 10 份 PDF，并对相关页使用 `page.get_text(sort=True)`，页码从 1 起；括号内偏移是该方法产生的**页内字符偏移**，从 0 起，尚不是生产 EvidenceSpan locator。对 2 份 TXT 读取原始 UTF-8 行。逐页检索仅用于找候选，随后人工阅读问答及上下文；中文来源做中文来源摘要，英文 TXT 做英文来源摘要。未调用 LLM、Worker、生产解析或下游投资分析。本轮结果是小样本的可行性与失效模式验证，**不构成整体召回率或成本节省率证明**。

### 试点来源摘要卡（人工抽样产物）

| 案例 | 原文定位与锚点 | 来源摘要 / 选择结果 | 必须保留的限定 |
|---|---|---|---|
| C01 年报新业务 | P01 PDF 第 40 页，页内 64 起“新产品开发已经取得了显著成效” | 多款 LPCVD/ALD 薄膜设备进入市场并获重要客户重复订单；EPI 处于客户端量产验证；湿法设备布局涉及**拟议**收购。选取产品进展，略过相邻口号式增长表述。 | “重复订单”“量产验证”“拟购买”是三种不同成熟度。 |
| C02 半年报中期方向 | P02 PDF 第 21 页，页首行业及业务讨论 | 半年报将自主研发、合作及潜在并购作为设备类别扩展方向，提出未来 5–10 年覆盖更广设备市场的愿景。需与年报更新做时间线。 | 未来覆盖是管理层计划，不是实现事实。 |
| C03 季报页内混排 | P03 PDF 第 3 页，页内 744 起“四款MOCVD 新产品” | 四款面向功率器件/显示应用的新产品进入客户端验证，部分获得批量订货；同页下半部转为收入、利润和非经常性损益。保留运营进展，财务表走结构化数据链。 | 不能按“季度财务页”整页跳过；“部分”不应扩大为全部四款。已视觉核对版面。 |
| C04 招股书历史基线 | P04 PDF 第 114 页，页内 55 起“第六节 业务与技术” | 招股时的刻蚀、MOCVD 产品、应用领域和客户阶段构成历史基线。相邻产品表需按产品保留关键用途。 | 招股书描述是其披露时点的状态，不能直接当 2026 年现状。 |
| C05 可转债项目 | P05 PDF 第 231 页，页内 518 起“项目建设的必要性”；第 13–14 页对应供应商/建设风险 | 项目论述从锻件向加工与零件交付延伸；蒙皮镜像铣项目受供应商产能和技术验证制约。建设理由与执行风险应成对呈现。 | 募投、产能消化和订单优势是预测/论证，不是已交付结果。 |
| C06 定增认证门槛 | P06 PDF 第 3 页，页内 132 起“募投项目供应商认证和产品认证的风险”；第 101 页为项目必要性 | 数字化集成中心向下游装配延伸，需要供应商及产品认证；文本给出认证时长的预计区间。项目逻辑和认证条件均应入选。 | 注册稿中的时间与达产安排为预计值；“无需”某项认证仅适用于文中明确的原有锻件项目。 |
| C07 IR 中试线 | P07 PDF 第 6 页，页内 198 起“16、问：” | 对硫化锂中试线，管理层表示当时预计 6 月底前建成并开展中试。单独保留问答与时间条件。 | 本样本不能证明后来按期建成；待后续来源验证。 |
| C08 IR 跨页问答 | P07 PDF 第 5 页问题 15 延续至第 6 页回答 | 车用沸石需求波动背景下，公司称推进石化催化分子筛，已有产品销售。页边界不能截断问答。 | 问题中的估值比较是投资者观点，不写作公司事实。 |
| C09 IR 错误前提 | P08 PDF 第 2 页，页内 61 起“2、问：”，随后问题 3 与回答 | 公司称非车用沸石已在石化催化及 VOCs 领域销售；问题 3 称 OLED 等业务收入不足 5%，回答明确纠正为所列两个 OLED 业务主体占比已超 25%。 | 必须区分投资者提问数字与管理层纠正；合作意向书不等于新增收入已实现。已视觉核对问答表格。 |
| C10 英文新式电话会 | T01 第 124 行起为 `Full Conference Call Transcript`，第 236–248 行讨论模型选择，第 252–258 行讨论容量 | **English source summary:** Management described enterprise model choice as part of its platform design. The CFO said demand still exceeded available capacity and efficiency gains were monetized quickly during the quarter. | 第 1–123 行含网站编辑摘要、词汇表等；来源为 Motley Fool 转写，不能把编辑摘要误标为管理层逐字发言。 |
| C11 英文旧式电话会 | T02 第 178 行起 `Questions & Answers`，第 184–212 行为双问题、多管理层回答 | **English source summary:** Management attributed prescription patterns partly to benefit-plan changes and starter-dose supply. On a separate CagriSema trial question, the development executive said it was too early to speculate on superiority. | 按两个子问题分别锚定答复；不能把“尚早判断”摘要成临床优势已证实。 |
| N01 制度负例 | P09 PDF 第 1–7 页 | 规定投资者关系管理职责、形式及合规要求，未发现具体业务动态；登记/检索原文即可，业务切片状态 `skipped_no_narrative`。 | 仅凭“投资者关系”文件名会误收。 |
| N02 会议通知负例 | P10 PDF 第 1–3 页 | 公告会议时间、地点和提问方式，并无正式会议回答；登记元数据与事件时间即可，业务切片状态 `skipped_event_notice`。 | 不能把“将回答问题”生成已经答复的问答。 |

### 对现行机制的直接检验

- P04 现有 `sections` 索引只含 `risk_factors`、`business_and_technology`、`important_events` 三个角色；其中 `business_and_technology` 覆盖 **83 页、302,779 字符**（页 114–196）。章级定位有用，但还须章内选择。现有 `normalized.md` 为 2,490,019 B，章节索引为 453,482 B；不能把章节 artifact 大小等同于最终摘要大小。
- 现行 `section_extractor.TARGET_DOCUMENT_KINDS` 包含年报、半年报、招股书、券商研报，未包含季报、投资者关系、再融资和电话会议；P03/P05–P08 的正例不进入该抽取范围。
- P05/P06 被归为 `other`，显示再融资识别和准入必须先修，随后才能按项目/风险抽取。
- P03 第 3 页及 P08 第 2 页的渲染图人工核对过：前者的运营叙述与财务段落在同页，后者一个表格单元连续承载多个问答。页级二元保留/丢弃均不够。
- T01 原文 65,980 字符，正式逐字稿从字符 7,214/第 124 行开始；网站尾注从字符 64,917/第 334 行开始。T02 原文 65,986 字符，准备发言从字符 545/第 20 行开始，问答从字符 27,770/第 178 行开始，尾注从字符 65,219/第 598 行开始。两种版式必须分别识别正文边界。

### 尚未验证

- 全语料的召回率、误收率、节省的数据库体积、LLM 费用与运行时长；本试点只有 12 份样本和有限人工片段。
- 英文电话会在线重新下载的可用性、FMP 来源校验和指定财年季度检索；本轮仅检查本地代码与已有 TXT。
- 现有来源版本中 `retired` 与下游可消费状态的完整影响；需在实施前做同文件多版本链路检查。

## 第二轮只读小样本实验（2026-09-26）

**方法**：不调用 Worker/LLM、不落盘解析产物。以 PyMuPDF 1.26.7 对 P03 第 3 页、P04 第 114 页、P08 第 2 页分别运行 `get_text('blocks', sort=True)` 与 `find_tables()`，按现行 `_pymupdf_page_snapshots` 的“块与表格 bbox 相交即排除正文”规则计数。另对 P05 第 231 页、P07 第 6 页比较 `get_text('text', sort=False/True)` 长度。对生产 `catalog.sqlite3` 使用 SQLite URI `mode=ro&immutable=1` 与 `PRAGMA query_only=ON` 读取元数据，并以固定随机种子 20260926 在 rowid 空间分散抽取 1000 条旧 `evidence_spans`；这是样本估计，**不是全库表/索引字节的精确分解**。尝试 `dbstat` 失败：当前 Python SQLite 没有该虚表，因此不把样本比例直接外推为准确的 46 GiB 构成。

| 观察 | 只读结果 | 对设计的影响 |
|---|---|---|
| 旧库容量/空闲页 | DB 46.266 GiB，4096 B/page，12,128,258 页，freelist 仅 9 页，WAL 当时 0 B | 不能把一次 `VACUUM` 当成主要节省路径；应先阻止新增高基数行，并在独立迁移中测表/索引占用。 |
| 迁移暂存容量 | 2026-09-26 C 盘空闲 83,279,212,544 B，约 77.56 GiB；一份与主库等大的副本约需 46.27 GiB，两份约需 92.53 GiB，尚未计 WAL/索引重建/备份增长。 | 现有 C 盘余量不足以同时放两份完整副本；W7 先核经验证的独立卷/快照和最坏空间预算，不能靠删除生产库临时腾空间。 |
| 旧 span 随机样本 | 1000 条中 820 条 locator 为 table cell，496 条 `raw_text` 为空；`raw_text` 平均 16.9 B，`span_json` 平均 812.6 B（p95 932 B）。JSON 含定位、结构值、来源和解析元数据，表上另有 3 个索引。 | 空表格单元和每单元 JSON/索引可能是大库的重要驱动；“46G 主要因为全文文本重复”过于简单。新流水线要按候选/选中单元存证据，禁止重新物化整表空单元。 |
| P08 IR 第 2 页 | 表格识别为 1 行 2 列，bbox 约占页面 71.9%；按旧排除规则 30 个正文块中 29 个被排掉，仅余约 4 字符，而表格单元含 864 字符和多个问答。 | 不能直接复用旧“表格优先、相交正文丢弃”的 PDF 快照函数；IR 需保留双视图并在大单元内拆问答。 |
| P04 招股书第 114 页 | 产品/应用表 bbox 约占 10.2%；27 个正文块中 7 个与表相交，表格单元含产品类别、应用领域等业务描述。 | 不能一概排除表格；应区分标准财务表和产品/客户/产能/募投等业务表，并校验表格提取与页文本的锚点覆盖。 |
| P03 季报第 3 页 | 财务表 bbox 约占 1.4%；32 个正文块仅 1 个相交，运营叙述仍在同页。 | 页级/表格级二元过滤仍不够；同页要按单元选择。 |
| PDF 文本偏移稳定性 | P03/P04/P05/P07/P08 五页 `sort=False` 与 `sort=True` 文本均不同，字符长度差分别为 157/190/55/213/59。 | 试点中的“页内字符偏移”只对指定提取方法有效，不能直接当持久 locator；新证据要绑定 parser 版本、精确片段 hash 与可回放的页/段/表锚，升级解析器时重验。 |

**仍待验证**：全库 table-cell/空单元比例与每张索引实际占用、不同 PDF 版式下双视图的召回/精确率、长期存储节省、按需回源时延、跨版本 locator 重验。旧来源 P01–P04 为 `retired` 的实际可消费语义仍要在隔离 catalog 中验证；只读 raw 试点不能证明这些来源当前可发布。

### 全文检索的最小反例

现有 `source_catalog/evidence_query.py` 的主要查询按精确 `source_id/document_id` 列出旧 spans；本仓 `source_catalog` Python 代码中未找到 FTS 虚表或 `MATCH` 查询。生产 SQLite 编译了 FTS5，但当前库无虚表。在**纯内存** SQLite 中插入一行含“硫化锂的中试线”的中文句子：`unicode61` 的 `MATCH` 对“硫化锂”“中试线”均返回 0；`trigram` 的 `MATCH` 对这两个三字词返回 1，但“出海”两字词返回 0（`LIKE '%出海%'` 可找到，索引是否有效和大库时延未测）。这证明不能把“引入 FTS5”直接写成中文全文检索已解决。W0/W5 要先定义中文两字词、英文词、精确短语、OCR 页和结果定位的查询合同，再比较轻量页级索引、trigram/分词器及按需回源的空间与 p95。新 DAG 不写全量 normalized 后，**现有证据列举接口无法自动替代全文检索**。

### 降容升级的附加只读/内存试验

对上述固定 seed 的 1000 条旧 `span_json` 仅在内存中测试 zlib：原 JSON 合计 812,588 B，逐行压缩合计 469,528 B，合并为一个压缩批次 175,172 B（原 JSON 的 21.6%）。大批量压缩能利用重复字段名，提示按来源的冷归档有潜力；这**不是**生产归档文件大小，更不是全库容量预测，未含 SQLite B-tree/索引、其它表、检索索引和备份。试图精确全库计数的只读扫描两次均因耗时较长主动中止；本机 Python/CLI SQLite 都没有 `dbstat`。精确分解及缩库预测必须在独立存储/副本上完成，详见[降容升级方案](space_reduction_upgrade.md)。

另一固定 seed（20260927）抽取 1200 行并把 `span_json` 解码后与关系列逐字段比较：1022 行为 table cell；JSON 平均 815.5 B。`span_id/source_id/locator/raw_text/parser_name/parser_version/parse_status` 七个字段与独立列逐行完全相等；这些键值在 JSON 内合计约 418,218 B，另有 table cell 的 `structured_value.raw_value/value` 再复制正文约 18,324 B。两项相加为 **436,542 B**，约占样本 JSON 的 **44.6%**（364 B/row）。之前记录的 460,942 B / 47.1% 比这两项多 24,400 B，未找到可复核的分项依据，故撤回该总数；W0 应用固定脚本复算。即使校正后，这仍只是样本 JSON 中已识别重复字段的比例，不是全库 DB 可回收率；行头、索引、其他结构和唯一业务字段未计。它支持 vNext 不重复嵌入身份/定位/parser 字段，正文也只存一次。

## 旧库提前退役的额外只读与临时库演练

生产库 `catalog.sqlite3` 当前 49,677,344,768 B（46.266 GiB）、WAL 0 B；`worker_control.json` 的 desired_state 为 paused。SQLite 中除 `evidence_spans` 外有 17 张表，共 189,580 行：其中 sources 43,112、documents 23,530、locations 46,606、artifacts 8,191。documents 中 active 13,839、retired 9,501，另有 upstream_rejected 189 与 quarantined 1。用 `idx_documents_status_kind` 和 `idx_spans_document` 的关联索引精确计数，active 文档共有 **1,490,530** 条旧 span（8.75 秒）；这不是对全表表/索引占用的分解。

在系统临时目录执行两次**不改源 DB**的 SQLite 复制试验，均完整复制原 DDL/非 span 数据和索引，并在结束后自动清理：

| 复制范围 | 临时 DB 大小 | 检查 | 实际意义 |
|---|---:|---|---|
| 17 张非 span 表 | 225,280,000 B = 214.84 MiB | 189,580 行，`foreign_key_check` 无错误，`quick_check=ok` | 来源、文档、位置、artifact、退役/恢复审计等目录状态可保存为小库；不是完整旧证据服务 |
| 上述目录 + active 的全部 1,490,530 条 span | 3,059,200,000 B = 2.849 GiB | 共 1,680,110 行、现有索引重建，`foreign_key_check` 无错误，`quick_check=ok`；总耗时约 143 秒 | 保持 active 旧证据热查询有真实空间基础；retired 旧证据仍需明确的归档/冷读状态及可恢复备份 |

`.source_catalog/derived` 约 2,826,010,634 B，`index` 约 45,052,670 B；`source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` 为 5,207,478,767 B，首条可解析为旧 span JSONL。ADR-009 记录 2026-08-07 归档 25,708,956 条 retired span，但 H01 独立复核指出该归档缺不可覆盖发布、逐项 hash 与稳定快照保证，不能直接替代完整旧库备份。StockWiki 生产 `config/source_provider.yaml` 当前 company-wiki provider 为 disabled；跨仓实际读路径仍需在切换前作差分验证。

只读抽取 6 处各 8 MiB 数据块做 zstd level 3 试压，比例分别约 15.3%、12.7%、12.7%、13.1%、12.2%、32.1%；**这不是完整 DB 压缩率**。当前磁盘空闲约 85,079,416,832 B（79.24 GiB）。完整压缩快照及恢复演练的峰值空间要在实际文件产生后判定，详见[提前退役审查卡](early_catalog_retirement.md)。

## 原文处置补充核查（2026-09-26）

- `src/company_wiki/source_contract/source_manifest.py` 中 `SourceManifest v1` 保存 source SHA、相对原路径、大小、`immutable_status`；`verify_file()` 在原路径不存在时失败。现有两个 immutable 状态未包含有意删除，因此需单独版本化 `SourceDisposition`，保留历史 manifest 而不伪称文件仍可回读。
- 生产 SQLite 只读查询的 `company_raw`/`original_primary`：active 7,524 个 location、历史 `observed_size` 合计 6,511,169,498 B；retired 9,046 个、合计 18,641,858,464 B。location 可能缺失/移动/不在 C 盘，且 retired 不能等同无价值；实际可回收字节须 D0 按真实路径/卷、SHA、别名和消费引用逐件核对。
- 旧源身份按 SHA，路径是 location；同 SHA 的重复副本可以在保住 canonical 一份且迁移所有路径引用后清理。唯一低价值原文删除会丧失未来原文回读/复核能力，不能仅由 `skipped_*`、未命中关键词或文档类型推出。详见[原文处置 D0–D5](raw_disposition_plan.md)。

## 逐步空间账补充只读实测（2026-09-26）

- 三处主要本项目数据目录的文件逻辑长度：`.source_catalog/` 52,700,659,299 B，`source_manifests/` 5,207,479,410 B，`companies/` 25,173,861,091 B；合计 83,081,999,800 B（77.376 GiB）。公司原文目录 PDF 15,129 个、25,073,770,125 B（23.352 GiB），不能据此认定均可删除。
- 在不落盘、不改生产 DB 的条件下用 `zstd -3 --stdout` 读取完整 49,677,344,768 B 主库并计输出流：6,198,704,362 B（5.773 GiB，耗时约 96 秒，输入前后 stat 长度与 mtime 一致）。此计数不是可恢复备份，正式 F2 仍需写快照、流/文件 SHA 与实际恢复验证。
- 以活跃临时库 3,059,200,000 B 和压缩流预算计算，同盘 F1/F2/F5 净释放约 37.644 GiB；完整恢复临时文件也在 C 时峰值增量约 54.888 GiB。C 盘当时空闲 85,058,437,120 B（79.217 GiB），理论峰值余量约 24.329 GiB，未含安全缓冲。逐步公式见[空间账](stepwise_space_budget.md)。

## G1 主样本与量化目标补选（2026-09-27）

- P02 半年报 p.21 将“超过60%的设备市场”拆在相邻 PDF 文本片段：第一段止于“超”，下一 locator 为“过60%的设备市场”。v15 的 17 锚点基线通过；为让量化目标摘要有完整已选证据，新增专用锚点后首轮诚实失败 1 次，未把不完整证据记为成功。
- 选择器新增量化市场覆盖目标识别：只将命中目标所需的连续 PDF 片段成组选择、共用原有每文档预算；排序使该组在容量竞争时优先于普通事件。回归测试用两 span 预算验证完整保留并验证“60%的设备市场”锚点精确映射到第二个 locator。
- v16 主样本：12 件、52,196,853 B 原文、1,289 个 span，1,289/1,289 定位回读、18/18 锚点命中、0 blocked、0 超上限；状态 2 selected、6 partial、2 skipped、2 needs_review。序列化 evidence JSON 542,820 B（1.0399%）。
- v11 回归集：4 件、14,939,109 B 原文、401/401 定位回读、5/5 锚点、0 超上限；序列化 evidence JSON 202,661 B（1.3566%）。这是一组固定回归文档，不是盲测留出集，也不能由小样本外推召回率。
- v8 对 13 条人工摘要草稿完成引用/角色/语言/问答关系机械校验；逐页核源记录在 [G1 摘要来源支持审查](g1_summary_source_support_audit_v1.md)。该审查由实施者完成，不是独立签字；所有摘要仍待审。实测候选 JSON 文件字节与序列化字节相等，但没有连接持久 catalog、扫描器或生产 writer，故不称为数据库节省量。
- 44 个相关单测通过，`ruff check` 通过；v16/v11/v8 JSON 可解析。Worker 仍暂停。Revenue-forecast 当前只读状态与剩余共享契约见[跨项目协调](cross_project_coordination_2026-09-26.md)；在 G0 通过前不接共享目录、不建持久需求、不做消费者切换。

## D0 当前文件元数据盘点（2026-09-27）

- 只读 immutable catalog 并逐路径 stat 29,409 条登记原文位置。company-wiki 自有 `company_raw` 里 7,524 条 active 为 6,511,169,498 B，9,046 条 retired 为 18,641,858,464 B；这些状态均不能推出删除资格。除 catalog 原已标记 `missing` 的 3 条外，登记路径实际存在且大小相符；本轮未算文件 SHA。
- `companies/` 当前目录元数据为 33,131 个文件、25,189,914,642 B，其中 16,561 个非登记原文路径占 36,886,680 B；须分类后才能识别 sidecar/wiki/遗漏来源，不能直接清除。`source_manifests/` 实际 5,207,479,410 B，`.source_catalog/derived/` 2,826,010,634 B，`index/` 45,052,670 B。
- `.source_catalog/` 全目录当前为 8,214 个文件、12,277,797,132 B；其中 `retirement/` 6,198,717,464 B、active-only 主库 3,055,796,224 B、`derived/` 2,826,010,634 B、`index/` 45,052,670 B。三个自有数据目录合计 42,675,191,184 B（39.744 GiB），较 F5 前同口径下降 40,406,808,616 B（37.632 GiB）；与 F5 实测净释放 37.630 GiB 口径不同，不以逻辑长度代替磁盘可用空间。
- 登记 artifact 有 8,191 行、6,714 唯一路径、唯一物理路径逻辑长度 2,794,944,096 B；1,477 路径由多条记录复用，620 路径存在历史大小冲突。这要求按 path + source/version + 当前引用整体核对，不能按 artifact 行数直接计算或删除。
- 本地 raw 按 catalog SHA 可识别 52 组双路径别名、共 197,690,786 B；“留一份”的 98,845,393 B 为理论候选上限，未新算 SHA、未查完引用、未判所有权或保留期，不能报告成可回收量。
- 本地引用映射：1,490,530 条当前 evidence span 涉及 1,636 个 source ID；其中 1 个 ID 没有登记原文 location，329 个 ID 在多个 root 有 location，未发现 span 只挂在 retired location 上。8,191 条 artifact 记录都有 source/document ID。跨仓 consumer 引用另受 G0 门禁约束。
- `source_manifests/` 内一个 643 B manifest 可与已登记 PDF SHA/location 对上；5,207,478,767 B retired-span gzip 仅核了路径和长度，未读取/验证内容，不作为可清理对象。
- `companies/` 中 5 个文件在 2026-09-26 UTC 之后更新，合计 16,120,320 B：紫金矿业 2023 年报 PDF+sidecar 与 Microsoft 两个 8-K HTML+sidecar，和 revenue-forecast 当前资料工作一致。确切路径查询确认 5 个都未登记到 catalog locations；目录总量已包含它们，但必须保持 `hold`，直到 owner 接管并完成登记。不得为 D0 盘点启动 scan/normalize，也不得进入 D1–D3 清理候选。
- D0 收据：[`d0_inventory_receipt_2026-09-27.md`](d0_inventory_receipt_2026-09-27.md)。本地 source/location/artifact/span 映射已完成只读盘点；跨仓 consumer 的处置响应仍须 G0/D1 合同冻结，G0 未放行前不做共享接入。

## 隔离检索试点与现有 API 边界（2026-09-27）

- CodeGraph 结构查询和源码复核确认：`EvidenceQueryService` 的 `lookup(source_id, locator)` 是精确定位查询，`list_spans` 只能按 source/document 列出旧 `evidence_spans`；`SectionQueryService` 只能列出 sections。legacy `scripts/search.py` 的 TF-IDF 索引输入是 Wiki 页面，不是新选择包。不能把任一现有接口声称为新叙述证据的全文检索实现。
- 在本仓新增隔离 prototype `source_catalog/narrative_retrieval.py`：只消费 `summary_scope=selected_evidence_only` 的版本化包，在进程内按证据组建立 BM25 postings；中文 CJK bigram、英文/数字词项；精确短语与覆盖度参与排序。结果保留 source ID/hash、文档类型、选择状态/覆盖、evidence IDs 和原 locators。`blocked`/`skipped_no_narrative` 不进入结果，`needs_review` 命中显式带状态。实例不建文件、不写 catalog、不保存持久索引。
- `narrative_evidence_pilot.py --package-output` 仅允许与 `--run-root` 联用，且输出必须位于 run-root 的 `outputs/`；文件封装已选 evidence groups，不写整篇 Markdown。G1 P06 定增 + T02 电话会 E2E 已用该包查询中文“向下游装配产业领域的延伸”和英文“too early to speculate”，检查 source SHA、证据 IDs/locator 并断言证据包文件小于两份原文合计；最终 run tree 已清理复原。
- 历史收据需按 schema 版本区分：bundle v0.2.0 的早期合并回归曾被 P06/T02 对旧 0.1.0 bundle 常量的断言阻断，断言已修正。最终代码上将 12 个检索/回源单测、P06/T02 双样本 E2E 与 12 件 selected-anchor/raw-replay E2E 合并运行，结果 **14 passed in 122.56s**，`ruff check` 通过；pytest 实际 basetemp 已删除并复核不存在，`tests/e2e/.runtime/` 运行前后均不存在。该回归证明已选证据链的 locator/raw replay 与样本链路通过，不证明未选内容召回率/精确率、盲留出集、p95 或生产 catalog/export/consumer。
- 同一合并回归在 2026-09-27 以唯一新 basetemp 再运行：**14 passed in 130.77s**；pytest 报告实际 basetemp 清理成功且逐路径核实不存在，`tests/e2e/.runtime/` 仍不存在，`tests/e2e` 文件 SHA 集合前后相同。测试范围与上一条相同，不扩大为生产 catalog、provider、Worker 或跨仓 consumer 验收。
- 当前边界：`NarrativeEvidenceResolver` 仍是 G2 预研，不是正式 package-backed service。bundle v0.2.0 自带 parser/selector 回放合同（含版本、语言/文档类型、options 与 max-selected）；resolver 的调用方仍须显式提供 source ID→raw path 映射。它没有生产授权/撤回、历史时点过滤或正式 query/preview API。现有 `EvidenceQueryService.lookup` 仍不能单独读取不落 `evidence_spans` 的新 package；G2 仍须冻结这些语义及三仓消费行为，不能据此删旧 spans/旧检索路径。

## Resources

- `AGENTS.md`（项目职责边界）
- `docs/plans/source-catalog-worker-recovery-v5-2026-09-03/`（现有独立 Worker 计划）
- `docs/plans/core-section-extraction/`（已有章节提取计划）
- `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/`（电话会议抓取与 TXT 样本）

## G1–G4 端到端计划复核（2026-09-27）

- E2E 运行根在开始时必须不存在且由唯一 run-id 独占；所有样本副本、模拟/真实下载、数据库/WAL、日志、锁和派生产物只能写到该根。新下载若不是基线内容，测试后必须确认文件与整个运行根均不存在。
- 为覆盖“运行目录已创建但进程在写清单前中断”的窗口，控制清单改为运行根的同级文件：先唯一创建 pending、完整写入并 fsync/原子改名，再创建运行根。pending 阶段不允许任何输入/下载/数据库输出；启动恢复只可清理同 ID pending 且运行根不存在的情况。
- 正常清理和强杀/断电恢复都只识别一个经过校验的 run root；不按 run-manifest 任意列出的路径或通配符删除。PID 必须连同进程启动时间校验以规避 PID 复用；manifest 损坏、进程仍活或发现 reparse/outside-root 写入时失败关闭并保留现场。
- 大节点矩阵区分真实 E2E 与合同测试：filing-fetch transcript 测试必须经过生产编排调用边界并以 fake tool/provider 替代外部副作用；下游三仓需由各自 reader/adapter 实际消费；Worker 必须是真子进程；原文处置只在 scratch 副本删除。
- E2E 只作为 G1–G4 大节点审查，不逐张 W/N/D 卡重复全套；日常变更运行受影响目标测试，节点放行才运行对应完整 E2E 组。

## FMP/Koyfin/Seeking Alpha 成本与权限调查（2026-09-27）

- 本地 companies 当前有 246 个目录；这只是预算压力分母，不代表 246 个已核实的美国上市证券。SEC 官方 submissions API 不需要 API key，可供美国披露发现。公司 IR、交易所原始公告仍是其他市场的首选来源。
- FMP 官网当前公开 Basic 免费 250 calls/day、滚动 30 日 500 MB；Starter $22/月年付、Premium $59/月年付、Ultimate $149/月年付。官网把 Earnings Call Transcripts 列在 Ultimate；官网又声明展示/再分发需要独立数据许可。精确 endpoint 的个人 key 权益必须实测，不能据套餐名称推定。
- 用户提供的 FMP key 只读 MSFT canary：profile 200、完整参数 SEC search 200、press releases 402、transcript dates 402。SEC 首次 400 是遗漏必填 from/to，补齐后 200；不是权限拒绝。早前完整 transcript canary 为 402。响应体不保存，HTTP 200 不证明全量 coverage 或落盘/只读 export 权利。
- Koyfin Plus 官网年付档显示 $39/月，网页含 filings/press releases/transcripts；Koyfin FAQ 明示不向用户开放 API，部分数据受供应商下载限制。Seeking Alpha Premium 官网 $299/年、官方列无限 transcript 阅读，但 API/feeds 属单独合作，站点条款限制机器人抓取/索引。二者不能作为 Worker 自动来源。
- 以 20 家每日、226 家每周五轮、20% 余量计算：FMP Basic 的 SEC 补充发现为 2,076 calls/30 日，首月加一次性 profile 为 2,372；纯 SEC/IR 方案为 0 FMP calls。条件性 Starter 新闻稿方案为 4,200，Premium 加三种日历 feed 为 4,308，Ultimate 事件触发 transcript 为 4,505；这几档互斥，后三级 endpoint 权益未证实。完整假设见 [外部来源成本卡](provider_cost_and_capability_2026-09-27.md)。
- 当前无需采购。G1e 需先冻结 provider/filing-fetch 合同，再取 20 家核实证券做 30 日增量覆盖、权限和带宽试点；不因网页内容和个人订阅默认取得自动采集或存储权限。只在大节点汇总审查。
- 本轮再次只读检查 earnings-transcripts 工作树，已见新增但未提交的 transcript_api.py 与 transcript_tool.py；这是旧审计之后的新本地状态，不再把“只有 scraper.py CLI”当作当前事实。filing-fetch 集成与正式跨仓 G1e E2E 仍未完成，G0/Worker 状态不变。

## G1e 电话会议来源权利与原件身份（2026-09-27）

- Motley Fool 官方 2026-01-29 更新的使用条款禁止 agents、robots、scripts 等自动访问/复制/采集站点内容；当前 earnings-transcripts 的 `motley_fool` provider 即使能返回英文 TXT，也不得因此接入 filing-fetch/Worker 自动生产。用户授权修改本地仓库不等于内容方授权。官方来源：https://www.fool.com/legal/terms-and-conditions/fool-rules/
- Seeking Alpha 官方个人站点条款限制机器人下载、索引和抓取；Koyfin FAQ 表示没有开放给用户的 API。二者适合人工对照，不进入自动化覆盖分子。来源：https://about.seekingalpha.com/terms ; https://www.koyfin.com/help/faq/can-i-get-the-data-via-api/
- SEC 官方允许有界程序访问并要求公平访问（目前公开指引上限 10 requests/second）；已有 8-K 实例在 EX-99.1/99.2 附件提供完整电话会议文字，但这不是所有公司的普遍做法。来源：https://www.sec.gov/about/developer-resources ; https://www.sec.gov/Archives/edgar/data/108516/000156459020058036/0001564590-20-058036-index.htm
- NVIDIA IR 挂出的 Q2 2027 transcript PDF 自带 FactSet CallStreet 版权标识；“发行人 IR 链接”不能自动推出批量留存、TXT 派生和 export 的权利。来源：https://investor.nvidia.com/files/content_files/TRANSCRIPT_-NVIDIA-Corp-NVDA-US-Q2-2027-Earnings-Call-26-August-2026-5_00-PM-ET.pdf
- G1e 需保存原始 HTML/PDF/TXT 的原件 SHA，并把派生英文 TXT 的转换版本、parent SHA/locator 关联回原件。当前隔离 CWP writer/importer spike 只证明 TXT 进入 catalog 和精确复用，不证明原始网页已不可变留存、来源权利、filing-fetch 编排或生产 G1e 通过。许可证/站点条款需逐 provider、逐动作审查，缺项默认拒绝。


### SEC EX-99 小样本（3 个 2026 附件 + 版权反例）

- TTM Technologies 2026-08-06 的 8-K/A 补交完整电话会 EX-99.2，HTML 直接包含发言人、管理层业务进展及 Q&A，可做“原始 HTML → 带 locator 英文 TXT”的解析样本：https://www.sec.gov/Archives/edgar/data/1116942/000119312526337923/d142017dex992.htm
- FitLife Brands 2026-04-07 8-K 的 EX-99.1 与 Global Indemnity 2026-03-12 8-K 的 EX-99.1 也包含电话会议文字；三份样本的网页文本没有检出 `Copyright` 或 `FactSet` 字样，但这只是有限表面检查，不是版权/留存许可的法律结论。来源：https://www.sec.gov/Archives/edgar/data/1374328/000143774926011607/ex_942831.htm ; https://www.sec.gov/Archives/edgar/data/1494904/000119312526103797/d126781dex991.htm
- 反例：SEC 内也有附带 FactSet CallStreet 版权字样的电话会议附件，故 `sec.gov` 域名和 8-K EX-99 类型不能直接替代逐附件权利审查：https://www.sec.gov/Archives/edgar/data/48039/000119312521235407/d211506ddefa14a.htm
- 这个便利样本只证明存在可发现的 HTML 全文，不代表在用户跟踪的公司或最近 30 日具有足够覆盖，也未下载到本地或测试爬虫。G1e 的 20 家核实证券覆盖/增量计数仍待做。


## G1e 现有可复用代码合同（2026-09-27 再核）

- `source_catalog.authorization.DownloadAuthorization` 已精确绑定 GapPlan hash、RuntimePolicySnapshot hash、provider/accession、件数/字节上限与 expiry；`validate_download_authorization` 返回拒绝理由。provider 内容权利要与它取交集，不另造相同的下载许可。`RuntimePolicySnapshot` 的作用是激活/根政策，不是内容许可证。
- `SourceManifest` 的 source ID 由原件 SHA 决定；`artifacts` 行已有 `source_id`、`source_sha256`（升级列）、`generator_name/version`、`content_sha256`、`metadata_json`。TXT 派生应绑定原件 source ID/hash，并把文本 locator 映射做成受校验的版本合同。当前架构没有现成受校验的 HTML→TXT parent/locator 字段，不能靠任意 metadata_json 字符串假装完成。
- 隔离分支 `provider_use_policy.py` 用受 hash 保护的只读规则、逐动作/时间/host/path/内容类别检查；无政策、站点禁止名单、缺动作/过期/撤销/歧义、导出范围不符均拒绝。`authorize_transcript_fetch` 复用现有精确授权，还要求候选 payload 中 market/security_id 与请求一致。没有正式政策文件，也未接 filing-fetch 或 earnings-transcripts 网络调用；只验证 prefetch 决策。


- 现有 `normalizer._html_text_markdown` 用 BeautifulSoup+markdownify 生成整篇 Markdown，只创建一个 `paragraph_index=0` 的 ParserResult/locator；这无法为电话会议每个 speaker turn 和问答建立足够细的原件定位。新路径应只对通过权限闸门的电话会议 HTML 运行专用轻量抽取，保留原始 HTML bytes，TXT 行/说话人单元逐条映射到原件 byte/DOM locator；不能借旧 `normalize_catalog` 全量产物来绕过低空间目标。

## earnings-transcripts 与商业阅读平台并排核查（2026-09-27）

- 只读盘点现有 `transcripts/`：6 家公司 43 份英文 TXT，43 份对应双语 JSON、43 份夹排 TXT，所有英文头部 `Source: motley_fool`。英文 2,441,306 B，双语 6,770,745 B，夹排 6,731,684 B，summary 9,996 B，总 15,953,731 B。配置为 7 个 ticker，其中 GENB 暂无本地英文文件。这是现存库存，不是来源实时覆盖率；体积约 15.2 MiB，不能解释 company-wiki 旧库的 46 GiB。
- 已提交的 `scraper.py` 是“最近 N 季”批量 CLI，有增量跳过、自动翻译、Web 阅读器和单实例锁；原件 HTML 未保留，`--output` 不隔离日志/锁/cache。工作树里未提交的新 `transcript_api.py`/`transcript_tool.py` 才支持确切 FY/Q、as-of、无翻译正文、双 SHA 与 JSON subprocess；但不返回原始 HTML/FMP JSON 字节，无法证明 TXT 行到原件 byte 的 locator，FMP `call_date` 不是可核实的 publication date，尚未接 filing-fetch 或权限闸门。新接口测试是 fake response 合同，当前 FMP key 的正文端点真实返回 402。
- Koyfin 官网 Plus 年付显示 $39/月并列 filings、新闻稿、transcripts，但官方 FAQ 不开放用户 API。Seeking Alpha Premium $299/年并列无限 transcript 阅读，个人条款限制机器人下载/索引/抓取。二者相对现有工具可能改善人工阅读覆盖与搜索体验，**实际独有覆盖、时效和价值尚未测试**；都不能直接填补 company-wiki 自动原件/locator 合同。比较方法和购买门槛见[对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)。
- 隔离 `transcript_material.py` 可从合规原始 HTML/TXT 产生无翻译英文行、原件字节范围及双方 SHA；`load_transcript_material` 重算确定性转换验证持久化 lineage，当前没有 catalog artifact 持久化。首次把重算误放在生成函数内，4 项出现递归；移到加载边界后合并 27 项通过，且 `ruff`/`git diff --check` 通过。此收据只涉及 fake 原件与临时 catalog，不是 provider 下载、原件来源许可或跨仓 E2E。

## 派生 transcript artifact 与 revenue-forecast 同步复核（2026-09-27）

- 再读 revenue-forecast 最新实际资料：progress Round 120、register §162、owner decisions §39；I-16-B 的部署结果已 `accepted_scoped` 落定，Worker 保持 `paused`。register 将 I-17-A 列为在飞且带真实观察 attempt；其来源卡模板仍为 `planned`，所以应按 register/attempt 观察，不能声称观察窗口已完成。I-17-B 为后继卡。I-05-C/I-06-A 的开放项仍足以阻止 G0。本轮没有写 RF。
- 新加 `transcript_text` 不能只 insert 到现有 `artifacts` 表：`SourceBundle` 依据 `ROLE_DEPENDENCIES` 形成 `KNOWN_ARTIFACT_ROLES`，未知 role 会产出 `artifact_role_unknown`；`artifact_read_model.read_artifact(s)` 同样 fail closed。对应全链还包括 `GENERATOR_REGISTRY`、`scripts/resolve_bundle.py` 的 `_ARTIFACT_ROLES`、producer event 触发器分类及 role producer contract 测试。新增 role 属共享读/导出合同变更；G0 前不动生产 bundle/schema。
- 为守低空间目标，逐行原文 locator 不应再全量复制到 artifact `metadata_json`：immutable raw 保留 source ID/hash；TXT 只保留一份和短 metadata；同版本 extractor 可确定性重算候选 byte locator；只有入选 evidence/package 保存最终 locator。读取时验证 raw SHA、TXT SHA 和 extractor/version，不匹配则重新提取或拒绝。该方案已补入 [G1e 来源合同](transcript_provider_rights_contract_v1.md) 与总计划。

## filing-fetch × earnings-transcripts 当前互操作缺口（2026-09-27）

- 只读检查 E-T 新工具源码、CLI、README 和本地 task_plan：工具为 `transcript_tool.py` stdin JSON 子进程（schema `earnings-transcript-request/1` / result `/1`），不是 MCP；精确 FY/Q、as-of、未翻译文本、payload/text hashes、双重授权位和无持久文件副作用都已有。它仅实现 Motley Fool/FMP。
- 成功响应没有原始 provider payload（HTML/JSON）bytes，也没有 final/effective URL；MF fetch 内部拿到 effective URL 后只返回规范候选 URL。filing-fetch 不能凭 hash 重新构造这些 bytes，也不能让 company-wiki 重新校验原件或建原文 locator。因此跨仓不能直接把 `content_utf8` 写为 canonical source 而声称来源原件完整。已形成[跨仓集成合同草案](filing_fetch_transcript_integration_v1.md)，要求 E-T 可选择返回有界原件字节/MIME/final URL，CWP 重新解析和哈希。
- 检查 filing-fetch 当前代码：`FILING_REQUEST_SCHEMA_VERSION=1.2`，`SKILL.md` 用户文档还标 1.1；strict request whitelist 没有 companion key。filing 流程返回一个 handle，下载失败与 companion 部分失败尚无独立 response contract；`--allow-download` 授权 filing 的下载，不能自动授权电话会。
- 用户要求“下载公司文档时也同步获取电话会”须表达为可选 companion exact FY/Q；季度报告和电话会 period 不能通过名字猜；先 resolve/reuse 已存在 transcript，再查权利和授权，再 provider fetch、post-fetch check、CWP canonical import。电话会失败必须保留 filing success。外网 fetch 不得持有 company-wiki catalog lock；Worker 只在短 canonical import transaction 使用既有协调，尊重用户 pause。
- 当前 real-provider gate 仍关闭：Motley Fool 自动访问受限，Seeking Alpha 无适用 adapter 且个人订阅不授权抓取；FMP 实测 HTTP 402 且 publication date/rights 未解决。后续 G1e 完成前仅可 fake provider 测试；本地 E-T task_plan 也将此阶段拆为 repo-specific、要求同步 revenue-forecast snapshot，不得借此改 RF。
- 2026-09-27 隔离实现把 lineage schema 升为 v2，去掉全量 per-line locator 数组，仅保留 `line_count` 与原件/派生物 hashes、sizes、MIME、extractor version。`load_transcript_material` 必须收到从 canonical receipt 获得的 `expected_mime_type`，并以原件重新抽取、逐字段比对紧凑 lineage 和派生 TXT bytes；持久化 locator 或伪造 MIME 会被拒绝。此处只证明 helper 的可重放性与小范围合同，不量化整个 company-wiki 的节省，也没有把 helper 接入生产 artifacts。
- 下载后安全门禁缺口已实测并补为隔离 `validate_transcript_fetch_result`：下载前通过仍不够；必须用新加载且 hash 与预取 pin 一致的 policy，再核对 final URL 的 automated_fetch/retain_original/derive_text 三个动作、request/candidate/receipt 身份、2xx、`text/html|text/plain`、授权 byte cap、时间、staging containment、文件类型、实际 byte size 与 SHA。拒绝时此 helper 不导入数据。`DownloadReceipt` 当前没有 effective redirect URL 持久字段，因此真实 E2E 先用无重定向 fixture；上线前需记录 effective URL sidecar，或要求 adapter 拒绝 redirect。该处理尚未在 `AcquisitionCoordinator` 或 production writer 接线。

## 2026-09-27 — 免费平台层是否值得成为 provider

- Koyfin 官方 pricing 当前把 Free 定义为有限 news/company snapshot、2 年 financials/1 年 estimates；filings/press releases/transcripts 列在 Plus。Free 对“业务叙述 + 电话会原件”没有可证的新增自动覆盖，故不做 connector。Koyfin 条款还限制再处理 Information；只可作为用户自己看的候选发现界面。
- Seeking Alpha 官方称有免费 earnings-call transcripts、每季覆盖约 4,500 calls；这是可选人工发现线索。其当前条款同时许可个人非商业阅读/下载，并明文禁止 robot、search/retrieval application/process 自动下载、检索、索引、data mine、scrape 或 harvest，因此不由 company-wiki/filing-fetch/Worker 获取或保存正文。只保留人工查阅链接，优先追到 issuer IR/SEC 原件。
- 决策：不为了 provider 数量而接入。company-wiki 只允许把人工外链作为来源发现线索，不复制站点正文、评级或作者观点；机器接入只选权利明确且能保存原件/重放 locator 的发行人/SEC 逐件许可来源。详细依据见 [Koyfin / Seeking Alpha 免费层对照](earnings_transcripts_vs_platforms_2026-09-27.md)。

## 2026-09-27 — G1e-C importer 实施复核

- 对 `CanonicalSourceWriter.import_staged` 的调用面使用 CodeGraph 检查后，采取可选 namespaced provenance extension；旧调用不传参数时 sidecar 字节结构不变。transcript importer 将 `DownloadAuthorization.receipt_hash`、provider-use policy hash、effective URL、raw SHA、adapter/extractor 版本和通过的动作保存在 `provenance_extensions.transcript_acquisition`，扩展不超过 16 KiB；不保存正文副本或逐行 locator。
- 预检复核发现 `authorize_transcript_fetch` 组合了 provider/accession/plan/runtime policy，但此前没有显式比较 `DownloadAuthorization.request_id` 与当前 `SourceRequest.request_id`。已改为不匹配即拒绝，并将 request/candidate ID 放入 admission 供 importer 绑定；合同测试覆盖另一请求的授权被拒绝。
- E-T discovery/fetch result 的 `exchange` 是请求参数回显，不是独立验证过的交易所。caller 必须从明确 security identity 映射出 `nasdaq` 或 `nyse`，禁止 `auto` 进入候选授权；CWP importer 对未知 venue fail closed，并以不区分大小写方式绑定 E-T 小写输出与 CWP identity。
- CWP library core 只在 synthetic provider fixture 下成功；`fixtures.invalid` fake E2E 覆盖坏 SHA、错 request/document、外部 effective URL、错 venue/period、重复 JSON key、未授权 admission 和成功 raw+sidecar import。相关 **56 项**核心/writer/acquisition/sidecar 合同通过，不证明真实 provider 权利、stdin CLI、filing-fetch 编排或 Worker 运行。

## 2026-09-27 — 数据湖边界与目录泄漏再调查（只读）

- 用户提出的“目录是底层细节”在**业务身份与消费者读取**层成立；生产 CWP 已有 `sources/documents/locations`、多 root 配置和同 SHA 候选回退。`canonical_writer` 固定 company_raw 写目标与外部只读根属于写入所有权，不应为追求表面平权而取消。Dropbox 占位、来源权利/公开时间和外发许可仍须按具体来源/动作处理。
- 2026-09-07 旧诊断有两处时效变化：resolver 已逐份验证同 SHA 副本并回退，且调用统一 reusable policy。仍存在 scanner 旧版按 root kind 选择文档默认类型/元数据容器与按 priority 合并、normalizer 自行选路径、`SourceHandle.canonical_path` 外泄。filing-fetch 与 RF 又直接读绝对路径；RF 导入 CWP 内部 DAG，CWP DAG 反含 `consumer_analysis`。这是跨仓职责耦合，不能以“所有文件搬到 company 目录”解决。
- `resolver.read_verified_bytes` 是进程内原语，尚无等价跨进程读取合同。正式 reader 需要 ID/版本定位、受控字节交付或短期物化、同版本校验、云占位/撤回/权限状态与清理；pilot 的调用方 raw-path map 是隔离试验的临时接缝。确切代码证据、责任表、R4 复用和大节点测试见[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)。本轮未证明 scanner 的 root priority 在真实同 SHA 样本上已造成输出差异，列为隔离验证问题。

## 2026-09-27 — RF/CWP 集成分支合同与回归

- `fcap` 原工作树含 9 个相对 `origin/master` 的提交；本轮把已审阅的 reader 和 transcript-companion 两条 CWP 功能分支并入本地集成分支，未推送。transcript writer 冲突以保留 immutable provenance、重复导入不重写现有来源 sidecar 为准，同时纳入首写 transcript acquisition 扩展。
- 集成合同修复了 normalized reader 的复杂度、canonical stage/reason 注册、SourceVersionReader 的 metadata handoff 计数，以及 `SourceOperationV2Input.acquisition_result` 命名；FC905 测试夹具恢复真实 SHA、规则哈希和签名 disposition，没有放宽生产验收。Windows narrative E2E 子进程输出使用 replacement 解码，避免 GBK 环境误报。
- 当前复杂度 ratchet 对新文件仍为 10；几个已并入的遗留复杂模块采用明确的非增长基线，作为 G0 前分解技术债，而不是视为已满足生产复杂度门。Worker/G0 仍关闭。
- 受影响回归为 **36 个测试模块、390 项通过**。全仓 3,108 项运行曾在约 40% 时因串行耗时被停止，因此不记为全仓通过；390 项是本次可声明的回归范围。

## 2026-09-27 — 集成失败审计的证据边界

- `.pytest_cache/v/cache/lastfailed` 当前保存 30 个历史 node ID，明显多于计划所述“8 个直接失败”；其中多项测试名在当前文件已不存在或已改名。该缓存是跨运行残留，不能证明当前仍有 30 个失败。
- 首次尝试把缓存 JSON 的 30 个属性名直接展开给 pytest，结果只有 7 项被收集，22 个 node ID 报 `not found`，同时 Windows 输出中的中文工作目录发生编码失真；pytest exit 4，未运行任何断言。独立 basetemp 已在 finally 中清理。后续不再复用这种重跑方式，改从当前测试收集和 Git 差异建立清单。
- 修复提交的差异已经显示至少四类性质不同的问题：observability/read-chain/source-operation 属生产合同整合；FC905 属安全夹具不再满足已加强的真实签名/哈希合同；narrative subprocess 属 Windows 解码测试环境；复杂度 ratchet 属架构债门禁，不能因登记非增长基线就称为已解决。
- 用 Git detached worktree 在修复前 `251805c` 重跑 6 个相关合同文件，得到 **6 failed / 53 passed**：FC-1301 未注册 38 个新 reason（1）、B10 新增两个 raw-column handoff 未登记（1）、FC905 旧夹具缺 mandatory source/policy/evidence binding（3）、FC-1204 新文件复杂度首先报 `narrative_evidence.py=363>10`（1）。`source_operation_v2` 和旧 stage taxonomy 在该提交均通过；计划中的“8”是后续修复时又引入/触发的合同失配累计数，不是一个时点的 8 个独立生产故障。
- `SourceEnsureResult.to_dict()` 与 `_read_only_ensure_result()` 的正式 schema 都输出键 `acquisition`；`source_operation._result_and_resolution()` 却在 `2ecb6f8` 改为只读 `acquisition_result`，而仓库除该实现和同步修改的单测外没有任何 producer 输出新键。内存复现用正式字段得到 `status=gap`，但 `gap_plan=null`、`request_id=null`。这是当前真实生产合同缺陷，测试与实现一起偏离 producer，现有绿灯是假阴性；R4 consumer 接线必须暂停到修复并加入真实 producer/CLI gap E2E。
- B10 failure 不表示 reader 自行解析 metadata：两处新调用和 scanner 新计数最终都进入共享 `store.metadata_state`，登记 handoff 是审计基线更新，不是数据行为修复。FC905 三项是测试夹具过期，生产 writer 的 mandatory SHA/payload/policy/signature fail-closed 逻辑正确；更新夹具不应放宽生产代码。
- 复杂度门禁揭示的风险仍未解决。Ruff C901 在新增模块中发现 13 个 >10 的函数；最严重为 `select_narrative_evidence=181`（仓库自定义 ratchet 为 363），其次 transcript/provider 权限路径达 22/20/18，`project_operation_result=12`。把文件加入 `FROZEN_MAX` 只阻止继续增长，实际绕过了“新文件 <=10”门。narrative 目前仅 pilot/retrieval 路径，transcript/provider 尚未接真实 provider/Worker，故不是已发生生产数据破坏；但 G0/G1e/G2 放行前必须有不可绕过的分解门。
- 修复前快照的 `git archive | tar` 方案因 Windows `tar.exe` 无法提取仓库中文路径而失败，测试未启动、临时目录已清理；改用 Git detached worktree 后成功复现并由 `git worktree remove --force` 清理。历史 pytest cache 及 tar 输出均不能作为产品失败证据。
- 当前相关范围重跑 **88 passed**，包括 reason taxonomy、read-chain、source operation 单测、真实 CLI exact-reuse、FC905、复杂度 ratchet、stage taxonomy 和 normalized reader。它与正式 producer gap 反例同时成立，证明问题是覆盖盲区：当前 E2E 只走 exact reuse，没有走 latest-as-of/gap；source-operation 单测手写了仓库中不存在的 `acquisition_result` producer。
- 影响半径：旧 legacy ensure 输出、exact reuse 的 v2 投影、close-gap 完成路径和底层 catalog bytes 不受这次字段断链影响；受影响的是 opt-in `ensure --source-ref-v2` 的 gap/latest-as-of 结果，会输出 `status=gap` 却丢请求和 gap plan。它尚未造成数据删除或错误写入，但正好位于 R4 跨仓抽象接口上，因此对当前优先级属于阻断级缺陷。
- narrative E2E 的 UTF-8/replacement 改动只作用于 subprocess stdout/stderr 捕获；测试的业务断言读取生成 JSON/文件，不用 replacement 后的输出作事实，因此归类为 Windows harness 修复。normalized reader 是保持行为的函数拆分，原测试未随实现改写，归类为有效复杂度修复。
- 第一性原理分类：FC-1301 是生产 registry 漏接且已正确修；B10 是正确共享 parser 上的新调用登记；FC905 三项是旧夹具；stage semantic 是 registry 扩展后的合理测试更新；source-operation 是测试与 consumer 一起偏离正式 producer，当前未修；FC-1204 是正确发现架构债，但加入高上限属于临时 waiver；narrative decode 是平台测试问题。

## 2026-09-27 — 大重构的第一性原理边界

- 真正不可替代的资产不是 SQLite、切片或摘要，而是原始来源字节、来源捕获事实和版本身份。只要 canonical raw、SHA、manifest、URL/时间/版本关系完整，绝大多数派生层都可重算；因此后续架构应围绕“原件不可丢、派生可删除重建”设计，而不是继续保护 46 GiB 旧中间结构。
- `reader` 是来源版本的只读交付端口：按 `document_id + source_id + content_sha256` 选择已登记的同 SHA 可读副本并验证实际字节。它不是 PDF parser、摘要器或 downloader；消费者依赖它的 ID/hash/bytes 合同后，company/dayu/Dropbox 的目录差异才能真正降为存储细节。
- 大重构不能只把 `acquisition_result` 改回 `acquisition`。当前 `source_operation.py` 同时承担 wrapper 猜测、schema 解码、状态机、reader I/O、路径过滤和 DTO 组装，并用 `_acquisition` 隐藏键跨 helper 传状态；这正是 producer/test 能一起漂移的结构原因。目标必须拆成 typed operation contract、纯 projection、reader port 和薄 facade。
- 正例测试若手写复制 JSON schema，会让测试和错误实现同时变绿。正式合同测试必须从 `SourceEnsureResult`、`CloseGapResult` 或真实 CLI 产生输入；手写 payload 只适合未知 schema、缺字段、request ID 冲突、路径泄露等负例。
- “每层对本层负责”可落成七个单向层：raw、catalog、read、acquire、derive、evidence、export/jobs。Worker 只调 application ports；consumer 不导入 store/resolver/DAG；selector 不打开任意路径；read broker 不下载或生成摘要。
- 当前几个新模块被加入高额 `FROZEN_MAX` 只说明不会继续恶化，不说明架构达标。按生产启用顺序，operation/read、provider/transcript、narrative selector 和 Worker 必须在对应 M1–M3 前拆分并下调/移除豁免。
- 为避免审查拖慢，后续只在 M1 读取/acquisition、M2 派生/evidence/provider、M3 Worker、M4 跨仓/清理做集中验收；小步骤只保留 TDD 红/绿、Ruff 和 diff check。

## 2026-09-27 — M1 实施后的架构结论

- 正式 producer→serializer→operation adapter→reader 的真实链路证明，原缺陷位于 transport contract，而不在 catalog/raw。拆开 parser 与 projection 后，producer 字段漂移、request ID 冲突和状态矛盾在读取字节前即可失败关闭。
- read-only ensure 过去手写第二套 JSON 是相同概念的第二事实来源；改为构造正式 `AcquisitionResult` / `SourceEnsureResult` 后，latest-as-of gap 与普通 ensure 使用同一 schema owner。
- provider unavailable 的稳定事实是布尔状态；底层 exception 字符串可能包含命令、路径和进程细节。公开 pathless DTO 不携带 `provider_reason`，详细诊断留在 producer/journal 边界。
- 测试目录“恢复原样”应比较持久内容与成员关系。SQLite `-shm` 的 mtime 会因只读连接活动变化，mtime 不是业务状态；文件内容 SHA、大小、路径集合和 raw SHA 才是本节点应验证的不变量。
- M1 的 115 项门覆盖同 SHA 跨 root 回退、错误 SHA 拒绝、版本/导出合同和两个 fake-provider gap 分支。该结果只验收 L1–L3 与 operation/read adapter，不外推到叙述选择、电话会议、Worker、跨仓消费者或 46 GiB 清理。

## 2026-09-28 — M2-derive 实施后的架构与空间结论

- locator 是稳定回放标识，不能兼任业务排序键。`loc:v1/page:161/...` 的字典序早于 `loc:v1/page:3/...`，会改变重复披露的保留位置。预算策略必须显式接收数值 `order_key`；测试同时覆盖两位数页码反例和 P06 真实文档。
- 真实 E2E 表明 P06 的“预计需要 4-9 个月”在物理第 3 页和第 161 页重复出现。选择任一处都能回放事实，但既定样本要求首个关键上下文位置；修复后保留第 3 页。该失败属于重构引入的排序语义漂移，不是放宽测试即可解决的夹具问题。
- 视觉分组只在内存中帮助识别跨块句子；持久证据仍是一组各自可回放的 span，并由 `selection_group_id` 保持原子性。PDF table/text 双视图去重优先保留表定位；回放计划绑定原件 SHA、source ID、单一 parser version 和必要 table pages。
- 12 件真实资料的 52,196,853 bytes 原件只产生 549,768 bytes selected bundle，实测比率 1.0533%。大型 PDF 的逐件比率约为 0.59%–2.02%，季报因原件很短为 4.77%，两份 TXT 电话会因原件本身较小为 16.83%/23.73%；这说明应按文档类型分别设上限，不能用一个百分比误判短文本。
- P09 投资者关系管理办法和 P10 业绩说明会通知完整扫描后分别只保存 326/331 bytes 跳过收据，验证“低价值格式文档判断后不切片”可显著降低长期派生空间。原件仍保留，未来策略变化可重算。
- 当前 Phase C 证明的是确定性 parse→select→summary-input→retrieval/replay 链。它没有证明真实 provider 权利、电话会 fetch/import、LLM 摘要语义质量、Worker 并发、跨仓 consumer 或 46 GiB 生产派生清理；这些仍按 Phase D–G 大节点验收。

## 2026-09-28 — M2-provider 实施前缺口结论

- 当前 transcript 测试形成了三段互不完整的证据：CLI preflight 是跨进程但不调用 provider；stdin importer 跨进程但 `/2` payload 由测试手写；fake provider 能验证 postfetch/replay，但在同进程内直接调用 writer 并直接读 canonical path。三者全绿仍不能证明 provider subprocess、importer 与 verified reader 可互操作。
- provider policy 本身和 transcript use admission 是不同变化原因。前者只拥有 rule/hash/URL/action decision；后者拥有 request/candidate/security/download authorization。把两者放在一个模块造成 38 的复杂度和反向依赖，拆分后应保留稳定 reason code，而不是重写政策语义。
- `/2` JSON 是不可信 transport；解码和 identity 校验应在纯 contract 层结束，返回 bounded bytes typed value。临时路径、writer 和 catalog 不能进入 transport parser，否则测试无法分别证明“错误输入零写入”和“合法输入唯一提交”。
- postfetch validator 与 canonical writer 也必须分开：validator 验证 fresh policy、effective URL、receipt、staging containment、真实 size/SHA；application service 才拥有唯一临时文件和 `finally` 清理。这样 timeout、坏 JSON、redirect 和政策变化才能逐层断言零残留。
- transcript selector 是通用 narrative selector 的消费者，不能把 provider 权利逻辑塞回 Phase C 模块。应用层在调用 selector/summarizer 前分别检查 `select_evidence`/`generate_summary`；动作不传递。该门是来源使用权，不是此前已取消的 private/public 分类或个人项目文件权限。
- Phase D 的完整链必须通过 `SourceVersionReader.open_version()` 或 reader CLI 读回原件；直接使用 importer 返回的 canonical path 会重新把存储目录暴露给上层，也无法验证迁移/同 SHA 副本回退后的抽象有效性。

## 2026-09-28 — M2-provider 完成后的合同与恢复结论

- provider policy、request/candidate admission、transport schema、postfetch byte validation、canonical commit、material replay 和 CLI 是七个不同变化原因。拆开后每层可以独立证明“错误输入在本层停止”，四个旧巨函数 freeze 才能真正删除，而不是把复杂度搬到新文件。
- `canonical_content_sha256/content_bytes` 必须有明确的 byte semantics。只校验 64 位 hex 和正整数会让 producer 同时篡改正文声明而通过；CWP 现在以 raw 独立重建 material 再比较。但这也暴露 E-T `/2` 的语义漂移：E-T 对 HTML 排除 `<h1>` 并用段落间双换行，CWP deterministic material 保留标题并按行规范化。当前 producer fixture 的两组 hash/size 不同，因此 Phase F 应升级 schema，显式区分 `provider_extracted_text_*` 与 `cwp_material_*`，或传输可独立核验的 provider 派生 bytes；不能复用同名字段表达两种文本。
- fake provider 必须与 CWP 无代码依赖，否则 producer 和 consumer 可能共享同一错误实现。测试 fixture 自己生成原件和合同 JSON，CWP 只通过 subprocess stdout 收到不可信对象；成功后也必须从 catalog identity 经 `SourceVersionReader` 取回 bytes，而不是读 importer 返回路径。
- runtime snapshot 的 `policy_hash` 是 catalog policy pin，测试不可填任意 SHA。reader 同时按 snapshot 控制 v1/v2 metadata 可见性；把所有 flag 设 false 会关闭 legacy bridge，使刚导入 sidecar 的 fiscal period 不可见。E2E 夹具最终显式启用现行 bridge，从而保留严格 FY/Q 校验。
- 多文档并发不能复用本阶段 test harness 的 subprocess 串联作为生产 orchestrator。provider 的 timeout/stdout cap/kill/wait 只证明边界故障可被回收；正式 job claim、lease、幂等 commit、outbox/reconcile 和 pause 线性化仍属于 Phase E automation 层。
- synthetic transcript 很短，固定 sidecar 与 SQLite page allocation 会使派生/原件比率看起来大于 1000%；空间预算应分别报告 raw、sidecar、catalog allocation、selected bundle，并以真实长文档批次估算总体容量。不要用短 TXT 百分比否定“选择性证据代替全量切片”的 12 件真实样本结果。

## 2026-09-28 — M3 Worker 实施前第一性原理结论

- 当前 Automation Worker 的核心风险不是“线程数不够”，而是领取、attempt、job 状态、Effect 和 Outbox 没有形成一个事务状态机。在此基础上直接加线程/进程会扩大半领取、旧 token 覆盖和重复副作用，因此必须先实现原子 Store application operations。
- `put_attempt` 是 insert-only 幂等 API，不能承担 finish/update。现有 Worker 构造完成后的 Attempt 再 `put_attempt`，冲突后吞异常，导致 job 可以显示 succeeded 而 attempt 仍未完成。这证明只断言 job status 的旧测试不足以验收恢复能力。
- Outbox 外键指向 Effect，但现有 success path 未持久化 Effect 就写 Outbox。真正的完成协议应当把 attempt 完成、Effect、Outbox 和 job→VERIFYING 放在同一 AUTO transaction；catalog 可见后再由 projector fencing ACK 并把 job 置 SUCCEEDED。
- pause 要阻止的不只是新 claim，还包括旧执行者的 heartbeat、finish 和 publish。JSON 状态单独检查不能与数据库提交线性化；AUTO v2 需要持久 generation，attempt 记录领取代际，projector 与 pause 还要共享短时 catalog operation lock。
- 旧 SourceCatalogWorker 把解析、LLM、导出和 destructive prune 放在一个高复杂 cycle 中，不适合继续演化为并发内核。最小风险路线是保持其 paused，关闭自动 apply prune，以新的 AutomationStore/worker processes 驱动 narrow narrative jobs。
- 多文档并发使用进程，模型并发固定为 1；唯一接触持久执行状态的辅助线程是每个执行进程的 Store heartbeat，它不触碰 LLMClient。E3 的真实父进程强杀试验证明还需要一个无状态 parent watchdog；它只检查父进程存活，不访问 Store、handler、catalog 或 LLM。这既满足 Windows/非线程安全 client 约束，也让不同文档的 parser/模型等待可以流水线重叠。
- 叙述流水线无需五个以上持久 job。Phase C 的结构扫描和选择已经按小模块拆开，可在一个 select job 内编排；summarize 和 verify 分开以隔离 LLM 重试；publication 由 outbox projector 承担。三 job DAG 降低状态数，同时保留同文档顺序与跨文档并发。
- 旧 `artifacts` 会按 `(document, role, generator, version)` 更新同一行，无法保存同一 document 的多个 source/policy 版本。只为 narrative bundle 建窄的 immutable version registry 比重建 generic artifact 系统更小，也比复用 legacy upsert 更可审计；旧 artifacts 暂作兼容 projection，不复制最终 bundle。
- Phase E 的长期派生只需一个 compact content-addressed bundle。selected evidence 和 summary candidate 在 attempt JSON 中设硬上限；skip 只存小型 coverage receipt；不生成整份 Markdown、全量 spans、逐页缓存或磁盘 BM25。这样并发不会重现 46 GiB 的“每阶段复制一份全文”。
- 本轮 150 项基线的五个失败属于陈旧测试 helper：生产 writer 新增 mandatory evidence payload 绑定后，helper 仍只传 hash。正确修复是让 helper 生成真实合法 receipt，同时保留缺 payload 拒绝测试；放松生产合同会把测试问题变成产品缺陷。

## 2026-09-28 — E1 原子队列实施后的恢复性结论

- `put_*` 幂等 CRUD 和 Worker application transaction 是两类接口。前者适合登记不可变 event/job/approval，不能由调用者拼成 claim 或 finish；claim/finish/reap/outbox ACK 必须由 Store 持有完整事务，否则任何中间异常都会留下无法推断的半状态。
- pause 的可靠边界必须持久化在与 attempt 相同的数据库中。`runtime_gate.control_generation` 在每次状态改变时递增，attempt 绑定领取代际；heartbeat、finish、outbox ACK/retry 都同时核对当前 enabled、generation、token、最新 attempt 与未过期 lease。这样 pause 返回后，即使旧子进程稍后恢复，也不能提交旧结果。
- attempt 的 `result_json` 应保存有上限的完整 `HandlerResult`，包括 outcome、result、artifact/effect 引用、metrics 和 error。只保存 `result` 会丢失恢复/审计所需的错误分类和副作用意图；重新 insert 同 attempt 也不能替代完成更新。
- Effect 与 Outbox 不能分开持久化，也不能在第一项 effect 投递后就把多 effect job 置成功。finish 原子写全部 effect/outbox 并停在 VERIFYING；每个 ACK 独立验证 intended/actual hash，只有同 job 不再有未 delivered outbox 时才 SUCCEEDED。
- retry 的 `not_before` 是持久调度事实，不应由 Worker 在同一调用中 `RETRY_WAIT→READY`。reaper 只结束最新过期 attempt 并写 `LEASE_EXPIRED`；promotion 是可重复的独立 Store 操作，未到期返回空，到期只提升一次。
- schema migration 也需要 fencing 思维：保留 v1 的精确结构快照，先只读验证再升级；v0 新库按 v1/v2 顺序一次提交；索引和 singleton gate row 都属于 schema health。仅检查 `PRAGMA user_version` 会把缺索引或空 gate 的损坏库误判为健康。
- 双连接 race 比单实例 mock 更能证明 SQLite claim 的线性化。E1 的 job/outbox 两组真实连接竞争都只有一个胜者；duplicate attempt/effect 故障注入证明事务 rollback 后 job、attempt、effect、outbox 数量保持原值。
- 事务层已集中，但 `automation/store.py` 同时保留大量 v1 CRUD 和 v2 application operations，文件规模明显上升。E2 不应继续把 DAG/planner/controller 逻辑塞入 Store；scheduler/runtime control 使用独立模块，只保留必须与 SQLite 原子提交的窄方法，并在 E-A 复核是否需要按 persistence capability 拆文件而不拆事务。

## 2026-09-28 — E2 / E-A DAG 与双 Worker 互斥结论

- DAG 幂等不能复用普通 `put_job` 的“整行相等”定义：job status、not-before 和错误字段会随执行改变，而 event/job identity 与 policy/handler/risk/priority 等不可变内容不能漂移。E2 将二者分开，并在一个 transaction 内核对 event、全部 jobs 和完整 dependency set。
- “前置 job 显示 SUCCEEDED”不足以放行下游。恢复语义还要求存在 outcome=succeeded 且 `result_json` 非空的 attempt；否则进程可能在状态更新和结果持久化之间留下伪完成。terminal predecessor 也必须留下明确 blocked 原因，不能让下游永久停在无解释的 PLANNED。
- SQLite generation 只阻止旧 AUTO attempt 回写，不能单独阻止旧 legacy Worker 被另一个 CLI 稍后 resume。完整互斥需要 DB gate 与 legacy control marker 双向检查，并让 AUTO enable/pause、legacy resume/start/session 都经过同一个短时 `CatalogOperationLock`。
- 安全的 enable 写序是先设置 legacy interlock，再开启 DB gate；中途崩溃最多使两边都停。安全的 pause 写序是先关闭 DB gate并递增 generation，再持久 legacy pause/清除 marker，最后在锁外等待或强停进程。
- `AutomationStore` 应拥有 transaction，而不必拥有所有 SQL 细节。DAG capability 被拆到 `dag_persistence.py`，只接收现有 connection；这降低 Store 增长速度，同时没有把 BEGIN/COMMIT 或部分失败恢复交给 scheduler/controller。
- 旧 Worker 的自动 `apply=True` prune 与“原件不可丢、派生清理由 Phase G 审查”冲突，而且旧调用没有传必需的 timezone-aware `now`，异常长期被 cycle 捕获。E2 将其收口为确定性 dry-run；任何真实处置仍必须走 Phase G 逐路径清单与大节点门。

## 2026-09-28 — E3 多进程恢复与 Windows 进程治理结论

- 真并发应按资源属性分进程槽，而不是把线程数配置成一个整数。P2 的一个 compute + 一个 model 已用执行区间证明跨文档重叠；model slot 永远为 1，compute 在 claim 前同时校验“不持有 model client”和“不接收 `llm=True` job”。
- child 必须在 spawn 后通过 importable factory 自建 Store、registry、executor 和 model client。把已构造 client 或 callable queue 从 parent 传入会重新引入线程安全、pickle 和隐式共享状态问题；数据库 job/attempt/lease 才是恢复事实。
- 三个强杀窗口最终都归约为同一协议：旧 attempt 保持未完成，heartbeat 停止，lease 到期，reaper 以 `LEASE_EXPIRED` 完成旧 attempt 并使 job 可重试，新进程领取新 token。故障注入不需要写进业务 handler；Worker 的通用 lifecycle observation seam 足以在精确边界阻塞测试进程。
- Windows 上直接 terminate 一个同时有多线程等待同一 multiprocessing Event 的 child，可能让 Event semaphore 永久锁住，反过来卡住 Supervisor shutdown。watchdog 因此不能等待共享 stop Event；它使用本地 sleep 和 parent process handle，主循环独占 stop Event 等待。
- 有界日志不能在 worker restart 时清空，否则最需要的上一轮 crash 诊断会丢失。正确行为是每个 slot 固定 stdout/stderr 文件，写入时保留最后 N bytes，重建 writer 时裁剪并延续既有 tail。
- Supervisor 的正常退出清理和父进程异常死亡是两种故障。前者用 signal→bounded join→terminate/kill owned children；后者需 child 自检 parent。两者都不改变 DB job 状态，后续恢复仍由 lease/reaper 决定，避免把“进程消失”误当“任务失败已提交”。

## 2026-09-28 — E4 Narrative handler 实施前结论

- Handler 的安全输入必须是一次一致性读取的执行快照，而不是 Worker 临时拼出的 job ID 字典。event、job、attempt、gate generation、lease token 和直接 dependency results 若来自多次独立查询，pause/retry/并发更新可能产生从未同时存在过的混合上下文。
- verified reader 已解决“文件到底在哪个 root”的底层问题，handler 再接收 Path 会破坏这一抽象。PDF 应从 verified bytes 解析；既有 path facade 与新 bytes facade 共用同一内部 parser，不能复制一套选择规则。
- summary prompt 不应作为 selection result 的第二份正文长期保存。EvidenceSpan 已包含模型所需的最小引用文本，prompt 可临时构造；同理 transcript 的全量 material/line map 只在一次执行内存在，持久结果只保留已选证据对应的原始 byte bindings。
- provider 权利不是一次下载许可。对 transcript 而言，派生文本、选择证据和生成摘要是三个动作；每个 handler 必须按当前政策独立授权，verify 还要在产生 publish effect 前重验实际用过的动作，以覆盖“模型调用后政策撤销”的窗口。
- 取消 public/private 外发分类不等于删除 prompt-injection 内容完整性检查。现有 review receipt 与 source SHA/review policy 绑定且只接受两个已审核状态；E4 应在模型外发前和 effect 前复核它，同时把来源证据放在结构化 data envelope，不能拼进固定指令。
- `skipped_no_narrative` 是完整扫描后的业务结果，不是 parser failure 的替代状态。coverage 不完整、transcript 起始结构缺失或 locator 不可回放应进入具名 blocked/terminal 状态，防止重要文档被静默丢弃。
- 模型配置缺失与模型响应非法是不同故障：前者在网络前进入 `MODEL_NOT_CONFIGURED` 人工阻断，后者不应重复消耗同一模型预算。429/timeout 才使用有界 retry。
- verify job 必须直接依赖 select 和 summarize。这样最终 bundle 可从两个小型结果组合，summary 无需再次复制 selected evidence，也能用 Store snapshot 明确证明所有输入版本。
- E4 不需要 catalog writer。verify 只生成 canonical bundle/hash 和逻辑 effect；对象原子写、immutable version row 与 ACK 恢复留给 E5，避免 handler 与 publication 再次耦合。

## 2026-09-28 — E4.2 一致性执行上下文结论

- handler 输入的一致性必须由 Store transaction 保证，不能靠多个 getter 后验比较。SQLite read transaction 在并发 dependency result 更新时保持旧完整视图；下一次读取才看到新完整视图，因此不会把旧 event 与新 result 拼成不存在的执行状态。
- context 的不可变不仅是 frozen dataclass。嵌套 JSON 需要递归转为 tuple/read-only mapping，dependency results 也要按 job type 建只读映射；否则 handler 仍可在进程内改写审计输入。
- event natural key 是 source revision 的幂等事实。同一 source/policy/input 的下游 job 必须复用原 event；测试 helper 为每个 job 造 event 会掩盖 planner 错误，也会在真实数据库触发唯一键冲突。
- 数据库 schema 与领域模型是互补防线：枚举状态由 SQLite CHECK 拒绝，格式合法性由 typed model 拒绝。snapshot boundary 将后者统一映射成具名领域错误，使 Worker 不暴露 JSON/enum/时间戳解析细节。
- Worker 对 Store 的依赖可以收窄为 claim、heartbeat、finish、reap、runtime gate 和 read snapshot 六类 operation；handler 只依赖 `JobExecutionContext`。这为 E4.3 registry/DAG 和后续 handler 单测保留了可替换边界。

## 2026-09-28 — E4.3 job 拓扑与能力声明结论

- registry spec 是能力声明，不是 handler 实现。可以先冻结 job schema、错误分类和资源属性，但在 E4.5–E4.7 完成前不能把 narrative job 装入生产 executor；多进程恢复测试因此使用 test factory 私有 specs，避免“返回成功的空假 handler”掩盖产品缺失。
- summarize 即使在测试中使用 replay model，也必须声明真实生产所需的 LLM 与 network 两项能力。默认 policy 以及只允许 LLM 的 policy 都拒绝规划，防止未来把模型网络访问错误归类为无网络任务。
- verify 直接依赖 select 与 summarize会产生三条 edge，而不是线性链的两条。幂等测试必须同时断言 job 和 dependency 数量；只检查 job key 会漏掉拓扑漂移。
- 旧 source jobs 从默认 registry 和 event mapping 一次性移除比保留兼容别名更安全。generic Worker/recovery 测试应使用 generic/test job identity，避免测试夹具反向迫使产品保留已经废弃的全量 normalize 路线。

## 2026-09-28 — E4.4 reader/bytes 边界结论

- 路径独立不能只停在 `SourceRef`。handler 如果拿到 reader 内部解析出的 Path，存储迁移仍会穿透应用层；让 reader 返回已验证 bytes、PDF parser 接受 bytes，才形成可测试的完整抽象边界。
- `open_version` 与 `verify_version` 对 narrative purpose 应返回同一 review snapshot。只在 open 上附 review 会让 verify handler 为复核内容完整性重新访问 review store，产生第二个时间视图。
- PyMuPDF 的 path 与 stream 打开方式不同，但结构扫描、table-page 决策、unit 生成和 locator 回放必须共用一个 document parser。只新增 bytes wrapper 而复制解析循环，会使同一原件因存储形式不同产生不同证据。
- hash 校验要发生在 `fitz.open(stream=...)` 前。reader 已验证 bytes 并不能成为 parser 的隐式前提；独立 bytes facade 的绑定校验让单元测试、未来其他 read port 和崩溃恢复都能 fail closed。
- `source_reader.py` 原有查询/描述/verified-read 方法仍有既存复杂度债务，但本次新 purpose/review 规则已提取成窄集合与 helper，并把整个 reader 纳入 strict mypy CI/pre-commit。后续若改 reader 决策逻辑，应单列重构节点，避免在 handler slice 内顺手复制或继续堆条件。

## 2026-09-28 — E4.5 select handler 结论

- “reader 已核 SHA”不能成为 handler/parser 的隐式信任。执行快照之后到解析之前仍需把实际 bytes 与 event pin 再绑定；这样替换 reader port、故障注入和未来恢复路径都不能把自报 hash 当成内容事实。
- 完整低价值 skip 需要 coverage 证明。PDF 初次选择为空但还有 deferred table pages 时，handler 必须完成表页扫描后才能 skip；结构损坏、opaque page、transcript 起始标记缺失或 locator 不能回放都应阻断人工处理。
- transcript 的空间最小化单位是 selected binding。全量清洗文本和全量行映射只在单次 handler 内存中存在；持久结果保留选中 EvidenceSpan、对应原件 byte ranges、deterministic lineage hashes/versions 和本次动作授权证据即可。
- policy pin 既要防配置漂移，也要执行当前撤销/有效期/动作判断。`derive_text` 与 `select_evidence` 必须分别存在；下载许可或任一单独动作不能推导另一动作。
- strict 类型检查只有和运行时值域校验配对才安全。仅对任意字符串 `cast(Literal)` 会制造静态假绿；E4.5 将 claim type、modality、draft status 的显式 whitelist 放在 cast 前，并用三个非法输入合同测试固定该边界。

## 2026-09-28 — E4.6 summarize handler 结论

- 模型端口应传递 canonical request 和 opaque response bytes，而不是复用旧全局 `LLMClient`。前者让 adapter 身份、prompt version、输入 hash、响应 hash 和错误分类可独立测试，也避免全局限流/线程状态进入 handler。
- “不翻译”必须同时出现在 prompt constraint、结果合同和验证测试。只在调用参数上关闭翻译无法防止 adapter 或模型改变语言；summary result 与 draft 都必须等于 source language，且 `translate` 只能为 false。
- prompt review 是调用时能力门。select 时通过的 snapshot 只证明当时状态；summarize 在网络前重读当前 receipt 并要求完全一致，才能覆盖 review policy 或 evidence receipt 在排队期间变化。
- 模型的 transient retry 不应在 handler 内再包循环。一次 attempt 只发一次请求，timeout/429 返回 retryable；总次数由 durable job 的 `max_attempts` 约束，crash/lease 审计与 E3 恢复语义保持一致。
- 对 model JSON 的严格 transport 校验和对 summary claims 的领域校验是两层边界。非法编码、重复 key、超限和路径泄漏属于 response contract；未知 citation、说话者角色混淆、空 claim 和 unstable locator 状态属于 summary validity。两者都不重试，但错误码不同，便于人工定位。

## 2026-09-28 — E4.7 verify/effect 结论

- verify 不能信任“select 当时能回放”。队列等待、raw/root 迁移、policy/review 变化都可能发生在 model 之后；publish effect 前必须重新打开 pinned bytes、重算 SHA、重读 metadata/review，并全量回放 locator。
- transcript 的证据回放有两层：parser 生成的 speaker-block roundtrip 证明文本定位，selected byte binding 证明这些行仍对应同一原件 byte ranges。只做其中一层不能证明派生英文文本与 immutable original 的关系。
- effect 幂等身份应由 logical target、canonical bundle hash 和 projector version 决定，而不是 attempt ID 或临时文件名。同一 job 重试得到同一 effect key/ID，Store/outbox 才能安全去重。
- verify 只生成 intent，不执行 publication。把 object write/version row/ACK 放到 E5 projector 后，handler 的 locator/policy/review 失败永远保持零外部副作用，crash 恢复也只依赖 DB attempt/effect 状态。

## 2026-09-28 — E4.8 与跨仓 Git 状态核对

- 端到端夹具必须使用 source catalog 已支持的 `investor_call_transcript` kind，以及 `companies/{entity}/raw/investor_relations/transcripts/` 正式位置；`earnings_call_transcript` 是 rights-policy content class，不是 SourceCatalog `document_kind`。沿用通用 sidecar adapter 会把未知 kind 降为 `broker_research`，因此 E4 runtime E2E 使用 `company_raw_v1`，避免绕过产品路径。
- company-wiki 的本地 feature 支线都已是当前 `master` 祖先，但本地 master 的 32 个提交尚未推远端；StockWiki 两个本地分支同指一个 commit且干净，但没有 remote。描述为“本地并线已完成”，不能表述成“远端同步已完成”。
- RF `fcap` 仍不是已并入 main 的状态，其工作树 dirty 内容与 `.planning/.../execution_runs/` 证据需先按 PWF 交叉引用分类。目录名像临时运行数据不构成删除依据；继续复用“commit 为主、引用到的收据保留、只删可证明的一次性临时副本”的规则。
- source guard 是应用边界，不是底层存储 adapter。它消费 `SourceRevisionEventPayload` 与 verified reader 返回的 bytes/metadata/review，对 select 和 verify提供相同的 fail-closed identity 规则，仍不暴露 root、Path 或 catalog SQL。
