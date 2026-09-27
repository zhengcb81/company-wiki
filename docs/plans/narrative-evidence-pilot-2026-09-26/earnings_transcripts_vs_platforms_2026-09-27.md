# earnings-transcripts 与 Koyfin、Seeking Alpha 的电话会议能力对照（2026-09-27）

本卡回答“现有工具是否已经够用、还需不需要订阅”。它只做只读代码和本地文件盘点、官方公开权益比较；没有登录付费平台、抓取第三方正文或扩大当前来源使用许可。价格和条款以购买及运行当天复核为准。

## 1. 现有工具的实测基线

`earnings-transcripts/earnings-transcripts` 当前有两条不同的接口，不能把两者能力混为一谈：

| 接口 | 已实现的能力 | 对 company-wiki 的关键缺口 |
|---|---|---|
| 已提交的 `scraper.py` CLI | 对 `companies.txt` 批量找 Motley Fool 最近 N 季 URL；可选旧版 FMP 接口；下载英文、默认翻译、双语 JSON、夹排 TXT、Web 阅读器；按文件存在性跳过、段落翻译缓存、单实例文件锁、`--dry-run` | `--quarters` 不是精确 FY/Q；仅 `--output` 不隔离配置指定的日志/锁/cache；原始 HTML 没有落盘，英文 TXT 加工具头部；完成判定不核原件 hash；默认翻译增加时间/费用；不应直接被多文档 Worker 并发调用 |
| 新增的 `transcript_api.py` + `transcript_tool.py` 机器边界 | 一次请求一个明确 FY/Q 与 as-of；默认 result `/1` 返回未翻译英文和 hashes；opt-in result `/2` 返回限长 base64 原件/MIME/清理过的 effective URL、不重复正文；有字节/超时/跳转边界、状态码；无日志/锁/cache；支持 Motley Fool 与 FMP | 仍不是 MCP；仅 ticker/exchange 仍缺正式 security ID/CIK 绑定；无当前获准生产 provider；FMP `date` 是电话会日期，`publication_date=null` 且 `as_of_cutoff_verified=false`；尚未接 filing-fetch/company-wiki。100 个离线测试通过，1 个需要未配置 LLM key 的既有测试 deselected |

2026-09-27 只读盘点 `transcripts/`：**43 份英文 TXT，分布于 FIG 5、MDB 8、MSFT 9、NVO 8、SNOW 8、TAL 5；7 个配置 ticker 中 GENB 暂无本地英文文件**。43 份英文头部均写 `Source: motley_fool`，43 份双语 JSON 与 43 份夹排 TXT 都存在。英文 2,441,306 B、双语 6,770,745 B、夹排 6,731,684 B、summary 9,996 B，总计 **15,953,731 B，约 15.2 MiB**。这是当前本地样本体积与来源标注，不能推断市场覆盖率、最新成功率或 46 GiB 旧库的来源；三种输出保留了相同会议的多份内容，用户要求的英文证据流水线只需要一个原件和经验证的必要派生物。

本地 43 份旧 TXT 不能凭文件存在便当作 company-wiki 的 immutable raw；要保留 legacy 阅读用途或 metadata/link，未来迁移正文须先核实该来源的自动保存、派生、选段和展示权利，并能补齐原件或如实标记不可回放。不要为了“统一管理”复制三套旧文件到新目录。

## 2. 同一目标下的能力比较

| 维度 | earnings-transcripts 现状 | Koyfin | Seeking Alpha | SEC/发行人原始披露 |
|---|---|---|---|---|
| 人工阅读 | 自有 Web 阅读器、搜索、段落中英对照；43 份本地样本可读 | Free 有有限新闻与图表；Plus 网页提供 filings、新闻稿、transcripts 和更长财务/预期历史 | Premium 提供无限 transcript 阅读、主题/关键词检索和观点文章 | 原始文件可读，跨来源 UI 需自行建设 |
| 自动给 filing-fetch/Worker | 代码已有批量 CLI 和未提交的精确期次 JSON 边界；正式接入尚未完成 | 官方明确不向普通用户开放 API | 个人站点条款限制机器人下载/检索/索引；内容 API 是另行合作 | 可建设有界官方披露发现；逐站/逐附件核内容使用范围 |
| 来源及实际覆盖 | 本地 **6 公司/43 份**均标为 Motley Fool；FMP 当前 key transcript 端点实测 HTTP 402；没有可计入生产的合法自动全文覆盖收据 | 官网列 Plus transcripts，未在用户关注公司上实测独有覆盖 | 官网列 Premium 无限阅读，未在用户关注公司上实测独有覆盖 | 已找到 SEC 8-K 电话会议全文附件，但也有第三方版权反例；20 公司覆盖率待测 |
| 原件、as-of 和证据定位 | 旧 CLI 不留原始网页；新 API `/2` 已提供原件传输但 CWP importer 尚未完成；FMP 发布时点未知；source ID→原件 byte locator 尚未跨仓验收 | Free 不列 transcripts；网页权益不是公司可留存合同 | 免费会议文本可人工发现；条款不允许 pipeline 自动检索/保存 | 可按原始 accession/附件和字节保存 SHA/locator，逐件判定版权/来源 |
| 费用与额外空间 | Motley Fool 抓取软件本身无订阅价，但其自动访问条款不允许当前接入；默认翻译有 LLM 成本；本地三格式约 15.2 MiB | Free $0；Plus 年付显示 $39/月，约 $468/年；没有供 Worker 用的用户 API | Premium $299/年加可能税费；个人订阅仍不是自动化许可 | SEC API 免费；抓取、解析与审核仍有工程成本 |

