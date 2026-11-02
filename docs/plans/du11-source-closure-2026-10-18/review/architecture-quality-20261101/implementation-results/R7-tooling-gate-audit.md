# R7 工具与工程入口门禁只读审计

**审计完成；确认两类应整改的共用问题，均是工程/实验工具中的过宽阻断。** 当前检查的 canonical 工具链没有发现逐材料人工许可、private/public、人工发布签收复活。不能因此代替另外两路对核心 src 和 FF/RF 的结论。

- 审查工区：CWP ROOT，运行时代码 HEAD `fa8ef38ee0e6e0cd659ad602df5844cc9571ebb9`。
- 范围：`tools/`、`scripts/`、配置字段名、实际 `.githooks/` 和 `.github/workflows/`。元数据清单为 tools 198、scripts 112 个 Python 文件；不是 310 文件逐行验收。
- CodeGraph 先做结构定位，再核当前入口、调用和错误传播；索引包含历史副本且漏部分新工具，不能用“无 callers”直接证明退役。
- 九项稳定证据文件测试前后 SHA 相同。完整调用链、路径/行号、探针代码与结果在同名 JSON。
- 新 observer 的旧 300k/16k/ancestry32、context/proof 混并已由 ROOT 接管，**不再重复按旧方案审查或计成新问题**。

## R7-T01 / P2：把观察材料和日志大小当成执行正确性

这些入口都是真代码，但作用范围不同：日常 push 不是业务运行，显式实验工具也不是每次来源读取必经环节。共同根因是把展示/记录层的任意体积阈值，升级为调用者失败，甚至让观察器在 owner 成功后抛错。

| 当前入口与实际调用 | 固定条件 | 实际后果与范围 |
|---|---|---|
| `.githooks/pre-push` → `pre_push_gate.main(--push-checks)` → `_dispatch_gate` → `_run_pytest_gate` → `_run` → `run_bounded` | stdout 4MiB、stderr 512KiB | `OutputLimitExceeded` 变为 125，日常 push 被拒；并非测试断言失败。显式本地检查也用此 owner |
| Phase C launcher/bootstrap → `phase_c_observer.install` → 替换 `NarrativeArtifactStore.prepare` → `original_prepare` → `capture_prepared_checkpoint` | prepared 2MiB；generation/capsule metadata 512KiB | **原 prepare 已返回成功，观察器才抛阈值异常**。只在显式测试子进程安装，但会扭曲真实 prepare/恢复实验结果 |
| `tools.identity_audit` CLI → core 构造 receipt → `_emit` | 16MiB | 实际审计结果被换成 `TOP_BLOCKED/RECEIPT_TOO_LARGE`，`--out` 不发布完整结果；不是 canonical 身份读取都要过此工具 |
| `narrative_g2_replay` 和 `source_root_portability` 的最终 `write_report` | 8MiB | 抛错后 `report.json` 没写出。均为显式工程实验 |
| `storage_footprint` CLI → runner → `enforce_report_budget` → `write_report` | 256KiB | 先裁报告，仍装不下则 `FAILED/report_too_large`，即使扫描已经完成 |
| `raw_duplicate_audit` → report 缩减 | 1MiB | 裁明细，头部仍大时改成 `refused/report_header_too_large`。实际扫描读取字节/时间上限是另一回事 |
| `cross_market_suite` child JUnit → `runtime_properties` | metadata/property 32KiB | 先去 jobs/reservations，再因体积抛错，实际跨市场测试证据丢失；不是来源业务入口 |

位置细节：`pre_push_gate.py:57,145–173`；`phase_c_observer.py:20–21,84–93,140–147,414`；`identity_audit/core.py:737`；`storage_footprint/runner.py:80–86`；其余见 JSON。

**统一整改，不逐工具建许可：**

1. 取消任意输出/receipt/report 体积否决，完整证据写入普通自有结果文件；需要时流式写入，控制台仅展示摘要。不要把 300k 改成更大数继续保留同一根因。
2. 记录层失败与业务 owner 结果分开：真实磁盘/编码错误要明确 `observation incomplete`，不能把已成功来源工作改成失败，也不能把缺证据叫测试通过。
3. 保留真实子进程非零、超时、资源耗尽和实际配置预算；日志多不应成为新的预算。不要为了放行体积而隐瞒真实测试失败或杀进程后的未知用量。
4. 大的完整报告留一份规范文件，简明终端/交接展示引用它，不建立第二套观察库或人工收据链。

## R7-T02 / P2：全树 clean 代替实际运行代码身份

`tools/holdout_replay/producer.py:15,34–54` 的 `verify_producer` 除 exact HEAD 外，还执行四轮 `git status --porcelain -- src/scripts/tools/config`。`run_replay`（runner.py:107）、`verify-freeze`、`bootstrap-lake`（`__main__.py:46,65`）均在真实动作前调用它。

因此一个无关的 `?? tools/unrelated_notes.py` 也会拒绝 holdout。这里是显式 W18 工程入口，不是正常来源读取要求全仓干净，但会妨碍并行开发和实际验收。需要保留的是“真正运行的代码是什么”，不是“整个工具/配置树没有任何变化”。

**根修方向：**记录真实加载依赖字节和 commit/worktree fingerprint，无关 dirty 路径只作诊断。若某个实验明确要测已提交字节，则自动在自有隔离目录准备所需 runtime closure，别让使用者清空四个树。错误加载目录、缺关键依赖、宣称 commit 与实际代码不符仍应报错；不得把 WIP 假记为冻结 commit。

## 六个小探针实际验证了什么

宿主 Python，执行 **1.33 秒、exit 0，六个当前行为均实际观察到**。这是诊断收据，不是宣称旧门禁合理或整个产品通过。

