# R1 新公司 holdout：完整 RF 执行、四路审查与共因修复施工细则

日期：2026-10-21。状态：`FREEZE_IN_PROGRESS`。本文件是当前 R1 的执行细则，**不是已执行或已验收收据**。

## 1. 唯一入口、范围与历史责任

整体状态以 [CURRENT_STATUS.md](../CURRENT_STATUS.md) / [JSON](../CURRENT_STATUS.json) 为唯一入口；本文件和 [checkpoints.json](checkpoints.json) 只细化 R1。选样证据与污染边界由同目录 `holdout-selection.md/json` 记录。协调员将版本、实际预算观察、隔离配置和最终 run 路径加入本目录索引后才派 executor。

本轮顺序为：**药明康德 CN → 药明合联 HK → Snowflake US**。一次只运行一家，先修复已证实共因并复验，再进入下一家，避免把同一故障和费用重复三遍。这是有理由的跨市场分层选样，不伪称旧随机池的新一轮随机抽样。三家公司在已查记录中未见完整RF审查run，所选年报也未见语义金标/调优；Snowflake电话会头部和元数据已有供应商调查暴露，不能称公司完全未见。这不等于穷尽所有历史。公司身份、来源资格和期间仍由原生边界解析确认一次，文件名不作为事实证明。

以下责任继续保留，不能被“三家干净”取消：

1. `revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/campaign.json` 及 `runs/pool-20261009-001-us-nvda`：保留旧种子、选择、初始封存、四审24问题、14根因/7工作包和未知费用；工程并线不等于最新版本真实复验闭环。给 NVDA 增加新 attempt，不能重新 init 擦掉历史。
2. [原八家公司后续目标](../../cross-market-rf-e2e-2026-10-08/followup_eight_company_audit.md)：阿里巴巴 → 小米集团 → 药明生物 → 药明康德 → 药明合联 → 微软 → Snowflake → MongoDB。该文件登记的下一目标仍需在当前目标真实达成后激活，不能因本轮出现重叠公司就提前标记八家完成；届时按有效代码/技能版本及规定顺序完成。
3. 当前 CWP PWF R2–R6、US 内容遗漏及已知测试债继续按当前状态入口处理，不把旧 CN/HK/US 回归当新 holdout。CN 已允许 8/10 收尾，不为最后两条继续付费调参。

## 2. 三个大节点和完成判定

| 节点 | 本轮工作 | 独立审查和可交付结果 |
|---|---|---|
| N1 冻结 | 选样/污染、as-of、有效代码和安装内容、配置、预算、隔离边界、检查点与来源侧预期方法 | 一次独立 freeze 审查；可执行输入/目录/预算引用齐备，发现的问题修完。通过只表示准备完成，不表示公司流程或预测通过 |
| N2 发现与共因方案 | 独立 executor 真实走 RF；封存 complete/partial/failed；四个互相独立 reviewer；编程专家追共因、建立 run/remediation PWF | 四报告 JSON+MD、执行包、全部 issue→根因→工作包→测试映射。诊断工具的结构通过不能代替来源和经济质量 |
| N3 修复、原公司复验和新公司泛化 | 测试先行、责任层修复、新 attempt 原公司复跑、相关独审并保留四路最终结论；随后下一未用于修复公司 | 原件保持、实际缓存/恢复及研究消费链通过、无未处置主要问题、清理恢复收据、PWF/提交/推送。版本变化和新公司失败如实回退 clean 计数 |

N2/N3 沿公司逐家循环，只有大的整合节点做完整独立审查。每次小编辑/commit 不再增加人签、授权 JSON、private/public、canary 或跨市场收费全套。用户既有授权沿用；配置缺失、资源超限与平台拦截写具体事实，不伪称“等待人工签收”。

本轮不能以“跑完命令”“报告齐了”或 CI 绿结束。主要问题是 P0/P1 及会实质改变本次预测的 P2；其余 P2/P3 也逐项实施或给有证据的不需实施理由。真实外部能力/配额限制保留 BLOCKED 和恢复入口，不能伪装 PASS。预算耗尽停止新增收费操作，不代表计划完成。

## 3. 角色、独占目录和盲审

