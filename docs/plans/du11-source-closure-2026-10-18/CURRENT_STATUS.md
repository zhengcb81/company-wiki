# 当前状态

唯一入口为本文件和 CURRENT_STATUS.json。实施顺序见 task_plan.md，交接见 HANDOFF.md，长期循环见 MAINLINE_LOOP_GOAL.md。

## 2026-11-10 本轮结果

- Dashboard P2 已并入 CWP、FF、RF 主线。D4/D5 的冻结公开接口和组合测试已有通过记录。
- 本轮进一步修复三条 PDF SDK 绕行。来源入库、CN 封面读取和语言采样现调用 parser_adapters 公开端口。边界测试和独立审查通过。
- 清除 source-case 对非 SHM 文件的 mtime 额外限制，统一内容 SHA、大小、存在性判定。指定基准样本加载限制在请求范围，历史 gold 独立归档。UTF-8 误读及退休测试观察点已修。
- cn-h1 原文 SHA 182e2062… 的 0.9 读取器复验为 10/10 业务事实、7/7 critical，整体 PARTIAL。冻结源码与原件检查、完整指标和检查点在 review/current-main-replay-20261110/cn-h1-09.json。
- r4-cn-h1-real 原文 SHA d0dba19e… 的正式 Reader 为 9/12。三项原文单位已解析但未入选，工作账户耗尽。两个样本分别记录，T4/SEM-QUAL-01 继续开放。
- W04 config 旧工区完整归档 25 个 modified/untracked 文件后移除。两个重复别名 ref 已清除。七份过期原始 push 日志压缩后减约 13.80 MiB，四个进程控制 scratch 文件已清除。

本轮源码、工具与测试经独审通过。定向组合先后为 147 passed 和最终补充组合 123 passed，两者有重叠。受影响集成 10 passed，现行配置范围 25 passed，独审另跑 42 passed。详细范围、原失败与留项见 review/current-main-replay-20261110/README.md。

## 2026-11-10 P3 公共 Reader 端口子节点

- CWP `SourceCatalog` 接管原文位置排序和浏览查询：`SourceVersionReader` 不再调用 `_annotate_locations`；`PublicDocumentBrowser` 不再直接执行 SQLite 查询或持有 metadata JSON 字段路径。新增冻结、pathless 的 `CatalogBrowseVersion` / `SourceVersionIdentity` DTO，以及 Catalog owner 查询接口。
- 用 AST 契约测试先验证原有穿透，再验证 Reader 只能调用公开 Catalog 方法、浏览器不能触碰 raw SQL。修复复用 handle 投影遗漏的 source/rank/manifest 字段，避免 Resolver 生成 canonical handle 时缺值。
- 定向边界组合 **66 passed**；浏览、原文复用、入库与锁组合 **52 passed**。扩展修复后最终固定组合 **130 passed**、无跳过；Ruff 通过；mypy 检查 235 个源文件通过。Windows 长路径测试先复现 260 字符处 `os.open` 失败，再覆盖 CatalogOperationLock 完整生命周期；独立审查 PASS，见 review/p3-public-ports-20261110/README.md。
- **此子节点不代表全项目解耦完成。** 截至 11-10，Reader 仍依赖 Resolver 私有预算/字节验证/metadata helper；这些调用于 11-11 子节点迁为公开 owner ports，见下节。旧 stream/canonical 候选不代表当前主线生产缺陷；公开流式 Reader 与 parser 接口仍未完成。

## 2026-11-11 P3 source_catalog 模块边界契约

- 在上一子节点公开 Resolver 读取端口基础上，为整个 `src/company_wiki/source_catalog` 增加 AST 边界契约：生产模块不能跨 sibling 读取私有符号/方法或导入私有模块；owner 的共享 API 必须在 `__all__` 中声明。规则在测试中扫描全包，而不是只测 Reader 几个已知调用点。
- 按独审发现先写 RED 探针并再修扫描器：覆盖直接/别名/局部导入、静态与未知动态导入、`sys.modules` 与反射、敏感模块和 sibling 的 wildcard import、helper/方法/绑定方法别名的参数传递、闭包/nonlocal 捕获、推导式作用域、方法体不查找 class namespace，以及参数重绑定时的误报反控。
- 扫描器契约 **6 passed**；SourceCatalog/Writer/获取范围/身份/摘要资格/读取器/恢复及真实字节 E2E 固定组合 **165 passed in 53.98s**，无跳过。补齐全部新增 owner-port 合同后的扩展组合 **285 passed in 145.11s**，无跳过；两套集合有重叠，不能相加。Ruff 通过。
- 首轮检查发现新的 AST 契约未在 CI 固定合同清单中运行。先给 `test_pre_push_gate.py` 加失败用例，再将该文件纳入 `FAST_CONTRACT_CASES`；清单用例 + 6 个边界测试 **7 passed in 11.01s**。CI 每次提交新增约 11 秒静态边界合同，不运行 145 秒 owner-port/E2E 扩展组合。
- 独立只读复核对最终探针组合给出概念 PASS（审查者未运行测试），并确认 nonlocal、推导式、class namespace 和重绑定反控已覆盖。审查绑定文件 `tests/contract/test_source_catalog_module_contracts.py` SHA-256 `a30dd6eea305b525aac8fbb1b6c1dee6bb117e5bec6455c4118bdccd8914bfc6`。AST 检查是静态 CI 规则，不是 Python 运行时沙箱，也不阻止任意动态代码生成。
- **范围仍有限**：这是 source_catalog 包内模块边界的制度化回归，不表示跨仓整体解耦、公开 streaming/parser ports 或所有其它包的内部边界已完成。下一步仍按 owner 契约迁移 stream/parser，再对其它模块应用同样的 RED/owner-port/组合验证方式。

