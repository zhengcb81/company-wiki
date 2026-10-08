# 与 revenue-forecast 三项目大计划的交叉及执行门禁

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 2026-09-27 08:xx UTC 只读刷新：读取 revenue-forecast `progress.md`（最新 Round 120）、`REMEDIATION_REGISTER.md`（§162）、`OWNER_DECISIONS.md`（§39）、I-05-C/I-06-A 正式 review、I-17-A/B 卡片及 register 当前状态。本专题没有写 RF 文件。以下上一条 I-16-B “planned”判断已被新证据取代；每次 G0 前仍须重新读源文件和卡级状态。

**I-16-B / I-17 现状（2026-09-27 刷新）**：§162 记录 I-16-B 的 R1–R8 部署完成、独立复审 `ACCEPT`、父侧 `accepted_scoped` 落定；其中 CWP 有已授权提交 `dbe4745` 与少量 raw/sidecar 新增，Worker 明确保持 `paused`。当前链已转入 I-17-A 自然观察：register 有 attempt `c9fec8de` 在飞及周运行失败信号；原始 `card_I-17-A.md` 模板仍写 `planned`，所以不能把模板状态等同真实 attempt 状态或已满足观察时长。I-17-B 仍是后继终审。旧 `I-16-B/a20260926-02/snapshot_manifest.json` 只证明生成时 91 项初始 `all_match=true`；此前复核 11 个 SHA 不同，且此后又有新的 company-wiki 专项计划编辑。它不能证明当前快照一致。任何跨仓/共享接口实施前，须按即将纳入的最终文件重新冻结并复核 RF 所需快照；不能把 §162 对 I-16-B 的接受误读成 G0 通过。此处仅改本仓专项协调文档，不写 RF。

## 已确认的交叉范围

| 工作 | 与本方案的关系 | 当前处理 |
|---|---|---|
| revenue I-11-B 收入参数幅度/联合情景校准 | 现行卡主体是收入预测研究证据和情景；不需要改本轮 F0–F2 的 SQLite 文件替换工具 | 可继续；本轮 `prepared.json` 只证明旧 DB 与候选/备份，不宣称对方计划通过 |
| revenue I-05-C 按需求最小补产 | 盘上 attempt 的 `accepted_scoped` 限于设计/隔离证据；owner §40 已授予 `consumer_analysis` 入口与 InvocationTracker schema 的决定权，**授权缺口已解**。正式 review 仍列真实 `produce_for_demand`、`consumer_analysis` 能力和调用事件持久化未实现/未验；RF 现行 `source_preparation.py` 仍用内存 DemandQueue | 与未来 W0–W6 的 producer/role/event 直接重叠。G0 前不接共享 producer；须验真实入口、D-W05 活动 DAG、事件 schema/版本、持久登记与复用行为，不用 `accepted_scoped` 或授权代替产品验收 |
| revenue I-06-A 持久需求/幂等键 | 执行卡 header 仍为 `planned`；最新 `a20260922-02` 有 `accepted_scoped`，但 reviewer 范围只含 store-side lifecycle；RF caller wiring、CLI c8/c9/c10、跨进程 claim、OPEN-4/6 runtime probe、I-06-B consumption face 等仍为 carried-open，生产晋升还需 owner commit | 不再把它笼统描述为“D-W06 全部未决定”。具体的剩余调用/消费/并发语义仍与 Worker claim、重试、崩溃恢复重叠；G0 前不写第二套队列或 schema，须对照正式 accepted scope 与剩余 contract 核定唯一 job owner/API |
| filing-fetch → company-wiki `resolve` → revenue-forecast | 依赖本仓 `SourceResolver`、`SourceCatalog.query`、来源身份、根策略及原文路径；StockWiki company-wiki provider 目前 disabled | F3 用旧/候选的相同配置做 no-download resolve 与 metadata query 差分；F4/F5 前重核消费入口 SHA。StockWiki 启用前另测导出合同 |
| filing-fetch → earnings-transcripts → company-wiki companion acquisition | 属上游获取，不写 RF、不依赖其下游 consumer schema。E-T 精确期次 `discover`/`fetch-candidate` JSON 工具和 CWP 隔离 importer/preflight 已实现；filing-fetch 1.3 companion 正在独立 worktree 开发，尚无跨仓 E2E/正式合并 | G1e 只用 fake provider 和隔离 run root，先验请求独立授权、候选绑定、partial success 与原件/locator；`canonical_writer.py` 与 RF 缺陷卡共改，需逐 hunk 整合。G2 consumer 仍受 G0 约束 |
| 其他 agent 往 company-wiki raw 写 Microsoft 8-K 文件/sidecar、紫金 AR2023 PDF/sidecar | 2026-09-27 D0 发现 5 个近新增文件，合计 16,120,320 B，均尚未登记到 catalog locations；原文添加不会自动更新 catalog，但若擅自 scan/normalize 会改变生产 DB/WAL，并可能干扰对方材料登记 | D0 仅 stat 与确切路径只读查询；这些路径保持 `hold`，不删、不移动、不扫描、不 normalize。待材料 owner 完成当前工作并确认登记状态，再由 G0/相应卡决定如何接入 |