审查工程实际根：`C:/Users/郑曾波/Projects/revenue-forecast-audit`。协调员用已安装 `revenue-forecast-audit`，不另建调度器、费用数据库或原文库存。

| 角色 | 独占写入 | 输入及职责 |
|---|---|---|
| ROOT 协调员 | run/scope、handoffs、总 PWF、remediation 三主文档、final、母账引用 | 冻结、预算、隔离、交接和跨仓接口；不模拟四审或代写结论 |
| 独立 executor | 本 run 的 `roles/executor/`、`execution/` 及 scope 指定隔离产物根 | 当前 RF/FF 全技能、公开通用检查点；实际研究和生产入口；不看盲来源期望或 reviewer 初稿 |
| storage reviewer | `roles/storage/`、本 attempt `reports/.../storage.*` | 原件/存储、虚拟化、解析、业务精选/摘要、RF 实际消费和空间/恢复 |
| fetch reviewer | `roles/fetch/`、`reports/.../fetch.*` | 请求/调用/逐文档结果、已有复用、缺失正确下载、ET 和各文档工具覆盖 |
| process reviewer | `roles/process/`、`reports/.../process.*` | 当前 RF 所有步骤、全部数字/来源/口径、公式及输入消费复算 |
| analyst reviewer | `roles/analyst/`、`reports/.../analyst.*` | 独立经营 cross-check、参数范围、管理目标/反证、情景/确认和买方质量 |
| 根因专家 | `roles/expert/`、`diagnosis/`、`remediation/work_packages/` | 四审齐后只读定位共因、查既有 PWF/commit/owner 工作，初次不改代码 |
| 实施 agent | 工作包明确的独占 worktree/目录 | 固定共享接口后实施；不写其他 owner 的目录、报告或原始执行包 |

四个总槽位包含 ROOT：executor 完成释放后先派三 reviewer，结束一个再派第四个；四路齐后再派专家。四人先读同一冻结执行包与各自卡，**初稿不互读**。允许重叠查错，不能共享结论代替独立判断。ROOT 记录真实 agent ID、指令引用、起止时间和 attempt；不记录隐藏思维链。

### 来源侧预期与输出侧检查分离

通用检查点对 executor 公开；**具体来源侧遗漏目标、预期数字/限定语和金标答案不发给 executor**。协调员/独立来源 reviewer 先只接收原件及locator、不接收selection/summary/forecast，从原件建立带 source/locator/context 的盲来源 inventory，不先看预测或摘要挑答案，再检查输出是否增添/遗漏。

已有原件可在 N1 通过 CWP 接口固定引用/资格。尚不存在的原件，N1 冻结公司、目标期间、发现窗口和来源侧检查方法；真实取得后追加不可改写的 acquisition/source manifest，再在审查者未看模型输出的条件下冻结该来源 inventory。此为自然记录次序，不增加每份文档人工许可。无法建立全文来源 inventory 时明确 `full_document_recall=not_evaluated`；只查 selected 不能声称全文召回通过。

## 4. N1 冻结输入和启动准备

协调员在派工前落盘以下事实，未核实项保持 pending，不推断 PASS：

