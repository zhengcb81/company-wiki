# 模块边界收口计划

## M3 — 当前 HEAD 边界漂移审查（2026-11-15 新增）

**状态：IN_PROGRESS — 九模块当前主线与可识别产品差异已逐项归类；CWP 两个可复现边界盲区均以 TDD 修复并经独立复核。** 最新扫描器修复提交为 `07d48118022e660d65e3218594bfb02085710caf`，已推送；M3 尚待 StockWiki 根 canonical PWF 与 RF 运行记录由各自 owner 对齐，并由 ROOT 绑定精确版本完成最终报告。原 M2/E01-E09 仍只对其绑定版本有效；M3 不抹去原收据，也不把新版本自动视为已验收。

### 目标与设计原则

验证 M2 后各仓的源码变化是否仍守住公开接口、单向依赖与数据/状态 owner；只对能复现的边界缺口写 RED 测试并修复。Python 私有命名不是运行时隔离；普通模块继续用公开 package/facade、依赖方向和静态反例测试约束，只有确需隔离资源/权限的边界才使用独立进程或服务合同，不把整个系统改成微服务。

### 工作阶段

1. **冻结当前基线（完成首轮快照）**：记录九个仓 current HEAD、PWF 唯一入口、M2 接收 ref、主线/remote 状态；逐仓列出接收 ref 之后的源代码改动文件。快照和 owner 状态差异见父计划 `module-pwf-reconciliation-2026-11-14/findings.md`。历史快照不得覆盖最新 owner 状态。
2. **审查边界差异（当前快照已完成）**：每个观察到的变化已映射到所属模块、公开 consumer、数据/配置/预算 owner 和方向；检查内部导入、跨仓路径/数据库操作、重复校验、循环依赖、全局可变状态及绕过公开 CLI/API 的方式。无代码差异的仓只核对合同，不强行改代码。owner 后续提交若改变 refs，再按新版本增量复核。
3. **测试先行**：每个可复现越界路径先添加最小负例并确认 RED；静态扫描覆盖显式/相对/别名/动态导入的约定范围，安装测试从构建产物验证公开入口；CWP 只维护本仓测试。不得用 grep 私有名字计数冒充完整边界验证。
4. **归属修复**：源码修复和本模块测试由对应 repo owner 完成；ROOT 维护总矩阵与 CWP 组合检查，不直接改其他模块实现。只复跑受影响合同和一次最终组合审查，避免全量测试反复运行。

### M3 完成条件

- 每条跨模块边都有唯一 producer/consumer、公开接口/schema、版本与 owner；不存在未归属的数据、预算或状态写入。
- 当前 HEAD 相对 M2 的源码差异均有明确处置：边界保持、测试补强或 owner 修复；不存在只因历史收据而跳过的新路径。
- 有针对发现的真实绕行方式的 RED→GREEN 测试；被测试范围和静态工具限制写明，不声称 Python 包内私有符号在语言层绝对不可调用。
- 受影响的 owner 合同与独立安装组合通过，最终报告绑定精确 HEAD；PWF 入口更新到同一版本。

### 2026-11-15 CWP 首轮边界漂移处理

