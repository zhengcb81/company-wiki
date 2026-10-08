# 外部数据源、月调用预算与采购闸门（2026-09-27）

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

本卡补充本计划的来源发现方案；不改变 G0–G4 状态，也不授权订阅、生产抓取或跨仓写入。对象是 company-wiki 的来源发现、原文和证据定位，以及 filing-fetch 的文档获取。清洗后的财务数字仍由下游专门金融数据接口处理；StockWiki 负责投资研究语义。

## 1. 采购结论

**现在不买 API 套餐或研究平台订阅。** 首先用 SEC EDGAR 免费公开接口、交易所/公司 IR 原始披露和现有市场下载器建立原始来源链；earnings-transcripts 的现有 Motley Fool 路径须暂停自动化接入，详见第 6 节。FMP Basic 可作为补充身份/SEC 发现源。现有 key 的小样本实测：公司 profile 200、带完整必需参数的 SEC filing search 200、press releases 402、transcript dates 402；之前完整 transcript 查询也得到 402。HTTP 200 只证明这次请求获准且返回数据，不证明全市场覆盖、内容质量或存储/再分发许可。

FMP 官方 MCP 只是调用接口的一种包装；官方说明每次 MCP 请求仍计入现有 API 限额，不增加数据权限或免费额度。其连接 URL 携带 API key，试点不得把完整 URL 写入日志、收据或提示词。Koyfin 与 Seeking Alpha 个人订阅可供人工阅读对照，不能作为 filing-fetch/Worker 的自动化数据接口。

## 2. 供应商比较：以本项目的用途为准

| 来源 | 当前公开价格 | 对业务叙述/电话会的价值 | 自动化与权利边界 | 本计划动作 |
|---|---:|---|---|---|
| SEC EDGAR + 公司 IR/交易所 | SEC 接口免费；IR 来源另按各站规则 | 美股 10-K/10-Q/8-K、招股/增发及附件的原始披露；IR 常有原始电话会/演示稿 | SEC submissions API 无 API key；遵守其程序访问规则；原文来源身份可追溯 | 美国披露优先使用，且只提取有业务叙述价值的证据 |
| FMP Basic | 免费，250 calls/day、30 日滚动 500 MB | profile/CIK/SEC 发现；本 key 这两类已返回 200 | 新闻稿、transcript 在当前 key 返回 402；不能凭“免费 150+ endpoints”推断具体权益 | 保持免费；只对增量价值做有界探针 |
| FMP Starter | $22/月，按年付 $264；300 calls/min | 官方列 US 覆盖及 Financial Market News，可能减少新闻发现工作 | 当前 key 的 press releases 402；Starter 对该精确 endpoint 的权益尚未实测/书面确认；显示/再分发另需许可 | 只有增量内容及权限验证后才考虑 |
| FMP Premium | $59/月，按年付 $708；750 calls/min | Starter 加 UK/Canada 与 Corporate Calendars | 官方套餐没有列电话会议正文；不为 transcript 买它 | 目前不买 |
| FMP Ultimate | $149/月，按年付 $1,788；3,000 calls/min | 官方列全球覆盖、Earnings Call Transcripts、13F | 尚须实测所需公司/期次覆盖，并确认原文存储、摘要和只读 export 权限 | 只有免费来源实测明显缺口且合同合适才申请 |
| Koyfin Free / Plus / Premium | $0 / $39 / $79 每月（页面选择年付）；Plus 为 $468/年 | Plus 网页可读 filings、press releases、transcripts；适合人工横向核对 | Koyfin FAQ 明示不给用户 API；部分财务/估值数据禁止下载 | 可用免费版人工比较；不买来接 Worker |
| Seeking Alpha Free / Premium | Free；Premium $299/年，折合约 $24.92/月，另可能有税 | Premium 官方说明可无限阅读 transcripts，也有作者观点/筛选工具 | 内容授权/API feeds 是独立合作；个人站点条款禁止机器人下载、索引及抓取 | 免费人工对照；Premium 仅在用户本人频繁阅读时单独评估 |

