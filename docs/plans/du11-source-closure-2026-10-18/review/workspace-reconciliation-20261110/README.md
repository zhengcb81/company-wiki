# 本地工作区核销 — 2026-11-10

## 22:05 UTC 更新

W04 config 的 25 个修改/未跟踪文件和 binary patch 已逐文件核 SHA，归档在 w04-config-author-package。当前 Config.load(validation_scope="llm") 已承担其职责并通过 25 项现行测试，旧工区与已并线本地分支已经移除。

重复别名 codex/d00-cwp-canonical-calendar-fix 与 codex/dashboard-cwp-readiness 已删除，全部 commit 分别由 codex/d00-return5-cwp-audit 和 codex/dashboard-cwp-return4-d00-fix 保留。现在有 8 个注册工区、20 个本地分支、15 个非祖先分支。

七份原始失败 push 日志从 15,896,545 bytes 压缩为 1,430,555 bytes，完整 gzip 已往返核验，原文件删除。路径与 SHA 映射见 retired-push-logs/manifest.json。另清除四个旧进程测试控制文件，共17bytes。已解释产物随本次提交归档，剩余运行产物继续逐项核销。

门禁与解析边界的新增修复和两份真实半年报复验见 ../current-main-replay-20261110/README.md。本节覆盖较早快照的状态数字。

## 20:49 UTC 复核更新（覆盖较早快照的当前值）

- CWP 代码盘点基线 `master == origin/master == 5d4b4f4b6ea70f703ca7710d65e3a27d158f62a5`；FF `main == origin/main == f65e6ca75fbce0616e65870f0aea78b793ef883c`；RF `main == origin/main == b005a179280ee19695578bdba9427b4dd44cdd73`。三个 Dashboard owner P2 提交均在各自 main 中。以上是本地 refs 对账，没有在这次快照声称新鲜查询 GitHub 服务端；随后的本次提交只更新 PWF，不改产品代码。
- CWP tracked worktree clean；9 个注册 worktree（含根）、23 个本地分支、17 个 tip 非 `master` 祖先。
- 当前未跟踪文件精确枚举为 13,279 个、198,372,372 bytes（189.19 MiB）：`.planning` 13,134 个/181,178,404 bytes；`docs` 143 个/17,173,810 bytes；`tools` 1 个/18,066 bytes；`.workbuddy-ai` 1 个/2,092 bytes。不能仅因未跟踪就删除。
- 本轮核实 269 个根仓标准 Python/pytest/mypy/ruff 缓存候选；268 个可重建 cache 目录已清除（8,349 文件、182,104,966 logical bytes）。其中一个位于名为 `.pytest_cache` 的 tracked test fixture 目录；初次清理误删该 19-byte fixture，随后按 index checkout 规则恢复并验证内容无 diff，因此该目录保留且不计入净清理数。另含此前 `.planning` 已移除的 1,746 个缓存目录（7,891 文件、158,237,631 logical bytes）。合计净清理 2,014 个 cache 目录、16,240 个文件、340,342,597 logical bytes（324.58 MiB）；逻辑大小不代表物理盘准确释放量。PDF SDK 环境、真实 run/paid evidence、原文、生产配置未清理。
- 剩余 CWP worktree 状态最新只读计数：extractive runtime `0 tracked / 81 untracked`；source-facts `11 modified / 12 untracked`；M3 acceptance `22 modified / 317 untracked`；W04 config `3 modified / 22 untracked`；W04 semantics `3 modified / 92 untracked`；R1 observation `98 modified / 566 untracked`。Dashboard 的两个 owner worktree 分别有 5 与 8 个未跟踪文件，仍需在各自 P3/P4 归属下核销。没有对上述工区进行 checkout、修改或清理。
- 失败分类已在[根因对账](../failure-root-cause-reconciliation-20261110.md)中单列：10 个归并根因类别不是 10 次尝试；4 个真实正常结果误拒，另有 1 个合法 error DTO 旧 schema 拒收。2 个明确过度设计检查已移除；错误 registry gate 和观察器故障也已修，不应再反复修同一旧收据。真实资源和来源事实约束仍有效。

下面未加时间标记的清理与跨仓盘点段落是更早的工作底稿；遇到数字冲突时，以本复核更新和 [CURRENT_STATUS](../CURRENT_STATUS.md) 为准。

## 结论

- Dashboard owner-integration **P2 已完成**，CWP、FF、RF 对应提交均已进入各自 owner main，且本机 main 与配置的 `origin/main` 同步。E2E 收据：[`p2_cross_market_e2e_receipt.json`](../../../dashboard-owner-integration-2026-11-09/validation/p2_cross_market_e2e_receipt.json)。
- 主线循环计划中另一个 **RF 实际采用 P2 仍 OPEN**：要求证明同一份已接受摘要实际进入 RF 原生参数/公式，须先完成 P1。两个 P2 不矛盾，只是不同阶段复用了编号。
- D4/D5 已按冻结公开接口和组合测试范围 ACCEPTED（18 passed、0 skipped）。这不是“整个系统零耦合”，也不代表 Dashboard P3/P4、PDF Reader 端口或全部跨仓流程完成。
- 本次做了有证据支持的清理，但**整个本地工作区仍未清干净**。没有删除任何原始公司文件。