- `eval` / `exec` / `compile` 字符串动态执行可绕过 AST 符号扫描。反例先后覆盖直接调用、`builtins` 属性/别名、`__builtins__` 字典、`builtins.__dict__`、`vars()`/`vars(builtins)`、`globals()`/`locals()` 和 `.get()` 查找；扫描器把识别出的内建命名空间访问归一到同一执行入口再拒绝。生产源码当前没有动态执行调用；这是静态边界合同，不声称 Python 运行时沙箱。
- `automation/narrative_batch.py` 曾直接导入未公开的 `NARRATIVE_SUBJECT_REF_SCHEMA`。不扩大 schema 常量的公共面；在公开值类型 `NarrativeSubjectRef` 增加 `for_official_json_projection()` 工厂，让版本常量继续由其 owner 管理。工厂测试先 RED 后 GREEN。
- pytest 默认临时根不是天然短路径：本机沙箱注入的默认基准路径为 153 字符，旧逻辑因 `basetemp is None` 跳过检查，且旧 fallback 仍放在 `%TEMP%` 下。现在按 pytest 默认命名估算实际路径；超过预算时选 checkout 与系统 temp 中较短的根，生成仓内被 `.gitignore` 屏蔽的唯一 `.cwpt-<12hex>` 目录并在退出时清理。实际运行路径为 53 字符，cleanup 收据显示目录已删除。
- 正式摘要 E2E 还暴露了 Windows 沙箱拒绝 `os.link` 的环境限制（独立复现 `WinError 5`）。对象存储层现在仅在 Windows 硬链接被拒时退回同目录、原子、无覆盖的 `os.rename`；遇到并发已存在目标仍按实际内容 hash 验真，损坏目标不覆盖。
- 边界扫描器独立复核发现 `visit_Lambda` 检查了默认参数却没有检查 lambda 表达式结果，因而 `return lambda: du` 可把外部模块对象藏进闭包；普通 `return du` 原本会被拒绝。先加入闭包逃逸 RED 用例，再让 `_local_body` 在 lambda 参数绑定仍生效时检查表达式体；`lambda du: du` 的参数遮蔽控制例继续通过。修复仅涉及扫描器支持代码和边界合同测试，不修改生产实现。
- 本次定向边界合同文件 **66 passed / 6.47 秒**；独立审查 agent 对精确修复复跑同一命令，亦为 **66 passed / 6.47 秒**；受影响 Ruff 通过。提交 `07d48118022e660d65e3218594bfb02085710caf` 已推送，push fast smoke **18 passed / 45.23 秒**；完整 GitHub Actions CI 仍由精确 HEAD 结果确认。
- 同一独立复核检查了 `worker_process` 与 OCR 的动态 factory：当前生产构造均由所属模块内组装并指向 owner-local 实现，没有找到具体跨包穿透。静态扫描无法证明任意运行时拼接的模块字符串；此处记为静态方法边界，不把未知可能性升级成生产缺陷，也不据此扩大重构。
- 最新定向结果：短路径与默认路径合同、对象存储、Subject owner、层边界合同（含上述命名空间绕行反例）、官方 JSON batch preparation 合计 **119 passed / 42.68 秒**；测试日志再次显示默认根 153 字符→仓内实际 53 字符，退出清理成功。完整空内容 CLI 摘要/发布/读取/缓存复用 E2E 在对象存储修复后 **1 passed / 40.48 秒**；受影响文件 Ruff 通过。此前首次集成失败已分别归因于长默认 temp 和硬链接被沙箱拒绝，修复后各自复验通过。
- CWP 实现与总控 PWF 已提交 `3bc4ed86a` 并推送 `origin/master`；推送 fast smoke **18 passed / 15.06 秒**。精确 CI 仍按仓库配置待 GitHub Actions 完成，不把本地快门测试称为完整 CI。
- **第一轮结论（历史，已由下方第二轮扩展）**：当时仅完成 CWP 首组差异，不能外推到其他仓或当前所有路径。下方第二轮补充了九模块差异归类、owner 证据和 I10–I12 契约；M3 当前剩余项以本节“下一步”为准。

### 2026-11-15 M3 第二轮当前 HEAD 审查

**状态：M3 仍 OPEN。** 当前版本的产品差异已逐仓归类；I10/I11 已有 owner 侧真实 producer/consumer 证据，本轮不重复跑同一回放。剩余是 StockWiki owner 对齐根 canonical PWF、RF owner 记录两项 weekly runtime 结果、绑定最终精确 refs，并完成 CWP 当前边界报告收口。本轮对外仓只读，不运行作者代码、不编辑其 PWF、不碰活动数据。