| 探针 | 结果 |
|---|---|
| 当前 `_run` 调用安静成功子进程 | 0 |
| 当前 `_run` 调用 stdout 超固定值的合成子进程 | 125 |
| 当前 `_run` 调用 stderr 超固定值的合成子进程 | 125 |
| 实际 `verify_producer`，自有假仓、受控 `_git` 仅返回无关 untracked 工具 | `ProducerError`；没有修改真实 Git |
| 实际 `prepared_artifact_observer`，成功的合成 owner + 大于 2MiB 的合法 bytes | owner 已成功，随后 `OBSERVED_PREPARED_PAYLOAD_BOUND_EXCEEDED` |
| 实际 portability 最终 report writer，合成大报告 | `RuntimeError`，结果文件不存在 |

探针没有运行 pytest、模型、真实 source、原件、数据库、网络或收费请求，也未读取密钥环境值。`tmp/a7` 初始 absent，完整 probe/输出已嵌 JSON；精确包含路径和无 reparse 核验后清理 3 文件、6,901 逻辑字节，现已恢复 absent。

## 没有发现为现役人工许可的项目

| 命中项 | 真实状态与建议 |
|---|---|
| private/public、逐材料/供应商授权、review receipt、人工 release signature | 所检查工具的 canonical 入口未发现复活。`pyproject.toml` 十个 console entry 都指向核心 src；核心行为由另一审计线复核 |
| 六个旧 architecture/clean-env/gold/semantic/test-framework/batch gate | 已是 stdlib 退役 stub，exit 78；control 下旧运行配置已删除。不要把永久退役旧链解释成“等待批准” |
| legacy review_queue/scheduler/stage4/5/full_pipeline/expire_tracker | 在 writer retirement 清单及旧 writer guards 下；人工 review/过期字样属于旧研究写入链，不是当前下载/摘要权限 |
| readonly_canary、legacy_observer、bridge_off_equivalence、N4C live preflight | 显式历史/工程观察命令，没作为当前 push/CI/canonical batch 的强制收据前置 |
| `verify_plan_claims.py` 的固定 28 天/豁免文字检查 | 独立旧计划启发式，当前 hook/CI/产品入口不调用。可退役或保历史诊断，不能宣称业务要等 28 天 |
| `secret_audit.py` 的 `required_authorization_pending` | 审计结论指已发布 Git 历史重写，不控制材料外发。generate 记录事实，verify 验收审计内容，不要求逐文档许可；本轮没读真实凭证 |
| 质量评估缺 independent semantic/gold review → PARTIAL/未测 | 用户要求的大节点质量测量，不能无证据声称准确率；不等于资料读取许可，不应挪到正常读取前置 |

## 保留措施及理由

- **原文不可变、准确路径范围、foreign 内容不覆盖**：用户“原件不丢”的底线。普通诊断输出可以大，但不能因此写到 raw 或别人的结果上。
- **来源字节/身份/期间/as-of 与引用回放**：保证读的是正确文件，由所属 owner 一次验证后交可信结果；不能删成把错公司、错期间当有效来源。
- **真实配置的费用/token/时间/空间上限及恢复结算**：这是实际资源约束，和任意日志/报告大小不同。观察器异常不能免费重做或退款未知用量。
- **现有静态检查、一次固定 push smoke、完整 CI、大节点独审**：测试实际红仍应红；目前 commit 不跑 pytest，push 不再自动做 AST 大包选测。没有额外人工签收文件。
- **PDF 部署的 target ownership/plan/receipt/samefile**：仅由显式部署/verify 工具检查，以便不覆盖外来环境、复用真实 hardlink；当前检查的生产加载链没有要求用户签 deployment receipt。ASCII/同卷是当前 runtime workaround 的部署技术条件，不是公司资料权限。
- **legacy-derived 删除的 `--apply` 与精确 manifest**：这是一次删除意图与范围，不是两级人工签收。必须继续保护 raw、共享/当前有效对象及被改动文件；输出 `--receipt` 是结果路径，不是审批文件。
- **本地 HTTP 只面向 loopback 的 transport 约束**：wrapper 选项传给原 adapter，属于网络/配置 owner 规则，不是逐材料人审。不要在每个调用者再重复问许可。

## 可顺带优化，不能冒充当前业务阻塞

`pdf_runtime_deployment._reconcile`（`:453–479`）在同次操作中先 hash source，再 hash 已有 destination，最后确认 samefile；对真实 hardlink 可重复读取同一 inode。若后续优化部署，可把字节和句柄/stat 身份合并为一个 owner 结果，同次不重复 hash；跨进程/时间的 verify 仍有意义。此处未读取真实模型或做性能测量，不给出虚构耗时收益，也不要求因此延后主线。

## ROOT 统一实施后的最小验收建议

只设一个工程整改大节点，不加逐工具人工许可：

1. 成功 noisy child 不再因 log 体积失败；真实非零和超时仍红。
2. 大 prepared/metadata 不改变真实 owner 返回；注入观察 I/O 错误可保存 owner 状态与不完整观察，恢复不能重复付费。
3. 大 identity/replay/footprint 报告保存全部必需 ID、角色与证据，完整文件与简明终端分开，避免新造多份正文。
4. 临时真实 Git 仓加入无关 untracked 项仍可测；改实际 runtime 依赖时 identity 正确变化；错 import tree 仍检测出来。
5. 与核心 src/FF/RF 的整改统一核对单 owner 预算和身份边界，沿用现有完整 CI；不重跑模型或整批资料来验证日志工具。

本次是只读控制流审计和六个合成探针，**不签真实 H1、正式摘要、缓存恢复、RF 经济采用或整个目标完成**。源码、主 PWF、Git、生产配置和其他仓库未修改；报告完成 STOP，由 ROOT 汇总实施。