1. **样本**：公司查询、已知市场及候选代码先固定；N1身份诚实标记 `pending_owner_resolution`。正式resolver标准主体/财年币种由executor首个原生 `source_preparation` 获取并追加身份收据，此后只传验真引用，不为文档冻结再解析一遍。as-of=`2026-10-21`、有效财年、基年和当前 RF 配置要求的连续预测年；股票代码仅候选时不冒充已验真 ID。记录污染搜索范围和排除理由。
2. **代码/安装**：CWP、RF、FF、ET、audit、StockInfoDLSimple 实际路径、HEAD、可解释的 owner WIP、运行 Python/依赖、关键入口/安装技能内容 SHA。`--version` 如只 hash 文件名列表，另核实际内容；无法取得 worktree 状态写 unknown，不能说 clean。
3. **配置**：有效 production model table/选择覆盖、catalog/FF/RF connection、解析/OCR/策略版本及相关 cache key。密钥只记环境变量名和 presence，不复制明文配置秘密或 dump 环境。当前 `config/models.yaml` 有 MiMo `mimo-v2.6-flash`、DeepSeek `deepseek-flash`、MiniMax `MiniMax-M3.1-Flash`；实际选择必须从当前配置解析，不把历史 MiniMax-M3 或临时猜值拿来调用。
4. **隔离**：唯一 run、独占 catalog/派生/cache/下载公司根、RF forecast/snapshot/publication registry、owned TEMP。配置必须使**整个 RF→FF→CWP 链**指向隔离写入，不只给一个 reader 参数就声称全部隔离。现存 CWP/Dayu/Dropbox 原件通过 public SourceRef/SourceExport 只读复用；不复制整湖、不让消费者拼目录。Dayu 代码绝不修改。
5. **初始清单**：隔离根起始相对路径/类型/bytes/SHA，小型受保护配置与相关原件指纹。只覆盖本次作用域，不每轮全盘扫描。为之后新下载文件记录测试所有权和保留至复审结束的期限。
6. **预算**：引用既有母 metadata、native usage ledger 和授权；冻结一次实时汇总观察与调用边界，不新起费用账。当前核算待 ROOT 复核值约为累计 **1,504,997 tokens / $0.615538**，含 prior 基数、FX hold 和全部 unknown holds；上限累计 **2,000,000 tokens / $20**，token 余量约 **495,003**。因此旧 `1,091,219 / $0.278311` 只是 append 账，不得再次当累计全账。正式观察以现有 `mother_totals` 结果为准，本文件不授予新额度。
7. **操作限额**：每公司本轮上界进一步收窄为 **100,000 tokens / $1**，并与 scope、deploy 及母账实际余量取更小值；不是三份新总预算。实际 bytes/time/并发继续服从配置。每次新增可能计费操作前保留 reservation，调用前先在本run的 `roles/executor/native_operation_index.json` 登记native DB/run/attempt/call引用（仅操作索引，不是收费账）；若此前POST后导出前崩溃，先检查所有已登记native store并重对账，不重发。每公司100k/$1跨全部文档、batch、run及replay累计收窄；调用后用既有 `phase_c_runner.append_native(database, run_id, output, "live")` 将真实native charge去重归母账。unknown 保留全 hold，不记 0、不因新 attempt 释放、不盲重放同一未知收费调用。正式摘要按已核实的原生 request/1 入口，`model: {}` 由有效 Config 解析；显式选 provider 也只能使用已配置 MiMo/DeepSeek 等，不手填猜测模型。

在 N1 质量审查通过前不派正式 RF executor；通过后正常继续，不再向用户索要逐公司许可。独立 reviewer 绑定确切冻结文件 SHA，不能把旧文档审查646b6937当作新冻结版本已通过。

## 5. 每家公司实际执行顺序

### 5.1 创建/恢复运行包

先读当前技能与每个 CLI `--help`，使用实际绝对路径。`audit_run.py init --root <AUDIT_PROJECT>/runs --company <公司> --as-of 2026-10-21` 只用于确实新的 run；恢复已有 run 先读 run/scope/manifest/events/reports，不重置。协调员把 R1 run 引用加入旧活动的 carried-responsibility 索引；旧 NVDA 不重 init。

记录 scope 中的 repo/skill/config/budget/isolated_roots、信息窗口和研究范围。初始 attempt 和 replay 分开，executor 不拥有共用元信息写权。

### 5.2 文档发现、准备与类型矩阵

通过当前 RF `scripts/source_preparation.py` → FF → CWP verified SourceRef 的单一生产入口；保存完整 result envelope，包括 filing 与电话会 companion 各自结果。已有原件先 verified open 复用，缺原件才用 schema2 `filing_intent=fetch_if_missing` 与实际 acquisition limits 请求。不要手组 RevenueSourceRecord 绕过入口。