## 本轮硬门禁与责任边界

1. F3 `consumer_audit.json` 冻结本仓配置与 14 个核心源码文件（包含 `artifact_dag.py`、`service.py`、`processing_demand.py`、`store.py`）及 StockWiki 配置、filing-fetch/RF 入口的 SHA。F4、两次烟测和 F5 逐项重核；任何另一任务落地代码都会阻止旧库删除，先重新审计或重新准备。旧库的 SHA/WAL 变化则必须重新准备，因为候选数据已过时。
2. F0–F5 只替换 `.source_catalog/catalog.sqlite3` 为“所有非 span 行 + active 旧 span”的等 schema 库，并保留完整压缩旧库；不修改 I-05-C/I-06-A 的产品文件、源原文、DAG、Worker、对方 PWF 或跨仓数据库。`catalog_meta` 的 active-only 标记仅驱动缺失旧证据的归档错误，不是投资研究状态。
3. 在 F5 前，旧物理 DB 保持可按 `cutover-intent.json` 精确切回。若别的 agent 的迁移先落生产，F4/F5 暂停，重新检查 schema/索引/表行摘要、消费者返回值及恢复路径。不能把其模型/卡片历史 accepted 当作新 DB 可用性的证明。
4. W0 **不预设 `NarrativeEvidencePackage/v1`**。先与 I-05-C/06-A 的**最新正式产品合同**作角色映射：来源包 = 上游非投资资料投影；`summary`/`sections` 复用或升级现有 producer，`consumer_analysis` 归下游；确定唯一 job owner、请求身份、attempt/outbox、缓存失效和版本 pin。若对方尚在候选/blocked，W0 只在隔离夹具做评估，不自行把候选提升为生产规范。另需保持 StockWiki strict Source Provider v1 与 pilot bundle v0.2.0 的 schema 差异显式可见；quick-scan 仅有可选身份互操作，不是叙述包消费者。
5. 两边各写各自仓库/计划，跨仓只通过版本化只读 export/ID/hash；不复用共享可变 SQLite，也不修改对方正在进行的 PWF 状态。本方案发现契约冲突时留下精确文件/hash/返回值并停在相应门禁，不以“计划互不冲突”的笼统判断放行。

## 目前结论

**Phase 17 F0–F5 已结束；G1 目前完成的仍是隔离离线试点**：v16 主样本 1,289/1,289 locator 回读、18/18 锚点通过，v11 回归集 401/401 回读、5/5 锚点通过；13 条来源摘要草稿通过机械引用/角色检查并经实施者核源，但保持 `needs_review`。新增 selected-only 内存检索和 pilot-only raw replay resolver 预研。bundle v0.2.0 已将 replay_contract 内置，resolver 仅需调用方显式 source ID→raw path 映射；历史合并回归为 14 项通过，当前最新合并回归为 12 个检索/回源单测 + P06/T02 双样本 E2E + 12 件样本 E2E，共 **14 passed in 130.77s**，`ruff check` 通过，唯一运行目录清理并复核恢复基线。该复跑范围不扩大，也没有改 revenue-forecast、StockWiki、invest-quick-scan 或共享 DAG/store/service/producer/processing_demand/Worker。G2 schema 审查另确认 pilot bundle 不兼容 StockWiki strict Source Provider v1；G2a 必须等待 owner 合同并执行真实 reader E2E，quick-scan 仅作 identity interop。

**G0 当前不放行共享集成**。RF Round 121 报 Phase 7 链 15/15 完成，仍限各卡审查范围；I-05-C 的 owner 授权已解决，真实 producer/consumer 入口和事件持久化仍未验。I-06-A 最新 `accepted_scoped` 只覆盖隔离 store-side lifecycle，I-06-B 的消费实现、RF caller wiring/CLI 与跨进程 claim 仍是 carried-open，生产晋升另需正式落地。Worker 仍 paused；不得因 Phase 7 的计数或某一部署卡接受而改其运行状态。

