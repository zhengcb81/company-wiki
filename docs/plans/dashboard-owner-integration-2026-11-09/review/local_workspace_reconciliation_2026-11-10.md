# P2 三仓并线与本地工作区对账

日期：2026-11-10。范围：CWP、Filing Fetch、Revenue Forecast 的 P2 主线发布，以及当前可见的 CWP/FF/RF 本地分支、工作树和未提交状态。这里只清理了证据明确的重复 P2 checkout 和临时测试副本；未把未知本地内容一概 reset 或删除。

## 结论

- **P2 已全部进入三个 owner 的远端主线。** 每个模块只在自己的仓库发布；没有把 CWP 私有实现搬进 FF/RF。
- **D4/D5 解耦按冻结的验收范围已 ACCEPTED。** 含义是跨模块通过 owner 的版本化公开接口协作并由隔离/组合测试验证；不代表绝对零依赖，也不代表以后不需要修复新发现的问题。
- **本地工作区尚未全部清理。** CWP 根目录仍有大量历史 PWF/审查文件，CWP 还有未合并分支及外部工作树；FF 留有一条已核实为旧 ff-job 候选的归档分支及未跟踪运行产物；RF 有未提交的 assurance 运行结果和其他产物。具体状态见下文，未将它们误报为 P2 代码。

## P2 正式主线

| Owner | 远端主线 | 合并方式 | 本次可确认的测试/CI |
|---|---|---|---|
| CWP | `master` `0fc56b25b89da9f3da5921ba64122d9745e1752d` | 从 `9d7f3de8e5d0` 普通快进 | push smoke 18/18；层边界/文档层隔离/DU 核心隔离 68 passed；本次未确认完整 Actions |
| FF | `main` `f65e6ca75fbce0616e65870f0aea78b793ef883c` | 从 `7d8392eb98c50a6d6d27d06d9d7fabee913fe484` 普通快进 | push hook 11 passed；P2 精确候选的 quality run `42746994685` 有成功记录。主线 push hook 仍写明 full validation pending，未确认该次 main push 的新 run |
| RF | `main` `b005a179280ee19695578bdba9427b4dd44cdd73` | 从 `cd24976a958bc2abee841a592691268b45b117ee` 普通快进 | push hook Ruff + fixed smoke 12/12；完整远端 Actions 本轮未确认 |

FF/RF 原 P2 candidate 分支保留在远端，提交 SHA 与主线相同。本机对应 P2 worktree 和 local candidate branch 已移除；没有删除远端候选分支。RF 本机 `main` 已快进至 `b005a179`，CWP 本机 `master` 与远端一致。

E2E 原件、SHA、复用零下载及 MDB 公共目录读回仍以 [P2 E2E receipt](../validation/p2_cross_market_e2e_receipt.json) 为准。MDB 报告仍有 1 条 partial citation（无 locator）与 10 条 quality gaps；入册不等于证据无缺口。

## 模块化/解耦状态

`du11-source-closure-2026-10-18/CURRENT_STATUS.md` 记录 D4/D5 为 COMPLETE/ACCEPTED：CWP 的规范化文档 port、StockWiki 消费入口和 FF V2/pathless 主路径使用公开合同，D5 跨仓组合为 18 passed / 0 skipped，并有独立最终审查。该验收只对冻结的接口与样本范围成立。当前 Dashboard 计划的 P3 Reader 流式与原生 PDF 端口、P4 Dashboard 实际消费切换仍未完成；D5 不能用来宣称整个产品集成全部结束。

## 本次确认并清理的重复目录