## 主线复核

| 仓库 | 当前 owner main | upstream | 状态 |
|---|---|---|---|
| company-wiki | `master` `2862fe951f08547cba9bd8b39ec5e13c5dc286c9` | `origin/master` 同 SHA | tracked clean；P2 提交包含在内 |
| filing-fetch | `main` `f65e6ca75fbce0616e65870f0aea78b793ef883c` | `origin/main` 同 SHA | tracked clean；P2 提交包含在内 |
| revenue-forecast | `main` `b005a179280ee19695578bdba9427b4dd44cdd73` | `origin/main` 同 SHA | P2 提交包含在内；4 个 tracked 差异是 assurance run 日志/manifest，不是源码，保留待核 |

StockWiki 的 F05 模块边界改造已在本地提交 `12c441e86282135b49120112dcf21c17509bbdd0`，定向测试及 lint 已通过；该仓没有 Git remote，因此不能推送。它的 7 个 SQLite、run、日志未跟踪项仍需确认所有者/用途，未删除。

## 本轮已归档并清理

下列 7 个 CWP linked worktree 的代码 tip 均为当前 CWP `master` 的祖先。先归档或核实唯一内容，再删除工区和相应**本地**已并线分支；没有删除远端分支。

| 工区/分支 | 处置及依据 |
|---|---|
| `w06/cwp-portability` / `codex/w06-cwp-portability` | 将交接声明的 6 份输入原件（18,343 bytes）原样归档到 [`docs/handoffs/w06-cwp-portability/input/`](../../../../handoffs/w06-cwp-portability/input/)，逐文件 SHA-256 与原件相同；修复了交接输入路径原本不存在的问题。 |
| `w06/cwp-acquisition-scope-root` / `codex/root-w06-cwp-acquisition-scope-20261011` | 3 份未跟踪 PWF（17,206 bytes）归档到 `phase6/w06-cross-period-acquisition-root/author-pwf/`。实现提交已在 master；作者报告 191 项通过，但原 41-case ROOT 验收仍 OPEN。 |
| `w08/cwp-g2-replay` / `codex/w08-cwp-g2-replay` | 完整归档 79 个文件、1,136,943 bytes 到 [`author-package/`](../../../cross-market-rf-e2e-2026-10-08/phase6/w08_parallel_completion_2026-10-12/evidence/author-package/)，逐文件 SHA-256 匹配；包含冻结 CWP/RF 输入、三次报告和发现记录。没有复制到正式资料库的原始财报。 |
| `company-wiki-w23-xiaomi-ocr-r1` / `codex/w23-ocr-r1-20261031` | 19 份 derived cache JSON（116,519 bytes）归档到 [`W23 R1 cache`](../../../w23-xiaomi-ocr-2026-10-30/evidence/r1-cache/)；额外 1,152 个 Python bytecode cache（30,923,099 logical bytes）随旧工区移除。 |
| `w06/cwp-acquisition-scope-root`、`w06/cwp-portability`、`w08/cwp-g2-replay` | 其余 ignored 内容检查为 pytest/ruff/mypy 缓存；本轮已移除对应旧缓存。原件、生产配置和密钥未动。 |
| `document-reading-review/facets`、`families` / 两条 DU2 分支 | 两个分支均已并入 master；移除的仅是机器本地 `bindings.local.json`（2,171 与 3,819 bytes）和 pytest cache。正式卡片/交付在根仓仍可用。 |
| `m3-acquisition-usage` / `codex/m3-acquisition-usage-20261010` | 功能提交 `d65e421cb` 已并入 master；删除仅含早期“冻结 DTO”下一步的 3 份草稿，没有未提交代码或最终测试证据。12 KB 空表 `ingested.db` 经只读检查为 0 rows。 |

另：W23 原试验工区此前已确认其 Qwen 模型缓存非共享链接、试验未进生产，并删除约 5.27 GB 模型/派生产物；系统盘可用空间当时实测增加 `5,267,775,488` bytes。该空间读数是当时实测，不把本轮逻辑文件大小当作物理释放量。

## CWP 当前本地盘点

- 当前 `master == origin/master == 2862fe951f08547cba9bd8b39ec5e13c5dc286c9`；根工区 tracked dirty = 0。
- `git ls-files --others --exclude-standard` 当前列出 **14,067 个文件、253,830,848 bytes**。这包括 PWF、测试/运行证据和本轮新归档；没有把它们统一当垃圾。
- 当前注册工区 9 个（含根目录）；本地分支 52 个，其中 17 个 tip 不是 master 祖先。非祖先不等于必需合并，也不等于可删，仍要按 PWF、提交和测试证据判定。
- 剩余 8 个外部工区：

