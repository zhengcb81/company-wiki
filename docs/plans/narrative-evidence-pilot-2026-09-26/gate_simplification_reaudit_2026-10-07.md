# G2：门禁与权限全面补漏及优先实施单

**状态：审计完成；实施 in_progress。优先级：P0，先于 R2 生产来源准备、R3 摘要运行和 R4 可选去重。**

这是 2026-10-07 用户“全面审查、查缺补漏、加到 PWF 并提高优先级”的实际施工入口。G1 的已发布成果继续有效，但其“约定范围完成”不能代表所有遗留机制已清空。总目标保持 active，不增加角色、人工签收、授权文件或逐小节点检查。

## 1. 审计范围和证据

已检查八个来源链仓库的当前主线/工作树、当前公开入口、运行配置、错误分类、维护命令、提交规则及 CI；另读两份已安装 filing-fetch 技能。结构问题用 CodeGraph caller/context，字符串与实际配置用文件读取；不以搜索到多少个 gate/review 单词作为结论。

| 仓库 | 实读 HEAD | 本轮重点 | 归属 |
|---|---|---|---|
| company-wiki | 2cad90d | live runtime policy、SourceReader pin、AUTO、CLI、冻结 Pipeline、hook/CI | MAIN |
| filing-fetch | 758e8f4 | v2 单下载意图、v1 兼容、安装技能 | MAIN 集成，改动前核最新状态 |
| earnings-transcripts/earnings-transcripts | 2b9fb84 | provider 配置、单网络意图、旧 TXT 复用 | MAIN 集成 |
| revenue-forecast | e241389 | 可选 release_readiness、coverage 工具、来源消费 | 隔离修改；三份 owner 日志不动 |
| StockWiki | 9f552a6 | check_all、AGENTS、覆盖率/体量硬门 | 隔离修改；投资研究状态不改 |
| StockInfoDLSimple/v2-clean-rewrite | 8ed5fdd | 当前 CWP adapter、Git 工作树 | 有 11 个 tracked 修改和未跟踪文件，保留 owner 改动 |
| MeetingConverter | 8a33a7f | 已交付 CI 精简、运行入口 | 未发现需恢复人工审批的新问题 |
| StockQAbyLLM | 34493d5 | CI 与本地检查一致性、指标门、重复 job | owner有已暂存pilot/其他改动，工程工具仅隔离目录清理 |

HEAD/文件 SHA/工作树/现场 policy 原文见[只读审计收据](harness_lanes/results/g2_gate_reaudit_2026-10-07.json)。这是入口和机制审计，**不声称逐行读完全部历史 worktree**。Dayu 是纯外部项目，零代码变更；IQS 有独立项目，不介入。沙箱/操作系统/供应商套餐限制不是项目内人工权限，不能通过修改项目声称取消了它们。

## 2. 已完成项继续保留，不重复施工

- private/public 外发权限、prompt-injection/not_reviewed/待修复提案的人工阻断已退出当前约定入口；历史审查记录只诊断，不恢复签收。
- AUTO Approval CRUD、独立 reviewer、gold/shadow/Work Unit 人工链已退出；历史表不为本次清理整库重写。
- FF v2 以一次 `filing_intent` 驱动下载，ET 为原语言 TXT；两份已安装 FF 技能都以 v2 为推荐入口，不能误报“还在默认 v1”。
- RF 人工 release_authorization 已退出；来源公开日而非下载日的跨仓合同已并线、正式六 CLI 已验收。
- CWP commit 已不跑 pytest；当前单 Python 快 CI 已绿。2cad90d 的 202 项责任节点/64.81 秒与[精确 CI 37582474369](harness_lanes/results/r2_systemic_exact_ci_2026-10-07.json)复用，不因补计划再次跑全部长测。
- 全根发现、有限登记、适配器重复 SHA、AUTO 范围 SQL、终态恢复零子进程的系统性修复已发布；生产配置迁移尚未执行，不能把源码绿冒充现场完成。

## 3. 漏项清单：按实际影响排序

### G2-00 / P0：现场 canary 未迁移（实施中）

