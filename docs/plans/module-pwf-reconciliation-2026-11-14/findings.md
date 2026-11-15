# 调查发现

## 2026-11-15 — 边界扫描器 lambda 闭包漏检已由 TDD 关闭

- 独立复核发现扫描器的 `visit_Lambda` 处理了默认参数，却没有把 lambda expression body 当作潜在的逃逸值检查。因此 `from company_wiki import document_understanding as du; return lambda: du` 能把外部模块对象藏入闭包；常规 `return du` 已被扫描器拒绝。
- 最小负例先 RED；修复让 `_local_body` 在 lambda 参数绑定仍生效时检查 expression body。参数同名遮蔽反例 `lambda du: du` 仍通过，防止把合法本地参数误判成导入模块引用。
- 最终 `tests/contract/test_layer_public_boundaries.py` **66 passed / 6.47s**，独立 reviewer 对同一最终代码复跑 **66 passed / 6.47s**；Ruff 通过。只改扫描器支持代码与契约测试，无生产代码改动。
- 对动态 factory 的具体入口做只读审查：`worker_process` 和 OCR 当前生产构造均从所属模块内组装且使用 owner-local factory，没有发现当前跨包穿透。静态扫描不能证明任意运行时字符串拼接安全；这是明确的方法边界，不是生产缺陷证据。
- 修复 commit `07d48118022e660d65e3218594bfb02085710caf` 已正常推送，push smoke 18 passed / 45.23s。M3 仍等待 StockWiki 与 RF owner 更新各自 PWF/weekly 运行记录，再绑定九模块最终 refs。

## 2026-11-15 — M3 当前 HEAD 第二轮核对（取代开工快照的待办判断）

- 精确的 M2→当前源码 diff 为：CWP 24 个 `src/` 文件；FF 0 个产品源文件、1 个测试文件；RF 1 个报告源文件及1个测试；StockWiki 4 个产品模块并带 owner 测试/fixture；Dashboard 2 个产品源文件，另有 UI 测试和测试依赖；RFAudit 没有计划/证据目录以外的产品源码变化。旧段落中的 `25/7/4/5/1` 是第一轮宽泛“代码形态路径”筛选，不能当成产品源码计数。
- 当前主线/状态：CWP `master@91137e257` 与 `origin/master` 相等且 tracked clean；FF `main@1dfd818` 与 `origin/main` 相等；RF `main@f2215959` 与 `origin/main` 相等，但 `assurance/runs/weekly_alert.jsonl` 与 `weekly_manifest.json` 有两项 tracked runtime 变化，原样保留；Dashboard `main@3f83bb5` 的本地 `origin/main` 缓存也在 3f83，owner 的 START_HERE 已记录 final receipt carrier，早前“缺收据”判断过时；RFAudit `main@50d8ab6` 按 owner 约定无 remote。
- StockWiki 当前 `master@0450506` 无 upstream，且把两条并行 owner 变更提交到了主线。其 11-14 子计划保留了详细测试/独审记录，但根 canonical `task_plan.md` 最后更新于 11-08，子计划中的“未提交/不提交”阶段声明与当前主线状态不一致。该仓另有活动 owner，ROOT 只登记差异并等待其 owner 更新，不改其代码/PWF/数据。
- 将 M2 后发现的两条公开 StockWiki wire 加入 I10/I11：I10 `stockwiki.company_assessment/2`（schema `2.0.0`，IQS→StockWiki），IQS active package 生成 53 题 envelope 并在隔离 StockWiki workspace publish/readback，另有 producer golden、StockWiki 107 项测试和独立 ACCEPT；C06 真实历史覆盖仍 OPEN，但不等于 wire 互操作未验证。I11 `stockwiki.membership_request/1.0.0`（StockWiki CLI→Dashboard/IQS adapter），StockWiki CLI 测试断言 lookup/history 的 `protocol` 字段；IQS 当前 PWF 记录 C38/C5 120 passed、固定核心组合 296 passed，足以覆盖当前 consumer 链，不再重复回放。Dashboard 公司评估仍通过 IQS `/1` 投影，不能误画成直接消费 StockWiki v2。
- IQS 主线与活动包分开登记：`master@3d9243c=origin/master`，截至 14:33 UTC 活动 `codex/iqs-manifest-delivery-01@ecb4a5d` tracked clean；相对 master 只有 `task_plan.md` 与计划/状态/证据文件，无产品源差异。该分支较上一快照 `239838b` 又新增了状态、SHA 清单与两份 dry-run 证据，并修正两个计划措辞；产品源码未变。当前活动包仍由 IQS owner 完成，ROOT 不改其文件。
- 以上接口登记和对应剩余项已同步到 `module-boundaries/interfaces.md`、`boundary_matrix.json` 与 M3 task plan。M2 E01–E09 继续只绑定原冻结 refs；本次不把新差异回写成 M2 已验收。
- CWP tracked 工作区仍 clean；`git ls-files -o --exclude-standard` 为 23,334 个未跟踪文件，与 11-15 清单相符（`.mimosa` 10,010、`.planning` 13,180、`docs` 143、`.workbuddy-ai` 1）。这些由既有目录 inventory 分别保留，未整批加入或删除。
- Dashboard 三张跨仓续核卡已与 owner `dashboard-closeout-handoff.md` 核对：C01 证据可移植性已由 `c8939e5` 并入 main；B-real 预览模块适配尚未执行，旧清单必须按当前 `main@3f83bb5` 重基线；B03 旧 review-closeout 仍缺绑定 R1 终态，只是证据任务，产品侧 B03 live 修复/验证另已接收。三者均不阻塞 CWP M3，外仓仍只读。

