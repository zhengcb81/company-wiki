# 跨仓主线整合与 company-wiki 后续交付总计划（2026-09-28）

> 状态：**调查完成后的施工计划，尚未执行本计划的并线、清理或生产发布**。本页是跨仓先后顺序、分支处理和大节点验收的当前入口；`task_plan.md` 记录状态，R4 实施卡、清洁架构总图、Phase E 施工卡和各仓 PWF 保留具体合同/历史收据。旧文档中的“当前下一步”若与本页冲突，以本页和实际 Git/测试复核为准。实施者必须先读本页，再读所需专项卡，不得根据过期收据跳步。

## 0. 目标、边界与验收定义

按用户确认的优先级完成三件事：①识别并把各仓**真正尚未并入**的有效实现安全并入各自主线；②让来源身份、位置、读取、下载、派生、消费和调度各层负责自己的合同，使目录/盘符/Dropbox/dayu 不进入上层业务分支；③完成叙述证据、电话会、可靠并发 Worker 与派生降容。RF 已提交的 `fcap` 内容已在远端主线；“RF 并线”目前实际指 reader WIP 与相关消费者合同，并非重复合并旧 `fcap`。

**不可破坏条件**：原始下载字节、对应 SHA、来源/版本/时间事实不丢；本轮**不删除任何唯一原文**，历史 D4“唯一低价值 raw 处置”暂停。相同 SHA 的重复原文位置也不在本轮空间目标中，若日后恢复 D4，须重新核用户当时的保留要求。所有测试仅在隔离目录复制少量原件，结束恢复测试目录原状；不完整恢复 46 GiB 历史备份。生产 Worker 一直保持 paused，直至 E-B 和发布门通过。company-wiki 只生产 source/evidence/quality，投资判断仍属 StockWiki/RF/IQS。

**整体完成**要求：真实 FF→CWP→RF 和 FF→ET→CWP、StockWiki→CWP 基础来源 reader 及后续 selected evidence 消费通过各自真实入口；所有跨仓对象无稳定物理路径；新 Worker 四类真实文档与故障/并发门通过；旧可重建派生分批回收且同卷净占用下降；原件清单、SHA、manifest 前后相同；各仓待并实现进入主线，临时/旧工作树按证据对账。可单独发布已验子能力，但不能把局部绿灯写成整体完成。

## 1. 已核事实与不可沿用的旧假设