**正在生效。** `.source_catalog/runtime_policy.json` 仍为 2026-08 canary，六个 flag、epoch/cohort 和关闭的 legacy bridge 影响当前 metadata 可见性。510B 并不占空间，却让旧 capture 字段被隐藏，是 G1 运行迁移漏项。

已核 16 条 active/verified、2 条 legacy/verified、4 条 candidate。直接删除 JSON 会退回 v1 默认并隐藏已生效断言，不能这么做。schema 2 `steady` 已在 2cad90d 发布、CI 绿，排除 shadow/candidate/rejected，断言优先、legacy capture 仅补缺，仍绑定真实来源 SHA。

**实施：**先核实际无活跃 writer/AUTO lease；用现有 `CatalogOperationLock` 和 `save_runtime_policy_cas`，比较旧 snapshot SHA/current root policy，再应用[已生成 steady payload](harness_lanes/results/r2_steady_runtime_policy_payload_2026-10-07.json)。旧小配置已在[预检](harness_lanes/results/r2_canary_retirement_preflight_2026-10-07.json)保存，不备份整个库。保留 activation journal，旧 schema 仅历史解码/迁移兼容；默认新库也应采用 steady，不能迁完旧库后新库又默认 canary/v1 控制面。

**完成条件：**真实 S07 原件打开 SHA 不变，capture 缺项可见；16 条原 active 非空字段保留；candidate/shadow 不能提升；17 张来源事实表不变；相同 payload 重复应用零写。迁移前后的 read pin 可识别真正语义变化，不悄悄重签旧任务。

### G2-01 / P0：读取指纹仍绑定整个配置

**正在生效，造成多余失效；不是目录权限。** `source_read_policy.py` 对 `asdict(CatalogConfig)` 全量 hash；`test_source_read_policy` 仍要求改变 `privacy_class` 就改变读取 pin。RootSpec 还保留 privacy/cohort 等兼容标签；取消权限后仍可使任务/引用失效，G1“只保留有效读取维度”并未彻底兑现。

**实施：**先逐字段追踪 reader/resolver/adapter 的实际使用，形成 `effective_read_policy` 显式投影；只纳入会改变本次读取/来源准入的字段。检查外层 RootPolicy hash、export/read_request/批次 event hash，防止删一层仍间接绑定标签。privacy_class 不再当权限；steady 不再受 cohort 标签影响。旧 v1 下真实影响可见性的 cohort 仅留历史兼容，不能在 steady 内偷偷复活。

保留当前根定位、适配器/格式、实际准入状态/路由/文件限制、来源版本与字节 SHA、期间/公开日等有效维度。路径迁根是否影响已有引用按现有虚拟化合同验证，不把目录细节重新传给消费者。若 fingerprint 解释改变，明确版本升级与旧 pin 报错/新 run 重绑；不更改旧费用或伪造旧包 pin。

**先写测试：**无效标签变化不使当前读取或同 run 恢复失效；真实路由/状态/格式/根或来源字节变化仍可检测；v2 CLI → FF → RF/StockWiki 结果一致。不能仅修改原测试的期望来证明实现正确。

### G2-02 / P0：AUTO 普通故障仍转“人工阻塞”

**当前 registry/worker/store 仍生效。** `registry.py` 的 `human_errors` 包括 PARSER_INCOMPLETE、SOURCE_UNAVAILABLE、MODEL_NOT_CONFIGURED、LOCATOR_REPLAY_FAILED，`retry.py` 可转 `BLOCKED_HUMAN`；这不是发现了审批收据要求，但错误语义继续误导接手者“要人工放行”。

**实施：**统一配置/输入缺失、可重试 I/O/限流、永久数据错误三类机器结果。配置/输入问题返回明确 reason 和需要修正的字段；修正后由正常事件/显式 retry 继续，不要求人工签收。可重试故障有界重试，坏 SHA/无效 locator 仍失败。新工作不产生 `blocked_human`；旧 enum/历史记录可读，不为改名字丢掉 usage、lease/outbox 或创建第二任务库。先查 handler 真实 outcome 和 Store 迁移，不能只改 UI 文案。