## 2026-11-15 — 九模块 canonical PWF 与主线状态复核（M3 开工快照）

- M3 的 TDD 反例先确认 `eval/exec/compile` 字符串执行能绕过当前 AST 边界扫描（RED）；扫描器增加对直接调用及 builtins 别名的识别后，专用反例通过。全量 `tests/contract/test_layer_public_boundaries.py` 为 63 passed / 1 failed，唯一失败是当前新增的 `automation/narrative_batch.py:17` 导入 `narrative_subject.NARRATIVE_SUBJECT_REF_SCHEMA`，但该常量未列入 provider 的公开 API。此为真实跨层合同违例；不允许通过扩大 `__all__` 或忽略该模块来消绿，先核实该数据的 owner 和适当接口位置。
- 符号使用核对确认：`NarrativeSubjectRef` 是声明的公开值类型，多个层通过该类型传递投影身份；`NARRATIVE_SUBJECT_REF_SCHEMA` 只在 `narrative_subject.py` 内定义/构造，唯独 `automation/narrative_batch.py` 直接读取常量并手动构造类型。正确修复方向是由该值类型提供“从 official-json 投影键构造 ref”的公开工厂，让 schema 版本仍由数据 owner 管理，不把常量扩成公共依赖。
- CWP 现有 `LayerBoundaries` 扫描器已覆盖常见直接/别名/相对/动态模块加载、`getattr`、私有成员、未声明导出、跨层方向和外部实例成员访问，并有针对性反例；这比仅检查下划线导入扎实。当前发现候选缺口：静态扫描不能执行字符串构造，`eval/exec/compile` 可能绕过语法树引用跟踪。尚未确认生产路径实际使用这些调用；M3 先加最小负例验证是否可绕过，再决定是否禁止动态执行。
- 本次读取各仓 canonical 入口及本地 Git 元数据；没有 fetch、运行测试或写入其他仓。历史子计划仍按历史记录处理，不把其旧日期单独当作错误。
- M3 开工观察时 CWP `master@0ff37fde5` 与本地 `origin/master` 相等；随后代码 `3bc4ed86a` 与 PWF carrier `f175e6c37` 已正常推送，最终两 refs 相等。FF `main@1dfd818`、RF `main@f2215959`、ET `main@50d9190`、SID `v2-clean-rewrite@26704a0`、IQS `master@a334293` 是本轮开工观察；RFAudit 无 remote、StockWiki 无 upstream，不能据此声称已推送。
- 需 owner 对齐的 canonical PWF：Dashboard START_HERE 仍记录 11-14 的 `2e8320e` 发布观察，CWP 总计划已记录 11-15 最终 carrier `3f83bb5`；RF PWF 快照停在 11-14，现场有两项 T3 运行结果 tracked dirty；FF PWF 的 F-08 仍未修，且“无未结产品 lane”与等待 Dashboard F-08 交付的下一步表述不一致。
- StockWiki 最近 owner 卡仍为 Phase 4 review remediation in progress，C06 缺完整可采信的组合测试；IQS 最新进度为 11-15，模块工程验收声明 I1-I7 已通过，旧段落中 OPEN 状态须按日期/标题识别为历史。两仓仍有 owner 交接/其他计划余项，ROOT 不替其改写 active work。
- ET canonical PWF 记录收据冲突退出码缺陷为唯一下一步；SID PWF 有唯一下一步；RFAudit 业务循环明确暂停等待 ROOT 调度。这些是开放任务，不等于模块边界验收失败。
- 模块边界计划的 M2 范围是当前登记的生产/公开运行接口；E01-E09 标记通过，排除研究质量和一般文档召回。IQS 边界测试说明覆盖常见静态显式调用，不是运行时沙箱。因此“已验收的接口集合通过”成立，“所有代码路径绝不可能跨层”没有此类证明。
- 总控计划需要把阶段 2 七仓收尾与九仓续办拆清，并保留阶段 3 未完成标记；本次核对不把 untracked 状态行直接认作垃圾。
- M2 接收 ref 均仍是当前主线祖先，但其后存在源码变化：CWP、RF、StockWiki、Dashboard、RFAudit 分别有 25、7、4、5、1 个代码形态路径变化。产品代码初筛定位到 CWP narrative/document-understanding、RF filing/report adapter、StockWiki public assessments/quick-scan、Dashboard forecast/synthetic adapter；RFAudit 的差异位于计划执行脚本。该计数是定位工作，不是缺陷判断；M3 需逐项审阅后才决定是否补测试或修复。
- CodeGraph 可用于 CWP/FF/RF/SID/StockWiki/IQS/Dashboard/RFAudit；ET 未初始化。IQS 本地 CodeGraph 库约 3.7 GB，不为本轮审查重建索引；ET 使用只读 AST/import fallback。一次 CodeGraph 符号搜索未发现 RF 的 `FinancialStatementSource`，说明后续以已确认文件路径做针对性只读检查，不能把索引无结果视为无依赖。
- M2 接收 ref 均仍是当前主线祖先，但其后存在源码变化：CWP、RF、StockWiki、Dashboard、RFAudit 分别有 25、7、4、5、1 个代码形态路径变化。初步路径筛选显示变化集中在 CWP narrative/document-understanding、RF filing/report adapter、StockWiki public assessments/quick-scan、Dashboard forecast/synthetic adapter；这只是范围定位，不是缺陷判断。M3 逐个审阅相关路径后才能判断是否要补测试或修复。
- CodeGraph 可用于 CWP/FF/RF/SID/StockWiki/IQS/Dashboard/RFAudit；ET 当前未初始化。IQS 本地 CodeGraph 库约 3.7 GB，不重建或扩张索引；ET 使用只读 AST/import fallback，避免审查本身继续膨胀磁盘。

