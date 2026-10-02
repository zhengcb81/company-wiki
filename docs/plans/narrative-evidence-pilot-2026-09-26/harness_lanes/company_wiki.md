# CWP 独占施工卡：来源、叙述证据与 Worker

> **2026-10-02 当前状态：**E-B 已并入 CWP 主线。本地 pre-push 覆盖完整 unit/contract pytest，使用短隔离 basetemp 与 UTF-8，最近完整七阶段 GREEN。全量负载下曾有两项 CLI test helper 的 10 秒子进程上限超时，已调整至 30 秒并复跑全门。GitHub run `36992457178` 的 3.11/3.12/3.13 Unit tests 全失败，匿名 annotations 未显示同一步失败 helper 的 node ID。CI 现改为独立 `if: always()` reporter，写 job summary 与 error annotations；待推送验证后按具体用例定位修复。

开工输入包：本卡、S0a observed 接口表、指定 base/worktree、只读 P/T 样本清单（绝对路径、SHA、大小、期次、locator oracle、隔离复制/清理规则）。缺样本只阻对应真样本验收，不阻本仓 RED/代码整理。

## 已知状态与第一步

截至 2026-10-01，专用分支 `codex/narrative-gates-integration@cba745a` 的聚焦回归为 **404 passed, 2 skipped, 695 deselected**；随后已通过逐文件审查与主线回归，合并到 `master@00af53f`（merge commit `9e73eb4`）。并线后相关测试 **349 passed, 2 skipped**，Ruff 检查 56 个变更 Python 文件通过；SourceExport v2 Windows stdout LF golden 有回归保护。E-B 的恢复场景和 E6 replay 已进入主线，E-B 不再是开放任务。原始 PDF/TXT、manifest 和历史证据均保留；生产 Worker 仍 paused/default-off。后续从当前 master 开始处理 G-0/G-A hold，再推进 selected narrative G-C。

## 目标和交给别人的接口

1. **CWP→FF/RF：**公开逻辑 `SourceRef`（现行 schema `2.0`，`document_id/source_id/content_sha256/byte_size/mime_type`）、source operation、verified read；最终打开实际字节并验 SHA。一个 SHA 多位置只影响 locator，不影响业务身份；外部输出不得给永久物理 raw 路径。给出真实 serializer 正例、坏版本/错 SHA/撤回/迁根负例、CLI 命令与退出码。
2. **CWP→StockWiki：**现有 SourceExportBundleV2 `2.0.0` 的真实 producer golden，含 manifest/span/locator、export ID 与 bundle SHA；提供 verified-open 入口。仅输出来源/证据，不输出研究结论。
3. **CWP→FF 的精确采集：**把 close-gap 的 policy hash + DownloadAuthorization 叠层收敛为一次 `RequestPlan`（精确 request/gap/candidate、provider、有限项目/字节/时间预算）。CWP 独自完成 raw canonical import、来源版本和 provenance；FF 不写 catalog。
4. **CWP→RF/StockWiki 的 selected package：**叙述 event/select/summary/bundle 试点 `/2.0`，E5 后形成持久、内容寻址 package，含 source ID、原文 SHA、locator、摘要和 skip 理由；无全量正文切片默认写入。跨仓传输使用独立的 pathless narrative reference/read receipt，不混入 raw `SourceRef 2.0` 或 `SourceExportBundleV2`；由当前 CWP CLI 产生 artifact SHA、source identity/as-of binding 与 locator 回放 golden。未知合同版本具名拒绝。只有现有通用 role DAG 确实能减少重复实现时才评估新 role，不把整份原文加入传输包。

每个 producer golden 必须由当前代码生成；字段、状态和 schema 变化先更新 producer 测试/golden，再交总指挥更新接口表。`privacy_class` 仍进入 RootPolicy 3.0 hash，删除前必须显式迁移版本与所有真实 consumer，不能在本线悄悄改变老 hash。

## 在本仓内的施工顺序

