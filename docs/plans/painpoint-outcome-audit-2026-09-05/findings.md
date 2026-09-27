# 审计发现

## 2026-09-27：全仓结构简化审查与实测反例

- CodeGraph 当前索引 559 个 Python 文件、`source_catalog` 83 个；审查覆盖结构、主要入口与热点实现，未逐行签收全部文件。`source_catalog/worker.py:441–696` 仍按周期串行调用 scan/normalize/sections/LLM/export，`automation/worker.py:56–100,286` 则已有独立 job lease/reap，两套状态机制并存。`scripts/scheduler.py:167–177,453` 的 legacy 默认流程仍列投资评估/判断，与当前 AGENTS 职责边界不合；需核真实启动入口后退役，不能仅删文件。
- `normalizer.py:1317–1341,1392` 可将 PDF 整篇转 Markdown；`section_extractor.py:294–297,370–398` 再写各章节正文和索引；`summarizer.py:163–225` 与 `llm_summarizer.py:411–471` 又分别读全文、写摘要。`narrative_evidence.py:1517` 已有精选逻辑，但主要由试点/检索入口调用，尚未取代生产整篇链。空间收益须先量 raw/MD/章节/摘要/索引/重复的真实字节占比。
- 隔离 CWP 反例：LLM 入口仅凭源 SHA 绑定 review receipt，规范化文件被替换后仍会发送未审文本；新增篡改测试先红后绿，发送前现核实际 normalized SHA。旧 active 根位置曾否决有当前根同 SHA 副本；新增根迁移反例先红后绿。`config_doctor.py` 的两个目录名/Dropbox 路径硬编码已 TDD 泛化，21 项相关测试通过。
- **统一工件读取器的旧数据兼容风险**：对现行库只读 SQL，`normalized` 共 4,984 行，其中 **4,797 行的 DB `source_sha256` 为空**；仅 3,507 行由 `source_catalog_normalizer` 命名，其余有 pdf/page-aware、docling、HTML、Office 等旧解析器名称。按各生成器抽一件现存文件核对，大多实际工件 SHA 与记录一致且 frontmatter 含当前 source ID/SHA；`plain_text` 与 `pymupdf_page_text` 的所抽样本实际 SHA 不一致，应拒绝，不能由此推断各生成器总体坏件比例。若新 helper 只收现代 DB lineage，旧文档会大面积假失败。S2 改为一个受控 legacy fallback：工件本身 digest 必须通过，再从 frontmatter 验来源与 parser；现代行继续严格 DB 绑定。不为迁就旧资料跳过工件实际 SHA。
- 只读查询进一步核实旧工件重复：`normalized` 4,984 行/3,507 文档，completed/partial 4,969 行/3,500 文档；其中 1,469 个文档各有两条可读工件。当前 22 个有 review 收据的文档没有双行，因而现有 LLM 测试没暴露，但 S7 自动扫描扩大覆盖后，若摘要查询不先按 source/version 选一条，会让同文档同批次重复调用 LLM。S2 新增“modern 优先、否则 legacy、同文档一次加工”的 TDD；坏的首选不能在同批次隐式退到另一工件并外发。
- 隔离 CWP `SourceExportBundleV2.build` 对纯 PDF manifest 曾先读入并保留整份原文。16 MiB PDF 实测 tracemalloc 峰值 33,598,348 B；共享规则的 streaming `verify_version` 后为 2,144,131 B，相关 76 passed/1 skipped。结论只覆盖此操作与该样本，不能外推到 46 GB 总体或生产 Worker 吞吐。
- 空间基线复核：[F0–F5 收据](../narrative-evidence-pilot-2026-09-26/stepwise_space_budget.md)已记录旧 46.266 GiB 主库删除及同卷净释放 37.630 GiB；[D0 盘点](../narrative-evidence-pilot-2026-09-26/d0_inventory_receipt_2026-09-27.md)记录剩余三自有目录 39.744 GiB、完整备份 5.773 GiB、退休归档 4.850 GiB、raw 23.460 GiB、derived 2.632 GiB。本轮只读 stat 现行 DB 为 3,055,800,320 B；并未重算整个目录。52 组同 SHA 本地双路径的理论重复差额 98,845,393 B 是候选上限，不是已核准可删量。
- 旧 46.266 GiB 库的主要成因是全量 `evidence_spans` 行与索引膨胀，而不只是整篇 Markdown 重复：[空间调查](../narrative-evidence-pilot-2026-09-26/space_reduction_upgrade.md)记录约 2720 万旧 span；1000 条抽样里 820 条为 table cell、496 条 `raw_text` 为空，平均 `span_json` 812.6 B。第二组 1200 条样本中，重复于关系列的 JSON 字段及正文复制有可复核分项，但只代表样本；尚无全库各表/索引的精确体积分解。当前 active 库仍有 1,490,530 span，所以阻止新 DAG 继续生成全量旧式 span 比删除 2.632 GiB 的 derived 文件更先要验证。
- D0 在 `future_lake` 登记一件 545 B 原文，因此旧实施卡“只有 README”的说法已过时。该一件尚不足证明原生第四根的文档/sidecar 适配；保留 `pending/limited_scope`，不夸大覆盖。最小目标结构为唯一来源读取、唯一工件读取、选择性叙述 DAG、唯一持久 Worker 队列和统一处置 ledger，见更新后的实施卡。
- 对当前生产 catalog 的 `immutable=1` 只读查询：共有 23,530 个 document，3,500 个有 completed/partial normalized 工件的不同文档；只有 22 个 document 有 `prompt_injection_review` 收据，且这 22 个都在已规范化集。旧库另有 2,734 件 `source_catalog_llm_summary` completed 产物，不能据此认定新入队也能通过当前收据门。需把干净输入的确定性扫描与 source/实际输入字节绑定写收据自动化，只对命中和错误待人工；否则新 Worker 并发也只会更快地发现绝大部分文档不合格。
- 三仓隔离真实 E2E 的首轮版本由 FF legacy `resolve` 和 RF final open 各读一次原文。后续显式 v2 opt-in 已改由 CWP `source_query_cli` 查 DB 候选，FF↔CWP 真实集成 11/11 绿，三仓真实 E2E 也已绿，零下载；同尺寸篡改文件时 DB 候选仍返回、RF 最终 open 拒绝，证明候选查询没有重验全文、最终验真没有被省略。此结果不覆盖旧默认入口或 StockWiki 正式切换，尚无 OS 级精确文件打开计数。`retrieved_at` 的 FF 位置观察与 CWP 共享版本记录不是同一时间事实；RF 只硬比稳定身份字段，两个观测保留 trace。
- 新读链曾有审查状态 TOCTOU：DB-only candidate 的 `capture_ready` 由查询时的 `prompt_injection_review` 计算，query 后撤回收据时 RF 可沿用旧 `not_detected`。撤回红测复现后，隔离 CWP 在原文字节验真后读取当时可见 review 并在同次回执带 source/evidence/rule hash；隔离 RF 只接受最终回执中与 source SHA 绑定的 `not_detected`。真实三仓撤回 E2E 已绿。该回执是读取时点的观测，不是长期数据库锁；默认/StockWiki 路由仍未切换。
- FF→CWP 请求模式复核发现：exact 无下载已走 DB-only v2 query；`latest_as_of` 在 CWP 侧调用 `SourceAcquisitionService.ensure` 以取得 provider freshness/gap，显式授权下载走 `ensure/close-gap`。这两种请求不能用本地 query 代替，但其 v1 subprocess JSON 仍把 `canonical_path/source_bundle` 送给 FF，FF 仅在构造最终 handle 时删去字段。跨进程仍有路径耦合；已在 R4 明确下一切片为 CWP-owned pathless ensure/close-gap 输出和对应真实 E2E，当前不能记抽象验收通过。
- 为避免新增回执字段被旧客户端静默误读，最终二进制读取回执采用独立 schema `2.1`，而 `SourceRef` 与 query candidate 保持 `2.0`；RF transport 与 record builder 都拒绝 `2.0` 的成功 read receipt。版本边界负例和三仓 E2E 已通过；这是隔离契约证据，尚不能签收生产默认路由。
- CI workflow 原文核实三版本重复 unit/contract/full coverage/6 组 canary，且 `--cov ... || true`、CLI smoke `collect_news.py --help || true` 可吞失败；`pyproject.toml` 的 extras 与 `requirements.txt`/CI 全量安装不匹配。StockWiki `pipeline_source_provider.py` 当前 disabled/not_configured 时会转排 Tavily，现行配置明确 disabled 是 legacy 模式；将来 v2 激活后需显式模式，防配置漂移触发双采集/费用。S8–S10 的实施与验收已写入 R4 卡，依赖与来源模式均不在当前 C.local 之前抢改。
- S1–S10 的落地行动、层级责任、TDD 与大节点 E2E 已写入 [R4 实施卡](r4-data-lake-priority-rollout-2026-09-27.md#全仓结构审查后的进一步简化2026-09-27-增量)。RF/StockWiki 正式合同、生产进程清单、完整空间分类和多类文档召回仍待验证。

## 2026-09-27 实时仓库状态核对：技术前置改为冻结候选

- 只读 `git ls-remote` 核 company-wiki 远端仅 `master=f39bd5a64224cd0c7aa098f23f64bf3811fa8939`、`fcap=8665c8c47c020cde7dcf683ee8e6389ead77f282`，远端 HEAD 为 master。本地主工作树在 `fcap=dbe474504a6187e22c37918743d17fe59c85a0a8`，是远端 master 的后代并多 4 个提交、比远端 fcap 多 8 个；本地 `master=109a1a6` 陈旧，不能当远端状态。主工作树有 24 个 tracked 修改和 16 个 untracked 条目；其中包括早已在飞的产品代码和本轮规划文件，未改/清理他人的修改。
- revenue-forecast 远端 `main=fcap=ee0a82bfd1eec935cf4e567eb42f0ef79efa0226`，其 Round 122 进度也记此前 `fcap → main`；用户澄清暂缓并入的是**本地未提交后续工作**。远端 SHA 只代表已推送基线，不能替后续候选作版本身份。后续跨仓 RF 消费者 E2E 须由 RF owner 固定包含运行依赖的不可变工作树快照或支线提交，不要求合并 main；CWP 产品代码暂停仍另行有效。
- 初次沙箱内 `git ls-remote` 因 443 连接限制失败，使用只读、经审批的同一查询成功；全程未 fetch/pull/merge/push、切分支或修改 Git refs。以上是核对时刻快照，实施前重锁。

## 2026-09-27 补充：路径抽象必须跨仓闭环

- StockWiki 当前 v1 manifest 强制 `original_path`，该字段参与 `export_id` 哈希，v1 sync 又按 `source_root/original_path` 打开原文；RF 与 filing-fetch 也读取 CWP 的 `canonical_path`。因此 CWP 内部副本回退即使修好，跨仓身份和使用方式仍依赖目录。具体版本化合同与迁移路线见 [R4 优先实施卡](r4-data-lake-priority-rollout-2026-09-27.md)；旧 v1 历史引用须保持可读，不能直接删字段或把 full sync 视为本地读验收。
- 真正的验收需两个独立问题：同一真实字节跨四个隔离根的位置等价；各原生根的真实目录/sidecar adapter 覆盖。catalog 所载完整 SHA 尚需对隔离副本重算。`future_lake` 无原生样本，三角防务 2023 年报原版/更正版缺权威修订链，分别记有限覆盖/hold；不使用改名副本或篡改夹具冒充真实事实。
- 本轮只读代码与 catalog/stat、修订计划；未运行新的产品端到端测试，未实施 CWP/StockWiki/RF/filing-fetch 代码改动。下方历史发现按其原时间保留。

> 2026-09-09 最新状态请先读 [current-delta-2026-09-09.md](current-delta-2026-09-09.md)：worker v5 独立轨道全部完成（冻结 51 项 + 三轴审查 accepted）、FC-705 门仍 false（差一晚）、R9 批 3 范围失真（仅 `artifact_backfill.py` 零生产读者）。下方 9/5～9/7 观测保留为当时快照，不重写、不当新 HEAD 全量验收。

> 2026-09-07最新状态请先读current-delta-2026-09-07.md：其他任务已推进R9删除/daily修复并产生失败run；下方9/5～9/6观测不重写，也不当新HEAD全量验收。同步23活动文档及执行手册R3已经独立审查；产品整改仍未实施于本任务。

> 按时间保留的发现日志；最终范围与结论见README及各分报告。下方“初步/待验证”是发现当时状态，后续条目与分报告提供核验结果。新审计不修改任何原计划。

## F009：R9 批 3 的"无生产读者"口径已失真（2026-09-09 深夜实测）

- 证据（逐符号 grep，wiki 源码）：`backfill_v2` ← `dropbox_governance.py:22`（生产治理链导入 `classify_bucket`）；`portfolio_promoter` ← `cli.py:27`（CLI 面）；`_scan_root_v1` ← `scanner.py:1401`（生产分派）+ `shadow_parity.py:94`/`trace_parity.py:206`（对账）；`legacy_bridge_enabled` ← `resolver.py:322`、`architecture_gate.py:127/139/278`。
- 🔴 **2026-09-10 更正（本条部分作废）**：当时写"仅 `artifact_backfill.py` 无 src/scripts 生产导入 → 零生产读者"是**基于过窄的 grep**，**已证伪**。完整扫描显示：① 该模块自带**运维 CLI**（`artifact_backfill.py:305 main()` → `python -m …artifact_backfill --catalog … --mode dry-run|apply`），`assurance/fc/FC-901/11_implementer_receipt.json` 明确记载「run_artifact_backfill 的 production caller 就是**同模块的 CLI main()**」；② 被 3 个契约测试导入（`test_zr305_legacy_migration.py`、`test_zr1005_artifact_backfill.py`、`test_source_catalog_artifact_backfill.py`）；③ **FC-906 工作单元卡把它列为 Forbidden files**（`assurance/fc/FC-906/00_wu_card_a.md:24`「`artifact_backfill.py`（FC-901 工具，**不改**）」）；④ 冻结 v5 基线 `baseline/plan/test_acceptance_plan.md` 有 ZR1005-C1~C4 验收行；⑤ ratchet 登记 `37`/`79`。→ **它不构成"最小死代码步"**：owner 2026-09-10 的"执行 3a"指令因前提证伪而暂停，**未删除任何文件**。
- 推理：09-02 授权申请把批 3 描述为"无生产读者 backfill/promoter"，若照此机械删除会破坏生产治理/CLI/对账/回滚路径。批 3 的实质是"退役 v1 扫描路径与迁移期机制"的架构清理，必须先有替代路径与回滚，再谈删除。
- 影响：R9 批 3 需**技术门（FC-705）+ owner 政策门（2026-09-06 延后至 v2 迁移稳定）**双重满足；拆分后 **3a 已由 owner 于 2026-09-10 正式撤销**（不是暂停），只剩 3b（`_scan_root_v1`+parity）与 3c（bridge+flags+resolver），二者均需先给出替代路径与回滚，**当前没有任何小批满足机械删除条件**。清单见 revenue 侧 `r9_batch3_checklist.md`。
- 边界：本轮只做只读 grep 与文档记录，未删除、未改产品代码。

## F008：worker v5 的"完成"只覆盖规划文档完整性（2026-09-09）

- 证据：v5 冻结集 51 项 + `--verify-manifest` 9188 + `--self-test` 17/32+4+3 全拒 + 三轴独立审查 accepted（见同仓 v5 目录）。
- 推理：冻结证明的是"规划文档完整、可复现、未被静默改写"，**不证明** worker 实现、配置、数据库、任务健康，也不授权恢复 worker。
- 影响：R4 中 worker 相关 WP 可把 v5 冻结作为**版本合同输入**，但 H01 风险、隔离验证、持久领取/失败恢复仍必须各自取证。

## F001：文档同步并不等于原始痛点消除

- 证据：`company-wiki/PLANNING_STATUS.md` 同时记载 117/117 accepted 和 GP-006/008/010 未闭环；原始目标文档要求实际多根消费、实际调度与观察窗口等。
- 推理：机器账本的 accepted 只能证明账本状态，不能自动证明原始用户结果。需要独立检查实现、真实接线、结果及签署绑定。
- 入口页仍写 GP-010 sections=0 和“尚未宣称全量审计完成”；上次审计记录已有更新线索，本次须用实际产物确认，不能直接沿用旧结论。
- 初步判定：全局完成主张不成立；具体功能逐项待核。

## 原始问题分类（不可降级的验收来源）

P01 防假绿/真实完成证明；P02 无副作用只读/锁与失败恢复；P03 全部授权根消费与身份；P04 最新版本与最少下载；P05 可信加工复用/最小失效/实际需求；P06 安全审查与消费闭环；P07 研报多实体/页表章节事实；P08 收入合约与事务发布；P09 矿山颗粒度与合并口径；P10 实际 E2E/动态监测/Windows；P11 技术债与旧实现退出。

来源：`revenue-forecast/audit_review/2026-08-13_three_repo_completion_rebaseline_plan/project_goal_and_pain_points.md`。

## 待验证线索（不是本轮确认结果）

上次文档审计发现 daily CLI 参数不匹配、Windows CI 非阻断且用 fixtures、broker 实际处理超出七份 cohort、收据重签与 reviewer SHA 不匹配、自然观察周期不足。必须检查当前代码和当前证据后给出最终状态。

## F002：场景验收仍按 status 汇总，而非 required tier × triplet × 实际证据

- 当前源码：`revenue-forecast/assurance/unified_completion/uc/scenarios.py::closure_report` 仅检查 status；`verify` 只检查冻结来源hash、计数和ID集合，不校验执行证据。`uc/closure.py::closure_report` 对场景也只检查 status。
- 原验收：CA-105 明确每个 scenario × required tier × triplet 都需要真实结果，缺一项 closure 红；CA-107 要求缺收据、陈旧组合和自然窗口均阻断。
- 反证：当前汇总函数没有读取 evidence_path、tier执行结果、当前triplet或freshness；因此通过该汇总不能证明原始验收。待隔离负例确认，并继续检查更外层是否有补偿门。

## F003：运行与源码已并发更新，不能复述旧 GP-008 快照

- 22:18 左右只读基线：wiki HEAD `853dca2d30bc2b85dc95e3117a6afc3b448daec7`，filing `89c8bdb2cfba4d88720d005d0558f422957e8ade`，revenue `2ff20d9b410d3498181f7258a23ed9625caab826`。
- wiki section_extractor.py 与其contract test已有未提交修改；这些不是本审计所写。
- daily_manifest 已更新到 `20260905T194055Z`、period=2、ok=true；旧入口页的run1已失效。新报告绑定 revenue `2cbd585...` 而不是观测HEAD；不能用于新HEAD的严格闭环。
- 报告中的 roots_fingerprint 实为三根计数，latency 名为 resolve_sample_sec；后续核查是否真实resolver/全路径hash。报告的 ok 不自动证明原 CA-202 目标。

## F004：隔离反例证明 freshness/weekly/scenario 门不足

- 证据：本目录 `audit_probe.py` 与 `probe-results.json`；2026-09-06执行exit=0。只编译预审过的具名纯函数，不导入生产入口、不运行DB/调度/网络。
- 2099年的ledger被 `freshness_status` 判fresh；缺evidence_path/fixture_hash的T2场景被 `scenarios.closure_report` 判closure_ready=true。
- `weekly_t3_schedule._suite_outcome` 对 `1 passed, 2 skipped` 和空stdout且rc=0均判ok；不符合全required markets不得skip验收。
- `task_status` 把AccessDenied判为missing，丢失部署未知和未注册的区别。
- 新daily源码已使用 `run-daily`；原参数错误是历史问题，当前缺口转为部署Action/自然触发来源不可证、报告质量及release门不足。

## F005：原始任务被缩减为机制验收，形成accepted循环证明

详见assurance-audit.md A01及25项CA表。CA206真实自然周期、CA301干净三仓独立重放、CA302真实三公司、CA304真实删除等，在11receipt把实际动作移到部署却标accepted；CA305再验证accepted/文件存在/40字符即可“证明”六问题。不能解释成只等时间即可完成。

## F006：当前业务仍有可复现实质错误

filing-audit.md记录policy旁路、global canonical遮蔽eligible、修订ID词序错误、多gap只做首项、deadline10秒可耗14秒、失败后下载计数丢失；revenue-audit.md记录矿山单位/TC-RC/持股时间与发布事务缺口；wiki-audit.md记录内存DemandQueue和producer journal/安全门生产接线不足。每条以分报告具体代码与安全探针为准，不据统一accepted推翻反证。

## F007：空间回收门会把未证实归档的retired证据纳入自动删除范围

详见historical-projects-audit.md H01。旧目录日期达标即due，DELETE覆盖所有retired，worker.py周期直接apply=True；archive同日覆盖且只count对账。未证明已发生生产误删，但恢复worker之前必须修复此门并独立审查，不能等日历自然放行。当前paused不等于代码已安全。

## F008：本轮静态证据覆盖量与局限

evidence-inventory.json记录117个单元、351个主要receipt元数据与hash（长说明明确为excerpt）；197场景全passed但fixture_hash与oracle均197个缺失。44个冻结plan input本次全部hash+size匹配，这证明历史输入未坏，不证明履约。

## F009：独立计划审查防止执行依赖歧义

remediation-plan-independent-review.md对R1提出两项P1和四类P2：裸工作包依赖可能造成能力验收互等、WP12真实运行安全前置不足，以及授权subtype/稳定归档快照/显式RED/恢复对象边界。R2第5–6节已逐项修订，获独立accepted_for_planning_delta；不得把计划审查通过等同产品验收或实施批准。15个工作包每个G0–G5均安排独立review（此为R2历史记录，R4已取代其编排）。

## F011：六类痛点实施粒度补充（2026-09-08，本轮）

用户要求细化修复计划实施步骤，范围仍是文档。FC903已有旧remediation-plan.md WP00第6条的原字节查找/unknown/新revision方案，应显式接入R4，而非称无计划。117项需按原注册条款及各审计表逐行分派实际验收，不能仅有WP级归属。H01硬禁用只控制运行风险、不关闭归档恢复完整目标；R4的隔离VR与真实AR仍分层，旧95门不重新执行。已安排协作者单独编写117映射，主agent负责实施细化与共享规划文件。

本轮按技能显式选择既有审计目录作PWF_PLAN_ROOT，resolver未返回命名计划，使用该目录既有三文件，不创建竞争root计划；子进程环境不冒称修改宿主hook pin。git diff无tracked变化，status显示本审计目录及既有临时文件等untracked并有全局ignore/.pytest_cache权限警告，保持它们不动。本轮不启用技能gated/attestation，也不读取本地会话历史。

## F010：R4减法与独立审查纠偏（2026-09-08）

R4调整的是活动编排而非原始目标：A合同、B位置透明、C瘦消费者/唯一生产入口、D安全运维，收入M独立。保留117项/GP/历史要求和旧反例；旧95门及其verifier只作R3历史，不再驱动R4。详细44个一级步骤和36组测试（12+8+8+8）见simplified-execution-plan.md及simplified-test-matrix.md，组内继续展开原领域步骤与反例，不是把所有断言减到36个。初稿导航误加为40，已由逐ID结构核对纠正，未删任何测试。

独立agent发现草稿“VR所有required”可能把尚待联网/自然AR的结果反向作为VR准入，另发现C本地签收误含worker、broker九源只挂M。已分隔离VR/真实AR层，C本地/加工/provider同包分栏，broker归C；D.SAFE不等C.AR亦不授worker绿灯，持续运行只等拟启用路线。新建快照为显式准备写动作，不能藏在query/open声称零写。独立修订复核accepted_for_planning_delta仅签两份R4文件，不是产品通过；transition由主agent通读审查，未冒称独立自签。

三仓根入口、旧总计划/手册及v5衔接已更新；旧正文与历史review保留。旧手册新增状态头导致当前hash变化属于本次授权文档变更，旧review仍仅绑定当时输入，冻结manifest/receipt/baseline不改。本轮未复验最新源码、启动worker或跑真实E2E。