## 2026-11-15 — M3 CWP 当前版本 TDD 结果

- 首轮 `eval` / `exec` / `compile` 反例证明静态 AST 边界扫描可被字符串动态执行绕过；新增直接调用、`builtins` 属性及别名导入覆盖后，合同扫描会拒绝这条绕行。生产源码没有发现上述调用。
- 对修复后的扫描器继续做反例检查，又确认 `__builtins__['exec']`、`builtins.__dict__['eval']`、`vars()`/`vars(builtins)`、`globals()`/`locals()` 与 `.get()` 字典查找及别名调用可绕过；这些反例先 RED，扫描器将识别出的内建命名空间及字典查找归一到相同动态执行标识后转 GREEN。静态扫描的边界和未声称运行时隔离均在 M3 计划中说明。
- 边界合同随后找出一个真实的私有常量引用：`automation/narrative_batch.py` 从 `narrative_subject` 读取未公开的 schema 常量。修复保留常量私有，由公开值类型 `NarrativeSubjectRef.for_official_json_projection()` 持有 wire version；新工厂测试先 RED 后 GREEN。
- pytest 默认临时路径的 153 字符来自沙箱注入 `%TEMP%`；旧 resolver 只检查显式 `--basetemp`，故默认路径完全跳过长度判断。新的默认路径估算按完整路径做 150 字符工作余量校验，超长时在 checkout/temp 中选更短的根，实际从 153 字符转至仓内 53 字符并成功自动清理。短路径合同同时验证不超预算时保留原路径。
- CLI E2E 首轮又显示 `NARRATIVE_PROJECTION_PermissionError`。独立 OS 探针确认沙箱拒绝同目录 `os.link`（WinError 5），而同目录 `os.rename` 可用。对象存储只在 Windows 硬链接被拒时回退到无覆盖原子重命名；新文件写入、同内容并发占位、损坏目标不覆盖三种合同都通过。
- 最新最终定向集合为 **119 passed / 42.68s**；日志复核默认 pytest 路径从 153 字符自动降至 53 字符并在退出时删除。空内容官方 JSON CLI E2E（摘要、发布、读取、跨 run 复用）在对象存储修复后 **1 passed / 40.48s**；受影响 Ruff 通过。首轮两次失败分别由默认 pytest 路径预算遗漏和沙箱硬链接能力不足导致，修复后重新运行通过。
- 仍需完成 M3 其他差异文件审查与各 owner PWF 同步；这些 CWP 用例不证明 RF/StockWiki/Dashboard/RFAudit 当前源码都通过边界合同，也不改变父业务摘要任务的 OPEN 状态。