## 现在的顺序

1. 继续 Dashboard P3。SourceVersionReader、Catalog 与 Resolver 当前可见的 sibling 私有调用已迁到公开 owner ports，并由 source_catalog 全包 AST 合同覆盖；下一步实现单一预算/生命周期的公开流式读取与 parser port。历史 stream/canonical 分支候选要先对当前主线行为重放，不能当作已上线代码的问题。按 owner 公开接口迁移并写隔离测试。
2. R4 工作量分诊已有收据。优先核对占9.05M的业务扫描统一预扣与下层实际计费重叠，增加owner回归并在原16M账户内修复三项遗漏。
3. 完成 T4 父链和 SEM-QUAL-01 反控及真实验收，随后推进新版摘要、同/跨 run 恢复、RF 实际采用和固定公司循环。
4. 核销 source-facts、M3、W04 semantics、R1 observation 与 Dashboard 工区，逐项合并已接受代码和移除已替代状态。

## 工作区快照

11-10 工作区整理以 e7758d54e162d97c7d97f6a76e3af9cd39ca627b 为起点。当前 P3 子节点从 master/origin-master 同步的 0a74c7478b2ffa78cb78547d83416126eeef9a15 开始；本轮仅修改 CWP 实现、契约测试和本计划证据。注册工区最后核实为 8 个（含根）、本地分支 18 个，其中 13 个 tip 非 master 祖先；历史运行产物仍须按 owner 核销。原件、生产配置和各 owner 数据库继续由所属 owner 管理。

## 历史候选与验收记录

## T4/SEM-QUAL-01 候选观察（不是当前主线验收）

- detached candidate worktree 中有 11 个 tracked 文件修改和 12 个 untracked 开发/测试/收据文件；改动横跨来源语义、解析、只读观察和测试工具。它不是一项可直接快进的单一补丁，且未绑定当前主线复验。
- 最近一次相关测试记录：note-scope 91 passed；source-case-runner 20 passed；decoder/source-frame/summary 组合 271 passed；qualifier 专项 17 passed。这些来自不同测试命令，可能有覆盖重叠，不能相加成总数。最终 Ruff 与大节点独审还未完成。
- H1/selection 收据原先只在 detached candidate worktree 的 `.planning` 下；已把五份关键 JSON 收据复制到 `review/source-facts-reconciliation-20261110/`，且五份归档 JSON 的 SHA-256 均与候选 worktree 原件一致。运行状态为 `OBSERVED_NOT_COMPANY_OR_ECONOMIC_ACCEPTANCE`，不能当成公司或财报质量验收。
- 与先前基线相比 native-member 数为 102 对 101；这不自动判失败，也不能忽略，需在收口时解释映射差异并检查 12 个成员/locator。
- 第一次 observer 尝试在读取原件前因 Windows `os.link` WinError 5 失败；改为 Windows 同目录原子 `os.rename` 首次发布后重跑成功。该失败不涉及来源、网络或模型调用。

## D5 接收结果