| 工区 | 本地状态 | 当前判断 |
|---|---:|---|
| `.codex/worktrees/du11-extractive-runtime/company-wiki` | 0 tracked / 81 untracked | 129 个 W04–W08 PWF/script 快照仍待对账；暂留 |
| `.codex/worktrees/du11-source-facts/company-wiki` | 11 tracked / 12 untracked | 活跃候选；先按 PWF 做当前主线零模型 replay，不直接合并 |
| `.codex/worktrees/m3-acceptance-20261010/company-wiki` | 22 tracked / 317 untracked | 含 W04/M3 重叠候选代码与大量证据；逐文件区分已被当前主线替代、仍有价值的测试/记录 |
| `.codex/worktrees/w04-llm-config-scope-20261011/company-wiki` | 3 tracked / 22 untracked | 有 `STOP_READY_FOR_ROOT_INTEGRATION` handoff；与 M3 的 3 个核心文件字节相同，需在当前主线验证后统一接收 |
| `.codex/worktrees/w04-narrative-semantics-20261011/company-wiki` | 3 tracked / 92 untracked | 语义候选；未发现最终 handoff JSON，先对照当前实现与测试，不据旧代码覆盖新主线 |
| `Projects/company-wiki-r1-local-observation` | 0 tracked / 566 untracked | R1 的观察/PWF 工件；需与已提交的 canonical R1 计划逐项比对 |
| `investment-dashboard/.worktrees/b34-cwp-prospectus` | 0 tracked / 5 untracked | 非祖先 Dashboard 分支，虽有提交和测试报告，未并入本次 P2；单独审查归属及是否已被当前 parser 替代 |
| `investment-dashboard/.worktrees/return5-cwp-audit` | 0 tracked / 8 untracked | 非祖先 Dashboard 分支；其测试/审计证据及代码尚未核销，不删除或并线 |

另有 15 个非祖先本地 ref 未由上述 2 个工区覆盖：`codex/d00-cwp-canonical-calendar-fix`、`codex/d00-e13-owner-integration-20261107`、`codex/dashboard-b33-cwp-source-proof`、`codex/dashboard-cwp-b34-diagnostic`、`codex/dashboard-cwp-canonical`、`codex/dashboard-cwp-exact-reader`、`codex/dashboard-cwp-readiness`、`codex/dashboard-cwp-return4-d00-fix`、`codex/du3-dependencies-20261014`、`codex/n4t2-selective-narrative-coverage`、`codex/rf-state-audit`、`codex/w13-cwp-gates-20261024`、`codex/x-c04-current-main-compat-01`、`codex/x-c04-cwp-original-stream-01`、`codex/x-c04-integrity-repair-01`。未先核对 PWF/远端/patch 等价性，不批量删。

## 相关仓库的本地变更

- **FF**：`main` 与 `origin/main` 同步，tracked clean；304 个未跟踪项，主要为 205 个 `.mimosa` 状态文件、87 个 pytest 临时文件、9 个 `.ff_jobs` 记录。`config/FMP_API_KEY.txt` 存在但未读取，按秘密配置保留。运行/任务收据须先核其是否仍被使用。
- **RF**：`main` 与 `origin/main` 同步；4 个 tracked 差异位于 `assurance/runs/` 日/周 alert 和 manifest。另有 5,867 个未跟踪项，主要为 `.mimosa` 5,005、`delivery` 582、`output` 147、`.planning` 133；它们可能是近期真实运行的故障证据，先保留。
- **StockWiki**：F05 模块边界改造已本地提交，测试已验；没有 remote，不可推送。7 个本地 DB/log/run 文件没有归档或删除，以免丢正在使用的数据。

## 下一步

1. 依当前唯一主线先跑 source-facts 当前 master 小范围零模型 replay；只在缺口复现时修 owner 层。
2. 集中对照 M3/W04 三个相互重叠工作区的源文件、handoff、测试证据与当前 master，决定单一接收、记录 superseded 或删除；不跨 owner 复制旧版本。
3. 清点 R1 observation、extractive runtime 的 PWF 快照和 CWP 根下 14,067 个 untracked 项；优先删除已被 canonical 收据完整替代的重复运行日志/缓存，保留原始样本与必要验收证据。
4. 按提交/PWF/远端逐项核销 17 个非祖先本地 ref，以及 FF/RF/StockWiki 状态文件；每次只清理已证实范围。
5. 再复核 `git status`、worktree、branch 和上游同步，更新本文件与 `CURRENT_STATUS.json`；只有所有残项都有“已并入/已归档/已证明可删”结论，才把 `cleanup_complete` 改为 true。

本轮没有运行产品测试：仅做只读 Git/文件盘点、SHA 归档核对和 SQLite schema/row-count 查询。也没有改写任何产品代码。

## 22:18 UTC 追加核销

DU3-dependencies分支交付的25个源码/测试/PWF路径与master逐blob一致，六个早期提交可按patch-equivalent核对。旧本地ref ef59a574bfe6525e6d7dc1c123b2e9294e00ea5e已清理。RF-state-audit旧ref447d1c74b78bec369ff5dc32fe78097905ce6342只含初期可见性不全的报告，main11b6472c3已有完整正式报告，旧ref已清理。当前工区8个、本地分支18个、非祖先13个。