## 2026-11-15 — 临时目录按后代活动时间分类

- 顶层目录 `LastWriteTime` 不能代表整棵目录树的最近活动：两个根目录时间看似很旧的 IQS 测试副本，其 `attestations/` 子目录仍在 11-13 更新；按用户的一周规则必须整目录保留。复核时应取目录、后代文件和子目录时间最大值。
- “临时”命名不代表内容可删：`_du6tmp`、`.du10-deps`、`_w20-runs` 由 PWF 指向真实回放、ET快照或验收证据；`cwp-temp` 也被历史 PWF 引用。删除前先确认路径具体含义与 PWF依赖，不以名称或可重跑测试为由假定证据可丢。
- 自动审批首轮拒绝 28 项约 518 MB 的 no-Git 临时目录递归删除，理由是该集合含 PWF 引用的数据库和 IQS 测试/审查快照。按其建议先对完整目录树建立 19,746 文件的压缩归档，再逐项核对源/归档 SHA-256，确认字节一致后才移除原目录；归档保留于 Projects 根。七个旧注册施工 worktree 的分支提交均已是各自主线祖先，因此通过 `git worktree remove` 正规移除并更新 worktree 注册表。

## 七条 owner lane 最终查收（2026-11-14）

- closeout 的“内容提交”和“后续只写收据的 carrier commit”可能是不同 SHA。RF 和 SID handoff 需明确这两类 SHA，避免把首轮候选、基线或历史提交写成最终主线 tip；Dashboard 的 D00 closeout 与其后 owner-acceptance 记录也需分开记。
- ROOT 找到并修复三项可确认的收据错位：RF final 错留 base 且 C4 pending；SID `independent_review.reviewed_head` 错留 CHANGES REQUIRED 初轮；Dashboard 汇总报告把 CWP push 写成已闭环并引用过期远端 SHA。对应内容已在 owner 仓修正、独立复核，并在各自主线发布。
- 截至 2026-11-14，CWP 未发布的原因不是本卡代码测试失败：平台 PreToolUse 的 Mimosa L3 对全仓历史扫描，阻断三次正常 push；被标记文件在 lane delta 外，lane delta 仅含 PWF 文档。完整报告没有落盘，已枚举 12 条 high，不完整列出其余 197 high 与 45 medium/low。该日期遵守不绕过平台检查的原则；后续推送状态见本文件 11-15 补记。
- 截至 2026-11-14，`git ls-remote` 因 `getaddrinfo() thread failed to start` 失败，最后一次成功远端观察仍是 `7361aad82`。当时将本地收尾记为 BLOCKED/未确认；该判断已由 11-15 的 GitHub push 成功响应更新。
- RF `assurance/runs/daily_alert.jsonl` 新增的 2026-11-14 运行记录属于实时运行账本，与 handoff 修复无关，已排除在 stage/commit/push 范围外并保留。不要将 tracked diff 误当作本卡 WIP 或清理掉。
- owner closeout 的清理目标是逐项归因并清除已证实可删材料，不是把所有非祖先 refs、活动工区、证据目录一律合并或删除。各 handoff 中 `ACTIVE_KEEP`、`EVIDENCE_KEEP`、`UNCLASSIFIED_HOLD` 仍按 owner 依赖处理；StockWiki/IQS 仍隔离。