价格是 2026-09-27 官网页面显示的美元标价，年付月均不是逐月付款承诺；结账价、税、地区、促销、商业使用与数据许可都应在购买当天复核。Koyfin 网页订阅不能替代 API；Seeking Alpha 个人 Premium 也不能成为自动抓取许可。研究平台的评级、观点与文章不作为 company-wiki canonical 来源判断。

**针对现有五项目的付费取舍。** Koyfin Free 已有基础图表、宏观面板、两份 watchlist/screen 和有限新闻，适合给用户做人工界面基准；Plus 才把较完整的 filings、press releases、transcripts 与十年财务/预期显示放进同一网页，年付标价为 $468/年。Seeking Alpha Premium 的优势是人工阅读大量观点文章、电话会文字、Quant/作者/卖方评级及筛选，官方标价 $299/年；这些观点适合在 StockWiki 的研究审核中作为对照，不应倒灌 company-wiki 成为事实来源。两项同时订阅是 **$767/年税前**，仍不给本项目可用的自动化正文接口。故基线组合为 **SEC/IR 原始披露 + FMP Basic 免费额度 + Koyfin Free 人工查看 + Seeking Alpha 免费阅读范围**；任何付费都先用 30 日人工日志比较“免费链路缺失且用户实际用到的独有信息/节省时间”，不以官网列出的功能数决定。若只为一个人的阅读体验付费，按实际需要二选一：多市场图表/公司筛选偏 Koyfin Plus，观点文章/电话会全文浏览偏 Seeking Alpha Premium；均不进入 Worker 成本预算。

**与现有 earnings-transcripts 的实物比较**见 [独立对照卡](earnings_transcripts_vs_platforms_2026-09-27.md)。它当前本地有 6 家公司的 43 份英文会议记录，全部标为 Motley Fool 来源；英文、双语和夹排三种输出合计约 15.2 MiB。已提交的批量 CLI 有下载/翻译/阅读器，但不保存原始网页；未提交的精确季度 JSON 接口有无翻译正文和双 hash，仍不返回原始 payload 字节。两者均不能凭现状成为获准的公司资料自动来源；Koyfin/Seeking Alpha 个人订阅也不能解决这个接口与权利缺口。

## 3. 可复算的 30 日调用模型

本地 companies 目录于 2026-09-27 实数为 **246 个**。这是保守压力分母 N，不等于已核实的 246 个美国上市证券，也不等于 FMP 实际可覆盖数。上线前应从身份表得到 N_US、退市/多重上市合并结果及事件频率，再用真实日志替代本表。所有数字是**请求次数预算，不是实测流量或实际每月账单**。

约定：30 日月；5 次完整周轮询作为保守上界；20 家优先公司每天查一次，其余 N−20 每周查一次；每种公司级 endpoint 对一次检查发 1 次请求。统一给成功请求总量加 20% 额度，包含分页、短暂重试和补漏；未授权的 402 不应反复重试。公司目录数减少时按公式线性重算。每日调度需有硬上限，不得把月余量一次用完。

| 路径 | 原始算式（N=246） | 含 20% 余量的 30 日预算 | 首月额外身份 bootstrap |
|---|---:|---:|---:|
| A. 纯 SEC/IR 公开源 | 不调用 FMP | **0 FMP calls** | 0 |
| B. FMP Basic 只补充 SEC 检索 | 20×30 + 226×5 = 1,730 | **2,076 calls/月** | 246 profile 一次性；首月 ceil((1,730+246)×1.2) = **2,372** |
| C. 假设 Starter 确认允许新闻稿 | 2×1,730 + 40 次按需查询 = 3,500 | **4,200 calls/月** | 首月 ceil((3,500+246)×1.2) = **4,496** |
| D. 假设 Premium 另启 3 个日历/事件 feed 每天一次 | 3,500 + 3×30 = 3,590 | **4,308 calls/月** | 首月 **4,604** |
| E. 假设 Ultimate 事件触发 transcript | 3,590 + ceil(246×4/12)×2 = 3,754 | **4,505 calls/月** | 首月 **4,800** |