- 候选实现版本：CWP `a28692a6c49125143d2240b4a6d6df2ba29a28a1`；StockWiki `6d1e40bcdcde5e99488e22c38d57bd8e1b33c27e`。两者均通过快进并入本地主线；StockWiki 当前无 Git remote，无法推送远端。
- ROOT D5 接收 commit 为 CWP `c28b122075748d99547fb0a7e2fd4adcd7490269`；本次 PWF 对账 commit `bd2c9ee328831f80626a216a99a7d503cebcfdd5` 已推送，推送后本机 `master` 与 `origin/master` tracking ref 一致。c28 与 bd2 的 exact-head CI 均未在本次新鲜核实；已知 D4 CI head `e7469d68` 不代替它们的 CI 记录。
- run-6 固定跨仓套件：CWP 13 个处理 port 合同用例、StockWiki 三入口消费与真实样本 E2E 2 例、FF V2/V1 路由 3 例；合计 **18 passed**，无跳过、失败或错误。ROOT runner 定向单测 **15 passed**，Ruff 通过；合并后 CWP 合同测试再跑 **13 passed**。
- 真实只读原件：中大力德投资者关系记录 PDF，113,954 bytes，SHA-256 `ef78655e0980ce0ae50a5c9ab77457a024a9a5999ab4c0dff0556dc144efa4ef`，测试前后 SHA/大小/mtime 一致。隔离 scratch 已恢复。
- StockWiki transport 配置 `config/cwp_source_index.transport.json` 在测试期间 SHA 稳定，并以 Git clean-filter blob 比较确认内容与审查 HEAD 一致；Windows CRLF/LF 转换不误报，真实内容修改仍被回归测试拒绝。候选工作树运行前后均干净。
- 独立最终审查绑定上述准确 HEAD 与 `run-6/report.json`，结论 PASS。审查静态检查 runner 门与报告；runner scope 单测由 ROOT 独立运行 15 项通过。
- D5 没有新建第二套缓存；本次没有证明存在可复用的通用持久化 normalized-unit cache。跨请求/跨运行缓存恢复仍 OPEN，按主线顺序后续验收。

## 以前已关闭

- P0 CI 根因修复：已完成并发布；当前不因历史 CI 失败而重跑长时间全量套件。
- P0-D / D4-01～D4-06：按冻结范围完成，独立审查及强制组合通过。范围详情和历史收据保留在 [D4 closeout](review/d4-closeout-20261104/README.md)。D4 本身不等于 D5；现在 D5 也已经独立验收。

## 后续状态

| 阶段 | 状态 | 顺序与边界 |
|---|---|---|
| D4 + D5 解耦 | **COMPLETE / ACCEPTED** | 只在冻结接口范围内声明通过；版本化接口是预期协作合同，不代表模块零依赖 |
| T4 + SEM-QUAL-01 | **IMPLEMENTED LOCALLY / H1 OBSERVED / FINAL REVIEW OPEN** | 先解释 member 差异、核对 H1 证据，完成一次大节点独审与 scratch 恢复 |
| 新版真实摘要与质量验收 | OPEN / 等 T4 接受 | 用真实材料核查召回、归属限定、财务碎片/套话占位、业务信息遗漏 |
| 缓存恢复 | OPEN / 等新摘要基线 | 付费中断、同 run 与跨 run 恢复；按实际配置记账，不声称 D5 已验证 |
| RF 实际采用 | OPEN / 等新摘要和恢复 | 证明同一摘要 artifact 进入 RF 参数、公式与报告 |
| 固定公司审查循环 | OPEN / 最后 | 依长期目标完成固定名单与新公司泛化，不以局部工程测试替代完整审查 |

继续保留原始文件、历史失败和未跟踪 WIP；D5 的已跟踪代码已在 CWP 主线，StockWiki 已本地并线但无 remote。当前 T4/SEM 改动仍在工作区，不清理其它历史产物，不修改 Dayu/IQS。后续仍只在大节点做独审和组合测试，避免逐小节点增加审查。

## 本轮发布记录

本轮源码和PWF提交729a787641fccdad490f81b34e10669b16385e53已进入master并推送；身份根修28e18043ccad06495a0843760ea46c79e0d2222c已推送，CI42914407976成功。后续 P3 子节点待提交/推送及 exact-head CI 核验。当前历史未跟踪工件计数为上次观察值 13,267 文件、182,457,744 bytes；该数字未在本子节点重测，跟踪文件目前有本轮修改。

## 2026-11-11 Commit-hook failure repaired by owner contract

- The first commit-hook run correctly stopped publication. Ruff and mypy found that the PDF version-identity refactor had removed two sibling module aliases while `_pdf_versions()` still read constants through those names; the existing PDF cache-identity regression reproduced the `NameError` (RED).
- Replaced those references with explicit public constants from the owning modules and exported `PDF_PROSE_LAYOUT_FEATURE_VERSION` from `narrative_evidence.__all__`. The same cache-identity regression plus the source_catalog boundary contract pass 7/7; assertion-owner port and cache-identity targeted checks pass 2/2; targeted Ruff passes.
- Ruff also found one unused local in the new assertion owner-port test; removed it. No hook was bypassed. The full commit hooks have not yet been rerun after these repairs.

## 2026-11-11 P3 milestone committed

SourceCatalog owner ports, package-wide static sibling-boundary contract, fast-CI registration, hook fixes, and the corresponding tests are committed as `e5dd29b1f`. Commit hooks passed Ruff, mypy runtime-source checks, and config doctor. The commit is not pushed yet; exact-head remote CI has not run. The next implementation node is the public stream/parser owner interface, starting with RED contracts.