## 当前已知约束

- 模块并线必须由各仓 owner 在各自仓内完成；company-wiki 总控只做 CWP 本仓工作和只读组合协调。
- StockWiki 有另一个并行项目正在修改；其写入、merge 和临时工区清理暂缓。
- 当前主线 goal `du11-source-closure-2026-10-18` 状态为 paused；本任务只整理计划与交接，不自动恢复该代码实施目标。
- CWP 当前 owner 边界更新已在 commit `1f9f3dcf3` 推送。此前移除的 CWP 临时测试 SDK/cache 目录有逐路径清理证据；其他未跟踪 `.planning`、`.mimosa` 或 handoff 不可按临时目录一概删除。

## 各仓起始盘点快照（2026-11-14；不是续办后的最新状态）

本表记录七张 owner 卡开工前的基线；StockWiki/IQS 的后续只读实时快照见本文件“本轮只读 hold 的最新现场”，其他模块以续办表与各仓 owner 最终收据为准。

Projects 顶层模块名目录已枚举：CWP 5 个，FF 14 个，RF core 14 个，RFAudit 9 个，ET family 8 个，SID 容器 1 个，Dashboard 3 个，IQS 1 个，StockWiki family 8 个，共 63 个候选路径。具体名字见 [顶层目录清单](projects_directory_inventory.md)。这是命名清单，不是垃圾目录清单。

| 模块 | canonical PWF / 主仓 | Git 快照 | 已发现的 PWF 问题 | 处置 owner |
|---|---|---|---|---|
| company-wiki | 本计划为总控；`Projects/company-wiki` | `master@1f9f3dcf3`；8 个注册 worktree；tracked clean；13 个非祖先候选 refs 待本仓处理 | 旧 module-boundaries 记录含已完成历史与当前状态，已新增 owner 并线规则；父业务目标仍 paused | ROOT 负责本仓与总控 |
| filing-fetch | 根 `PLANNING_STATUS.md` 自称全量入口；`Projects/filing-fetch` | `main@d4f35ca` = `origin/main`；tracked clean；35 个注册 worktree；3 个候选 ref | 根状态指向 10-04 的 `fcap` 旧 HEAD；根 PWF 是 8 月记录；MB-FF handoff 未更新 11-14 HEAD；W20 READY 与完成收据冲突；DU10 NEXT_HANDOFF 与接收收据冲突 | FF owner |
| revenue-forecast | 需 RF owner 核定 canonical landing page；`Projects/revenue-forecast` | `main@ec5ba004` = `origin/main`；ROOT 提权读取 tracked 状态 clean；61 个注册 worktree；19 个本地非祖先 refs | MB-RF `task_plan.md` 与 `handoff.md` 互相写“未合并/已合并”；W20 是否已接收需核实；旧 report dirty 报告已被当前 HEAD 吸收 | RF owner |
| earnings-transcripts | 根 `task_plan.md`、`progress.md`、`findings.md`；repo 在 `Projects/earnings-transcripts/earnings-transcripts` | `main@915f216` = `origin/main`；tracked clean；`.workbuddy-ai/` 未跟踪；12 worktree；0 non-ancestor ref | 根计划仍将 Phase 3 标 in-progress、引用 9 月过期 RF 依赖；MB-ET 子卡 11-13 已关闭 | ET owner |
| StockInfoDLSimple | `docs/plans/mb11-sid-2026-11-11/`；repo `Projects/StockInfoDLSimple/v2-clean-rewrite` | `v2-clean-rewrite@d084c4a` = origin；tracked clean；3 worktree；0 non-ancestor ref；两个人工名单文件未跟踪 | G4 卡称整体完成，但保留旧 1.3.0 路由待办；需同当前 HEAD 核实并校正 | SID owner |
| investment-dashboard | D00 的 `.planning/unified-dashboard-2026-10-26/START_HERE.md`；`Projects/investment-dashboard` | `main@50602de` = `origin/main`；tracked clean；80 worktree；92 local branch refs；`.workbuddy-ai/` 保留 | 总状态页面停在 11-04；CWP 三张卡基线仍为 `ff6e764f`；Dashboard 产品仍部分完成 | Dashboard D00 owner |
| StockWiki | 暂缓；`Projects/StockWiki` | 本次未核 Git | 另一项目正在施工；既有旧观察不作为当前接收状态 | StockWiki owner，暂缓 |
| invest-quick-scan | 暂缓；`Projects/invest-quick-scan` | 本次未核 Git | 等当前 owner/并行项目交接后确定 canonical PWF 与清理范围 | IQS owner，暂缓 |
| revenue-forecast-audit | `docs/plans/company-pool-cycle-2026-10-09/task_plan.md` 是循环主计划；`Projects/revenue-forecast-audit` | `main@fa0564fb`；clean；无 remote；0 non-ancestor refs；18 worktrees，其中 17 clean，W08 有未跟踪 PWF 数据 | skill-build 与 W20-AUDIT 已完成；company-pool-cycle 未完成且含多段覆盖状态；需加唯一 START_HERE/status 指针 | RFAudit owner |

