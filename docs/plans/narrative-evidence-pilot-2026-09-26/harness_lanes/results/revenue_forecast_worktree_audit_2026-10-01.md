# RF 本地未提交状态只读审计报告（2026-10-01）

> 对应施工卡：`harness_lanes/revenue_forecast_worktree_audit_2026-10-01.md`。
> 本报告为只读取证与分类结论，**不是删除授权，也不执行任何并线/清理**。全程 RF 仓库只读（所有 Git 命令带 `GIT_OPTIONAL_LOCKS=0` 且无任何写性命令）；除本报告文件外未创建、修改、移动或删除任何文件。

## 1. 方法与环境

- 环境：Windows，git 2.51.2.windows.1；引用命令均加 `-c core.quotepath=false` 以完整解析路径；`status` 用 `--porcelain=v1 -uall` 展开全部 untracked 路径（与快照口径 404 一致）。
- 读取范围：RF 根 `C:\Users\郑曾波\Projects\revenue-forecast`（fcap）、`Projects\rf-impl`（main）、`AppData\Local\Temp\rfv2-tdd-20260927`（reader）、`AppData\Local\Temp\rf-merge-review-20260927`（assurance-merge）；及 `.planning/2026-09-19-three-project-history-audit/` 冻结件与运行目录。
- 冻结输入快照与开工实测**一致**：root `fcap@ee0a82bf`（12 tracked 修改 / 404 untracked）、local `main@415d8eb3`（rf-impl 干净）、reader `codex/revenue-source-reader@3b00b938`（rfv2-tdd worktree 干净）、`codex/rf-reader-v2-20260929@415d8eb3` = main 同提交。**无快照偏差**。

## 2. 起止 Git 状态快照与分支拓扑

| 项 | 开工实测（2026-10-01） |
|---|---|
| 根工作树 | `fcap@ee0a82bf`；`12 M + 404 ??`（porcelain -uall） |
| rf-impl | `main@415d8eb3` 工作树**干净**（0 状态项） |
| rfv2-tdd（reader） | `3b00b938` 工作树**干净**（0 状态项） |
| rf-merge-review（codex/rf-assurance-merge-20260927） | `3a69f9c5`；状态报 41 `D` —— 与 21 个 "Filename too long / Permission denied" 警告对应，属 **Windows 长路径可见性缺陷造成的假删除**，非真实状态（详见 §5 可见性限制） |
| origin/main | 停在 `3a69f9c5`，落后本地 main 3 个提交（未见 push） |

分支拓扑（merge-base 实测）：
- `merge-base(main, fcap) = ee0a82bf = fcap tip` ⇒ **fcap 提交历史是 main 的祖先**：`main..fcap = 0`、`fcap..main = 4`。main-only 四提交：`3a69f9c5`(assurance 合并复审) → `8b11b0ce`(scenario bytes) → `88b3bda3`(release readiness 门) → `415d8eb3`(verified reader)。这些四提交累计净改动 157 文件 +41,074/−382（含 release-readiness 大改与 reader 落主线）。
- `merge-base(codex/revenue-source-reader, main) = 3a69f9c5`；reader 分支 = main 历史上的 `3a69f9c5` + 1 个分支提交 `3b00b938`（`main..reader = 1`，`reader..main = 3`）。
- `codex/rf-reader-v2-20260929 = 415d8eb3 = main`，同一提交，**无独立内容**。
- 正式计划记录确认（progress Round 122）：**"revenue-forecast 推送并入主线：fcap → main = ee0a82bf（门禁 GREEN ×2）· fcap 分支同步备份 ✓"** —— fcap 已提交内容已被主线吸收并登记。

## 3. 12 个 tracked 变化逐项结论

由于 `main..fcap = 0`，fcap 已提交版本 = main 分支已含版本；下述均为**工作树相对 fcap/main 的未提交改动**。