**完成条件：**选择→摘要→回放公共链中的上述错误均有准确终态与恢复方式；历史 blocked 记录可读，修正后的正常重试不重复扣费，kill/ACK 幂等保持。缺密钥不能因此冒充模型已调用，错误资料不能自动放行。

新 registry/handler 的错误语义变化须同步 handler_version；旧任务按既有 version 解码/明确恢复，不能同一个持久版本悄悄换含义。复用原 error/retry/lease Store，不新增泛化“权限中心”或人工重开任务接口。

### G2-03 / P1：冻结 Pipeline 的 gate 家族还在

**冻结历史链，不是现行摘要 worker。** `config/pipeline_rules.yaml` 仍有 Gate0–5、approval_threshold、human_review；`scripts/gate_system/` 和 `full_pipeline.py` 保留旧评审/金融 writer。`writer_policy` 已将 full_pipeline 永久退休，所以不能把这些描述成正在阻断每份新文档。

**实施：**以 CodeGraph/公开 entrypoint/package/test import 为依据退休无当前生产消费者的整条配置/模块/控制面，而非留下“disabled approval”空壳。仅将仍有价值的来源解析反例迁到当前 parser/selector 包。删旧专属测试和 CI/mypy/hook 清单项；不重新启用投资 writer，也不把 writer freeze 当个人权限移除。历史说明用 Git 链接，不新复制大 archive。

### G2-04 / P1：公开旧维护命令和特例审查

**可调用工具残留。** CLI 仍提供 `archive-retired-evidence`、`prune-retired-evidence`、`focus-cleanup`、`duplicate-recycle`；后两者有 confirmation-token。旧审计“无生产 caller”没覆盖到公开 CLI，结论过宽。`dropbox_governance.inventory_dropbox` 仍有平安特例“eligible without reviewer-completed evidence”，实 caller 是可选 `tools/dropbox_governance_replay.py` 和旧测试，不是正常 reader。

**实施：**逐项对账 S5/S6 已完成的数据迁移和当前合法消费者。无再用需求的派生清理/archive/prune 整体退出公开 CLI；原件处置先变成只读报告或退休旧破坏入口，不能只去确认 token 后开放随意删 raw。真实维护仍需要的集合版本一致性用 machine CAS，取消人造签收与重复 smoke/强制全量备份。Dropbox 工具取消公司特例人工签收；身份不明仅报告不明，不能靠文件名升级 verified，不写外部 Dropbox。

**完成条件：**help/CLI 不再引导旧审批维护；旧入口给明确退休说明且零写；保留原件、来源版本/location；没有把来源质量错误改成通过。

### G2-05 / P1：RF 可选发布工具仍绑三个仓库和固定样本

**可选，不在当前日常 CI。** `tools/release_readiness.py` 仍要求三 repo HEAD、恰好 197 场景、backup 目录；`backup_readable` 实际写 `.read-probe`，`run_checks` 写 rollback_manifest，检查名称与效果不符。直接定位 sibling CWP SQLite 也违反抽象边界。

**实施：**发布检查只验证实际 RF 代码与本次确实消费的版本化证据；197/邻仓 HEAD 为历史统计诊断，邻仓缺席不阻 RF 独立开发。来源读取走正式接口，不直接查 CWP 内部库。只读检查零输出文件/原目录修改；rollback 文件只在确实执行有状态发布时按需保存，不强制备份目录和全量恢复演练。`run_coverage_gates.py` 的指标阈值改报告，行为错误仍失败。旧人工 release auth 已退出，不能重新添另一签收。

**先写测试：**无 sibling 仓/无 backup、样本数量变化、check-only 无写仍可检查；消费的证据 bytes 不符仍失败。只在 RF 隔离目录实施，三个 owner 日志不动，不跨仓写。

### G2-06 / P1：StockWiki 每次提交全套与数字门仍保留

**现行脚本和 AGENTS 均生效。** `scripts/check_all.sh` 全 pytest 包 coverage，73% overall/40% ui 是硬门；AGENTS 仍说 Before commit；framework 新模块 600/god-module 1000 行也硬失败。上次外线消除了两遍 pytest，未取消这些要求。