| 仓库 | 基线 / 当前 ref | 源码差异与边界处置 | 当前证据/剩余项 |
|---|---|---|---|
| company-wiki | `c6189c623` → `master@07d481180` (=已推送 `origin/master`) | 精确产品 diff 仍为 24 个 `src/` Python 文件；最新 `07d481180` 只改扫描器支持/边界合同测试，不增加产品源码路径。依赖保持在 CWP 内部或经已声明公开 DU/WorkBudget 值接口 | 原切片 119 项定向测试及 CLI E2E 已过；新增 lambda 闭包逃逸合同测试 66 项通过并由独立 agent 复跑；Ruff 和 push smoke 18 项通过 |
| filing-fetch | `d4f35cab` → `main@1dfd818` (= `origin/main`) | M2 后一项测试文件变化，无产品源码变化；F-08 仍是 FF owner 的单独开放产品项，不是新边界失败 | `PLANNING_STATUS.md` 已记录 11-14 主线收尾；F-08 owner 后续按 FF PWF 处理 |
| revenue-forecast | `fab819c2` → `main@f2215959` (= `origin/main`) | 产品变化限 `scripts/revenue_report.py` 与对应报告测试，属 RF 自有报告呈现，不引入跨仓实现依赖 | `assurance/runs/weekly_alert.jsonl` 与 `weekly_manifest.json` 当前 tracked dirty，视为运行记录保留；RF owner 需把 11-15 运行结果写入 canonical PWF |
| earnings-transcripts | 当前 `main@50d9190` (= `origin/main`) | M3 观察到的差异限测试路径；无产品源变化或新跨层依赖 | owner PWF 另有 transcript-audit 退出码后续项，不属于本轮边界回归 |
| StockInfoDLSimple | 当前 `v2-clean-rewrite@26704a0` (= `origin/v2-clean-rewrite`) | 本轮未发现新增产品边界变化 | 用户名单与本仓工作区按 owner 收据保留；不扩展为 StockInfoDownloader 主线 |
| StockWiki | `21cf4891` → `master@0450506`（无 upstream） | 本仓 assessment、quick-scan store/universe 及根 CLI；不见导入邻仓私有实现。新发现两个公开 wire，登记为 I10/I11；不能以 I10 新版替代 Dashboard 当前 IQS 投影 v1 | assessment v2 有 107 项 owner 测试与独立 ACCEPT 记录；quick-scan owner 记录 C06 组合未跑成。根 `task_plan.md` 最后改于 11-08，隔离子计划 11-14 内容与主线提交状态不一致；由 StockWiki owner 在并行任务后对齐，本总控不写 |
| invest-quick-scan | `master@3d9243c` (= `origin/master`)，活动 `codex/iqs-manifest-delivery-01@ecb4a5d`（tracked clean；较先前核对新增证据/状态文件并修订计划，仍无产品源码差异） | 活动分支只含 `task_plan.md`、状态及证据文件；不把 owner 的真实研究/付费样本任务当作边界缺陷 | C38/C5 **120 passed**、固定核心组合 **296 passed**；该 owner 证据覆盖 I11 当前 consumer 链，不重复派发 lookup/history 回放 |
| investment-dashboard | `e1d1f927` → `main@3f83bb5` | 两个产品文件的变化为 Dashboard 自有比较错误呈现与 synthetic fixture；不新增对 CWP/RF/StockWiki 私有模块的导入。Dashboard 报告仍通过其 IQS adapter 消费已有公开 projection | `START_HERE` 及 receipt carrier 已更新至 3f83bb5；owner 收据记 fresh remote 对齐，本地 `origin/main` 亦相等 |
| revenue-forecast-audit | `3589b69c` → `main@50d8ab6`（按 owner 约定无 remote） | M2 后没有计划/证据目录外的产品源码变化 | canonical cycle 计划把 W08 子卡标为 complete；无新增边界回归 |

#### 新增的公开契约与 M3 退出检查

- I10 `stockwiki.company_assessment/2` / schema `2.0.0`：IQS 当前 producer 用 active package 生成 53 题 envelope，并在隔离 StockWiki workspace publish/readback；StockWiki 107 项 owner 测试、IQS producer golden 与独立 ACCEPT 也已留证。协议边界有真实互操作证据；C06 的真实历史覆盖/完整业务 run 仍 OPEN，归 StockWiki/IQS owner 业务计划，不据此把已通过的 wire 合同标红或声称业务闭环。
- I11 `stockwiki.membership_request/1.0.0`：StockWiki public CLI 的成功 apply/lookup/history 均带 `protocol`，IQS C38 使用该公开 CLI，Dashboard adapter 读取同版本响应。IQS owner PWF 已记录隔离 C38/C5 **120 passed** 与固定核心组合 **296 passed**，StockWiki CLI 测试也断言 lookup/history 版本字段；这些当前 producer/consumer 证据足以覆盖 I11，不再重复跑 M2 E08 或另造回放。
- I12（CWP 内部公开模块协作）`document_understanding` → `source_catalog`：`document_understanding.assertion_frames.source_assertion_frames` 与 `statement_grammar.english_question_start` 是显式公开函数；只消费调用者传入的文本和 owner 提供的 WorkBudget，不自行访问来源目录、分配业务身份或产出研究结论。`test_layer_public_boundaries.py` 把依赖方向纳入合同；原组合定向组 **119 passed**，随后 scanner closure follow-up 的该合同文件为 **66 passed** 并经独立复跑。CodeGraph 当前没有解析出这两个函数的调用边；该跨文件图为 best-effort，不据此声称接口未使用，也不把它当运行时封锁证明。
- Dashboard 最终 receipt carrier 的待办已经完成；旧 11-14 快照中的“START_HERE 未记录 final receipt”被 11-15 `3f83bb5` 取代。不要重复派发 Dashboard PWF 修复。
- ROOT 本仓 `git status`：tracked clean；仍有 **23,334** 个未跟踪文件，按当前清单分布于 `.mimosa` 10,010、`.planning` 13,180、`docs` 143、`.workbuddy-ai` 1。它们是 hook 状态、PWF/审查证据与用户记忆；本轮不提交、不整体删除，后续按已有 inventory 精确处置。