- 删除四个 `%TEMP%` 中的旧 CWP 测试 worktree：`company-wiki`、`cw-baseline`、`cw-preb`、`r4b02-preb02`。清理前均为仅含 tracked deletions、无 untracked/ignored 文件；每个 HEAD 都是 `origin/master` 的祖先；`companies/`、`sectors/`、`themes/` 共检查为 0 个文件。因此没有从这些副本删除原始公司资料。清理了 14,498 条临时 worktree 删除状态。
- 删除 FF/RF 两份已经并线的 P2 本机候选 worktree 与本地 ref。它们工作树干净，仅有 Python/test caches；各自 P2 commit 已是 `origin/main` 的祖先。远端 candidate ref 保留。
- 删除 CWP 两个没有工作树、且提交系列已由 `origin/master` patch-equivalent 覆盖的 local refs：`codex/r1-contract-debt` 与 `codex/r1-summary-runtime`。
- 另删除 14 个已并入 `origin/master`、无 tracked/untracked 改动、没有 `companies/sectors/themes` 数据目录的本地 worktree 与对应 local branch refs：`d4-01-company-source-index`、`d4-03-document-model`、`d4-04-transcript-wire`、`d5-cwp-processed-port`、`du-benchmark-20261013`、`du-profiles-20261013`、`du4-form-20261015`、`du4-state-20261015`、`du4-table-20261015`、`du5-corpus-20261015`、`du7-pdf-tables-20261016`、`du9-geometry-planner-20261016`、`du9-geometry-policy-20261016`、`main-replay-config-isolation-20261009`。删除前核对的 ignored 内容只有 Python/pytest 可再生成缓存；远端分支一律保留。
- 再删除 7 个同样满足“提交在主线、工作树干净、无公司数据目录”的本地 checkout/ref：`r1-holdout-controller`、`w05-cwp-ocr`、`w18-cwp-holdout-20261025`、`w19-sina-statements-20261025`、`w22-atomic-io-20261030`、`root-du67-pdf-20261016`、`w22-pdf-deploy-20261030`。最后两个额外核实了 `.ingested/ingested.db` 仅有 0 行表，以及 `w22probe-m0qvqkpo/s.pdf` 是未被任何计划引用的 2.1 KB 临时测试文件；目录中的其余 ignored 项都是缓存。完整 handoff/evidence 已在 CWP 主线，远端 refs 未删除。
- 再移除 `_w22r` 收口工作树：该分支已在主线，tracked 内容干净，唯一 48 个未跟踪文件是 4.2 KB `.cg-tmp` CodeGraph 测试夹具；相关独审/PWF 已提交在主线。先核对路径与文件类型后仅删除该临时目录，再正常移除 worktree/ref。另移除 DU3 quality 的干净重复 checkout/ref：4 个提交全部 patch-equivalent、无原件目录、只有可重建缓存。

没有实测磁盘空闲量变化；工作树可能含硬链接，逻辑文件大小不能当作物理释放空间。

## CWP 根目录剩余状态

当前 CWP `master`=`origin/master`=`0fc56b25b89da9f3da5921ba64122d9745e1752d`。本次 PWF 更新前 Git status 有 14,025 条（3 个既有计划文件修改、14,022 条未跟踪）；加入本次 owner 状态对齐和本审计文件后，提交前为 14,028 条（5 个已修改计划文件、14,023 条未跟踪）。本次 PWF 提交后，计划代码差异归零；约 14,022 条历史/本地未跟踪状态仍保留，主要是：

- `.planning` 约 13,876 个 Git status 项，含 119 个直接子目录和大量历史运行/验收材料。`.planning/c3-20261028` 约 90,467 个文件、2.16 GiB 逻辑大小；其中 `pdf-sdk-isolated/env` 是 W21/W22 计划明确复用的 104 distributions 隔离环境，约 36,151 个 hardlink、1.18 GiB 逻辑文件、当时实际新增 scaffold 约 517 KB。不能把逻辑大小当作实际新增磁盘，也不应重建或删除该环境。
- `.planning/c3-20261028/rf-use-compat` 是干净的 RF 独立 checkout，HEAD `0991e25d` 已包含于 RF 远端主线；但历史 PWF 明确说它要留到最后兼容集成完成，故未删除。`stockwiki-use-compat` 的主线/远端关系也未在本轮确认，保留。
- `docs/plans/du11-source-closure-2026-10-18/review/` 下 143 个审查/运行证据文件，约 17 MB；保留为历史验收材料。`tools/document_understanding_benchmark/gold/us-10k.du11-v2-20261024.json` 被既有报告按 SHA 引用，保留为 benchmark fixture。`.workbuddy-ai/memory/2026-11-02.md` 是 D4-03 交付记忆，保留。
- `.worktrees/d00-e13-owner-integration` 是干净 P3 候选 `62602102ae5ab9a6bba54879756b800854c941a1`，与 `origin/codex/d00-e13-owner-integration-20261107` 相同但尚未并入主线；P3 仍待接线，保留。