| 公司/方向 | 本轮特别要验证的行为；实际期间仍由原文和来源日期确认 |
|---|---|
| 药明康德 CN | 既有年报/中报/季报和 IPO 可复用；as-of 前最新半年/季度需要真实发现，不能只拿2025年报作最新信息。IR 问答、最新业务/监管/处置及可比口径更新影响模型时须读取；CN 新下载用 StockInfoDLSimple 的当前能力 |
| 药明合联 HK | CWP 未见本地公司原件不等于不存在官方披露；通过当前配置正确发现/获取官方年报、中期、IPO及有价值业绩/业务沟通。HK transcript 不支持要给具体能力缺口，不能自动将 release/deck当 Q&A |
| Snowflake US | Dayu 已配置数据湖根有 FY2026 10-K，**不能因为 CWP 公司目录为空重复下载**。通过抽象层复用；查 as-of 前更新的 10-Q/8-K/exhibits/业绩沟通；FY、自然年及单季/累计分开，电话会 fiscal year/quarter 明确后交 ET，不由年报猜 Q4 |

每家公司 matrix 都考虑：annual/10-K/20-F、semi/interim、quarter/10-Q、IPO、equity/new-share/placement、convertible/use-of-proceeds、IR activity/问答、presentation、call TXT/JSON、并购/处置原文及标的审计/pro-forma、最新财报公开日至 as-of 的重大公告、独立行业/客户/竞争参考。每类给业务问题、有用性、实际查询/工具、已有/缺失/失败/不适用理由；没有文件或 provider 不支持不是自动 N/A。一般格式公告可以有依据跳过，不能把整类 IR/募投视作套话。

保留 transport、business、逐result/source、失败原因、真实 bytes/cost 分列。HTML 错误页/空文本不能当财报，JSON 不默认当电话会。新文件由 CWP 校验 SHA/主体/期间/as-of/类型并入库隔离根，消费者传已验证引用，不重复建身份库/人审许可。

### 5.3 共享引擎精选、正式摘要、实际消费

使用当前已发布共享引擎＋文档阅读策略生产入口；**只运行 reader 不等于生成正式摘要**。记录 source→normalized/parsed→selected units→generation/summary→公开 NarrativeRef/bundle→RF 已读记录→claim/parameter/DAG 的真实引用。策略与选择理由覆盖有价值业务/新曲线/出海、限制/否定/确认进度，不把全财务表机械切片。无摘要不妨碍研究者读已验证原文，缺口据实记录。

摘要原语言，保留 source_id/locator、parser/generator/策略版本、support/context 分组和表头/期间/单位。电话会 actor/Q&A question+answer 与 closing/stream 关系正确；投影必须指向真实母页，不复制 capture 假装独立文档。

不注入依赖gold的 `phase_c_observer`；在真实普通链路做一次**有界的恢复/缓存验收**：保留已付费 response 后于可控激活边界中断/恢复，确认同 attempt 恢复、无额外收费；同原件/有效配置的新 run 验证缓存准确复用、provider POST=0、generation/current parent 正确，并由 RF 公共 reader 实际消费。以真实命令/response/native ledger 的前后差证明，不只写“应当0”。需要失效测试时使用独立小型变体或相关单元/集成，不改原件，也不为每份文件重复收费恢复。

普通单次恢复与已知实验性两 attempt `activation-resume/ReservationConflictError` 分开记。`CW_SUMMARY_COVERAGE_REPAIR` 默认关闭；本轮不偷开实验开关，也不把普通恢复通过当 R2 修完。若新公司暴露同根因，进入专家共因计划。

### 5.4 完整 RF 研究到模型

逐项完成本次实际技能步骤及子步骤，不把固定旧编号当规范。至少包括：九维覆盖；冻结信息集；六类管理沟通与目标语义；独立经营参考；从已读来源到模型的 bridge；两期以上 primary 历史收入及 external segment+signed adjustment 对账；来源/claims/参数；收入曲线和生命周期；确认政策；同模型三情景；因果树/反证/领先指标；约束与汇总；敏感性/joint stress；置信度；原生验证/计算/渲染；immutable snapshot/真实回测适用性。

研究要求：