Git 状态只读报告分别来自模块 agent 和 ROOT 命令。每个模块 owner 在写入状态前仍须用本仓最终 HEAD 与在途工作复核；不能将 worktree 数、非祖先 ref 或顶层目录名直接解释为“要删/要并”。

## 目录清理原则

“一个主要目录”按一个模块一个长期主仓理解；短期内可保留必需的隔离 worktree，但它们必须有 owner、PWF 和截止/清理动作。可清理目录只包括已确认可重建的测试 scratch、空旧 worktree 或已被正式交接吸收的副本。真实原件、业务输出、未提交源码、尚未交付的 worker worktree、PWF 历史证据、密钥、`.mimosa`/工具记忆和不清楚用途的目录默认保留并标 owner。

## 待确认

- IQS 和 StockWiki 暂不检查，以免与在途 owner 工作重叠；需等最终交接。
- 每仓顶层额外目录的 dirty/handoff/config 引用尚未全部逐项映射；只有 owner 卡收据齐备后才可删除。

## CWP lane 收口发现（2026-11-14，cwp_closeout 卡）

- 实时基线推进到 `master@7361aad82`（= origin/master）：卡面快照之后并入的 `codex/mb11-cwp`、`codex/root-mb11-cwp-fix` 等已使 6 个 ref 转为主线祖先，实时重算非祖先 ref 恰为 13 个，计数与卡面一致但成员已更新。
- 13 个非祖先 refs 中 11 个已 `ABSORBED`：cwp_review.md（2026-11-11）第 3 节指认的全部 T-\* 候选能力均由 MB-CWP 卡移植进 master（`source_stream_cli`、`public_canonical_browser`、readiness/link/recovery 六模块、B34 诊断/IPO 封面、T-N4 核销、T-CONFIG 严格类型反例），本卡用 `git ls-tree master` 逐一实测了移植模块/CLI/测试路径存在。T-W13 历史完成事实已在 `delivery/w13/handoff.md`（提交 `050c6d479`）。
- ABSORBED ≠ 可删 ref：这些分支的原始提交携带主线没有的历史 handoff 文档（`docs/handoffs/dashboard-*` 等路径只在对应 refs 可达），删除会使独有历史不可达；退休 refs 须先归档这些提交内容。
- 两个 Dashboard 物理工区（`b34-cwp-prospectus`、`return5-cwp-audit`）tracked 均 clean、各含 1 个 untracked 证据目录；按卡步骤 2 保持 `UNCLASSIFIED_HOLD`，CWP 侧仅记录 branch/HEAD/dirty。
- 清理为零的直接原因：所有 CWP 侧工区都含唯一证据（.planning 审计材料、M3/W04 未归档 WIP、R1 resume 记录）或 clean-filter 伪差量；三个非 git 的 Projects 目录（et-live、gates、storage-audit）都是唯一历史证据，gates 的 9,700 文件/262,499,631 B 观测产物可重建性未经证实。
- stash 仅剩 `18ac0d0562`（br-ci-fix）：c3 semantic 的 `5b1415d6e` 已退休；剩余 stash 含 llm_cost_log 独有差量，归账 owner 处置。
- CWP 业务主线唯一下一步未变：du11 P1 业务摘要质量修正（partial 来源；66 条 claim、26 个冗余任务、载体/承诺人混用），其后复验缓存恢复与 RF 采用；公司循环 paused。