**实施：**提交只运行改动责任范围的便宜静态/行为检查；全套真实工作区 E2E 只在相关大节点/显式运行一次。覆盖率、体量变成诊断，framework 的实际配置/模块一致性错误继续失败。同步 AGENTS/脚本/文档，不留“脚本精简但接手模型每 commit 必须全测”的冲突。投资研究 accepted/rejected 属 StockWiki 业务状态，本卡不取消投资结论语义。

**验收：**hook/docs 不触发全套、指标低于旧阈值本身不失败；一个真实责任测试故意失败时整体 exit 非零。一次相关来源 CLI/E2E 节点即可，不因小改动重复 935 项。

### G2-07 / P1：CWP 工程检查与退休清单同步

**现行小门与可选旧工具混合。** host-assumption regex 曾误拒测试中故意的 `C:/absolute.pdf`；mypy/hook/CI 仍包含旧 canary/维护模块，另有 optional coverage/complexity ratchet 历史测试。

**实施：**保留真正可移植行为的责任测试，将误伤合法反例/注释的字符串扫描收敛为诊断或语法范围检查，不增加 allowlist 签收表；同一退休模块在 package、tests、hook、CI、pre-push 清单一起移除。覆盖率/复杂度数值报告化，当前快 CI 维持单 Python，不恢复全合同/多平台矩阵。Ruff、实际公开 DTO 类型、相关配置体检和密钥泄露检查保留，不重复全仓无关检查。

### G2-08 / P1：FF v1 兼容与安装入口最终收敛

**v2 正确；v1 残留需 caller 审计。** 旧 `--allow-download` 与 request authorization 兼容仍在，不能算到 v2 单意图上。两份安装技能已推荐 v2，但 legacy 附录和摘要会让较弱模型反复询问授权。

**实施：**查 RF/其他正式 caller 的 schema；无合法新下载 caller 则退休 v1 下载路由，必要只读复用留薄兼容，不继续支持两套审批协议。库和 CLI 使用同一个 intent，不二次 ask。同步 repo skill 与两个安装副本的实际脚本/文档，仅从对应已发布版本安装；哈希差异先解释，不覆盖用户密钥/配置。当前持续授权作为上下文使用，`reuse_only` 仍零网络；限时/字节/费用不是人工签收。

**验收：**正式 FF→ET→CWP 离线链走三个真实 CLI、复用零 provider、语言/SHA/清理正确；相同 intent 的库与 CLI 一致，未来公开和预算拒绝仍明确。使用既有链测试入口，不新增十套 request contract。

### G2-09 / 已核能力边界：ET、provider 和外发文案

ET `ProviderSettings` 仍称 Reviewed runtime availability，但实际是单运行能力配置；没有发现新的人工 receipt。`download_authorized` 是一次请求网络意图。FMP 402、缺凭证、disabled provider 是现实能力，不能为“简化”冒充可以付费下载。只清理误导文案/重复问答；已有 TXT 在 provider 关闭、无翻译 LLM 凭证时也应正常零 HTTP 复用。MiniMax/MiMo/DeepSeek 必须继续遵守已配置模型与预算，持续外发授权不意味着无限预算。

StockInfoDLSimple 的 provider host、include/exclude 是来源发现和过滤，不是个人权限。MeetingConverter 当前快 CI 未见新人工审批门。此两仓无明确问题就不强加施工；StockInfoDLSimple dirty 不由本卡顺手清除。Dayu/IQS 无写。

### G2-10 / P1：StockQA CI 与本地脚本不一致

**远端正在生效。** CI 两 Python、独立 type/lint/black/bandit/radon/build/report，多次安装同类依赖；coverage 门 87%，本地 run_ci 却 60%。本地 `command | tee` 没有 pipefail，会吞失败退出码；pylint `--exit-zero` 却称“质量通过”。这能解释一类本地绿/远端红，不能假称是此前全部 CI 失败的唯一根因。