| 仓库/工作树（2026-09-28） | 已核基线及待处理项 | 禁止误判 |
|---|---|---|
| company-wiki | 本地 `master@43c5f4a` 比已核远端 `origin/master@f39bd5a` 领先 33 提交；已知命名支线均是 master 祖先，**无待合并的 CWP 产品分支**。调查起点仅有 3 个 PWF 文件修改，本轮又补总计划与入口指针；`SourceVersionReader`、M1/M2、E0–E4 已在主线，E5–E7 未完成。 | 不把历史独立 worktree 的旧 HEAD 再并一次；不把 pilot `source_id→raw path` resolver 当正式消费合同。 |
| revenue-forecast | 真远端 `origin/main@3a69f9c5b` 已包含 `fcap@ee0a82bfd`；本地 `main@3ce9cc4d3` 落后远端 813 提交。reader worktree `codex/revenue-source-reader@3a69f9c5b` 有 3 修改/7 未跟踪。RF 根在**沙箱外**为 11 修改/404 未跟踪/**0 删除**。 | 沙箱内 6,123 状态/3,778 删除为 ACL 误报。根工作树旧 §42 宽松 hash 代码已被主线 §43 严格规则覆盖，绝不整包并入；81 个 RATCHET-FIX 文件有 PWF 复审价值，不能按临时文件删除。 |
| filing-fetch | `fcap@d35b6f5` 与缓存 `origin/main` 相同，本地 `main` 落后 39 提交。SourceRef v2 工作树在 `90771d8` 上有后续改动；transcript-companion 为另一份未提交 WIP，两者修改相同 `fetch_filing.py`、`filing_contracts.py`。根目录 `config/FMP_API_KEY.txt` 为本地秘密。 | 只挑 `90771d8` 会复活后来已删除的旧 transport；不能 stage API key，也不能把两个 WIP 直接叠加。 |
| earnings-transcripts | 本地 `main` 与 `codex/transcript-companion-adapter@1a48f66e` 同 HEAD，比缓存远端 main 领先 4 提交；精确期次 JSON 工具、免翻译 flag、测试仍有未提交实现。定向测试 31 passed。 | PWF 勾选不等于接口代码已提交/并远端；旧 `.workbuddy-ai`/eval 文件须另分类。 |
| StockWiki | 本地 `master` 与 `codex/source-export-v2-reader` 均为 `f5b8526`，reader 分支**没有 reader 实现**；无 remote。主树有活动 QuickScanStore W01 未提交实现，当前其测试 8 passed/10 failed。历史 Source Provider v1 源码/配置当前不存在。 | 不把历史 W02/W03 的 59 pass/1 skip 收据、旧 `.pyc` 或空 reader 分支当现行能力；不清除 W01。 |
| invest-quick-scan | 本地 `master@25b8d14`，47 tracked 修改、719 untracked，其中大量为活动 PWF/证据；无 remote。C01 身份合同已变为 issuer/security/listing v2.1，旧回执过期。 | 不能用“未提交=垃圾”整体恢复；G2b 身份映射与叙述 G2a 是两条独立消费线。 |

上述 SHA 是本次调查锚点，**不是未来直接合并命令的固定目标**。每次真正并线前在可访问环境只读 `fetch`/比较 live refs、worktree HEAD、`status --porcelain=v1 --untracked-files=all`；受限沙箱中的删除计数不能用于清理决策。RF、FF 等非本仓 Git 操作必须在能读完整 worktree/.git 的环境进行。遇长路径/ACL 警告，只复核受影响精确路径，不外推为删除。无 remote 的仓先实现本地主线整合；远端发布需先有真实 remote，不编造地址或强推。

## 2. 冻结跨仓合同：层归层、位置只是位置

| Owner | 稳定责任与输出 | 不得泄漏/越权 |
|---|---|---|
| CWP L0/L1 | immutable raw、manifest、SourceRecord/SourceRef、同 SHA 的多个位置与每次采集 provenance；root adapter 仅在此解释 company/dayu/Dropbox/未来根。 | root priority、文件名、目录不能改变 source/version、kind/period 或业务身份。 |
| CWP L2 | `SourceVersionReader` 按精确版本查询，实际打开完整字节并验 SHA，再返回已验证内容/收据；候选 metadata 可无打开。 | `resolve` 候选不能冒充 verified bytes；跨进程不把 PDF 塞无界 JSON，也不把永久路径交给消费者自行打开。 |
| CWP L3/FF | CWP 拥有 discovery/admission、授权后的 canonical import 和归属；FF 负责请求编排、已存在复用、缺口呈现及调用 CWP/ET。 | FF 不写 CWP catalog，不凭 physical path 验 v2 handle，不在无授权时下载/隐式联网。 |
| ET | 按明确公司及 fiscal year/quarter 返回原语言 TXT、来源 URL/时间/hash、机器可读结果；新 `transcript_tool.py`/`transcript_api.py` 固定返回未翻译原文。 | ET 不决定 CWP source identity、投资结论或最终 storage root。 |
| CWP L4/L5 | 确定性结构/locator、业务叙述选择、带来源引用的摘要和 coverage；普通制度/通知可有带理由的 skip。 | 不默认保存全文全段切片；解析/OCR 缺口不能伪装成“无业务价值”。 |
| CWP L6 / RF / StockWiki / IQS | CWP 提供版本化 SourceRef/SourceExport/selected bundle；RF、StockWiki 通过各自薄 adapter 读取。IQS 只可选映射身份。 | RF/SW/IQS 不导入 CWP 内部 DAG/Store，不要 `--source-root` 作 v2 必填，不跨仓写 mutable DB。 |
| CWP L7 | 持久 job/attempt/outbox、generation/token fencing、单 writer projector、进程并发和统一资源预算。 | 不共享非线程安全 LLMClient，不靠内存 queue 恢复任务，Worker 不删原文。 |

接口裁定：CWP operation、SourceRef 和 verified read receipt 各自保留**独立版本**，producer 输出 golden 正例，consumer 用其正例测试；未知版本/多余路径字段、source/hash/期间/时点/撤回漂移须 fail closed。FF 默认 v1 保持原退出码与 JSON 行为，opt-in v2 envelope 必须显式可识别且全部 pathless，再讨论技能默认路由。RF 保留主线 `OWNER_DECISIONS §43`：有 evidence path 必须有合法 64 位 fixture hash，缺失/错误不能 closure ready。StockWiki reader 的旧 v1 兼容只为**实际发现的历史持久引用**实现，先审已存对象，不凭过期 R4 清单重建死代码。IQS 的 issuer/security/listing v2.1 只进入其身份线，不硬塞进 CWP SourceRef。

电话会编排的可执行语义：filing-fetch 技能在“采集公司文档”工作流中，取得**明确 fiscal year/quarter**且用户的下载授权覆盖电话会时，自动附带 transcript 请求；standalone 旧 v1 调用仍保持原行为。年报不能仅因是全年报告就猜 Q4；仅 ET/来源 metadata 明确映射到 FY 或精确 Q 时调用该期，无法确定时返回 `period_unresolved/not_requested` 类具名结果而不抓错误季度。财报成功、电话会失败要分别报告和可重试，不回滚已保存财报；电话会原语言 TXT 入 CWP canonical raw，直接进入 L4/L5，无 PDF 转录与翻译。工具入口经显式配置/包入口注入，不猜相邻 ET checkout 或 `wiki_root/src`。FMP/Koyfin/Seeking Alpha 本轮不强加 provider；真实 provider 权利/成本配置缺失时只执行离线 fake E2E，不误报生产抓取可用。

## 3. 一次排好的施工依赖图

```text
S0 基线/合同/样本与测试根冻结 → G-0 跨根 verified reader 门
 ├─ S1 RF 旧 fcap 已并线核账、CWP 已并支线核账（无重复 merge）
 ├─ S2 ET 精确期次+免翻译 WIP 收拢入 ET main ───────────────┐
 ├─ S3 FF SourceRef v2 净差异入单一集成支线 ── S4 RF reader ─┤
 │                                              │               ├─ G-A 三仓来源+电话会真实入口门
 │                                              └─ FF companion ─┘
 ├─ S5 StockWiki v2 source reader ─────────────── G-B C.local 门
 ├─ Q1 IQS C01 v2.1 → Q2 StockWiki W01 绿/提交 → Q3 W02/W03 → G2b
 └─ N0 CWP 旧链退出/单一工件读取 → N1 E5/W5 → N2 E6/E7/E-B
                                               → N3 G2a selected 消费 → G-C
                                                    │
                                 G-A + G-B + G-C → G-D 派生清理/发布
```

S2 与 S3、S5、Q1、N0/N1 可并行，**但每仓写入只由其集成分支/owner 负责**。G-0 是消费者主线/默认路由的共同前置；已有 CWP 内部 M1 绿灯不等于 R4 的独立 B.AR。FF companion 在 S3 最终合同后移植；RF reader 在 FF v2 合同冻结后才切默认；StockWiki 基础 reader 不等待 IQS W02/W03，Q 线只决定 G2b。CWP E5 可独立进行，但 G2a 消费必须等基础 pathless reader 和持久 selected package 真正存在。N2 的进程并发通过 E-B 前不启动生产 Worker。任何消费侧默认切换都在相关 G 门通过之后。

## 4. 逐步施工卡（每一步有输入、动作、测试与提交边界）

### S0｜冻结基线、样本与集成工作区

1. 在完整访问环境获取各仓 live refs，逐仓保存 `HEAD/branch/upstream/merge-base/status`、tracked diff 摘要及 untracked **路径清单**；仅记录密钥文件名，不读值。把本节表格与新快照差异写 `findings.md`，避免按旧 SHA 操作。每个有效 WIP 建其仓内独立 `codex/...-integration` 工作树，基于**当前主线**；不得在 RF/StockWiki/IQS 活动脏树上 `reset --hard` 或批量 checkout。工作树创建/归档依 Codex worktree 工具；若是既有用户管理工作树，先识别 owner，不能替换。
2. 冻结 CWP `SourceRef`、operation、verified receipt、**基础 SourceExport v2** 与 ET companion/selected bundle 的字段、版本、错误、期次和授权矩阵；**已存在的** operation/SourceRef/read producer 生成 golden，现行 `source_export.py` 仍是 schema 1.0.0，v2、companion、持久 selected bundle 先冻结设计夹具，在 S5/S4b/N1 的 RED→GREEN 中由正式 producer 产出 golden 后替换夹具。基础 export 至少约束 source/version/hash/locator/质量/撤回/as-of、稳定 export/evidence/candidate ID、标题/kind/period 和旧 `cw1_*` 引用对照；导入范围与 full sync 另列发布门。冻结 P01 年报、P04 招股书、P07 IR、T01/T02 TXT、P06 定增、P09 低价值文档、微软 10-K 与星环年报的真实 SHA/时期/kind/locator；未验证项目列 `unknown/hold`，不能补造。保留独立盲留出集，不以已选 anchor 的重放证明召回率。
3. 所有后续 E2E 用唯一不存在的 `C:\cwt\<gate>-<nonce>`；先验证绝对路径在专用测试根内，再创建；测试前后比较**本次测试树全量**和**本次选用的生产原件**路径/大小/SHA，生产 catalog/control 用写入拦截及前后 metadata/操作日志证明零写，异常时再做内容核验，不在每个小测重哈希 23 GiB 原文或 2.8 GiB 数据库。测试造出的真实下载与 sidecar/derived 全部删除；子进程、WAL/锁和本次 run root 均须消失。旧测试根若已存在则停止核查，**不预先通配符清空**；正常 `finally` 与崩溃恢复只处理本次经确认的精确根。若 ACL 导致无法恢复，门保持红，不能改写“已清理”。

### G-0｜R4 A 增量裁定与 B.AR 多根读链（先于消费者默认切换）

1. 复用 A v0.4.2 的历史 A.DR/A.VR 与 A08 处置，只对当前 SourceRef/open 语义、真实 oracle 和变化字段做**一次**增量审查；历史 A.AR rejected 不能自动改写为 accepted。在同一 G-0 收据记录增量 A 的 `可实施 B / scoped hold` 结论、残留条目与适用范围；B.AR 由非 oracle 编写者独立复核真实字节和结果，不另开小审批门。现有 `document_id` 与版本绑定；逻辑文档/更正关系在找到权威更正证据前只记 `unknown`，不同 SHA 不按文件名合并。冻结四根/原生 sidecar、时点、locator、真实 429 页招股书与 8.16 MB 10-K 的资源上限。
2. 用 P06 真字节在四个隔离已配置根验证同 SHA 等价、首选故障回退、换 priority/搬位置、同尺寸篡改、读中替换、ACL/需水合/全失效；另用星环、微软、拓尔思的 company/dayu/Dropbox 原生布局走 adapter→`query_local`→verified `open_version`→locator。候选 query 零全文 I/O；最终交付前完整 SHA 验证；第五根只注册 adapter 不改消费者。旧精确版本引用能回放或具名 unavailable，不能用另一 SHA 偷换。真实云离线不可测的栏明确 hold，不用合成反例冒充。
3. 本门在同一结果包中签 scoped A 结论、CWP 通用 B.VR/B.AR 和资源/清理收据，**不签** FF/RF/StockWiki C.local；测试根、生产原件和 catalog 不变。G-0 未通过时 S2/FF/StockWiki 可继续隔离 TDD，但新消费者不得切默认路由。

### S1｜只完成真正的历史并线与脏树分类

1. RF `fcap` 已是远端 main 的祖先，不执行重复 merge；本地旧 main 从远端主线在**干净工作树**更新，不把根工作树的旧 §42 三文件或旧测试带入。对 RF 404 untracked 按 PWF/manifest 分组：已纳入 main 的 DEF-MSFT/T3、DEF-I00C 已签选件、81 个 RATCHET-FIX、`.tmp-*`、日志/备份分别对账；RATCHET 先保存为独立可审提交或明确归档收据，再清理重复/一次性文件。不可读目录只记录 hold，绝不凭沙箱“删除”恢复。RF 根 PWF 的新独特决策可整理成单独文档提交，控制字符和旧 §42 表述先清洗；未签 scratch 不进入主线。
2. CWP 命名产品分支均已是 `master` 祖先，仅维护本计划文档和后续新实现分支；本地主线 33 ahead 的提交与 live remote 再比较，普通快进推送，若远端变动则先做冲突审查，不强推。FF 本地 main 落后远端 39，基于远端主线新建集成支线，不在带密钥的根工作树做 `git add -A`。StockWiki/IQS 无 remote，仅制定本地 main 合并和可复现收据；不声称远端已并线。
3. ET 的未提交接口/测试与旧杂项分开；StockWiki W01 和 IQS 47 M/719 ?? 是活动工作，Q 线收口后才清理。任何“一律恢复主线”仅对**已核为旧实现、重复或一次性**的具体路径执行；先有 `path→用途→PWF 引用→处理` 清单，再恢复或删除，不能碰原文和引用中的证据。

### S2｜earnings-transcripts 自有接口入主线

1. 基于 ET 当前 4 个已提交的主线增量，先把 `transcript_api.py`、`transcript_tool.py`、legacy scraper 免翻译 flag、README/CLI 合同、两组测试和专项 PWF 整理成解释清楚的提交；原语言 TXT、精确 FY/Q、来源 URL/抓取时间、hash/size、无凭证/未找到/失败结果均有版本化测试。新 tool/api 本来只返回未翻译原文，**不要向它传不存在的 `translate=false`**；仅 legacy `scraper.py` 使用 `--no-translate`/`--disable-translation`，旧翻译能力仍是显式选择。
   ET 的 `canonical_content_sha256/content_bytes` 若指 provider 已抽取文本，必须与 CWP deterministic material 的 hash/字节数使用不同字段和 schema 语义；不得把两阶段字节身份硬认为相等。分别给出 provider 原始/抽取、CWP canonical raw、后续 L4 material 的可追溯 lineage 和畸形输入负例。
2. 先跑当前定向 31 项与受影响离线回归，再在干净 ET main 做快进/正常合并；对可推送远端只作非强制推送。旧 `.workbuddy-ai`/eval 单独分类，不随接口提交。没有真实 provider 权利时不把离线结果写成可联网抓取。

### S3｜filing-fetch SourceRef v2 producer 整合

1. 从 FF `origin/main` 建一条整合支线，把 reader 工作树的**最终净差异**逐文件移入，特别核实 `90771d8` 带入又被后续删除的 `source_reader_transport.py`/旧测试最终不在树中；用 CodeGraph/字面 import 扫描真实调用者。先写 v1 golden、v2 schema/字段白名单、exact/local、latest-as-of、gap、显式授权下载及回滚 RED 测试，再实现/整理。`fetch_filing.py` 大 diff 全读一次，抽掉重复路径/策略分支；v2 response envelope 明确版本，不能用旧 1.1 标签承载新语义。
2. v2 只传 SourceRef/metadata 与 CWP operation，不传 `canonical_path/source_bundle` 给上层；FF 不自己打开 CWP raw。真实下载只在授权的隔离 stub；默认 v1 兼容回归、22 项已通过的 FF→CWP 定向测试、`test_fetch_filing.py` 和未测最新/close-gap 路径均要绿。完成后先提交 FF source v2，再给 S4/S4b 使用同一个提交 SHA；不提前切技能默认路由。

### S4｜RF reader WIP 整合与三仓读取

1. 从 RF 真 `origin/main` 建洁净 reader 集成工作树，选择性纳入 `codex/revenue-source-reader` 的 3 M/7 ??，不导入 RF 根旧宽松 assurance；先写 `SourceRef→verified bytes→RevenueSourceRecord` 正反例、同 SHA 换根、错误 SHA/撤回/as-of、证据 hash 严格门。修正式 `tests/test_source_ref_v2_three_repo_e2e.py` 的硬编码 2026-09-27：fixture 的 capture 与 request as-of 在同一冻结测试时间线上，保持生产 as-of 拒绝规则，不能把生产校验放宽来让测试绿。
2. 在真正 RF 测试文件上跑 FF→CWP→RF 全链：已审真实来源正例产生 verified bytes 和 RF source record；无下载授权/撤回/同大小篡改/迁根负例，无下载或生产写，测试树恢复。此前只改 TEMP 副本 1 pass 是可行性，不作正式通过。再跑 RF v1 兼容及 §43 assurance 严格 hash 回归，确认 197 个现缺 hash 样本仍是红而非被错误放行。G-A 完成后，RF reader 合入 RF main；FF source v2 和 companion 作为同一 FF 集成分支上的两组独立提交，一次正常合入 FF main。
   RF 的 I-06 caller/claim 与 producer/consumer/event 持久生命周期是独立 RF 施工项；本 reader E2E 只证明来源准备，不冒充 RF 跨进程队列/forecast 全链验收。需要该能力的正式 RF 运行仍遵其自身 PWF 门。

### S4b｜FF companion 与 ET/CWP 串联

1. 在**同一 FF 集成主线上**移植 transcript-companion WIP，人工解决 `fetch_filing.py`/`filing_contracts.py` 的重叠改动；`_resolved_handle` 改用 CWP v2 SourceRef/verified reader，ET tool 和 CWP CLI 以显式配置/可安装入口调用。保留 v1/1.2 JSON/退出码，v1.3 将财报与 companion 各自状态、期次和授权范围分开；将普通“收集公司文档”的技能编排改为“期次已确认且授权范围覆盖时自动请求”，歧义期次具名跳过。**固定实际调用顺序**：caller 先通过 CWP discovery preflight → ET `--operation discover` 仅取 metadata 候选 → 选择唯一精确 FY/Q/venue/URL → caller 经 CWP candidate preflight 核 DownloadAuthorization、retain/derive 权利及截至时点 → ET `--operation fetch-candidate` 只取被授权绑定的候选 → CWP postfetch 再核 URL/MIME/bytes/hash/权利状态 → stdin importer canonical raw/sidecar 与英文 TXT locator。不能用 ET 旧单步接口跳过两个取前门，也不能只凭 importer 的事后校验宣称取前授权成立。
2. 现有 6 个 fake 单测保留；另写真实 FF CLI→真实 CWP preflight/import CLI→真实 ET tool 边界（仅 fake HTTP/provider）的隔离 E2E：成功、重复复用 0 下载、无授权 0 网络、权利状态变动 0 落盘、身份/期次漂移、坏 payload/超限、财报成功电话会失败、TXT 原语言与 locator 回放。测试根前后同一清单；生产 `provider_use_policy.json` 当前缺失，FMP 402，不以此 E2E 宣称实际付费 API 可用。G-A 收据包括 S4 与 S4b；FF companion 作为独立提交跟在 FF v2 提交后，整条 FF 集成分支过门才合 main，并更新安装的 filing-fetch skill 入口。

### S5｜StockWiki 基础来源 reader；Q 线并行

1. **CWP 先生产基础 SourceExport v2**：现行 `src/company_wiki/source_contract/source_export.py` 是 1.0.0；按 S0 夹具先写 v2 无路径、稳定 ID/locator/版本/时点/质量/撤回、旧引用映射和迁根负例，借 L2 verified reader 生成正式 golden，不把 selected bundle 混入基础 export。随后 StockWiki 从当前 `master@f5b8526` 建与 W01 脏树隔离的 reader 工作树；先查实际持久历史 export/引用，再决定 v1 兼容范围。新写 SourceExport v2 strict reader/CLI 和 StockWiki 自有 DTO 测试：仅凭 SourceRef 调 CWP verified open，确认 source/version/hash/locator/质量/撤回/as-of；不需要用户提供 `source-root`，同 SHA 换根时 export/evidence ID 与业务字段不变。真实 P06/星环/微软样本经过 StockWiki 新 CLI dry-run，不能以旧命令、空 reader 分支或 CWP fake consumer 代替。reader 与主树 W01 代码触点若相交，先以当前 W01 绿提交为基底再正常合并；若不相交，可分别提交、最后一次集成测试。无 remote 只可声明本地 `master` 完成。
2. 独立 Q 线：IQS 先按 C01 v2.1 完成 issuer/security/listing 合同和受影响回归/收据；修 StockWiki W01 现 10 项失败（绑定漂移、同 revision 覆写、verified 无 receipt、布尔/版本 coercion、SQLite 句柄），使 18 项及相关集成绿后提交；再按新合同恢复当前确实缺失的 W02/W03，历史八文件/59 pass 收据只作设计资料。最后 G2b 仅测 optional identity `mapped/unknown/ambiguous/null`，不读取原文/叙述包。Q 线不能拖住 S3/S4 或 StockWiki S5 基础 reader。
3. G-B **只签基础 reader 与隔离 dry-run**，reader 代码可合本地 `master` 但保持新路由 opt-in；StockWiki source-provider/full sync、撤回/supersession 批处理和 weekly 任务不因此默认开启。
4. **S5b（不另开审查门）**：StockWiki owner 在 G-B reader 合同上先冻结 full sync 的导入范围、旧版本 supersession、来源撤回、幂等及 weekly 触发状态；对当前树确实缺失的 provider/sync/weekly adapter 先写 RED（正常、重复、撤回、版本替换、坏 receipt、Tavily 不应被调用），再实现显式 v2 来源模式。保持默认 disabled/opt-in，在 G-D 用隔离目录跑完整 CLI 与 weekly 真入口、0 次非预期 Tavily 网络回退；G-D 通过才可切默认，不为每个 CLI 新设签收门。

### N1–N3｜company-wiki 原计划与抽象层会合

0. **N0：旧链退出前置**。先 TDD 建单一 normalized artifact reader：新工件核 source/version/parser/generator/实际 artifact SHA；旧行也必须核**实际旧工件 SHA**，并比对 frontmatter 的 source ID/SHA/parser name/version 与 DB/当前来源，DB 无 source SHA 的行不盲回填；同文档现代/legacy 双工件一次只选一件，选中工件被篡改即失败，不能再回退重付 LLM。三个旧消费者统一经此边界，逐一测试旧工件篡改拒绝。列旧扫描/摘要/章节入口的真实调用者，切换前以真实年报、半年报、季报、招股/再融资、IR、TXT 验 triage 召回/误跳过/空间；新 DAG 对入选与跳过件均零新增旧式整篇 `normalized.md`、章节副本和全量 `evidence_spans`。旧 `assess/distill/judgment/consolidate` 投资研究 writer 从可启动默认入口退出，旧 source_catalog Worker 与新 AUTO 不可双跑；不删只读 legacy 页面。**自动 review 正路径**：对将要外发的同一份已验输入先做 prompt-injection 扫描；无命中时自动生成绑定 source/input/rule hash 的 `not_detected` receipt，再调用摘要；命中、字节/规则漂移则阻断并交人审。不能因历史大多数来源没有预置 review receipt 就让正常文档永久 blocked；N1/N2 用真实招股/IR/TXT 无收据正例及注入/篡改/规则漂移负例核扫描与 LLM 次数。此机制保留内容完整性，不重引 public/private 分类。CI 的 `|| true` 假绿用失败夹具证明退出码传播后删掉；StockWiki v2 激活时将旧 Tavily 隐式回退改为显式来源模式并测网络次数。旧配置键按真实读取者/默认行为映射后删，保留一套暂停/并发/费用/重试旋钮。R4 S10 可选依赖拆分先量收益，不作为主线门。
1. **N1：E5 + W5**。E4 handler 已准备好 effect，但持久 bundle/projector/reader 未实现。先写 object 写半、rename 后、catalog insert 后、ACK 前、generation/来源/hash/locator 漂移的 RED；实现 content-addressed bundle、唯一 catalog writer、verified narrative reader、稳定 schema/coverage/skip。12 件探索材料与盲留出集区分召回和重放；一般格式化低价值文档仅存小 skip receipt，半年报/季报/招股/定增可转债/IR/TXT 做分类型叙述选择、原语言摘要，不重建全量 PDF→MD→全段切片。
2. **N2：E6/E7/E-B**。在 `C:\cwt\m3-e2e-<nonce>` 用 P01 年报、P04 429 页招股书、P07 IR、T01 TXT 四份真实复制原文：临时 catalog→DAG→P1/P2 worker→选择→fake/replay 摘要→locator 回读→outbox/projector→reader→同请求重放 0 重复。至少两文档 P2 执行区间重叠、同 work_key visible<=1；R01–R10 各一确定性注入，关键进程竞态三次，R11 一次 100-job 中断重启；P1/P2/P4 交错 benchmark 按原 E7 阈值选默认，模型槽始终为 1。最终 bundle/skip/临时峰值和同卷字节按 E7 门验；结束测试根 0、原 raw SHA 不变，生产 Worker 仍 paused。E-B 只做**一次**大审查，不逐 helper 签收。
3. **N3：G2a**。以正式持久 selected bundle 通过 CWP pathless reader、RF/StockWiki 各自真实消费入口查询与 locator 回读；覆盖撤回/as-of、partial/needs_review、证据版本、跨根不变及无隐式下载。若 RF/StockWiki 尚无叙述消费入口，该栏保持 hold，不能用 CWP 内部调用冒充。G2a 与 Q 线的 G2b 分开签收。N1 可与 S3/S5 并行开发，N3 必须等 S4/S5 基础读验收和 N2 的真实包。

### D｜派生降容与生产发布

1. 先重新量测当前同卷各类字节；历史 46.266 GiB 旧 SQLite 主库已于 F0–F5 退役，实际净释放 **37.630 GiB**，不能再写成待完成收益。最近 D0 的 `.source_catalog/ + source_manifests/ + companies/` 逻辑长度 **39.744 GiB**，含约 23 GiB raw、压缩回滚包、归档和派生；这些不等于可删量。新持久选中对象目标 E6 cohort `<= raw 的 3%`，单 selection `<=1 MiB`、摘要 `<=64 KiB`、bundle `<=1.25 MiB`、skip `<=16 KiB`；以真实 cohort 和月增长测量，不用短合成文档比率。
2. G-D 只为**可从原件重建且无消费者引用**的旧 normalized/full spans/cache/index、过期 staging/attempt 派生建立精确 manifest；先在隔离副本删→重建→比 source/evidence/export/query 与净字节，再按批次生产清理。原件/manifest/SHA 历史、尚未完成的 RF RATCHET/其他 PWF 证据、唯一 raw 全部排除。备份/退休归档单独证明来源历史与回滚期后再决定，不能为了目标数字提前删。清理器只对已冻结的精确文件/对象及记录执行、有 intent/receipt 与重启对账；共享 SQLite 如需缩容按整库影子切换协议，不逐来源误算释放。
3. 默认路由切换按已通过的 G-A/G-B/G-C **具体能力范围**分别发布，逐项保留失败回退开关；StockWiki 的 G-B 只可使 v2 reader/CLI opt-in 可用，source-provider/full sync 默认启用必须等本节 G-D 的真实批处理/weekly/撤回/显式来源模式验收。生产 Worker 需 E-B 与最小受控 canary 再从 paused 改为小并发，监控 job 完成、重复、429、锁等待、RSS、派生净增长；异常立即暂停 gate、由持久 attempt/outbox 恢复，不改原件。G-D 收据写明确认实际净释放与未覆盖范围。只有所有目标线完成才标整体计划 complete。

## 5. 集中审查/测试矩阵：TDD 约束实现，少开大门

| 大门 | 进入条件 | 一次性真实验收 | 阻断与回退 |
|---|---|---|---|
| **G-0：CWP 通用读链** | S0 真实 oracle/合同冻结；内部 M1 收据已核 | 四隔离根及原生 company/dayu/Dropbox 字节、版本/字段/locator、旧引用、429 页资源与测试树恢复 | 未验字节、元数据随 root 改变、旧 ID 丢失或树未恢复则不签 B.AR；消费者只可保持 opt-in。 |
| **G-A：FF/ET/CWP/RF** | G-0 已签；S2、S3、S4、S4b 各自单元/合同绿；FF v1 golden、RF §43 不退化 | 正式 FF→CWP→RF 原路径及 CWP ensure/close-gap CLI，FF→ET→CWP 原入口；隔离 provider stub 测 latest 已有、refresh gap、as-of 后版本排除、无授权 0 下载、授权一次落一份且重试 0 下载、stdout/stderr 无 raw path；最终 RF 验同尺寸篡改/撤回；OS I/O 证明 FF 候选零原文读取、RF 最终一次完整验真；真实样本与前后测试树/原件 SHA 相同 | 任一跨仓 schema/期次/来源错误或清理失败，不切默认；只回退该新路由，旧 v1 保留。 |
| **G-B：StockWiki C.local；Q 线另收据** | G-0 已签；S5 reader 已实现；IQS/W01 若并入同 main 已各自绿 | StockWiki 新 CLI 实读 CWP verified bytes，迁根/篡改/撤回/旧引用；Q 线独立 C01→W01→W02/W03→G2b | reader 空分支、仅旧命令或 8/10 红测不能放行；G-B 仅 opt-in 基础读，full sync 留 G-D；Q 线 hold 不阻 RF/FF 基础读。 |
| **G-C：叙述与 Worker** | N1 形成持久包；基础 reader 已验 | N2 四真实文档、R01–R11、P1/P2/P4、预算；N3 RF/StockWiki 真消费与 locator；测试根恢复 | 任一原文写入、重复 visible、未回源、空间超限即继续 paused；N3 消费缺席则只签 E-B、不签 G2a。 |
| **G-D：空间与发布** | **本批拟清派生**的所有消费者已切新合同；G-A/B/C 对该批对象已验；StockWiki G-B reader 已签，S5b sync 仍待本门实测 | scratch 删除重建、精确生产批次 intent/receipt、同卷前后净字节、原件/hash/manifest 不变、受控 canary 恢复；StockWiki full sync 的撤回/版本替换、weekly/CLI、显式来源与零隐式 Tavily | 未证明可重建/仍被引用/净字节无法解释即不删；StockWiki full sync 失败只保持 opt-in reader，**无关派生批次可独立 scoped 签收**；异常暂停新路由/Worker 并按收据回滚派生。 |

每个小步骤执行最小 RED→GREEN 单元/集成、Ruff/类型/diff check；仅大门运行完整真实 E2E 与独立审查。收据统一记录：仓库 HEAD/dirty，合同版本与样本 SHA，命令/退出码/测试数，前后测试树及原件清单，资源/空间指标，阻断与受限结论，reviewer/日期。不能以 monkeypatch producer+consumer 的假整合、历史绿灯或 TEMP 修正副本替代正式门。

**已存在的可执行测试入口（从各仓根目录运行；`--basetemp` 使用 S0 创建的唯一短路径，外层 wrapper 做精确清理）：**

| 施工线 | 先跑的当前文件 | 大门另需新增/复跑 |
|---|---|---|
| CWP G-0 | `python -m pytest -q tests/contract/test_source_operation_v2.py tests/contract/test_source_version_reader_cli.py` | R4 L01–L12 的真实四根和原生 company/dayu/Dropbox 样本，429 页资源门；内部单测绿不能代 B.AR。 |
| ET S2 | `python -m pytest -q tests/test_transcript_api.py tests/test_translation_controls.py` | 精确 FY/Q 与原语言 TXT 的真实 ET tool CLI、两级 hash/bytes lineage；需凭证/联网的旧项单列跳过。 |
| FF S3 | `python -m pytest -q tests/test_source_ref_v2.py tests/test_source_ref_v2_db_query.py tests/test_fetch_filing.py` | 显式提供已记录的 `CWP_V2_CODE_ROOT`/`FILING_FETCH_V2_WIKI_SRC` 指向本次固定 CWP checkout；latest/close-gap 与 v1 golden 正式 E2E 零跳过。 |
| RF S4 | `python -m pytest -q tests/test_company_wiki_source_reader_v2.py tests/test_source_preparation_v2_cross_repo.py tests/test_source_ref_v2_three_repo_e2e.py` | 修**原测试文件**日期后，真实 FF/CWP/RF + §43 严格 assurance；已审来源正例不能只靠 fake ref。 |
| FF companion S4b | `python -m pytest -q tests/test_transcript_companion.py` | 当前 6 项仅 fake CWP；补真正 FF CLI/CWP import/ET tool 三边界 E2E。 |
| StockWiki S5/Q2 | `python -m pytest -q tests/test_quick_scan_store.py` | 当前 8 pass/10 fail 先修 W01；v2 reader/CLI 测试文件尚不存在，TDD 先写，再做 P06 真字节 dry-run。 |

以上命令只作实施者的**定位入口**，不替代各仓按当前版本补测的直接依赖。先在各自仓根用 `rg --files tests` 核文件仍存在，再运行；测试中不可复用生产密钥、联网 provider 或生产 catalog，失败时保留精确日志/收据并恢复本次测试根。

## 6. 并主线的机械规则与冲突收敛

1. 每仓先提交**有边界的实现**再合并：ET 接口；FF v2；RF reader；FF companion；StockWiki reader；IQS C01 与 StockWiki W01/W02/W03；CWP E5–E7/G2a；最后清理。先比较 live remote 与工作树 SHA；同仓重叠改动只在一条集成分支解决，不将两个脏目录互相 `checkout`。提交说明写合同版本、测试收据位置和未覆盖范围。密钥、raw、巨大测试副本、过期 scratch 不 stage。
2. 合并采用常规快进或有记录的正常 merge；拒绝 force push。RF/FF 本地旧 main 先从真远端主线在干净工作树更新；CWP master 已含历史命名支线，只提交新计划/实现，发布前再次比较远端；ET 在本地 main 与 feature 同 HEAD 的基础上提交，再更新远端。StockWiki/IQS 无 remote，只能在各自本地 `master` 签收。遇远端同时推进，停该仓合并、只重跑受影响合同与门，不重做全部历史试验。
3. 脏树清理由独立 `path→来源提交/PWF 卡→当前调用者/引用→保留提交/历史归档/精确清理` 清单执行；保留 RF RATCHET 与 IQS 活动文档，淘汰已被 main 覆盖的旧 §42 代码和已证明一次性探针。ACL/长路径不可读者留 hold；不使用目录名推断用途，不做整仓 `clean -fdx`、通配符删或对原件路径的 reset。清理后再对各工作树做 Git 状态审计，标明预期本地密钥例外。

## 7. 已知风险与分支裁决

- **SourceRef v2 response 仍写 1.1**：S3 修版本并用 golden 保证 v1 默认；未完成前 FF v2 只能 opt-in 试验。
- **RF 原三仓测试日期过期**：修 fixture 的冻结时钟，不放宽生产 as-of；§43 严格 hash 是唯一有效裁决。
- **StockWiki 旧代码/历史收据消失**：按当前树实现 strict v2，兼容范围只由真实旧引用决定；QuickScanStore 10 fail 先修再用新回执。
- **ET/FF companion 仅局部 fake 测过**：G-A 必须经过真实编排、CWP importer/writer 和 ET 工具边界；目前无 provider policy/FMP 402 不宣称生产联网可用。
- **空间误算与重复检查**：旧 46 GiB 已退役；只按同卷实际文件变化算收益。单元/集成持续 TDD，大节点一次集中 E2E；失败只复测受影响链。
- **测试根 ACL/沙箱幻象**：凡 test root 无法删除或 Git 状态只有受限视角，收据写 hold；先换可访问的短路径和正常权限核验，不修改项目权限规则来制造绿灯。

## 8. 本计划之后的第一批具体动作

先完成 S0 的 live refs/工作树与合同样本冻结，并将 ET、FF v2、RF reader、StockWiki reader、IQS C01/W01 分到各自隔离施工线；FF v2→RF reader→FF companion 的生产合同顺序固定。随后按 G-A、G-B、G-C、G-D 放行，缺失的测试或来源只把该栏保持 hold，不阻独立线推进。每次节点结束更新同目录 `task_plan.md`、`findings.md`、`progress.md`；不要在其他仓的活动 PWF 上覆盖内容。