因此本专题当前不接跨仓 export/生产检索，也不改共享 producer、DAG、store 或 Worker。company-wiki 只有 run-root 内存检索与 pilot raw replay resolver 预研；bundle v0.2.0 内置解析/选择回放合同，resolver 仍需调用方显式 raw-path 映射，不构成正式共享 schema、生产来源授权/query service 或 consumer 接入。特别是新建 `transcript_text` artifact role 会扩展 `ROLE_DEPENDENCIES`、`SourceBundle.KNOWN_ARTIFACT_ROLES`/generator registry、`artifact_read_model`、`scripts/resolve_bundle.py` 与 producer-event 分类；即使 catalog DB 表本身可容纳该行，也不能只做一次 SQL INSERT。G0 要按卡级最新正式裁定冻结唯一 source producer、持久 job owner、请求/attempt 身份、事件/schema/API 和消费端映射，之后再一次性评估该 role 是否允许进共享 SourceBundle；G0 前不把未知 role 写入生产 catalog，也不让它静默出现在 RF reader 中。

G1e acquisition 不依赖下游 RF G0。E-T 的精确期次无翻译工具与 CWP 隔离 importer/preflight 已实现，filing-fetch 独立分支仍需完成 1.3 严格 schema、授权、部分成功和跨仓 E2E；技能说明与代码版本须同步。详见[实现计划](implementation_plan.md)、[测试验收计划](test_acceptance_plan.md)与[E2E 计划](end_to_end_test_plan.md)。这些隔离实现不授权真实 provider 正文下载或生产写入。

## F 阶段执行后的核对与后续节奏

2026-09-26 的 F3 对 18 个本仓/跨仓合同文件冻结 SHA，6 组 query 与 12 组 no-download resolve 的旧/新库响应一致；F4 两轮生产烟测和 F5 前重核合同文件未变化。F5 19:06:54 UTC 已删除精确旧库，保留新库与完整备份，Worker 继续 paused。此结论只覆盖已审计的读接口，不代表 revenue-forecast 全业务预测、StockWiki consumer 或 invest-quick-scan 已完成端到端回归。

后续改用 [G0–G4 大节点审查](milestone_review_cadence.md)：G0 一次核 I-05-C/I-06-A 最新正式产品合同与 job owner，G2 仅在新 export/检索合同变动时让受影响消费者跑一次只读夹具，G3 复用 R4/v5 对基础 Worker 的已通过收据。不因对方 PWF 文字更新重做全库哈希；实际共享代码、schema、来源身份或消费者行为改变才重开受影响节点。

## 2026-09-27 11:xx UTC：revenue-forecast Round 121 / owner §40–§42 交叉复核

本节是对上文 Round 120 / register §162 / owner §39 快照的追加校正；不改 revenue-forecast 文件、状态或提交，也不将其 plan 文本当作产品集成验收。

- **RF 计划进度的适用范围**：Round 121 与 `task_plan.md` 报告 Phase 7 的 15/15 链项落为 `accepted_scoped`、7/7 条件和 35/35 清单完成，并提交计划批次 `ee0a82bf`。这些是各卡明确范围内的验收；不能外推为所有产品路径均已部署、跨仓 G0 已通过或 Worker 可运行。该批次记录为只含 `.planning`。本机 git refs 显示 `fcap` 与 `origin/main` 指向 `ee0a82bf`，本地 `main` 为 `3ce9cc4d` 且不包含该提交；本轮没有 fetch，故不据此断言远端当前状态。
- **状态账本存在需整理的矛盾**：`task_plan.md` 新状态行已写 Phase 7 complete，但同一部分较后仍保留旧的“Phase 未完成 / Status 保持进行中”的条件清单；`progress.md` 的 Round 121 顺序也在 Round 120 之前。合并或引用完成状态前，应由 RF 计划 owner 统一当前状态行与遗留历史注记，避免读者把历史门槛当现行或把局部链完成读成整体验收。
- **新增 RF 完成后事项**：Round 121 记有 I-17-B 的九例只拒 3 例；独立 `DEF-I00C-GATE-NEG` attempt 随后记录修复后 9/9 拒、控制例通过及 17 项定向测试通过。更晚的 owner §42 又记录生产 `closure_ready` 因 197/197 条 `fixture_hash=null` 恒为 false，并指定按“存在 `evidence_path` 时才校验其 hash”修正，且要求九例负例仍 9/9 拒。这是 RF 新的产品修正工作，不属于 Phase 7 的链卡数字；CWP 不接触该代码。
- **company-wiki 推送门禁是当前直接交叉阻塞**：owner §42 当时看到 archive 19>7 与未跟踪 narrative 363>10。2026-09-27 的完整 FC-1204 重算显示 archive 已由 RF 工位拆分至 7/7，但门仍红：`observability.py` 27>6、`prompt_injection.py` 17>15、`prune_retired_evidence.py` 27>12、`narrative_evidence.py` 363>新文件上限 10；当前棘轮测试 2/2 failed。前三个是已跟踪旧提交留下的违例，不应再断言“archive+narrative 两项齐就能推”。此外 archive 两个旧合同测试均因新必填 `now` 和旧固定文件名预期失败；pre-push 不覆盖这组行为测试，需按新 manifest/唯一 token 合同修复并做定向回归，再跑门禁。
- **共享代码文件重叠风险**：RF `DEF-MSFT-CANONICAL-DUP` 候选 `canonical_writer.fixed.py` 与 CWP 主树同文件当前 SHA 相同，主树未提交 diff 为 102 行新增、8 行删除。transcript 隔离分支也改了 `canonical_writer.import_staged` 的同一 `_write_provenance` 调用点；不能机械合并。联合回归须覆盖首导入、同原件重取、hash 后缀碰撞、相同 provider identity 的不同 bytes、无 adapter 根、sidecar 篡改以及 transcript rights/auth extension 在复用时不丢失。整合前不得覆盖或重置任一侧文件。
- **G0 仍关闭，但阻塞描述需更新**：owner §40 已解决 I-05-C 的 `consumer_analysis` 入口授权与 InvocationTracker schema 决定权；这消除了“等 owner 授权”的说法，不等于 producer/真实调用入口、事件落地和 RF consumer contract 已实现并验收。I-06-A 的 `accepted_scoped` 仍只证明其审查范围；I-06-B consumption/CLI、RF caller wiring、跨进程 claim 等接口须依卡级最新正式载体另行核实。更新 G0 时应把“授权已解决”与“产品合同/实现仍待核”分开写，未冻结唯一 reader/adapter、source role 与持久 job owner 前不改共享 DAG、SourceBundle 或 Worker。
- **执行隔离**：company-wiki 可继续做与 RF 共享文件无关、留在隔离 worktree 的上游 transcript 合同试验；涉及 `canonical_writer.py` 的分支整合、`SourceBundle`/artifact role、consumer adapter 与 Worker 接入留在上述门禁之后。测试继续用 fake provider 与独立 run root；不启用 Worker、不做生产抓取或目录清理。