| # | 路径 | diff | 引用/证据 | 分类 | 建议 | 置信 |
|---|---|---|---|---|---|---|
| 1 | `.planning/…audit/OWNER_DECISIONS.md` | +46 行 | Round 121–123 三段追记（§四十一 dayu 归属规则、§四十二 cw 门禁+closure_ready P2 放宽、Round 121 链 15/15 收官） | 计划/阶段证据（正式账本） | **commit**（下轮四步提交主体） | 高 |
| 2 | `.planning/…audit/REMEDIATION_REGISTER.md` | +68/−1 | 新增回合行 L4130–L4133（三新工位 ACCEPT 记账 + §165 复审收尾） | 计划/阶段证据（正式账本） | **commit** | 高 |
| 3 | `.planning/…audit/findings.md` | +22 | 追记父侧错误 #40/#41（棘轮口径两错）+ 纪律 23 候选 | 计划/阶段证据 | **commit** | 高 |
| 4 | `.planning/…audit/progress.md` | +37 | Round 121（Phase 7 COMPLETE/四步提交 ee0a82bf）、Round 122（三件收口+r并行+棘轮在飞）、Round 123（§四十二 执行完+三仓定案 "rf ✅ 已并主线"） | 计划/阶段证据 | **commit** | 高 |
| 5 | `.planning/…audit/task_plan.md` | +2/−2 | Phase 7 状态行 "COMPLETE 15/15" 刷新 + 七条行 7✅ | 计划/阶段证据 | **commit** | 高 |
| 6 | `assurance/runs/daily_alert.jsonl` | +1 | 2026-09-27 例行 T2 runner 告警条目（run_id 20260927T210002Z，stale/not-ok） | 运行产物（告警账本，按时间戳追加） | **commit**（作为观测记录随账本走；否则 next runner 将在旧账上继续） | 中高 |
| 7 | `assurance/runs/weekly_alert.jsonl` | +1 | 2026-09-27 T3 周任务 exit 1 条目 —— 正是 T3-DIAG 工位诊断的**真实产品信号**（progress Round 121 "外部周任务失败作真实样本"） | 必须保留的审计证据（与 T3-DIAG 运行目录互证） | **commit** | 高 |
| 8 | `assurance/runs/weekly_manifest.json` | ±5 | latest_run_id→20260927T033001Z，triplet revenue→`b7a6a116`（= 提交前预检中登记的 fcap 处于该状态的 tree/HEAD hash，见 register §L2948 "HEAD=b7a6a116"），wiki→`dbe4745` | 运行产物（跨仓 hash 三元组账本） | **commit** | 中高 |
| 9 | `assurance/runs/monthly_manifest.json` | ±6 | latest 20261001T182300Z（**10-01 当日**），triplet revenue=`ee0a82bf`、wiki=`b0fd763`、filing=`d35b6f5b` | 运行产物（月任务账本，最近一次更新在本审计窗口内） | **commit** | 中高 |
| 10 | `assurance/unified_completion/uc/scenarios.py` | +62/−6 | DEF-I00C-GATE-NEG 根因修复（`_evidence_problems` 三重校验）+ §四十二 裁定二的 `closure_ready` P2 放宽（有 evidence_path 才校验 hash） | **有效实现**（owner 已裁定的修复） | **commit（但注意：与 main 版本有真实分叉，见下方 ⚠）** | 高 |
| 11 | `assurance/unified_completion/uc/closure.py` | +13 | 配套闭合面小改（同一缺陷卡修复） | 有效实现 | **commit（同 ⚠）** | 高 |
| 12 | `assurance/unified_completion/tests/test_scenarios.py` | +71 | 同卡测试（九例负例 + 复审变体；Round 123 "test_scenarios.py 11 passed"） | 有效实现/test | **commit（同 ⚠）** | 高 |

**⚠ 关键整合风险（#10–#12）**：这 3 个数据/测试件写于 fcap 基之上；main 在 `3a69f9c5`/`8b11b0ce` 之后已先行改动同一目录（`diff fcap..main` 在 `assurance/unified_completion` 内含 7 文件 +241/−503，scenario_registry.json、cli.py、test_closure.py 等 main-side 前进）。即 **fcap 工作树的 closure/scenarios 修复与 main 现行版本存在双向分叉，不是纯追加**；并线前需在 main 基上做三方合并/重放并跑 `tests/test_scenarios.py` + 九例负例回归（9/9 拒 + 恒红解除），不能直接覆盖 main。

## 4. 404 个 untracked 路径全量对账

### 4.1 顶层分组（与快照一致：353 `.planning` + 45 `.tmp-r41-mutation` + 其它 6）

