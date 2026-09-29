# S0a 现场接口与样本输入（2026-09-29）

本页是总指挥的**观察记录**，不是冻结合同或人工签收。生产者要先从实际 serializer/CLI 生成 S0b golden；消费者只根据相应冻结版本接线。任何仓库的未提交工作先由其唯一 owner 保存，不能以本页的旧 SHA 执行 reset/clean。原始文档只读，派生与测试文件在隔离根生成并清理。以下工作树 SHA 是 **S0a 时点**；2026-09-29 的新提交见第 5 节。

## 1. 工作树和独占写入

| 仓库 | S0a 观察 | 唯一后续写入者与立即可做事项 |
|---|---|---|
| company-wiki | `master@c5ce72b`，相对 `origin/master` ahead 35；此前 39 个源码/测试 WIP 连同 CI/pre-commit 修正保存为 `codex/narrative-gates-integration@db3ff32`。主树与专用代码 worktree 均干净。 | 总指挥只写本计划目录；代码仅在 `C:\Users\郑曾波\.codex\worktrees\data-lake-reader\company-wiki` 实施。先做 SourceVersionReader P0 RED→修复，再出 SourceRef/verified-open/SourceExport 真实 golden 与 G-0。 |
| earnings-transcripts | `codex/transcript-companion-adapter@1a48f66`，本地 main 同点、领先 `origin/main` 4 个提交；API/CLI 等有效未提交 WIP 已盘点。 | ET owner 独占本仓，先保全 WIP，再修单一网络意图、默认禁用 Motley、FMP 具名失败，产 `/2` 真实 serializer golden。 |
| filing-fetch | 根 `fcap@d35b6f5 = origin/main`，本地 main 落后 39；两个不同 WIP worktree 都改 `fetch_filing.py`/`filing_contracts.py`，必须由同一 FF owner 顺序收拢。根唯一 untracked 为密钥文件，内容未读取。 | FF owner 先保存两组 WIP、做 v1 兼容 RED；v2/companion 依赖 CWP/ET golden，不把两个工作树并发写同一文件。 |
| revenue-forecast | 根 `fcap@ee0a82b` 已是 `origin/main@3a69f9c` 祖先；本地 main 落后 813。reader WIP 在 `rfv2-tdd-20260927`，根另有活动 PWF/assurance 文件。受限沙箱对 `.planning/execution_runs` 的删除报告不可信。 | RF owner 独占独立工作树，先做严格 evidence hash/两个 CLI 退出码与去人工 review RED；reader 等 CWP/FF golden。绝不合入 §42 的“有 path 无 hash 也 ready”宽松语义。 |
| StockWiki | `master`/reader 均 `f5b8526`，无 remote；根的 W01 store/test/.gitignore WIP 待保全，另有独立本机设置文件。 | StockWiki owner 保存 W01，独立修已有 RED；v2 来源/身份/selected 的正式接线分别等 CWP、IQS 及 CWP selected golden。 |
| invest-quick-scan | `master@25b8d14`、无 remote；多量活动 tracked/untracked PWF、合同和测试，尚在逐项归属，不清理。 | IQS owner 独占本仓，先保存有效合同 WIP；只出 identity schema/参考校验 CLI，不写 StockWiki 真身份库。 |

## 2. observed 接口与 S0b 缺口