**实施：**一份短检查定义供本地/CI 共用；保留实际行为、类型/格式错误，coverage/pylint/radon 分数仅诊断。日常单受支持 Python，额外兼容测试显式大节点；依赖安装一次，不因报告/格式再建六 job。脚本真实失败退出码贯通，成功报告不能来自 tee；报告准确区分检测通过与指标统计。不削弱真实 failed test，不加新的人工质量签收。

**先写测试：**伪 pytest/type/format 返回失败时本地与 CI 共用入口非零，tee 不掩盖；低覆盖率本身成功，实际反例失败；无密钥离线执行短责任包。独立测试目录最终恢复原样。

### G2-11 / P0：摘要质量标记由模型重复维护并硬校验

**当前摘要校验生效，属于多余状态门，不是人工审批。** `narrative_evidence.validate_summary_claim` 调 `_validate_claim_review_status`：证据带 locator_unstable 时要求模型同时写 claim.needs_review=true 和 draft.status=needs_review；claim.needs_review 与草稿状态不一致也抛 SummaryValidationError。R6允许局部恢复，但这种标签矛盾仍会丢弃对应内容；只有一个相关claim时可能整稿失败。证据事实和质量标记是程序掌握的信息，不应要求模型重复正确抄写两份状态。

**实施：**解析后统一根据当前 evidence quality/replay 与保留claims推导质量诊断/草稿状态，保留模型 uncertainty 作为内容诊断；不因可确定的标签不一致拒绝有效内容。schema/来源SHA/原语言/引用ID/发言角色/真实locator仍由自动反例严格验证；locator确实无法回放的内容仍剔除，不靠改成needs_review放过坏引用。质量状态需要对外展示时由单处投影生成，旧字段兼容读，不添加review receipt。

**先写测试：**相同有效claim/evidence只改变模型review标签，保留内容、引用和原语言一致，程序质量投影一致；坏locator、未知evidence、问题冒充公司陈述仍不能入final；同run恢复不再因冗余状态变化重复付费。只用离线合法响应/已有真实响应做回归，不为测试这个状态多调用模型。

公开兼容字段可以保留，最终值由单处投影确定；若实际输出合同/prompt/handler解释变化，同步现有版本字段与消费者契约测试，不能重签历史final、更改旧费用或把整个provider响应重存一份。

## 4. 实施次序、所有权和接口

MAIN 是唯一集成与生产变更负责人。此表是施工顺序，不是新增 11 次签收。

| 顺序 | 工作 | 输出/责任 | 状态 |
|---|---|---|---|
| 1 | G2-00 steady 现场迁移/默认新库收敛 | 当前 policy、旧小 snapshot、来源实际读和 16 断言对照 | in_progress；代码已绿，现场未切 |
| 2 | G2-01 effective read pin + G2-02 AUTO 机器错误 + G2-11派生质量状态 | 版本化读取语义、现有 AUTO 单库/恢复错误合同、单处计算质量诊断 | pending；先 TDD |
| 3 | G2-03/04/07 CWP 冻结家族/公开维护/检查清单清理 | installed/import/CLI/help/CI 同步；不启用 raw 破坏入口 | pending |
| 大节点 A | CWP 当前链集中责任/E2E | isolated 真实 IR PDF/英文 TXT；公开 read/有限登记/零模型 skip/loopback worker；canary 现场小对照 | pending；复用已绿 202 与旧大节点 |
| 4 | G2-05 RF、G2-06 StockWiki、G2-10 StockQA 工程工具 | 各自独占目录/提交，MAIN 集成；仅本仓写 | pending；可独立但本轮不派新 harness |
| 5 | G2-08 FF 安装/v1 收敛、G2-09 文案和能力核对 | 唯一 v2 intent 与配置能力；main/installed 版本说明 | pending |
| 大节点 B | 三仓离线链 + 当前消费者 + 发布 | FF→ET→CWP、RF/SW 读取；每仓对应代码 CI；保护/临时根清理 | pending；不重复付费模型 |
| 6 | 回 R2 metadata/有限登记 → R3 → R4 → R5 | 原目标全部待办继续；G2 非缩减目标 | pending |