#### 下一步

1. 由 StockWiki owner 对齐根 canonical PWF 与已并入 `master@0450506` 的计划/源码，并由 RF owner 记录 weekly runtime 结果；ROOT 保持只读，不重复更改其他仓 PWF。
2. 将 CWP 当前 24 个产品路径审查结果、I12 公共接口及原 119 项与 follow-up 66 项边界合同绑定到 `master@07d48118022e660d65e3218594bfb02085710caf`；确认无未分类越界路径。已有 IQS 120/296、StockWiki 107/独审和 IQS→StockWiki 53 题 publish/readback 作为 I10/I11 证据，不重跑同一测试。
3. 最终核对九模块当前 refs、对应 owner PWF 和活动/dirty 状态，更新矩阵及总控状态；只对证据不足或能复现的真实边界问题补 RED→GREEN。全部报告绑定精确 HEAD 后才关闭 M3。

## Goal

从当前各模块架构出发，定义有限、可验收的模块化与解耦范围；用公开接口、独立安装/隔离测试、owner 状态归属和 TDD 完成边界封装，再恢复原主线。父计划为 `../du11-source-closure-2026-10-18/`。M0原为规划；用户随后明确授权A1调查、清理和有限并线，执行结果见reconciliation.md。

## Current Phase

### Phase A1 — 各模块工作区与未并线提交核销
**Status:** complete

2026-11-11用户新增授权：逐模块调查未提交及已提交未并线改动；确认归属后可删除无用改动，尽量并入正确主线；余项必须写进原施工卡。ROOT负责所有Git/清理变更，各路审查只读。保留下载原件；已证明需保留的有效代码和正在施工内容先分类，不能用整仓reset/clean代替调查。

步骤：新鲜Git refs/worktree/dirty盘点 → PWF/commit/交接与patch-equivalence逐项归因 → 删除确认无用内容/并线有依据且可验收分支 → 余项逐卡归属/顺序/测试 → 独立核对与发布。

证据集中在review/repo_reconciliation_20261111/；新架构实现仍按五卡后续执行，本节点仅做用户新要求的仓库整理与并线。

结果：8仓390个分支/remote refs、253工区、7tag、2stash已调查并分责；FF B34与Dashboard边界修复独审/定向回归后已入main、推origin。清理确定测试目录约216MB、7个空旧工区、source-facts重复源码、已吸收stash及生成物；未接收能力/有价值WIP全部加入原五卡A0和ROOT清单。A1 complete只代表本次核销交付，不代表所有历史工区清空或M1/M2完成。

### Phase A / M0 — 当前架构、接口与完整施工图
**Status:** complete

三路只读代码调查及ROOT对账已完成。五卡和接口矩阵已通过独立方案审查（PASS），两项阻断及三项精确性建议全部修复；本轮只改计划。证据：review/cwp_architecture.md、acquisition_architecture.md、research_architecture.md、root_baseline.md。

- [x] CWP 479个src文件/7包+根35模块清单；FF/ET/SID/RF/StockWiki/Audit/Dashboard实际模块图。
- [x] 当前实现、已证明能力、确定缺口、风险和未运行验证分开；原D4/D5/P3结果限定范围保留。
- [x] architecture.md/interface责任、boundary_matrix.json和acceptance E01–E09有限出口。
- [x] 五张互斥仓库卡、worktree基线/写集合、测试先行、独审、交接格式与合流规则。
- [x] 方案独审与修复、父计划状态对齐及文档JSON/链接/工区互斥检查完成；本轮以正常Git文档提交交付，实际发布版本看Git历史。

### Phase B / M1 — 五个owner并行TDD与模块交付
**Status:** complete

五条 owner 卡均已审查并入各自主线并推送，测试和发布版本见 [progress.md](progress.md) 与 [boundary_matrix.json](boundary_matrix.json)。StockWiki C38/B03 及公开来源消费者已进入本地 `master`。M2 集中处理各仓公开接口的组合结果。

任务卡见 dispatch.md。保持现有跨仓wire，作者各自A→B→C连续实施；不是每一步等ROOT批准。

| Owner | 本轮有限任务 | 独立验收 |
|---|---|---|
| CWP | CWP-01协议外OCR配置、02隐藏预算、03类型导入、04实际安装、05根/状态/模型边界分类 | 七责任逐项说明，公开替身/安装/恢复/原件保护 |
| FF | FF-01六operation及job/三表隔离，02command/config组装 | 真subprocess+无邻仓环境；已满足允许NO_CHANGE |
| RF | RF-01 旧越层工具分发、02 core/report 依赖、03 历史 profile 与默认隔离及 B37 公开合同 | MB-RF 已并入，证明范围以该卡收据为准 |
| ET | ET-01纯合同/进程与provider分离，02固定表示限额复现根修 | worker CLI成功/错误/unknown/预算/取消 |
| SID | SID-01typed错误贯通，02metadata反向依赖 | 纯API、稳定wire/过滤语义、staging-only |