当前 CWP 共有 68 个已登记 worktree（含根目录），51 个外部 worktree clean，16 个 dirty，0 个无法读取；本地分支共 65 条，其中仍有 22 个 tip 不是 `origin/master` 的祖先。16 个 dirty worktree 的状态：

| Worktree | 状态摘要 | 本轮处理 |
|---|---|---|
| `.codex/worktrees/du11-extractive-runtime/company-wiki` | 81 个 file-level untracked，仅 `.planning` 输出 | 保留，待按对应 PWF 核对 |
| `.codex/worktrees/du11-source-facts/company-wiki` | 11 条 tracked source/test 修改 + 12 条本地文件 | 保留，可能关联 T4，不作为 P2 处理 |
| `.codex/worktrees/m3-acceptance-20261010/company-wiki` | 22 条 tracked 修改 + 317 个 file-level untracked，含 `.planning`、docs、src、tests | 保留，需按 M3 交接审查 |
| `.codex/worktrees/m3-acquisition-usage-20261010/company-wiki` | 3 个未跟踪 W06 PWF 文档 | 保留，核对是否已归档进 canonical plan |
| `.codex/worktrees/w04-llm-config-scope-20261011/company-wiki` | 3 条 tracked 脚本/测试修改 + 22 个新增用例/PWF文件 | 保留，需比对主线和 W04 PWF |
| `.codex/worktrees/w04-narrative-semantics-20261011/company-wiki` | 3 条 tracked 叙述代码/测试修改 + 92 个新增 PWF/docs/evidence 文件 | 保留，需比对主线和 W04 PWF |
| `_harness_worktrees/document-reading-review-20261013/facets` | 1 个 `bindings.local.json` | 保留本机绑定配置 |
| `_harness_worktrees/document-reading-review-20261013/families` | 1 个 `bindings.local.json` | 保留本机绑定配置 |
| `_harness_worktrees/w06/cwp-acquisition-scope-root` | 3 个未跟踪 PWF 文件 | 保留，核对后可归档 |
| `_harness_worktrees/w06/cwp-portability` | 6 个 handoff/input 文件 | 保留，输入来源未核销 |
| `_harness_worktrees/w08/cwp-g2-replay` | 12 个未跟踪 PWF/合同/receipt 文件 | 保留，核对是否已归档进 canonical plan |
| `Projects/company-wiki-r1-local-observation` | 98 条 tracked 文件变化 + 566 个 file-level untracked（PWF/审查/运行证据） | 保留；属于较大 R1 观察/证据集，不能当临时产物丢弃 |
| `Projects/company-wiki-w23-xiaomi-ocr` | 47 个文件，5.27 GB `.w23_cache/hub` 模型快照 | 明确为 W23-R1 共享模型资产，PWF要求复用并留存；不误删为普通缓存 |
| `Projects/company-wiki-w23-xiaomi-ocr-r1` | 19 个文件，116 KB `.w23_cache/r1_cache` 结果缓存 | 保留以支持已记录的缓存恢复/复验；不是模型权重 |
| `Projects/investment-dashboard/.worktrees/b34-cwp-prospectus` | 5 个 XML 测试收据，81 KB | 保留测试证据，等待 Dashboard owner 对账 |
| `Projects/investment-dashboard/.worktrees/return5-cwp-audit` | 8 个 JSON/Python 审计证据，72 KB | 保留审计证据，等待 Dashboard owner 对账 |