- `reported`、`management_target`、`third_party_estimate`、`analyst_assumption` 分清；原始数字、币种、scale、FY/季度/累计、总额/净额、并购/处置/CC/FX 口径传到真正参数。USD billion=10亿USD，不能与亿1:1；HKD/CNY/USD不混加，FX有时点/依据。
- 管理 target annual/run-rate/cumulative/ambiguous 区分；期限、比较口径、转换参数和情景 treatment 明确，不把愿景强塞 Base。未采用也须有独立 benchmark 或明确重大 gap。
- 先观察量/价/客户/利用率/履约等，再选最小充分经营桥；一个历史点不是实测区间，历史季节性不是未来增长幅度证明。可用透明 aggregate fallback，但写明限制；不为显得细而堆无依据参数。
- 未来假设可以是条件化非空值，不能因未来 actual 不存在把全预测留空；不得捏造区间/共识/回测来补表。订单、bookings、backlog、TAM、capex、产能不是确认收入。
- 最大贡献驱动有机制、实际 Base 参数、范围/期间、反证、falsifier；独立参考和管理目标不是同一消息的重复包装。joint stress 保留共同敞口和时序，避免逐线任意±百分比和重复冲击。
- 每个报告数值均可追至事实/参数/公式/输出，全部数字审计有分母；不得抽几项正确就说无幻觉。置信度不是达成概率，不给无来源 beat 结论或投资评级。

每次 validate/compute/render/snapshot 等调用前，用已安装 `execution_request.py build` 和 `audit_run.py capture --freeze-input` 留存并**实际消费**确切输入副本。同文件既输入又输出时按真实 argv `--freeze-arg-index` 消歧；input SHA 与 RF canonical JSON hash 分开。保持原生失败码、超时/截断/unknown；只引用 SourceRef 不把 PDF/raw塞 text capture。正式 registry 仅隔离 scope 根，reviewer 不执行正式发布。

### 5.5 封存成功或失败

executor 写 `execution/manifest.json`，逐 artifact 的 path/SHA/kind/producer/step，另有 `execution_outcome=complete|partial|failed` 与 `artifact_completeness=complete|partial`。协调员据实写 handoff；**执行失败也交四审**，不能自动降级 synthetic/offline 成功。

最小产物：step ledger、文档矩阵、source ledger、facts/parameters/calculations 或 RF 等价字段索引、正式 input/result/markdown、验证/snapshot/trace、通信/target/operating-research、工具调用和失败、Native usage/bytes、trust_boundary 真实说明、隔离清单与空间/缓存恢复收据。现成原生表只索引不重复抄一套；原文只 source+locator+SHA+少量必要摘录，不复制全PDF。

开审后原 execution 不再改。任何修正用 `execution_replays/<attempt_id>/`、新 handoff 与 `reports/<attempt_id>/<role>.json/.md`；不能覆盖旧失败。

## 6. N2 四审和根因专家的具体验收

公开检查点见 [checkpoints.json](checkpoints.json)，技能原卡的 S01–S18/F01–F17/P00–P19/A01–A18 是本轮起点，以实际安装版新增要求为准。

四人分别实际打开原件/证据，status 为 PASS/FAIL/BLOCKED/NOT_RUN/N/A，N/A给公司/期间相关理由。每个 FAIL 和有实质影响的缺证据都建 issue，给 expected/actual、artifact+locator、影响、原因假说与建议。报告 `executor_completion=verified` 仅表示执行证据可复核，不等于执行/预测成功。JSON 与 MD一致。

- storage：双向查摘要增添与重要遗漏；回原件查否定/限制、group context、表头/actor，实测派生文件/bytes及缓存/恢复，不把命中率当业务召回。
- fetch：通过实际 source_preparation/FF/ET 请求响应证明启动；复用前 verified open、缺失才下、逐文档 outcome、provider真实限额/失败。SNOW跨物理根复用为本轮关键点。
- process：当前 RF 步骤及每条数字**全量**实读/复算，保留覆盖分母/未知；typed ledger/financial_measure_audit 只辅助口径算式，不能证明来源真值。
- analyst：独立搭最大贡献驱动的简洁 operating cross-check，比较合理约束/区间、相反证据、确认时序/客户/竞争/供给；用实际金额/路径解释结论，不凭感觉通过。analyst risk 工具不能代替经济判断。