Koyfin 和 Seeking Alpha 更适合**用户自己阅读、横向核对或发现问题**；在本项目的自动来源链里，现有订阅不能替代原件、source hash、权利、locator 和可恢复作业。两项年费合计 $767（税前）却仍不给此链一条可用的个人订阅 API。现有 earnings-transcripts 的 UI/批量处理值得保留，尤其精确期次、无翻译 JSON 接口应继续演进；但当前唯一已有本地正文来源是 Motley Fool，按其现行条款不能因此自动迁移或继续抓取。FMP 付费只有在权益与正文使用范围有凭据、且增量覆盖明显时才评估。

## 3. 有意义的平行比较试点

选 **20 家已核实 CIK/security ID 的美国公司、最近 4 个财政季度**，提前固定公司/期次/as-of 和历史观察窗。先对现有本地 43 份做来源、发布日期、speaker/Q&A、文字完整性和重复判定，但不再次访问 Motley Fool。随后在 30 日内用合法的 SEC/发行人源做受限发现；用户若已有 Koyfin/Seeking Alpha 免费或付费阅读权益，可人工记录同一格是否存在、发布时间、独有的业务/新产品/海外扩张/管理层指引片段，**不把平台正文复制进测试目录**。现有新 API 仅用 fake provider 跑合同测试；FMP 402 记录终态，不重试或自动购买。

每个 `(CIK, fiscal_year, fiscal_quarter, as_of)` 格只记：来源是否存在、候选数/歧义、发布时间是否可核、原件可合法留存与否、是否有 Q&A/主营业务进展、是否有独有可引用证据、人工打开与定位分钟数、获取/存储/处理实际成本。区分“网页可读”与“可机器留存和 export”。试点报告计算：精确期次覆盖率、时效差、唯一高价值片段数、可回放 locator 率、错误/重试量、每份永久增量字节与每个独有片段的增量费用；不按网页功能清单评价数据增量。

**决策规则：**先保持 Koyfin Free、Seeking Alpha 免费阅读范围与 FMP Basic，自动链优先 SEC/发行人披露。若人工阅读确有持续价值，Koyfin Plus 与 Seeking Alpha Premium 按用户的图表筛选或 transcript/观点阅读偏好二选一，不计入 Worker 能力。只有试点显示合法公开来源缺口、付费 API 能填补且合同允许原件/派生/选段/受限导出时，才比较 API 套餐；否则继续 $0。G1e 接入仍需 provider 权利、原件+派生合同及 filing-fetch 端到端验收，不以人工平台试用结果代替。

## 4. earnings-transcripts 的具体升级顺序

1. **保留人工产品，拆开自动入口。** `reader.py`、已有本地英文阅读与可选翻译继续可用；`scraper.py` 的批量/最近 N 季模式只作 legacy 手工工具，不由 filing-fetch 或并发 Worker 调用。机器入口以 `transcript_tool.py` 的精确 FY/Q、as-of、无翻译结果为基础；其未提交状态由 earnings-transcripts 仓库 owner 先固定版本/测试收据。
2. **先给机器入口加原件合同。** 已加 `/2` bounded base64 HTML/JSON、MIME、safe effective URL；CWP 尚需验 SHA/size/URL/期次并存 sidecar。若 future provider 需要先授权具体 URL，必须先暴露 discovery-only 候选阶段，再在授权后取正文；不能把 one-step 自动选择+正文 fetch 冒充“已在 exact candidate 下载前授权”。不能只返回“原件 hash + 已抽取 TXT”。
3. **先做合法来源适配器。** 第一候选是 SEC accession/附件与逐件核实的发行人稿件，入参用已核实 CIK/security ID、accession、精确期次和 as-of；多候选返回 `ambiguous`，未知发布日期返回不能通过历史 as-of 的状态。FMP 只在 endpoint entitlement 与正文留存/派生/受限展示权利获证后开启。Motley Fool 和 Seeking Alpha 网站的当前自动动作始终由 company-wiki 权限闸门拒绝，不靠工具“可抓到”判定可用。
4. **filing-fetch 编排调用一次，company-wiki 负责保存。** filing-fetch 已成功的财报结果与 companion 结果分开记录；先由其复用公司身份和 `DownloadAuthorization`，再由 company-wiki 检查逐动作来源政策；工具仅返回原件/元数据。company-wiki 原件 writer 按 SHA/manifest 保存唯一副本，派生英文 TXT 及行到原件 byte locator 进入现有 artifacts 的版本化角色。对 HTML 的标题、发言人、Q&A、脚本/导航过滤做真实样本质量审查，不能把 synthetic line replay 当作内容质量验收。
5. **只在 G1e 大节点集中验收。** fake provider 走真实 filing-fetch → ET subprocess → CWP writer/catalog → TXT 选择/摘要；验证首次导入、同 SHA 复用、精确期次、发布时点、原件/派生 hash 与 locator、无翻译、filing 成功而 companion 失败、402/版权/权限拒绝零正文落盘。测试目录从空 run root 开始，结束逐项与基线比对并清除文件。正式来源再做单件受控 canary，不把付费平台人工网页作为机器端到端夹具。