E 中的两次调用分别是假定每场电话会查一次可用期次、取一次正文；246 家每年各 4 场均匀分布，约 82 场/月。实际日期不均匀、版本修订和缺失会改变预算。若不用事件触发而每周扫描全部 246 家 transcript dates，再增 246×5=1,230 次，E 变为 **5,981 calls/月**，首月 **6,276**；计划明确禁止无理由全量高频轮询。A、B、C、D、E 是不同方案，**不能把它们相加**。

Basic 的 250/day 理论上对应 30 天 7,500 次，但 B 的平均约 69.2 次/天仍可能因同日补漏超过日额；设生产请求队列默认不超过 200 次/日，剩余给人工/错误恢复。周轮询按公司 ID 分片到不同日期，246 次首月 profile bootstrap 也由同一队列分多日执行，禁止集中首日冲破日额。持续记录 30 日响应字节以守住 500 MB。免费版能否对全部所需 symbol 使用某 endpoint 仍需逐项实测。Starter/Premium/Ultimate 的公开限制主要按每分钟标示，不等于允许无限调用或无限流量；各自还有 30 日带宽限制。C–E 的套餐映射尤其依赖精确 endpoint entitlement/内容权利核实，不能仅凭上表购买。

空间费用另计：API 调用额度和存储体积没有直接关系。只保留合法原文、source manifest、选中证据及必要索引；新闻稿/电话会不全量生成 Markdown、重复切片或跨仓副本。用每来源实际永久增量、原文唯一副本字节及 package 字节做月度空间账，与 [逐步空间账](stepwise_space_budget.md) 对齐。

## 4. 跨项目数据分工与可选扩展

- company-wiki/filing-fetch：SEC/公司 IR 的 filing 发现、文档链接、原文 hash/manifest、附录和业务叙述证据；FMP 可补充 CIK/证券身份、新闻稿/电话会发现与源链接，但任何第三方正文落盘和 export 均先过授权核实。
- earnings-transcripts：在获准的 provider 上统一获取/去重/精确期次，保留英文和 speaker/行号，不翻译。当前 Motley Fool 路径暂停生产接入；FMP transcript 402 由 provider 返回可分类的“订阅不可用”，不让 Worker 无限重试。
- revenue-forecast 与 StockWiki：消费 source ID/locator/版本化只读包；结构化产品/地域收入、财务口径、估值和预测由其各自适合的数据契约管理。FMP 的 product/geographic segmentation、guidance 邻近数据、日历可作为按需交叉核验候选，不能在 company-wiki 写一套数值事实库。RF 正在大量提交，G0 保持关闭，不能改其共享接口。
- invest-quick-scan：可选 entity/security 身份关联；不消费叙述包。FMP profile 可做身份交叉核验，需消除 ADR、双重上市和 symbol 变更歧义。
- 所有第三方/MCP 连接：先查 endpoint、覆盖、调用配额、存储与展示/再分发条款；MCP 能调用不代表已取得使用和再授权权利。

### 候选数据的优先级与落点

以下是 FMP 官方数据目录列出的候选类别，**并非当前 key 均可访问**。先检查免费/原始来源，再查实际权益与增量；任何类别都不应为了“API 有数据”而常驻轮询。

| 类别 | 触发及可能解决的问题 | 归属与试点处理 |
|---|---|---|
| Profile、CIK、symbol/交易所变更、行业分类 | 新公司入库、证券改名/双重上市、披露身份错配 | company-wiki 身份交叉核验；保留来源版本/映射，不把 ticker 当永久 ID；Basic profile 已做单证券 200 探针 |
| SEC filings、form type、8-K、IPO/股权发行 | 新披露、招股/增发/重大事项附件的发现 | filing-fetch/company-wiki；与 SEC 原生列表比较唯一新增文件和时效，原文仍指向官方披露 |
| Press releases、股票新闻、M&A 事件 | 新业务、海外扩张、客户/产能/交易动向 | company-wiki 只做来源发现与证据选段；新闻转载先定位公司原始稿/公告；当前 press releases 402 |
| Earnings calendar、transcript dates/正文 | 触发精确季度电话会获取，避免每家公司每日扫描 | earnings-transcripts 提供无翻译 TXT，filing-fetch companion 编排，company-wiki 保存合规原文和 evidence；日期当前 402 |
| 产品/地域收入分拆、历史报表、as-reported facts | 检查业务叙述中的经营规模、地域/业务口径 | revenue-forecast 与 invest-financials 等下游管理清洗数值及会计版本；上游只保留原始披露 locator 和可选数据引用 |
| 分析师预期、日历、市场/行业数据 | 事件提醒、预测共识差、行业背景对照 | StockWiki/revenue-forecast/invest-quick-scan 按自身合同按需拉取；不是 company-wiki 投资判断或必备证据 |
| 13F、insider、管理层薪酬/股份变动 | 所有权、激励和资本配置的研究输入 | 下游 invest-management/invest-distribution 使用；若追溯原始 Form 4/13F，company-wiki 可提供 SEC 来源记录 |
| ETF 持仓、宏观/外汇/大宗商品 | 主题、供应链或跨币种研究背景 | 下游主题/行业分析按需使用；不进入本项目的常规公司文档 Worker 队列 |