ROOT 已在 StockWiki 和 Dashboard 各自工区接收对应接口。Audit 的公开资料包读取在 D4 被重新验证，五卡原作者工区已回收。

### Phase C / M2 — ROOT组合与整个架构阶段关闭
**Status:** complete

1. 锁各模块交付commit和正式runtime形态；选择真实本地样本/已有报告/三表快照并冻结必需点。
2. 核对Dashboard选用release代码根与数据根，不把缓存remote、main或旧配置当现行部署事实。既有owner处理必需release并线。
3. CWP卡交付后ROOT才改组合runner，按acceptance E01–E09一次运行。已有D4/D5/reader替换证明按用例复用；不重复收费全文测试。
4. 集中独审，不通过的格交给对应owner修复并复跑受影响部分。无必需skip；可选诊断不作许可，真实失败不改成PASS。
5. 各正确主线/remote对齐、当前自有测试目录恢复、交接证据完整、PWF CLOSED；立刻回父计划R4/T4→新版摘要→真实缓存→RF实际采用→公司循环。

此阶段不等待未来所有研究问题消失；其验收范围在矩阵里。新业务质量问题进入父计划，不无限延长解耦阶段。

## Next Step

E01–E09 已通过，范围限定见 [ROOT 组合记录](review/root_composition_20261114.md) 和 [E01–E09 矩阵](boundary_matrix.json)。当前唯一架构下一步是完成本计划 M3 的有限收口：九模块可识别产品差异已分类；CWP 当前 24 个产品路径和 I12 边界合同已审，IQS/StockWiki 的 I10/I11 有 owner 侧互操作证明。剩余为 StockWiki 根 PWF 与 RF weekly 运行记录由各自 owner 对齐，再由 ROOT 将当前 refs/owner receipts 绑定到最终 M3 报告。只对新版本里可复现的越界先写测试并修复；不重复已通过回放。M3 没有关闭前，不声称全项目当前版本已完全解耦，也不把旧收据外推到新代码。M3 有限范围完成后，再回 [父计划](../du11-source-closure-2026-10-18/task_plan.md) 的 P1 真实摘要任务；公司循环继续按原 PWF 保持暂停。

## Decisions

- 主线质量问题与模块边界分别记账；不以全文摘要/研究质量作为架构阶段永远延后的出口。
- 不新增人工许可、逐步签收或 Python 运行时防反射沙箱。
- 保留原件、现有配置和外部 harness 工作区。
- 采集审查最初建议只派FF/SID最小卡；ROOT依据用户“每模块设计解耦”要求，将已确认ET协议反向依赖和SID下层导入上层纳入本轮，形成五卡。没有确认缺陷的StockWiki/Audit仍先验证，避免强制改写。
- 同理RF core/report职责纳入同一RF作者，历史B34兼容不全面迁移。Sina只在CWP owner，金融数值不转回PDF抽取。

## Errors Encountered

| 观察 | 原因与处理 |
|---|---|
| 外仓Git普通沙箱status报work-tree/Permission denied | ROOT宿主只读重查成功，记录真实WIP；不是源码缺陷 |
| installed PWF resolver按旧PWF_PLAN_ROOT=docs/plans静默无结果 | 当前脚本变量语义不同，改用显式-PlanRoot与PLAN_ID，已正确解析本目录；不改技能/不增加许可 |
| CodeGraph部分当前文件不在索引 | 记录覆盖限制，用文件列表与已定位文件读补齐；未运行init/重建索引 |


## 2026-11-13 — 五条 owner 卡并线收尾

- [x] MB-CWP、MB-FF、MB-RF、MB-ET、MB-SID 均已独立审查并进入各自主线。
- [x] 五条线的最终集成测试、异常基线和独审状态已回写 boundary_matrix.json。
- [x] 本地/远端引用均核对；各仓 ROOT PWF 收据已推送。
- [x] ROOT 接收 StockWiki C38/B03 及安装态来源读取。
- [x] Dashboard 移除 CWP 私有读取依赖，公开流及摘要通过独立安装测试。
- [x] 2026-11-14 按矩阵收口 E01–E09，复验并线版本和回收自有工区。见 [ROOT 组合记录](review/root_composition_20261114.md)。