| 生产者 → 消费者 | 当前观察到的版本/语义 | S0b 冻结物与现存缺口 |
|---|---|---|
| CWP → FF/RF | `SourceRef` schema `2.0`：`document_id, source_id, content_sha256, byte_size, mime_type`；`query_local` 是 metadata-only，`open_version/verify_version` 应最终重验真实字节 SHA。当前 `capture_ready` 要求 review status `not_detected`，review store 故障可阻断；pending remediation 也阻断查询/open。 | CWP 修 P0 后用正式 CLI/serializer 出正例和错 SHA/撤回/as-of/版本反例、命令/退出码、SHA；G-0 核真实跨根字节。FF v2/RF reader 此前的 WIP 输出都只算 observed。 |
| CWP → StockWiki | `SourceExportBundleV2` 现有 producer 与 CLI，schema `2.0.0`；StockWiki 的 v2 reader/CLI 尚不存在，旧 `sources.py` 以绝对路径 SHA1 造 ID。 | CWP 真正导出 P01/P06/P07 的 source/evidence/locator golden；StockWiki 用其自身入口加 verified-open 真读，不以旧 `--doc-root` dry-run 代替。 |
| ET → FF/CWP | 请求 FY 和 Q 均必填。`earnings-transcript-result/2` Motley fetched 为 24 字段；FMP fetched 为 26 字段，多 `call_date, publication_date, as_of_cutoff_verified` 且无 `published_date`。`provider_payload_sha256` 是原始响应哈希，`canonical_content_sha256`/`content_bytes` 是抽取 TXT。 | ET 固定测试时钟、从真 serializer/CLI 假 FMP HTTP 产稳定 golden；CWP 当前 importer **只接受 Motley 24 字段**，MIME 不收 `application/json`，URL 禁 query，而 FMP 安全 URL 有 `symbol/year/quarter` query。CWP 在 S0b 明确定义 provider-specific 字段/URL/期次规则并作版本裁定，FF companion 随版本消费；禁止悄悄放宽 exact-key。真实 FMP 200 权益未证实，此离线成功不等于付费接口可用。 |
| FF → RF | v1 request `1.2`（兼容 `1.1`）/response `1.1`；默认禁下载。v2 SourceRef WIP 仍混用 `1.1` 响应并将 `not_reviewed` 拒绝。companion WIP 仍使用 CWP 旧 rights preflight，与已定简化方向不一致。 | FF owner 保留 v1 golden，整合一个显式 v2 envelope；拆分 filing 与 transcript 子结果，FY-only 返回 `period_unresolved`，不猜 Q4；给 RF 真实 serializer 正反例与退出码。 |
| StockWiki → IQS | W01 store `SCHEMA_VERSION=1`，尚无 Listing/AnalysisSubject、identity snapshot CLI/golden 或四态 mapping。IQS 目标包 `2.2.0` 含 Entity `2.1.0`、Security/Listing `2.1.0`、AnalysisSubject `1.0.0`。 | IQS 先出 schema/参考校验器/负例；StockWiki 从真实 DB serializer 出 identity snapshot golden；`mapping_status=null` 是未尝试，尝试后无匹配是 `unknown`，其余状态以冻结合同为准。G2b 暂 pending。 |
| CWP selected → RF/StockWiki | 试点 `narrative-evidence-selection-bundle/0.2.0` 不是持久消费合同；正式 selected package/CLI 尚无 golden。 | CWP 完成 E5 持久 package 和 locator 回放，再独立冻结；两个消费者分别实现本仓 adapter，`skip` 不生成证据，`partial` 只用可回放片段。 |

每行冻结时补：`producer repo+commit | schema/version | serializer/CLI 命令 | 正例/畸形反例路径和 SHA | 身份/时间/SHA/locator 语义 | 错误码/退出码 | consumer repo+版本 | frozen`。字段变更先由 producer 升版本并更新 golden；本页没有第二套人工批准。

## 3. 只读试点输入清单

| ID | 原件绝对路径 | 字节 | SHA-256 | oracle / 用途 |
|---|---|---:|---|---|
| P01 | `C:\Users\郑曾波\Projects\company-wiki\companies\中微公司\raw\financial_reports\中微公司：2025年年度报告.pdf` | 9,165,875 | `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5` | 第 40 页产品进展；财务表混排。 |
| P04 | `C:\Users\郑曾波\Projects\company-wiki\companies\中微公司\raw\prospectus\中微公司：首次公开发行股票并在科创板上市招股说明书.pdf` | 11,211,796 | `19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67` | 第 114 页业务技术起点；429 页资源门。 |
| P06 | `C:\Users\郑曾波\Projects\company-wiki\companies\三角防务\raw\research\三角防务：西安三角防务股份有限公司向特定对象发行股票并在创业板上市募集说明书（注册稿）.PDF` | 5,595,592 | `cd803fe9528f4646f8f29b518a450ae4bd5b5968c482eb49789f9786b523595b` | 第 3、101 页认证/项目；原 catalog sidecar 不足时仅 preview，不假装正式 reuse。 |
| P07 | `C:\Users\郑曾波\Projects\company-wiki\companies\万润股份\raw\research\万润股份：投资者关系活动记录表20260515.pdf` | 153,851 | `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7` | 第 5–6 页跨页问答。 |
| P09 | `C:\Users\郑曾波\Projects\company-wiki\companies\中微公司\raw\investor_relations\中微公司：投资者关系管理办法（2025年8月）.pdf` | 167,252 | `76e146985388c926f2683e24af47e6a1ab0ce8a156864fb16e7df9a2cc99b678` | 整件低价值负例，仅跳过业务切片，保留原文。 |
| T01 | `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts\transcripts\MSFT\MSFT_Q4_2026_earnings_call.txt` | 66,324 | `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a` | 第 124 行开始逐字稿；目标陈述在 236–264 行。 |
| T02 | `C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts\transcripts\NVO\NVO_Q4_2024_earnings_call.txt` | 66,597 | `d00e2a4537b86628ef019180e27de5ae0a57e715770ddf15135bd75627a6d59e` | 第 178 行问答；目标答复 184–212 行，另一处同短语在 422 行。 |