在 30 日试点里，先只验证身份、SEC filing、新闻稿和电话会四条与当前目标直接相关的路径；其他类别列入按需候选，不扩大每日调用分母。数字类要核对会计期、币种、单位、restatement、ADR/证券身份，不能拿单个 API 字段取代财报原文。

## 5. 仅在大节点做的验证与采购判据

1. **G1e 来源侧试点**：从身份表筛出 20 家真实美国证券，覆盖高频/低频、ADR 或多重上市、最近电话会及无电话会反例；冻结 company ID、CIK、symbol、时间窗和人工基线。试 30 日记录 SEC/IR、FMP Basic 和现有 transcript 工具各自发现的唯一文件、时延、空结果、重复、HTTP 类别、字节和人工核实结果。真实调用只写独立测试 run root，结束按现有 [E2E 计划](end_to_end_test_plan.md)核对树恢复；正式采集另走授权和 source manifest。
2. **费用/权益判据**：按日志重算 N_US、每日峰值、分页/重试、30 日带宽、每个付费 endpoint 的权益；将候选内容以原始披露 ID/hash 去重，计算“付费独有且与业务叙述相关的可合法保存文件/月”和每件实际增量费用。优先询问/试用 Starter 对 press releases 的精确权限；若没有明确权益或增量几乎为零，维持 $0。Koyfin/SA 不计入 API 预算。
3. **Ultimate 判据**：只有现有合法 transcript 来源在 20 家样本中有可复现覆盖/时效缺口，FMP 能补齐，且合同允许本项目的 TXT 留存、选段、摘要和受限只读 export，才比较 $1,788/年与节省的人工/其他数据成本；此前不买 Premium/Ultimate。
4. **实施闸门**：用户实际订阅选择以试点和当天合同/价格为依据；当前计划只能推荐“先不买”。供应商评估不是 G0/G2/G3/G4 放行条件；G1e 上游接口与 RF 消费合同分开推进。拒绝 402 自动升级、频繁轮询、网页抓取及凭网页阅读权限复制整站内容。

## 6. 电话会议来源权利复核与接入顺序（2026-09-27 补充）

上述“现有 earnings-transcripts 项目”仅代表代码存在，不代表其现有 provider 已可用于自动生产。Motley Fool 官方条款明确禁止以 agents、robots、scripts 等自动方式访问、复制或采集站点内容；当前 `motley_fool` 适配器和任何基于它的 filing-fetch 自动链路应失败关闭，不能以用户对本地项目的写权限代替内容方许可。Seeking Alpha 的个人订阅同样不能做自动抓取/索引。Koyfin 的网页订阅没有用户 API。三者都不应计入“可合法自动获取电话会”的覆盖分子。

优先调查 SEC 8-K 的 issuer-furnished transcript/management prepared remarks 附件，再调查发行人 IR 自行撰写的稿件；逐文件保存原始字节、来源 URL、提交/发布日期、版权/授权判断和解析出的英文 TXT。SEC 可程序访问，但须遵守其身份标识和公平访问限制。第三方供应商署名的 IR PDF（本次核查的 NVIDIA 电话会 PDF 标有 FactSet CallStreet copyright）不能仅凭 IR 链接判为可批量留存或再分发。发行人自行发布也需核对所在站点条款与下游展示范围。未核实的来源只保存元数据/链接，不下载正文、不做全文切片或 export。