## 本轮只读 hold 的最新现场（2026-11-14）

- StockWiki 已有本地 owner commit `0450506`，无 remote；现场是 28 个注册 worktree、39 个分支、41 个主仓 untracked 状态项。IQS `master@dab8724` 与 `origin/master` 一致，13 个注册 worktree/13 个分支，主仓有 22,658 个 untracked 状态项。两仓 PWF 仍有开放并行实现/组合验收；这些差异与测试材料保持 owner 持有，不由 ROOT 删除或整支并线。
- CWP 自身根 `.mypy_cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__` 是明确可再生的测试/静态检查缓存，已清理 1,682 文件/36,929,089 B；`.codegraph` 索引和 `.venv` 保留。CWP `.planning`、`.mimosa` 与历史 review 文件远大于本轮缓存，但分别承载会话/执行、平台 hook 状态及审查材料；未对它们做 bulk 清理。后续由只读分类决定是否存在可精确删除的冗余副本。
- FF/ET/RF/SID 的 owner PWF+Git 已分别在主线提交并推送；RF 内容与 receipt carrier 都经独立复核 PASS。Dashboard 已修复初审发现并形成 `4d2def1` 候选，等待最终复审后推送。详见 `progress.md` 的时间顺序记录；本计划保持 `进行中`，不能把 StockWiki/IQS hold 或 CWP 未发布的提交写成完成。

## RF / Dashboard 最终 closeout 独审发现（2026-11-14）

- RF 内容提交 `3ca619283411cf2a48afa57a449c44e2aa907768` 已通过独立复核；只含 146 个 `.planning/`、5 个 `assurance/` 文件及 `PLANNING_STATUS.md`，不含产品源码。审查核对原支线/ledger SHA、排除的 470,806 字节 MDB 摘录仍在源 ref、真实 `daily_alert.jsonl`、测试和 `.pytest_cache` 未删除状态。receipt-only carrier `f2215959d33abc76778342a95d39a8e38191da75` 推送后也经独立复核 PASS：仅四个收据文件变更，旧报告字节前缀保留，handoff/JSON/README 指针一致。
- Dashboard 初次独审绑定 `9cb67502c8943a4857e48c50d8c2022049ce2a65`，结论 CHANGES_REQUIRED：错误码 `constructor` 触发原型继承并向 React 返回函数；新增 pytest-asyncio 未锁入 `uv.lock`；handoff 最终/审查/远端 SHA 过期；E14 暂停包未记为保留例外；review 报告路径、`schema_version` 类型与 owner-requests 索引不符合施工卡。owner 声明已修复这 7 项，形成 `4d2def1c5dc0a774a0609543a6bcce4d98680518`，相关前端/后端/E2E、构建及锁定安装检查均通过；最终复审尚未完成，未推送。
- Dashboard 第二轮独审确认 4d2def1 中代码、测试、依赖锁、E14 保留和其余索引/收据问题已修复；先后发现 `handoff.json.final.head` 错指产品提交 `e8eaa85`、e58 的额外顶层键违反卡片固定 schema。owner 的 `fc6dbe7` 修正后独审 PASS，carrier `2e8320e` 推送后发现 status/delivery 与远端字段滞后；最新 docs-only carrier `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` 已正常推送，fresh remote SHA 等于本地，等待最终 receipt-only 复核；E14 与 WorkBuddy 均保留。

## Dashboard 最终收据更新（2026-11-15）