仍有 23 个 CWP local branch tip 不是 `origin/master` 的祖先：

`codex/d00-cwp-canonical-calendar-fix`, `codex/d00-e13-owner-integration-20261107`, `codex/d00-return5-cwp-audit`, `codex/dashboard-b33-cwp-source-proof`, `codex/dashboard-cwp-b34-diagnostic`, `codex/dashboard-cwp-b34-prospectus`, `codex/dashboard-cwp-canonical`, `codex/dashboard-cwp-exact-reader`, `codex/dashboard-cwp-public-browser`, `codex/dashboard-cwp-readiness`, `codex/dashboard-cwp-return4-d00-fix`, `codex/du3-dependencies-20261014`, `codex/du3-geometry-20261014`, `codex/g1-legacy-entry-retirement`, `codex/n4t2-selective-narrative-coverage`, `codex/p5-storage-retirement`, `codex/rf-state-audit`, `codex/w13-cwp-gates-20261024`, `codex/w21-pdf-runtime-20261029`, `codex/x-c04-current-main-compat-01`, `codex/x-c04-cwp-original-stream-01`, `codex/x-c04-integrity-repair-01`.

这 23 个不能用 ancestry 状态直接判断为未完成或可删除：部分是 Dashboard P3 候选或仍有唯一改动，部分已 patch-equivalent，部分仅文档/审计。各分支在最终处理前要确认对应 PWF/handoff、当前 worktree dirty 状态及主线内容；本次没有 bulk merge 或 bulk delete。

## FF/RF owner 根目录剩余状态

- FF 本机 `main` 已对齐远端 `f65e6ca75fbce0616e65870f0aea78b793ef883c`。原七提交 `a34f60e`…`154c292` 保存在 `codex/ff-job-facade-01`；独立交接和审查显示它是完整 ff-job 候选，且远端当前主线已包含同一 CLI 入口及更新后的实现/测试。因此没有把旧代码重复 cherry-pick；历史分支暂保留供追溯。自动审批第一次拒绝 reset，是因为当时尚未证明这七项改动如何保留；核对远端树和确认备份分支后，正常 reset 成功，未绕过审批或删除提交。FF 根目录仍有 304 项未跟踪状态，主要含 `.ff_jobs`、`.mimosa`、`.planning`、`.worktrees`、pytest 输出、可重建缓存与 `config/FMP_API_KEY.txt`；API key 内容未读，未对这些材料做批量删除。
- RF 本机 `main` 与 `origin/main` 均为 `b005a179`。4 个 tracked 修改是 `assurance/runs/daily_alert.jsonl`、`weekly_alert.jsonl` 和两个 manifest，记录 2026-10-06 至 2026-11-09 的 daily canary `bound=0 events=473`，weekly T3 run 持续 exit 1；monthly manifest 已更新至 2026-11-01、weekly manifest 至 2026-11-08。它们是运行失败证据，不是 P2 代码，未回滚、未提交；应由 RF owner 单独调查。
- RF 另有约 5,867 个未跟踪状态，主要为 `.mimosa`、`.planning`、`.worktrees`、delivery 和 output。它们包含此前的研究/交付或运行材料，不在本轮删除。

## 尚未完成的清理

1. 继续按各自 PWF 对 CWP 17 个 dirty worktree 与 23 个非祖先 branch tip 分类；完成任务的提交/并线，过期日志和缓存仅在确认无输入、无唯一收据后清理。
2. RF 的 assurance 失败是单独问题；保留证据并由 RF owner 查明 canary 绑定数为零的根因，不用本轮 P2 变更掩盖。
3. `.planning` 大型旧结果按引用与 owner 收据分批裁剪。先保留仍被 W21/W22、D5、M3/R1 handoff 明确依赖的运行物；不要用 `.gitignore` 或索引排除来伪装成“清理完成”。
4. FF 的本地主线已经对齐；待其未跟踪材料逐项核销后，再决定旧候选分支是否保留为归档，不能把“文件已被 Git 忽略”当成清理证据。