| 组 | 路径前缀 | 数量 | 字节（实测文件之和） | 扩展名主导 | 时间范围 | 引用情况 |
|---|---|---|---|---|---|---|
| A | `.planning/2026-09-19-three-project-history-audit/execution_runs/**` | 353（+2 个引号路径，合并计入 = 355） | 41,866,327（§4.2 分账） | py/json/log/md | 2026-09-26 ~ 09-27 | 全部被本轮 PWF 文档逐 run 引用（见 4.2） |
| B | `.tmp-r41-mutation/**` | 45 | 1,154,149（du） | py（scripts/ 全镜像 + 2 test） | mtime ≈ 09-20 18:31 | task_plan L877/L968/L1101/L1620、register：多卡明确其为 **T1-5 遗留、非本卡产物、"保留不删"** |
| C | `assurance/runs/weekly-run-20260927T033001Z.log` | 1 | 3,684 | log/log | 09-27 | **被已 tracked 的 `weekly_manifest.json` `report_path` 直接引用** |
| D | `assurance/unified_completion/manifests/plan_inputs.json.bak` | 1 | 11,916 | bak | ≈09-21 | register 多次点名 `plan_inputs.json.bak` "不可能是本卡产物…一律保留"；某轮计数时是 3 个计划外 untracked 之一 |
| E | `h2.log`、`h2.log.err` | 2 | 各 0 B | log | 09-27 02:58 | register：多次登记为 "0 B 别会话 scratch"（T1-F3-FIX 披露），**保留**型历史注记对象 |

**文件对账**：git status 可见 = 404；按文件系统 find 直接清点 8 个 run 目录得 385 个实际文件（readable 部分），> 状态面口径 —— 差额源于 §5 可见性限制（长路径/权限不可读目录不被 status 看到），**404 是下界不是全量**。数据对账含此差异，已如实记录。

### 4.2 execution_runs 8 个 run 目录分账与归属

| run 目录（`execution_runs/<id>/a<date>-01/`） | 文件数 | 字节 | 内容要点 | PWF 引用 | 分类 | 建议 |
|---|---|---|---|---|---|---|
| `DEF-I00C-GATE-NEG` | 191 | 1,164,236 | 顶层正式载体（oracle.md、pre/post_image、nine_negatives_before/after/red_revert.json、run_mutations.py、run_nine_negatives.py、mutation_results.json、fix_diff.md、review.md、reviewer_report(.sha256)、handoff.json）+ `tmp/` 147 件（92 py/55 json/24 pyc，`i17b_n3_*` 变异测试 scratch） | register L944/998、owner §四十二 裁定二、Round 121"工位 78a935b1"、Round 122 落定记录 | 顶层 = **必须保留的审计证据**（含红绿/变异/负例唯一证据）；`tmp/` = **可重建运行产物** | 顶层整体 commit/入证据仓；`tmp/`（约 0.5MB 小体量）为候选清理（删除前需满足其 run 账引用核销） |
| `DEF-MSFT-CANONICAL-DUP` | 106 | **39,816,750（最大头）** | `rig/` 85 件（w/companies/MICROSOFT CORP/raw/financial_reports/annual 下的 **3 份 .htm 原件副本** + .source.json sidecar + 36 json/21 log/15 py/8 yaml/3 patch 测试台架）+ `pre/post_image` 等；另 2 个含空格路径（引号形式）的 `*.htm.source.json` | register L945/979、owner §四十一/§四十二、Round 122 落定"39 测试+6 变异+11 案自跑复现"、"P3 6 件孤儿登记不删" | **正文类运行产物**（非生产原件，测试自建副本；报告按卡要求只登元数据） | **暂缓**：canonical-dup 问题的唯一复现环境；39.8MB 是可释放空间的主要候选，但与 register "6 件孤儿登记不删" 及复现能力挂钩 → **需总指挥决定**（建议：与 owner 核销后，将需保留的少量证据件转写/迁入正式证据位置，再按精确清单清理） |
| `RATCHET-FIX-A` | 24 | 236,622 | pre/post_image、oracle、handoff 等 | register §（P3 归因档） | 计划/阶段证据（含恢复留痕） | commit（当轮皆需） |
| `RATCHET-FIX-B` | 24 | 244,705 | 同上（含 evidence_* 扫描输出、selfproof 脚本） | 同上 | 同上 | commit |
| `RATCHET-FIX-C` | 17 | 259,363 | 同上（probe_pre/post.json、signature/measure/dual_metric 脚本 + verification_output） | 同上 | 同上 | commit |
| `RATCHET-FIX-REVIEW` | 12 | 103,645 | 复审本体（report.md 15.8KB、behaviour/lineage/metric/diag checks+out、review_transcript、pytest_gate_out） | register L4182 "E. 复审 RATCHET-FIX-REVIEW 收尾 ACCEPT 0 P1" | **必须保留的审计证据**（唯一裁决载体） | commit |
| `RATCHET-FIX-ARCHIVE` | 4 | 25,636 | oracle.md、pre_image（git show HEAD blob）、post_image、handoff.json —— register L4185 明确该项为**补齐归属/留痕而新建** | register L4185 | 必须保留 | commit |
| `T3-DIAG` | 7 | 30,370 | diagnosis/reviewer_report/review/handoff/evidence(.json) + evidence 子目录 | register L4132、Round 121/122（周任务连败根因 = SYSTEM 账户无 Playwright 浏览器目录） | **必须保留的审计证据**（唯一诊断载体，下周日还会复败的使用价值） | commit |