- 先前记录的“等待 8cd 最终 receipt-only 复核”已完成并被新状态取代：独立 reviewer 对 `8cd2d9477b60a6391dc5b1a4e3d0c94fb66dc6d0` 的 post-push 状态收据复核为 PASS，审查报告追加后由 docs-only carrier `3f83bb518ca782cb1bff495f7119fda7f3154097` 推送；fresh remote SHA 与本地 HEAD 一致。
- Dashboard owner 报告 tracked worktree clean，E14 用户暂停 handoff 与 `.workbuddy-ai/` 仍保留。无产品代码修改、未重跑产品测试；最终内容代码测试仍按此前实现证据及最终完整审查记录引用。
- 本轮总控 PWF 已更新为 Dashboard 最终 `3f83bb5`，不再把 Dashboard 报告追加 carrier 写作待办。CWP push 状态和 StockWiki/IQS owner hold 见后续 dated update。

## StockWiki / IQS 首轮读取失败快照（2026-11-15，已由文首第二轮刷新取代）

- 两仓 canonical PWF 可读，均显示 owner 工作未闭合：StockWiki Phase 40 的真实数据与 owner-shape release 终验仍 OPEN；IQS 的跨仓组合复跑、主体 bundle 核验、真实付费样本和独立终审仍 OPEN。
- 此次较早的尝试因文件系统权限未读到 Git 元数据；这一失败是历史观察，已由文首第二轮只读核验取代。当前可用 ref、owner 活动分支和 tracked 状态只看 2026-11-15 顶部第二轮记录；旧 SHA/工区数不作实时状态。

## 全模块收尾续办现场（2026-11-14）

- 用户本轮明确要求重新逐模块更新 PWF、归因并清理未提交项、把有效提交并入主线、移除确认无用的临时材料。ROOT 只改 CWP；FF/ET、RF/RFAudit、SID/Dashboard 由互斥 owner lane 并行。StockWiki/IQS 实时 PWF 仍有在途 owner 工作；两仓暂时只读，不碰活动 worktree，待 owner 交接后续办。
- CWP untracked 不是一种“垃圾”：提交四份新增收据后，2026-11-15 复测为 23,334 项：`.mimosa` hook-state 10,010、`.planning` 执行/审查记录 13,180、`docs/` PWF 与审查证据 143、`.workbuddy-ai` memory 1。全量删除会丢当前平台 hook 状态、历史测试/审查依据或用户笔记。
- 已安全删除 CWP 根下 37 个空旧测试目录、7 个已无引用的旧 `.tmp_*.json`（16,301 B）、两个 11-02 测试遗留 `tmp/osred/**/race.json`（20 B），以及无生产引用的一次性 `.tmp-build-registry.py`（1,019 B）。本轮释放 17,340 B，另删 37 个空目录；删除均在 CWP 根内逐项验路径/mtime/文件清单。
- 截至这份 2026-11-14 续办快照，CWP tracked 代码未改；`master` 仅增加本任务的文档/临时脚本删除记录，`origin/master` 最近成功观察为 `7361aad82`。随后正常 push 的状态见下方 2026-11-15 补记。

## CWP 推送状态更新（2026-11-15）

- 11-14 的三次 Mimosa L3 全仓扫描拦截仍是有效历史事实。11-15 以普通 `git push origin master` 重试后推送成功，GitHub 响应明确为 `7361aad82..0e741063f master -> master`；这次未见 Mimosa 拦截。不能由一次成功推送推断此前告警已修复或平台规则已永久改变。
- push 快速反馈的 fixed smoke 为 **18/18** 通过（6.58 秒）；输出仍注明完整 CI 会在远端运行。推送差量由 `git diff --name-only 7361aad82 0e741063f` 核对，共 13 个 PWF/审查文件及一次性脚本删除，无生产源码改动。
- 推送后单独读取 `git ls-remote` 时，本地 Git 报 `getaddrinfo() thread failed to start`。因此以 Git push 服务端成功响应作为当次发布证据，不虚报独立 fresh-read；该读取限制已写入后续 PWF 状态 carrier `f58011ddd` 并通过普通 push 发布。
- 后续 PWF 状态 carrier `f58011ddd` 已由正常 push 发布，服务端响应为 `0e741063f..f58011ddd`；随后本地 `origin/master` 与 `HEAD` 相同。独立 `ls-remote` 不重复尝试；这两次正常 push 均未复现 11-14 的 Mimosa L3 拦截。