## 5. 核查依据

- 本地只读：`earnings-transcripts/README.md`、`scraper.py`、`transcript_api.py`、`transcript_tool.py`、`companies.txt`、`transcripts/` 的文件名/大小/英文头部来源字段；未修改该仓库。
- [Koyfin 价格与功能](https://www.koyfin.com/pricing/)；[Koyfin 用户 API 答复](https://www.koyfin.com/help/faq/can-i-get-the-data-via-api/)。
- [Seeking Alpha Premium 价格](https://help.seekingalpha.com/what-is-seeking-alpha-premium)；[transcript 阅读权益](https://help.seekingalpha.com/premium/seeking-alpha-premium-feature-list)；[个人站点条款](https://about.seekingalpha.com/terms)。
- [Motley Fool 使用条款](https://www.fool.com/legal/terms-and-conditions/fool-rules/)；[SEC 程序访问说明](https://www.sec.gov/about/developer-resources)。

## 免费层复核与是否接入项目（2026-09-27）

按“不付费且只有真实增量才增加 provider”的标准，结论是：**不新增 Koyfin 或 Seeking Alpha 的机器采集 connector，也不建立账号依赖。** 两站作为可选人工浏览/发现入口保留链接即可；需要落入 company-wiki 的事实材料，优先转到发行人 IR、SEC/交易所等可核原始来源。

| 免费层/用途 | 当前核验 | 对本项目的决定 |
|---|---|---|
| Koyfin Free | 官方价格页列出 2 年财务、1 年预期、有限公司快照和有限新闻；filings、press releases、transcripts 列在 Plus（官网显示 $39/月，价格页处于年付展示）。 | 对本项目关心的业务叙述和电话会全文，免费层没有明确增量。可人工看有限新闻寻找原始披露线索；不复制、转存或程序化接入 Koyfin 内容。 |
| Seeking Alpha Free | 官方 transcript 页面称每个财报季覆盖约 4,500 场电话会，并称 earnings transcripts 免费；早期产品说明曾描述新 transcript / article 有一段免费阅读窗口，但免费可见期和具体单篇访问应以当时页面为准。 | 对人工发现近期电话会有实际价值，是两个站中唯一值得保留的可选阅读链接；但官方条款允许个人非商业阅读/下载，同时明文禁止 robot、retrieval app/process 自动下载、检索、索引、data mine、scrape、harvest，不能作为 company-wiki 自动 provider。 |

**使用边界：**人工打开页面后只记录外链/来源发现线索，不把 Seeking Alpha 正文或 Koyfin 数据写入 company-wiki，也不启动自动浏览器抓取。若将来要持久保存其原文、做派生摘要或导出选段，须先取得相应书面许可/数据合作合同；站点页面能打开、免费账户能读不构成许可。当前 CWP rights policy 对这两站的机器 fetch/retain/derive 仍应 hard-deny。

**与 E-T 能力的关系：**Seeking Alpha 免费 transcript 可帮助人工发现“可能有这场电话会”，但不改善 E-T 当前不能自动使用 Motley Fool 的权利状态，也不能把 SA 正文合法变成 immutable raw；Koyfin Free 亦未列出 transcript access。故正式自动来源仍先调查发行人原文与 SEC 逐件可留存附件；若这一路缺覆盖，再单独核 FMP/其他许可 provider 的实际覆盖与留存权，不为“网站名单更长”加 adapter。

核验来源： [Koyfin 当前 Free/Plus 权益与价格](https://www.koyfin.com/pricing/)；[Koyfin Terms and Conditions](https://app.koyfin.com/terms-and-conditions)；[Seeking Alpha 官方 transcript 覆盖/免费说明](https://about.seekingalpha.com/transcripts)；[Seeking Alpha 当前 Terms of Use（个人使用、自动抓取限制）](https://about.seekingalpha.com/terms)。