跨仓公共接口继续为 SourceRef/SourceExport v2、NarrativeRef/只读消费者、FF 单 intent 和 ET TXT 工具，不以 reviewer DTO、文件路径或共享可变数据库接线。若 wire 有变化，MAIN 先定版本化接口，责任仓只实现本仓部分；其他 owner 工作区修改先保留，隔离集成不覆盖。当前无重复目录写分包，不在用户没安排时启动新 agent。

## 5. 两个大节点的测试包和验收边界

实施先写行为反例，再改代码；每个 helper 不做独立签收。新测试按职责放置：

- `tests/unit/test_source_read_policy.py`（新计划文件；现有契约包在 `tests/contract/test_source_read_policy.py`）：投影纯函数、无效标签稳定、有效准入变化、版本化 pin。
- `tests/unit/test_automation_worker.py`（含 classify_outcome/retry 现有反例）、`test_automation_models.py`、`test_automation_store_atomic.py`：新故障分类、历史解码、有限重试、不能以成功掩盖无效来源；仅修改影响的责任集合，不猜不存在的 retry 测试文件。
- `tests/contract/test_gate_simplification_current_entrypoints.py`（待新增）：当前 CLI/help、旧 writer 退出、check-only 无写、默认 steady、不再要求人工 receipt。
- `tests/unit/test_narrative_partial_summary.py`（现有）：真实有效内容不因重复review标签矛盾丢弃，程序统一状态；坏locator/未知引用/发言角色错误仍拒绝，保留原R6局部恢复合同。
- `tests/integration/test_gate_simplification_source_chain.py`（待新增）：独立短根用真实 S07 PDF 和 S09 TXT，走实际登记/read/export、零模型 skip、本地 loopback 有界子进程；真实定位/SHA、坏字节/未来公开拒绝，只有选中组改变。跨仓链复用现有正式脚本，不再另造全功能链。
- RF/SW/StockQA 新工程入口测试各放本仓 tests 的独占责任模块；外部返回码用 stub 验证，再在大节点一次实跑相关行为集合。无需逐小模块全 coverage。

测试资料仅在新的独立测试目录；运行前记录 absent/原清单，结束 finally 删除新复制/下载/SQLite/模型工作目录，恢复原状。真实 paid provider POST **0**；不全文恢复备份，不将生产原件/owner 配置当夹具。现场 policy 迁移是正式操作，以小配置 CAS/断言/SHA 对照验收，不在生产造坏记录。

大节点 A 只集中跑修改的责任集合和公共 E2E；已发布融资、budget、kill/ACK 等节点不因本清理全重跑，只有其实际调用合同被修改才加相应反例。大节点 B 对真正变化的仓跑短 CI 和离线集成，纯 PWF/收据提交不触发新代码 CI。失败就定位具体责任，不能扩大门禁或改预期凑绿。

## 6. 应保留的自动正确性（不再包装成权限）

1. 原件不丢、真实 open 字节 SHA、来源版本/撤回事实；不能将任意输入自动标 verified。
2. 公司/证券/期间/公开日和 as-of；晚下载旧公开资料可用，未来公开拒绝。
3. evidence locator 真实回放、原语言和来源支持；上游只供应资料，不写投资结论。
4. 目录包含/写入归属、跨仓只读、外部 Dayu 零改动；同一用户不等于自动跨项目写。
5. 显式有限批次的字节/时间/token/费用和未知账保留；lease/generation/幂等/outbox 单库恢复。
6. 实际 schema/类型/语法/相关配置和密钥泄露检查；数字覆盖率/复杂度不是行为正确性的替代。

不保留人造授权文件、review receipt、签名/信任 TTL、固定样本数、无关 repo HEAD、必须备份目录、每次 commit 全套检查。保留项均需对应真实失败反例；没有实际当前责任的控制直接退休。

## Next Step

**先完成 G2-00：核无活跃运行，以既有锁/CAS 应用已发布 steady policy，集中验真实旧来源与 16 条断言；随后按 G2-01/02/11 的测试合同收敛读取投影、AUTO 错误和派生质量状态。** 未实施项明确 pending，不用“审计已完成”冒充“门禁已全部清空”。