## 2026-09-27：数据湖与跨仓职责再裁决（仅规划）

2026-09-27 最新口径：用户澄清 RF 的后续改动在本地未提交工作树，要求暂停后续并线；远端 RF `main=fcap=ee0a82bfd` 是已推送基线，不能覆盖后续 dirty 代码。R4 A/B/C 的技术路线改用固定候选快照/支线提交与版本化合同，**不等 Git merge**；company-wiki 产品代码暂停仍独立有效。本节只增加[数据湖边界复核](data_lake_boundary_review_2026-09-27.md)的规划口径；上方“可继续做隔离试验”是历史允许范围，**不构成本轮恢复 CWP 编码的指令**。R4 仍是位置透明读取的唯一 owner，本专项不新建 reader 或第二 catalog。

| 责任方 | 应承担 | 不应把什么推给别仓 |
|---|---|---|
| company-wiki | 来源身份/版本、多个 location、字段级 provenance、受控读取、来源解析工件与只读 export；canonical 新下载写入指定公司收件区 | 不保存 RF `consumer_analysis` 或 StockWiki 投资研究状态；不让 root priority 决定文档事实。现有 DAG 下游角色先审调用者，再兼容迁出。 |
| filing-fetch、dayu、earnings-transcripts | provider 发现/执行、精确期间、原始字节、来源许可信息与 receipt；filing-fetch 编排用户显式请求和获准的获取时序，交给 CWP 复用或 canonical import | CWP 统一复核具体来源/动作的 `DownloadAuthorization`、retain/derive 与导入资格；各 provider/filing-fetch 不建立第二套权限中心、root 白名单或 catalog，也不把工作目录当来源身份。 |
| revenue-forecast | 来源需求、预测驱动/情景及其 `consumer_analysis`、本仓消费缓存与调用事件 | 不直接打开 CWP 的 `canonical_path`、导入 CWP 内部 DAG 或为新目录改 CWP store/resolver。 |
| StockWiki / invest-quick-scan | 前者经版本化包做研究消费，后者仅可选身份互操作 | 不共享可写 DB，不从 raw path 推断来源权利或研究结论。 |

RF/filing-fetch 若遇到真正缺失的跨来源通用能力，可向 CWP owner 提出一份包含失败反例、所需版本化合同及受影响调用者的变更；先判断是否 adapter/consumer 自己可解决，再在 R4 A/G0 集中裁决，不逐文件设审查。CWP 已有进程内 `read_verified_bytes`，但没有可直接供 filing-fetch/RF 使用的跨进程命令；设计受控流或短期物化时保留字节完整性、权限、云占位、撤回与租约清理。G2 正式 reader 不沿用 pilot `source_id → raw path` 映射。位置透明的真实验收复用 R4 L01–L12、P01–P03，并补叙述证据跨根不变与 RF/StockWiki 真实 reader E2E；G1e 上游 acquisition 可单独设计，但不能据此放行 G2/Worker。