1. **先写 G-0/P0 RED：**四隔离根、company/dayu/Dropbox 原生布局、同 SHA 迁移与 fallback、同尺寸篡改、读中替换、旧引用、真实 span→locator、429 页招股说明书资源负例；再写 pending proposal、无 prompt-review receipt、review store 故障不应挡 verified open 的反例。此步只确立测试与真实原件只读 oracle，不能报告 G-0 已通过。
2. **清 P0 真阻断并完成 G-0：**`resolver.py`/`source_reader.py` 不再因仅有 proposed remediation 就拒绝无争议原文；`source_reader.py:464-537` 的 metadata-only `capture_ready` 只看捕获/provenance/身份元数据，review metadata 故障降为诊断，不挡查询；实际字节 SHA 留到 `open_version/verify_version` 使用前验证，篡改原件可查候选但不可打开。真实 quarantined、身份或 SHA 冲突仍拒绝。`close_gap.py`/`authorization.py`/`acquisition.py`/CLI 改成单次精确请求+预算，**下载前重验当前 root/config/activation epoch**，计划后策略变化须 0 fetch 或重规划；只退出多余审批 receipt/hash。保留 stale gap、重复调用不重下、并发 single-flight 和原文完整性。修 `SourceVersionReader`/root adapter 后跑本仓真实样本包，总指挥再跑跨仓 G-0；正式通过后才给 consumer frozen golden。
3. **清 P1/P2 复杂度：**逐项先核当前生产 caller，再按下表用自动事实替代人工字段；不要用关键字全库删除。

   | 现行文件 | 本仓改法 | 必留性质 |
   |---|---|---|
   | `automation/models.py`、`migrations.py`、`store.py`、`human_inbox.py`、`handlers/gold_review.py`、`planner.py` | 退役无人调用的 Approval CRUD、人工 inbox、占位 gold receipt 处理和其 `BLOCKED_HUMAN` 路径；旧 SQLite 表只读保留，不破坏式 DROP。 | retry、lease、outbox、dead-letter 和其它真实任务错误状态。 |
   | `automation/policy.py`、`registry.py`、`controller.py`、`scheduler.py` | `allow_llm` 已默认 true；`source.narrative_summarize` 的模型 API 是联网能力，须可由已授权叙述任务调度并受模型费用/限流预算约束。采集正文网络仍由精确请求/provider 配置启用，不把模型 job 假标为无网络。 | `max_fan_out`、费用/字节/并发上限与 Worker pause；`plan_jobs` 可排 summarize，未请求采集 0 fetch。 |
   | `source_lifecycle.py`、`readiness_graph.py`、`prompt_injection.py`、`prompt_injection_guard.py`、`source_reader.py` | shadow readiness 不因缺 prompt-review receipt 禁止来源使用；`capture_ready`/review-store 实际阻断已在 P0 迁移，review metadata 只作可选诊断，不阻 verified open/LLM。 | 原文 hash、locator、输出引用/结构验证，正文当不可信数据。 |
   | `activation.py`、`restore.py`、CLI | 必填 `reviewer` 改本地 actor/run ID 自动记录；无需第二人签字。 | 已验证 assertion、策略快照/CAS、epoch、单文档 SHA/provenance、原子回滚。 |
   | `config.py`、`models.py`、`policy_2x.py`、`policy_3x.py` | `privacy_class` 不控制外发但仍入 RootPolicy 3.0 hash；先发布新版本/golden、确认 FF/RF/StockWiki 消费，再删字段。 | root containment、只读根写入归属、immutable raw。 |
   | `scripts/deletion_manifest.py`、`dropbox_governance.py`、旧 reviewer/gold gate 脚本 | 清派生不要求 `user_authorized`/独立 reviewer；无人调用的历史工具退役默认入口；硬编码个案改通用来源事实报告。 | 只列可重建、无引用的精确派生路径及文件 SHA；原文禁删。 |

   对每组运行本卡测试包，确认旧持久对象仍可读；本线不得以关闭验证器的方式让错 hash、错公司或预算超额通过。