四报告齐后 ROOT 运行 `audit_run.py check/status` 和 `review_protocol.py coverage --execution-root <RUN>`，必要时显式限定额外工程证据根。工具只诊断结构/证据可开/覆盖，`quality_status=not_evaluated`；真实问题导致 needs_remediation 不改断言消掉。source bytes_verified、declared_field_match、semantic_source_truth 分开，hash/locator可开不等于支持结论。

随后独立专家逐 issue 定位 code/config/research/data/provider/observability；查实际调用链、责任层、相关 PWF/commit/WIP和最小反例，给证据而非归因猜测。症状同源合并，但同样 not_found 不必同根因。每 issue 映射 root cause、disposition、工作包、复测；不同 run/role/attempt 的同名 issue 不合并覆盖。

run 的 `remediation/` 是独立运行诊断 PWF，不抢占本项目唯一当前入口。工作包必须列 owner/可写与禁写目录、固定 DTO/错误/unknown接口、RED单元+集成反例、按职责层实施顺序、幂等/费用/清理、真实 E2E、完成标准、安装定点同步和交接。研究问题用来源反证与更正模型前后对照验收，不能假装 pytest 证明预测准确。

## 7. N3 从共因修复到真实闭环

1. 协调员审读一次共用设计和测试方案，固定边界后再并行无重叠目录的包。共享接口由 ROOT 整合，不让不同 agent 各自改同一路径。
2. 在隔离 worktree/独占目录先做可复现 RED：至少一个不同公司/格式/物理根反例；不加入公司名白名单，不镜像实现写测试。
3. 在正确责任层修实现，相关单元/集成 GREEN；失败如为测试过期，先证明当前契约为何不同，不能为绿改事实/删关键检查。
4. 新独立 executor 用新 attempt 真跑原公司；相关 reviewer 复验，最终仍保留四路完整有效版本结论。已有收费 response可按native恢复规则复用，unknown不盲重发。
5. 同一有效源码/安装/配置下轮到下一未用于修复公司。若其暴露共因，先修/复验该公司，已用于修复的公司成为 regression；必要时另冻结未见公司继续泛化。有效版本变更重置 clean streak，不把旧版本 PASS 累加到新版本。
6. 保留 NVDA 旧问题映射并按其责任顺序复跑，之后恢复旧池选择历史；原八家下一目标仍按规定激活和顺序执行。不得用新进度文件 reset 旧活动。迁移先用已有 `pool_progress.py migrate-preview`，保存算法/历史差异，不强装成同一种抽样。
7. 只把证实且有触发/证据/误判边界的重要风险更新 audit 技能及相应示例/测试；无新风险记录无需修改。源项目完成相关测试后定点同步实际安装副本，保留配置/output/owner内容，不整套覆盖。

## 8. 空间、恢复、提交和交接

每个隔离根在运行前/后记录路径、数量、raw与derived bytes、最大文件、cache/generation数量。比较声明上限与实测；发现重复全正文、每attempt完整拷贝、无限日志/缓存等要根因修复。审计 evidence 保留小型索引/必要摘录；不把全数据湖、全响应或一次性脚本无选择提交。

最后仅删除**经解析绝对路径确认位于 owned 测试根且初始清单不存在**的新增项；测试下载原件保留至全部审查复验结束后，按测试约定删除并记录 URL/sourceID/SHA/期间及 `local_original_removed_after_test=true`。生产原有 raw 和用户正式采集永不删除/改写；开始已有的隔离文件 bytes/SHA恢复原样。不做全量备份恢复演练，不清理他人 WIP，不换通道重试旧平台拒绝删除。

运行日志、四审、共因/处置、真实复验/清理和账本引用留在 audit run，CWP PWF保留摘要和可解析索引。完成节点及时更新当前入口/JSON与两层PWF，记录 code+test+审查绑定SHA，正常 commit/push已完成文件。Git/CI报告以确切SHA与真实结果为准；不能为验证文档反复启动不会触发的行为CI，也不能跳过现有必要责任测试。

**交接至少说明**：有效代码/配置/技能；run与attempt；实际执行/失败步骤；四报告；issue→根因→修复→测试；原件/隔离清理结果；已知费用与unknown；已经提交/推送的SHA；未闭环项和唯一下一动作。材料可打开和结构完整只证明可复查，最终结论须受实际来源、数值和经济审查支持。