exec_runs 合计 ≈ **42.0MB**，其中 `DEF-MSFT-CANONICAL-DUP` 独占 39.8MB。

### 4.3 引用与"安全删除候选"结论

- **零个 untracked 路径当前可以无风险直接删除**：353 个 run 路径全部归属已登记（round/register）的工位回合；`.tmp-r41-mutation` 被 4+ 处登记为"保留"；`weekly-run-*.log` 被 tracked manifest 引用；`plan_inputs.json.bak` 与 `h2.log*` 被 register 专门登记为"一律保留/不可能是卡产物"的非卡历史件（其存在本身是若干纠错记录的依据）。
- 相对可释放空间候选（均需 owner 核销后才可动）：`DEF-I00C-GATE-NEG/…/tmp/`（~0.5MB 级，变异 scratch、可由脚本重建）；`DEF-MSFT-CANONICAL-DUP` 测试 rig 的原件副本与台架（39.8MB，需先完成转写为永久证据或确认 oracle 已可从台架脚本重建）。合计**最多 ~40.3MB**，收益有限。

## 5. 可见性限制（如实登记）

- 根工作树 status 报 7 类不可读目录：1 处 "Filename too long"（I-07-D-REPRO/…/staging/cf4d7291…，该路径本身被 24 个 tracked 文件覆盖目录之下）与 3 处 `reviews/revenue/scratch/{model,publication,pytest}-tests/` + 3 处 `.tmp-zr408-*` "Permission denied"。⇒ status 的 404/12 **不含这些不可读子树**，真实盘上状态是其超集。
- rf-merge-review worktree 的 41 个 `D`（deleted）与 21 处长路径警告对应：该 worktree 所在 `Temp` 路径触发 Windows MAX_PATH，git 将其实际存在的深层目录误判为已删。**按卡要求，不算作真实状态**，建议合并处理者到该 worktree 时配置 `git config core.longpaths=true`（其所在仓已用过此法，见 register 提交相关记录）后再复核。
- 本审计未做任何修复；所有 `find/stat` 与 status 的差异已记录为口径差异。

## 6. reader 分支唯一提交评估（`codex/revenue-source-reader@3b00b938`）

- 单提交 `3b00b938 "wip: preserve pathless source reader prototype"`（2026-09-29 18:38），父 = `3a69f9c5`（已在 main 中）。wip 名如实：**一个“防丢失型”原型保存点**。
- 改动：`scripts/company_wiki_source_reader_v2.py` +227、`scripts/company_wiki_source.py` +9、`scripts/filing_fetch_client.py` +9、`scripts/source_preparation.py` +85；新增 5 个测试（+1560/−2 全部 10 文件）：
  - `tests/test_source_preparation_v2.py`（**main 不存在**）
  - `tests/test_source_preparation_v2_cross_repo.py`（**main 不存在**）
  - `tests/test_source_ref_candidate_preparation.py`（**main 不存在**）
  - `tests/test_source_ref_v2_three_repo_e2e.py`（**main 不存在**）
  - `tests/test_company_wiki_source_reader_v2.py`（main 存在但**内容大幅重写**：reader_v2 两版相差 210 行，测试相差 269 行）