4. **N0/E5–E7：**单一 normalized artifact reader 验真实工件 SHA，E5 内容寻址 selected package 与单 writer projector；E6 年报/招股/IR/TXT 真样本；E7 Windows 多进程 1/2/4 在途、kill/lease/retry/outbox、预算和空间。只处理不同文档并发，同文档按 DAG；非线程安全 LLMClient 不跨线程共享。生产 Worker 在 E-B/G-C 自动测试通过前保持 paused。
5. **空间准备：**可实现派生清理器及 scratch 删除重建测试；生产清理只在总指挥确认**该批派生实际消费者所需**的 G-A/G-B/G2b/G-C 已覆盖且无引用后按精确清单执行，不把无关身份门当全局前置。原始下载文档永不进入删除清单。

## 本线测试包

- G-0：`tests/contract/test_source_operation_v2.py`、`test_source_version_reader.py`、`test_source_version_reader_cli.py`、`test_source_export_v2.py`、`test_source_export_v2_cli.py`，及 `tests/e2e/test_source_version_reader_real_bytes.py`；加四根、旧引用和大文件资源用例，并迁移 CLI 中“无 receipt→capture_ready=false”的旧断言。现有 77 passed 只是较窄基线，不能当 G-0 完成。
- P0/P1：`test_remediation_workflow_fc403.py`、`test_close_gap_fc801.py`、`test_close_gap_concurrency_fc804.py`、`test_source_catalog_download_authorization.py`、`test_runtime_policy.py`、`test_source_lifecycle.py`、`test_readiness_graph.py`、`test_prompt_injection_guard.py`、`test_activation_transaction.py`、`test_restore_flow.py` 与 automation planner/store/worker 测试；旧人工门禁测试改为“无人工回执可处理 + 数据错误仍失败”的行为测试。
- E5–E7：按现有 `phase_e_m3_worker_implementation_spec_2026-09-28.md` 找到本仓测试，再补正式 producer→catalog→verified reader→selected package→locator 真链、故障恢复与资源上限。大节点由总指挥统一跑 G-C。
- 全部测试使用本线唯一不存在的短路径隔离根；前后断言所用生产原件路径/大小/SHA 和本次测试树一致，`finally` 清本次 DB/WAL/cache/下载/进程。仅在大节点做昂贵的真实样本 E2E，迭代时跑受影响测试。

## 交接与停机

交付本仓 commit、base、改动路径、CWP 四类接口的真实 golden 路径/hash 与版本、测试命令/结果、测试根恢复状态、未解 hold。总指挥据此调 FF/RF/StockWiki；本线不得替他们修改目录。若来源身份/SHA/期间不符、原件写入、测试根未恢复或 Worker 重复 visible，停止受影响能力并给出复现；无需创建人工审批队列。

**本线自动验收：**P0/G-0 真字节样本和对应负例通过、正式 producer golden 可从当前 commit 重生、P1/P2 删除不影响旧持久数据读取；E5–E7 在独立报告中分别列通过/未通过，新 Worker 在总指挥 G-C 通过前保持 paused。新增路由的测试不可 skip。只在本仓可写短临时根运行，原件/manifest SHA 和测试根前后相同；每次小改仅跑受影响测试，交接时汇总一次本线测试包。

## 收尾暂停与 G-A 细则（2026-10-01）

本轮仅完成盘点/计划收尾并发布已验收主线，暂停新实施。恢复时先按[跨线收尾报告](results/cross_line_closeout_2026-10-01.md) 为 ET FMP 26 字段/JSON 的原始字节、转义 locator 和 publication 未知语义写 RED；不能用 HTML fake-provider 通过声称 FMP admission 完成。不要把 call_date 当 publication，不重复 E-B/W04。

发布检查补强：两项 transcript helper 保行为拆分（13 passed），六个 source audit/catalog lifecycle/叙述试点 CLI 从 legacy research 分类中分离（六项 RED→writer freeze 20 passed）。不追加人工权限门，不放行退役研究 writer；原件/生产配置不改。恢复后先处理 RF 已记录的 historical snapshot/live HEAD push blocker。