**小样本反例核对（只读，非覆盖率估计）：**[American Outdoor Brands 2026 年 8-K](https://www.sec.gov/Archives/edgar/data/1808997/000180899726000033/aout-20260625.htm)明确将电话会议逐字稿列为 Exhibit 99.1；[Worthington Enterprises 2025 年 8-K](https://www.sec.gov/Archives/edgar/data/108516/000095017025091689/wor-20250625.htm)也如此。但 [Microsoft 2026 财年 Q4 的 8-K 附件目录](https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/0001193125-26-323632-index.htm)的 Exhibit 99.1 是业绩新闻稿，[附件正文](https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-ex99_1.htm)并非电话会逐字稿。故不能把 Item 2.02、EX-99.1 或“发布业绩”自动标成 transcript；发现器须核附件描述和实际文种，并以 CIK、accession、FY/Q 与 as-of 双重绑定。SEC 官方说明公开 submissions API 无 key，但[程序访问 FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)要求声明 User-Agent，当前最大 10 次/秒；试点应远低于该上限、复用缓存/增量列表。此三例只证明路径存在且非普遍，不推断 20 家覆盖率。

G1e 的实现顺序修正为：①冻结 provider 权利表，按 `discover`、`download`、`retain_raw`、`extract_txt`、`summarize`、`export_excerpt` 分动作记录证据与有效期，默认全拒；②先做 SEC 8-K 附件的精确证券/季度/截至日期发现和原始 HTML/TXT 保存，保留原件与派生 TXT 的 parent SHA 关系；③以 fake provider 做 filing-fetch → earnings-transcripts → company-wiki 的隔离 E2E，并加“Motley Fool/Seeking Alpha/FMP 402 均不触发正文落盘”负例；④仅对权利已核实的单份真实来源做受控 canary。测试结束按 [端到端测试计划](end_to_end_test_plan.md)恢复运行树。任何 provider 覆盖与费用比较只统计通过权利表的文件。此变更不放行 G1e、G0、Worker 或生产采集。

## 7. 原始证据与官方资料

- 2026-09-27 用用户提供的 FMP key 做只读 MSFT canary，响应体未保存：profile HTTP 200（读取 3,803 B），SEC search 首次缺 from/to 返回 400，补足 from/to/page/limit 后 HTTP 200（381 B）；press releases HTTP 402，transcript dates HTTP 402。前一次完整 transcript canary 也为 HTTP 402。一次未提权网络运行只有 URLError，不能用于判断权益；另一次命令在 Python 解析前失败，也没有发请求。所有 canary 没有创建仓库文件。
- [FMP 官方套餐与权限/带宽](https://site.financialmodelingprep.com/developer/docs/pricing)；[FMP 官方 MCP 与同一配额](https://site.financialmodelingprep.com/developer/docs/mcp-server)；[FMP SEC 按证券查询及必填参数](https://site.financialmodelingprep.com/developer/docs/stable/search-by-symbol)；[SEC EDGAR 免费 submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)。
- [Koyfin 官方价格与 Plus 文档功能](https://www.koyfin.com/pricing/)；[Koyfin 不提供用户 API](https://www.koyfin.com/help/faq/can-i-get-the-data-via-api/)；[Koyfin 下载限制](https://www.koyfin.com/help/faq/can-i-download-data/)。
- [Seeking Alpha Premium 价格](https://help.seekingalpha.com/what-is-seeking-alpha-premium)；[Premium 的 transcript 权益](https://help.seekingalpha.com/premium/seeking-alpha-premium-feature-list)；[站点使用条款](https://about.seekingalpha.com/terms)；[内容 API/feeds 合作入口](https://seekingalpha.com/partnership/form)。
- [Motley Fool 官方使用条款](https://www.fool.com/legal/terms-and-conditions/fool-rules/)；[SEC 程序访问与公平访问规则](https://www.sec.gov/about/developer-resources)；[SEC 8-K 附件含电话会议文字的实例](https://www.sec.gov/Archives/edgar/data/108516/000156459020058036/0001564590-20-058036-index.htm)；[NVIDIA IR 上的 FactSet 版权稿实例](https://investor.nvidia.com/files/content_files/TRANSCRIPT_-NVIDIA-Corp-NVDA-US-Q2-2027-Earnings-Call-26-August-2026-5_00-PM-ET.pdf)。

## 8. 六家公司同季度官方来源定点核查（只读，不代表覆盖率）

对 earnings-transcripts 本地 MSFT、FIG、SNOW、MDB、TAL、NVO 各取一份近期纪要核对；六份本地文件 header 均写 `Source: motley_fool`。找到同季度官方材料时应建立**新的 source/version**，不得给现存 TXT 改写 provenance。表内“未核实”只表示本次定点检查未取得证明，不能记成不存在。

| 公司与期次 | 官方来源核对 | 本轮分类 |
|---|---|---|
| MSFT FY26 Q4 | [Microsoft IR](https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4)刊载含问答的文字纪要；[SEC 8-K](https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-20260729.htm) EX-99.1 仅为新闻稿 | IR 全文存在；自动留存与展示许可待核 |
| FIG 2026 Q2 | [Figma IR](https://investor.figma.com/news-events/events-and-presentations/event-details/2026/Figma-Q2-2026-Earnings-Call/default.aspx)同时链接[公司准备发言稿](https://s206.q4cdn.com/973901332/files/doc_financials/2026/q2/Figma-Q2-26-Prepared-Remarks.pdf)和[完整纪要](https://s206.q4cdn.com/973901332/files/doc_financials/2026/q2/242074090_2010801861_3782208_Transcript_EditedCopy_20260806030511.pdf)；后者标 S&P Global Market Intelligence 版权；[8-K](https://www.sec.gov/Archives/edgar/data/1579878/000162828026053331/fig-20260805.htm) EX-99.1 是新闻稿 | 准备发言稿可单独做权利评审；第三方全文默认拒绝入库 |
| SNOW FY26 Q4 | [IR 全文 PDF](https://s26.q4cdn.com/463892824/files/doc_financials/2026/q4/CORRECTED-TRANSCRIPT_-Snowflake-Inc-SNOW-US-Q4-2026-Earnings-Call-25-February-2026-5_00-PM-ET.pdf)署名 FactSet CallStreet；[8-K](https://www.sec.gov/Archives/edgar/data/1640147/000162828026011631/snow-20260225.htm) EX-99.1 是新闻稿 | 第三方全文默认拒绝入库；另有无公司稿未核实 |
| MDB FY26 Q4 | [IR 活动页](https://investors.mongodb.com/events/event-details/mongodbs-q4-fy26-earnings-call)有 webcast；[8-K](https://www.sec.gov/Archives/edgar/data/1441816/000162828026013199/mdb-20260302.htm) EX-99.1 是新闻稿 | 官方全文/准备发言稿未核实 |
| TAL FY26 Q4 | [IR 活动页](https://ir.tal.com/Events?item=89)有 webcast；[6-K](https://www.sec.gov/Archives/edgar/data/1499620/000110465926047673/tm2612561d1_6k.htm) EX-99.1 是新闻稿 | 官方全文/准备发言稿未核实 |
| NVO 2025 Q3 | [IR 财报页](https://www.novonordisk.com/investors/financial-results.html)有 webcast；[SEC 6-K](https://www.sec.gov/Archives/edgar/data/353278/000035327825000005/caq32025.htm)为 38 页季度报告，含业务/研发叙述，非电话会纪要 | 官方完整电话会文字未核实；6-K 可独立按季报文种筛选 |

下一轮 20 家、每家一个**精确 FY/Q**：本表六家 + 八家美国本土发行人 + 六家外国 ADR，冻结 CIK、证券、截止日和会议日；逐件登记附件/IR 文种、制作方、版权、是否含 Q&A 及可准入动作。只读官方页面每家最多七次请求，基础上限 140 次，另留 20 次有界重试；SEC 端每秒最多一次，远低于其公开公平访问上限。只有通过逐动作权利表的文件才进入候选覆盖分子；不在试点中自动保存第三方全文。现有六样本只验证“官方路径有价值且混杂版权”，不足以决定 API 订阅。