各线只按需复制子集到自己独占、事前不存在的测试根；初始/结束目录树必须相同，测试前后对原件 SHA 复核。无需复制 46 GiB 数据库，也不做完整备份恢复。P02/P03/P05/P08/P10 的历史观察和 oracle 仍见 [findings.md](findings.md)，用于扩充后续留出集；新增样本先核完整 SHA 再列入正式测试。

## 4. 本次命令问题与边界

PowerShell 不接受 Bash 花括号路径列表，改为单文件或明确数组；`foreach` 输出后接管道须先赋值再 `ConvertTo-Json`。这些只是只读命令语法失败，未触及产品代码或原件。受限环境的 Git 访问警告与 RF 上千删除不可作为清理依据。

## 5. S0b 实际到件（2026-09-29）

| Producer | 当前本地提交与可用输出 | 消费前约束 |
|---|---|---|
| company-wiki | 专用代码分支 `codex/narrative-gates-integration@7760b09`：P0 `d5162e5`，SourceRef/文本 span/SourceExport v2 真 CLI golden `c508e8e`，Windows LF 属性 `3dd41e1`，真实 P06 四根与 P04 429 页资源 E2E `58e2f21`，verified-open 收据 `822a43a`，拒绝回执 LF 修正 `7760b09`。golden 目录 `C:\Users\郑曾波\.codex\worktrees\data-lake-reader\company-wiki\tests\golden\source_v2\`；`source_ref.json` SHA `aca22689b9369151932d8402614c48d0122a8049fee3015b420264bcfd335cf1`，坏 ref SHA `45f2f3a6dfaec665ebb6ac85eb2127093092a367031952f5c7e83bc477d714d1`，bundle 文件 SHA `50127fc93f77e38f391917e5b152037c5375e385eedd0284419555348e16d793`，成功 receipt normalized SHA `b27dccb3d8f4adf101d8f66b8feb1dcc98b987ec7993fbcc9c995f865f3d5869`，坏 SHA receipt LF SHA `daed1b192dab90daf50bc2c9a3dc92695009944f51457177374cc77e0d53a0b5`。指定 G-0 测试包 80 passed/0 skipped，CLI 收据 6 passed。 | 基础 SourceRef/Export 为自包含**synthetic 合同 golden**，不等于真实来源端到端签收。成功 verified-open 的动态时间/策略 SHA 先校验格式再对照 normalized 示例；PDF span 当前不允许，E5 immutable parser registry 后再做真实 PDF locator。 |
| earnings-transcripts | 本地 `main@4924d57044ae061d5fec3ccd4f1b7e74633f013a`。FMP `/2` fake HTTP→真实 serializer/CLI golden manifest SHA `2b098b1f53b5d347671ddeda9aa7f8eabb08ca97b539ccbdddf7b3699e7f5453`；FMP fetched SHA `ee643fbbd6c37b82c933689f819525330df21c6383e8b2fa81500902ac39ece3`；Motley fetched SHA `35469e35d91149f175ba15118ef10b4825eda265f2c58fe063300907e2acde6a`。 | ET FMP 提供 `call_date`、`publication_date:null`、`as_of_cutoff_verified:false`；CWP 不得把 call date 伪装成发表日期或声称 as-of 已核。真实 FMP 200 权益仍未知。 |
| revenue-forecast | 独立 `rf-impl` worktree/local main 已到 `88b3bda3`：197 个 registry scenario 证据真 SHA、strict path/hash、两个 CLI 非零语义和 review 诊断已提交；按用户授权将可伪造的人工 `issue-auth` 改为自动 HEAD/证据/catalog/容量/回退门，13 个定向测试通过。 | 新 opt-in SourceRef/verified-open reader 已按 CWP golden RED 开工，FF envelope/selected 正式消费仍待；`origin/main` 未 push。 |
| filing-fetch | 唯一 owner 的 `codex/ff-source-companion-integration@5532ce0` 干净：v1 默认保持，v2 pathless SourceRef 与独立 transcript 状态已用 CWP/ET 真 producer golden 消费；全套 433 passed/13 skipped/78 subtests，隔离 FF CLI→CWP E2E 15 passed。 | CWP RequestPlan 合同、FMP canonical admission 与真实多根 G-0 保持 hold；复制的坏 SHA receipt fixture 仍需对齐 CWP `7760b09` 的 LF pin。根密钥文件未读取或纳入提交。 |
| StockWiki | W01 已在本地 `master@5bb68f6` 完成并独立验收 18/18；基础 SourceExport v2 reader 尚不存在，已给出[独立施工卡](harness_lanes/stockwiki_source_reader.md)。 | 可由新的唯一 StockWiki harness 先做 opt-in reader/G-B；W02/W03 仍等 IQS 正式公开 CLI 与真实 DB identity snapshot，G2b pending。 |