- 替代关系：main 用 415d8eb3 以**更窄的“opt-in verified reader”口径**独立落地了 reader_v2（258 行 + CWP fixtures/allowlist），`merge-base = 3a69f9c5` ⇒ **main 未吸收 reader 分支**；rfv2 分支 = main 同 hash，只是同一 reader 主题的另一落点。3b00b938 是**先行的超集原型（含跨仓/3 仓 e2e 与 candidate preparation 测试），未被替代的是那 5 个 test 文件与 source_preparation 的 +85 行准备逻辑**。
- 与 CWP→RF 接口的关系：这 4 个缺失测试正是 `source ref candidate/preparation`、cross-repo、three-repo e2e 的用例面，对应并行计划 S0a 的 CWP→RF `SourceRef/verified read` 接口验收素材，**不建议丢弃**。
- **建议**：`暂缓 + 重建评估` —— 不宜直接 cherry-pick（同文件 reader_v2.py/test 在两支均已重写，会产生对照冲突）；先由总指挥在 main 基上独立比对功能覆盖（reader 分支中 `source_preparation.py` +85 行、`company_wiki_source_reader_v2.py` +227 行原型可供参考），决定是否以"补齐缺失测试文件 + 移植候选准备逻辑"方式择要整合；所需最小测试 = `tests/test_company_wiki_source_reader_v2.py`、`tests/test_company_wiki_source_ref_v2.py` 在现 worktree + 若移植则 4 个缺失测试文件 + `tests/contract/cwp_*.json` fixtures 回放。**此卡不执行任何 pick/merge**。

## 7. main@415d8eb3 吸收状态三分账

1. **提交历史**：已吸收 —— fcap tip `ee0a82bf` 是 main 祖先；main 另有 4 个后行提交（见 §2）。fcap 分支保留为同步备份（计划 Round 122 已登记并线）。
2. **dirty 工作树变化**：**未吸收** —— §3 的 12 项（5 计划 + 4 run 账本 + 3 实现/测试修复）只存在于根 fcap 工作树；其中 #10–#12 与 main 现行 uc 代码**有真实分叉**，需重放合并。
3. **untracked 运行资料**：**未吸收** —— 404+ 路径只存在于磁盘，不在任何提交中（8 个 run 目录、tmp-r41 等）。
   ✔ 卡要求警示兑现：**不能把 "fcap tip 是 main 祖先" 写成 "fcap 根工作树已全部并入 main"**。

## 8. 分组总汇（决策矩阵摘要）

| 分组 | 内容 | 建议 | 风险 |
|---|---|---|---|
| **必须保留 / 建议 commit** | 5 个 .planning PWF 文件改动；RATCHET-FIX-A/B/C/REVIEW/ARCHIVE、T3-DIAG、DEF-I00C-GATE-NEG 顶层载体；4 个 assurance 账本(diff 6-9) | 下轮四步提交原样入库 | 低（mtime/sha 与引用一致） |
| **需总指挥决定** | ① #10–#12 与 main 的 uc 双向分叉如何重放；② `DEF-MSFT-CANONICAL-DUP` 39.8MB rig 中正文副本是否转写为永久证据或核销；③ `codex/revenue-source-reader@3b00b938` cherry-pick 与否 | 见 §3/§4.2/§6 | 中 |
| **候选清理（owner 核销后）** | DEF-I00C `tmp/` 147 件 scratch；（条件性）MSFT rig 可转写部分 | 精确清单核销 | 低；合计约 0.5MB～40MB |
| **一律不删** | `.tmp-r41-mutation`、`plan_inputs.json.bak`、`h2.log/h2.log.err`、tracked manifest 所引 run log | 保持登记原状 | —— |

**审计未定项**：`.planning/…/reviews/revenue/scratch/*`、`.tmp-zr408-*` 等 7 个不可读子树的内容（本轮权限下无法读取）；其归属与是否可清理**需总指挥在获得完整可读访问后决定**。另：同类 scratch 中有 24 个文件以 tracked 形式存在于提交历史（如 I-07-D-REPRO 所引 staging cwroot 之下，`git ls-files` 可见），说明此类测试根目录既有 committed 先例、也是当前不可见的持留物。

## 9. 结束快照与一致性

- 结束/开始一致（命令与开工逐同为 `status -uall -porcelain`、`rev-parse`、`worktree list` 及 8 个 run 目录 find）：HEAD `fcap@ee0a82bf`、`12 M + 404 ??`；main、reader、worktree 集合与开工完全相同，无 index/ref/文件差动。任何意外写入：**0 起**（全程只读命令，无一写性 Git 操作，新建文件仅本报告）。
- 未读取任何凭证类文件正文；文件名与摘要已按卡要求脱敏（财报原件仅以"目录中 htm sidecar"元数据方式登记）。

— 报告完 —
