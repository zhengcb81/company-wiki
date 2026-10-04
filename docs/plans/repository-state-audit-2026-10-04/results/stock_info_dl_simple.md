# Repository State Audit — StockInfoDLSimple（唯一结果）

按 `../handoff_template.md` v1 编写。所有结论均来自本轮只读命令；无法证明处写 `unknown`。

## 0. 审计元信息（必填）

```yaml
audit_id: "RSA-stockinfodlsimple-20261004"
repository: "StockInfoDLSimple（本地目录名；origin 实为 StockInfoDownloader.git，见 §2）"
repository_root: "C:\\Users\\郑曾波\\Projects\\StockInfoDLSimple（Git common-dir 位于其 v2-clean-rewrite\\.git）"
audit_status: "complete"
started_at_local: "2026-10-04 约18:35 +01:00（约，分钟级精度）"
finished_at_local: "2026-10-04 约19:10 +01:00（约，分钟级精度）"
current_branch: "v2-clean-rewrite"
current_head: "1693045caeb5d72bfc83a4fa6d034802e80b0a3f"
base_ref: "refs/heads/v2-clean-rewrite（与 refs/remotes/origin/v2-clean-rewrite 及 live 同名 head 一致）"
base_sha: "1693045caeb5d72bfc83a4fa6d034802e80b0a3f"
remote_live_check: "ls-remote success"
remote_checked_at: "2026-10-04 约18:41 +01:00（约）"
source_changes_made: false
tests_run: false
```

## 1. 一页结论

- **branch-only commits 相对什么 base：** 唯一含独有提交的本地开发分支是 `codex/cninfo-bounded-budget`，相对 base `v2-clean-rewrite@1693045` 为 **2 个独有 commit**（`git rev-list --left-right --count origin/v2-clean-rewrite...codex/cninfo-bounded-budget` = `0\t2`：左列 base-only 0，右列 branch-only 2）。两个 commit 均已在 live 远端（`ls-remote` 见同 SHA）。另有 3 个 **live 远端独有、本地无对象** 的 heads（`main`、`feature/local-changes`、`改版新下载器`），按禁令未 fetch，无法计算 merge-base/独有数（见 §3）。
- **tracked staged / unstaged 文件：** staged **4** 个（2 个纯 `A`，2 个 `AM`）；unstaged **13** 个（含 2 个 `AM` 的工作树侧；无删除、无 submodule）。index 与 worktree 必须分开看：2 个 `AM` 文件的 staged 版与工作树版内容不同。
- **untracked / ignored candidate：** untracked **9** 个文件（`git ls-files --others --exclude-standard`；其中 `scripts/`、`tests/fixtures/` 两个目录展开）；ignored 候选按目录汇总：`.pytest_cache/`、`.ruff_cache/`、`__pycache__/`（多处）、`downloads/`、`logs/`、`e2e_official_report*.json`（3 个）、`src/stock_orgid_mapping.json`，外加仓库根外（非 git 仓库）的 `.claude/`、`.codegraph/`、`.mimocode/`、`nul`、`.benchmarks/`、`logs/progress.json`（见 §6）。
- **linked worktrees：** 2 个——默认 checkout `v2-clean-rewrite\`（**dirty**：4 staged / 13 unstaged / 9 untracked）与 `cwp-cninfo-bounded-budget\`（**clean**，无任何未提交项）。无 detached、无缺失路径、无多余临时 worktree。
- **PWF 称完成但 Git 未合 / Git 已合但 PWF 待办的差异：** 本仓 **完全没有 PWF 记录**（无 `.planning/.active_plan`、无根 `task_plan.md`/`progress.md`/`findings.md`、无 handoff、无 `rg --files` 可找的 plan 文件——以 Glob 全仓搜索为准，`rg` 本机不可用）。因此仓内无可对照的 PWF↔Git 差异；唯一 PWF 类声明来自**仓外** CWP findings（62 项 provider tests、真实 BYD CNINFO E2E），属外部引用，需总指挥核验（见 §7、§11）。
- **最大未决项：** 主 checkout 的 staged/unstaged/untracked **是 2026-07-25/26 冻结的 owner WIP（adapter v1.1.0、pre-budget 血统）**，而 `codex/cninfo-bounded-budget` 的 2 个 commit（2026-10-04 由 Claude 作者创建）= 该 WIP 的**子集 + budget 层（v1.2.0）**。两套血统并存：CWP 引用的是分支侧 1.2.0 budget CLI，主 checkout 的 WIP 从未提交、且含分支上不存在的独有改动（downloader LoadState/校验、浏览器 DNS 加固、`--companies` 文档、e2e round 报告等）。谁是最终集成形态、owner WIP 是否已被分支取代，需要总指挥/owner 决策。

## 2. 主线与远端识别

| 线索 | ref/值 | SHA/结果 | 证据命令/文件 | 解释 |
|---|---|---|---|---|
| `origin/HEAD` 或服务端 default | 本地 **未配置**（`refs/remotes/origin/HEAD` 不存在，`symbolic-ref` fatal） | n/a | `git symbolic-ref refs/remotes/origin/HEAD` | 单分支 clone，未设 origin/HEAD |
| 服务端 default（live HEAD） | `git ls-remote origin` 首行 `HEAD` | `6df45a128a893…`（与 live `refs/heads/main` 相同） | `git ls-remote origin`（只读，未 fetch） | 远端默认分支是 `main`，**但本地从未 fetch 过它，对象不在本地** |
| 本地目标主线 | `refs/heads/v2-clean-rewrite` | `1693045caeb5…` | `git branch -vv`、`git for-each-ref` | 工作 checkout 所在分支；lane 指定的审计基线 |
| live remote `ls-remote` | heads：`main=6df45a1…`、`v2-clean-rewrite=1693045…`、`codex/cninfo-bounded-budget=8ed5fdd…`、`feature/local-changes=3b6b6a6…`、`改版新下载器=064a837…` | exit=0 | `git ls-remote origin` | 本地唯一 remote-tracking `origin/v2-clean-rewrite@1693045` 与 live **精确相同**（不过期）；其余 4 个 head 本地无 remote-tracking 记录 |
| 工作 checkout | `v2-clean-rewrite\`，branch `v2-clean-rewrite` | `1693045…`，dirty | `git status --short --branch` | `## v2-clean-rewrite...origin/v2-clean-rewrite`，无 ahead/behind 标记 |

关键事实：

- **origin URL 是 `https://github.com/zhengcb81/StockInfoDownloader.git`**（本仓 clone 来源，reflog `2026-04-19 clone: from …StockInfoDownloader.git`）。即 “StockInfoDLSimple” 与被排除的 StockInfoDownloader **共用同一个远端仓库**；本卡边界仍是本地这个 checkout（lane 明示 StockInfoDownloader 本地仓不碰、不作合并基线）。远端 `v2-clean-rewrite@1693045` 与 findings.md 记录的 StockInfoDownloader `v2-clean-rewrite` SHA 相同，属同一远端分支。
- **remote-tracking 可能不完整**：本地只有 `refs/remotes/origin/v2-clean-rewrite` 一条（`git for-each-ref refs/remotes` 证实）。对其他 4 个 live heads 本地无任何记录；按禁令未执行 fetch，未刷新任何 remote-tracking ref。
- findings.md §已验证远端 heads 把 `main/改版新下载器/feature/local-changes` 归在 StockInfoDownloader 名下——与本轮 `ls-remote` 结果一致（同一远端），可交叉印证。

## 3. Branch 矩阵（每个本地/远端开发分支一行）

| branch ref | tip SHA | merge-base | base-only commits | branch-only commits | patch-equivalent/ cherry | diff stat | PWF/交接关联 | 当前判断 |
|---|---|---|---:|---:|---|---|---|---|
| `refs/heads/v2-clean-rewrite`（= base） | `1693045caeb5d72bfc83a4fa6d034802e80b0a3f` | （自身） | 0 | 0 | n/a | n/a（但工作树 dirty，见 §5） | 本仓无 PWF；CWP findings 称 downloader_dir 默认指向此目录（外部引用） | 基线本身；dirty 见 §5 |
| `refs/heads/codex/cninfo-bounded-budget` | `8ed5fdde5e88c13470c120665ff3074a7f44a052` | `1693045…`（= base tip，`git merge-base` 确认；`merge-base --is-ancestor` exit=0 → base 是其祖先） | 0 | 2 | `git cherry -v origin/v2-clean-rewrite codex/cninfo-bounded-budget` 两行均为 `+`（**无任何 patch-equivalent 已在 base**） | `git diff --stat origin/v2-clean-rewrite...codex/cninfo-bounded-budget`：13 files, **3206 insertions(+)**（0 deletions） | CWP `config/source_acquisition.yaml` 指向该 worktree 的 `stockinfo-cninfo` 1.2.0 budget CLI（**外部引用需总指挥核验**；本地侧证据：分支 adapter `ADAPTER_VERSION="1.2.0"` 与该说法吻合） | **merge_candidate**（已 push；合入前需集成测试，见 §9） |
| live `refs/heads/main` | `6df45a128a893f24792231f0bd1f18d1e457060e` | unknown（对象不在本地，禁 fetch） | unknown | unknown | unknown | unknown | 远端默认分支；同远端亦被 StockInfoDownloader lane 引用 | **owner_decision_needed / 超出本卡可测范围**（不 fetch、不评估） |
| live `refs/heads/feature/local-changes` | `3b6b6a6f01bf51dfa68e94504e9262c9d62cfed9` | unknown | unknown | unknown | unknown | unknown | 同上 | 同上 |
| live `refs/heads/改版新下载器` | `064a837963e873cb0baa43d45980d9a68b43cde1` | unknown | unknown | unknown | unknown | unknown | 同上 | 同上 |

原始计数与解释：

- `git rev-list --left-right --count origin/v2-clean-rewrite...codex/cninfo-bounded-budget` → `0	2`：**左列（base 侧）0 个独有，右列（branch 侧）2 个独有**。
- `git cherry -v origin/v2-clean-rewrite codex/cninfo-bounded-budget` → `+ 947e839…`、`+ 8ed5fdd…`（`+` = base 中**没有**等价 patch）。
- `git merge-base --is-ancestor origin/v2-clean-rewrite codex/cninfo-bounded-budget` → exit 0。

branch-only commit 明细（full message + name-status/stat，代码/测试/计划/唯一证据计数）：

1. **`947e839c5e99266b65674eeb080c57d0d11fd353`** — `feat: enforce CNINFO acquisition budgets`，作者 `Claude <noreply@example.com>`，AuthorDate `2026-10-04 00:23:31 +0100`。13 个文件全为新增（A），+3206 行合计于此 commit 的绝大部分：
   - 代码 5：`src/acquisition_budget.py`(113)、`src/cninfo_api.py`(619)、`src/company_wiki_adapter.py`(383)、`src/company_wiki_adapter_cli.py`(216)、`src/transport_states.py`(29)
   - 测试 6：`tests/unit/test_cninfo_api.py`(507)、`test_cninfo_api_budget.py`(197)、`test_cninfo_api_fixture_contract.py`(166)、`test_company_wiki_adapter.py`(494)、`test_company_wiki_adapter_cli.py`(140)、`test_company_wiki_adapter_cli_budget.py`(258)
   - fixtures 2（唯一证据类）：`tests/fixtures/cninfo/byd_fy2024_announcement.json`(71)、`synthetic_empty_from_real_schema.json`(13)
   - 计划/文档 0：commit message 无 body、无计划文件、无测试收据。
2. **`8ed5fdde5e88c13470c120665ff3074a7f44a052`** — `fix: keep StockInfo adapter stdout as JSON`，同一作者，AuthorDate `2026-10-04 02:03:14 +0100`。2 个文件（M）：`src/company_wiki_adapter_cli.py`(+12)、`tests/unit/test_company_wiki_adapter_cli.py`(+37)。代码 1 / 测试 1。

worktree 来源佐证（reflog，只读）：`codex/cninfo-bounded-budget@{2026-10-03 23:53:23}: branch: Created from HEAD`（从 1693045 建支），随后两笔 10-04 commit；`cwp-cninfo-bounded-budget` 目录创建时间同为 2026-10-03 23:53:23。

## 4. Worktree 矩阵

| worktree path | branch/detached | HEAD SHA | porcelain 状态 | PWF/owner/创建来源 | 可能用途 | 确定度 |
|---|---|---|---|---|---|---|
| `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite` | `v2-clean-rewrite` | `1693045…` | **dirty**：`git status --short` = 4 staged（A/AM）、13 unstaged（M/AM）、9 untracked | 无仓内 PWF；reflog：2026-04-19 clone → 2026-07-24 `1693045` commit → **2026-07-25 12:26:52 `reset: moving to HEAD`**；WIP 文件 mtime 集中在 2026-07-25 12:26–17:56（`stock_orgid_mapping.json` 至 07-31） | 默认 checkout + owner WIP 所在地；CWP findings 称 `scripts/config.py` 默认 downloader_dir 指向此目录（外部引用需核验） | 高（命令直接观测）；“owner 正在用”属推断（mtime 已 2.5 个月未动，但内容从未提交） |
| `C:\Users\郑曾波\Projects\StockInfoDLSimple\cwp-cninfo-bounded-budget` | `codex/cninfo-bounded-budget` | `8ed5fdd…` | **clean**（`git status --short --branch` 仅输出分支行，无任何条目；无 untracked、无 ignored 残留：`.pytest_cache`/`downloads`/`logs` 均不存在） | 创建时间 2026-10-03 23:53:23（与 branch reflog 同刻）；CWP `config/source_acquisition.yaml`（仓外、用户 dirty）指向此处（**外部引用需总指挥核验**） | CWP provider `stockinfo-cninfo` 1.2.0 budget CLI 的运行载体 | 高 |

其他：`git worktree list --porcelain` 仅以上 2 条，无 detached/临时/review 路径，无失效路径（未做也不需要 prune）。

## 5. 当前未提交文件

### 5.1 staged（index）— 4 个

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `src/company_wiki_adapter.py` | `AM` | +368 行整文件新增；**index blob `648a1cde…` 不在任何 commit 中**（`git rev-list --all --objects` 无匹配）；内容为 **v1.1.0、无 budget 参数**（与分支 1.2.0 版不同） | 11 行（index→worktree）：改为 `TYPE_CHECKING` 惰性导入、删除 `DownloadRequest` 导入、`discover()` 本地导入只取 `CninfoApiError`；**worktree blob `f6c69591…` 也不在任何 commit 中** | CWP adapter 主体（注释 `CW-2.27F / Phase 5`） | 分支 `947e839` 内有同名文件的 **budget 演化版**（1.2.0）；CWP CLI 是其消费者（外部引用需核验）；无 PWF 卡文件 | 无敏感内容 | `preserve_active_work`（与分支血统的取舍 → 总指挥/owner 决策） |
| `src/company_wiki_adapter_cli.py` | `A`（纯暂存，worktree==index） | +161 行；index blob `8c41599c…` 不在任何 commit；**既不等于 `947e839` 版（`f886bc41…`）也不等于 `8ed5fdd` 版（`e9507bc0…`）**——pre-budget 原始 WIP | 无（worktree 与 index 相同） | provider CLI（JSON stdout/stderr 契约，`SCHEMA_VERSION=1.0`；版本经 adapter 间接为 1.1.0） | 分支 tip 版是“+budget+JSON fix”演化；CWP 消费 1.2.0 版（外部引用） | 无敏感内容 | `preserve_active_work` |
| `tests/unit/test_company_wiki_adapter.py` | `AM` | +497 行；index blob `c9a11c8b…` 不在任何 commit；**顶部 `from src.cninfo_api import (…)` → staged 集合依赖 untracked 文件**，单独提交会 import 失败 | 6 行：删未用 import（`json`/`Any`/`urllib.error`）；worktree blob `b6c85041…` 亦不在任何 commit | adapter 离线单测（`CW-2.27F / Phase 5`） | 分支 `947e839` 含其演化版（494 行 vs staged 497 行） | 无敏感内容 | `preserve_active_work` |
| `tests/unit/test_company_wiki_adapter_cli.py` | `A`（worktree==index） | +103 行；**index blob `d351fad0…` 与 `947e839` 内该文件 blob 完全相同**（唯一一个与分支内容逐字节一致的 staged 文件） | 无 | CLI 单测 | 分支 `8ed5fdd` 在此基础上 +37 行（JSON fix 测试）→ staged 版 = 分支第一版、缺第二版 | 无敏感内容 | `already_in_base`（等价内容已在 `codex/cninfo-bounded-budget`）+ 仍属 owner WIP 的一部分 → 随整组 `preserve_active_work` |

### 5.2 unstaged（worktree vs index）— 13 个

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `README.md` | ` M` | 无 | +126/-…：新增 `--companies` TXT 列表用法、CLI 参数表、执行优先级说明；行数声称 1500→2300 | 下载器功能文档 WIP | 与 untracked `companies.txt`/`a_share_companies.txt` 及 base 已有 `--companies` CLI（`0c911cf`）对应 | 无敏感内容 | `preserve_active_work` |
| `config_template.json` | ` M` | 无 | 3 行：`max_pages` 2→3；定期报告页新增 `allowed_keywords` | 下载关键词配置 | 与 downloader 校验功能（`_verify_downloads`）配套 | 无敏感内容 | `preserve_active_work` |
| `main.py` | ` M` | 无 | +13：消费 `verification_warnings`，有告警则判失败并记日志 | 下载校验结果接入 runner | 与 `src/downloader.py` 的 `verification_warnings` metadata 同一功能 | 无敏感内容 | `preserve_active_work` |
| `src/browser.py` | ` M` | 无 | +81：`CW-2.27H / Phase 8` DNS 加固（关键/可选 host 分离、禁硬编码回退 IP、launch args） | 浏览器启动/解析加固 | 卡号注释 `CW-2.27H`；配套测试在 unstaged `test_downloader.py`（`TestBrowserStaticHostMapping`） | 无敏感内容 | `preserve_active_work` |
| `src/company_wiki_adapter.py` | `AM` 的 M 侧 | （见 5.1） | 11 行 | 见 5.1 | 见 5.1 | 无敏感内容 | `preserve_active_work` |
| `src/downloader.py` | ` M` | 无 | +212：`CW-2.27D` 类型化 `LoadState` 管道（`_official_status`、`_switch_tab` 判空、CONFIRMED_EMPTY 语义）、新增 `_verify_downloads` + `verification_warnings`、`CW-2.27H Phase 7` user_override 相关 | 下载核心的状态/校验重构——**直接支撑 adapter 的三态零文件契约** | 卡号注释 CW-2.27D/H；**模块级 `from .transport_states import LoadState` → 依赖 untracked 文件**（工作树可运行、仅提交 staged 则该改动不在内） | 无敏感内容 | `preserve_active_work` |
| `src/logger.py` | ` M` | 无 | 1 行：console handler `stdout → stderr` | 保证 adapter JSON 独占 stdout——**与分支 `8ed5fdd`（"keep StockInfo adapter stdout as JSON"）意图互补**，但分支未改此文件 | 分支 commit 未覆盖 → 属 WIP 独有 | 无敏感内容 | `preserve_active_work` |
| `src/mapping.py` | ` M` | 无 | 38 行：`_crawl_org_id` 去掉 try/except（异常直接上抛）、删 `MappingError` 导入 | orgId 抓取错误传播行为变化 | 无卡号注释；意图不明 | 无敏感内容 | `preserve_active_work`（意图待 owner 说明） |
| `src/models.py` | ` M` | 无 | +9：`DownloadResult` 增 `load_state/error_code/retryable`（`CW-2.27D` 注释）；**模块级 import untracked `transport_states`** | 三态契约的数据模型侧 | 与 downloader/adaptor 改动同属 CW-2.27D | 无敏感内容 | `preserve_active_work` |
| `tests/e2e/official_e2e_test.py` | ` M` | 无 | +38/-…：`report_path_for_config(path, suffix)` + `--report-suffix`（round1/round2 防覆盖）+ 若干格式化 | E2E 报告分轮落盘 | 产物即 ignored 的 `e2e_official_report_round1/round2.json`（07-25）；与下方 `test_official_e2e_contract.py` 签名修正配对 | 无敏感内容（报告本身见 §6） | `preserve_active_work` |
| `tests/unit/test_company_wiki_adapter.py` | `AM` 的 M 侧 | （见 5.1） | 6 行 import 清理 | 见 5.1 | 见 5.1 | 无敏感内容 | `preserve_active_work` |
| `tests/unit/test_downloader.py` | ` M` | 无 | +313：新测试组 `TestVerifyDownloads`(9)、`TestLoadState`(2)、`TestDownloadInternalTypedFailures`(2)、`TestBrowserStaticHostMapping`(2)、`TestCliErrorJsonContract`（断言 adapter **1.1.0**） | CW-2.27D/Phase 3 的 RED/GREEN 配套测试 | 文件头注释 `CW-2.27D / Phase 3`；**断言 1.1.0 → 与分支 1.2.0 版本冲突**（两血统分歧的直接证据） | 无敏感内容 | `preserve_active_work` |
| `tests/unit/test_official_e2e_contract.py` | ` M` | 无 | ±1 行：monkeypatch 适配 `report_path_for_config(_path, _suffix=None, **__)` | 与 e2e 报告 suffix 功能配对的契约测试修正 | 配对证据如上 | 无敏感内容 | `preserve_active_work` |

### 5.3 untracked（9 个文件）

| 路径 | Git 状态 | staged diff | unstaged diff | 类型/可能用途 | PWF/commit/调用者证据 | 敏感性 | 推荐后续分类 |
|---|---|---|---|---|---|---|---|
| `src/cninfo_api.py` | `??`（未 ignored） | — | — | 20,179 B / 504 行；**pre-budget 变体**（全文无 `acquisition_budget/budget` 标记，分支版 619 行含 budget）；**worktree blob `c1864c7306…` 不在任何 commit** → 独有内容 | 被 staged adapter、untracked `test_cninfo_api.py` 导入；注释 `CW-2.27F / Phase 5` | 无密钥；含官方 API 端点/请求构造（公开端点） | `preserve_active_work`（与分支 1.2.0 血统需 owner 裁决） |
| `src/transport_states.py` | `??` | — | — | 977 B；`LoadState` 四态枚举 | **worktree blob 与分支 `947e839` 中该文件逐字节相同**（内容已由分支引入）；被 unstaged downloader/models 模块级导入 | 无敏感内容 | `preserve_active_work`（内容已 `already_in_base` 于分支，但本地 WIP 运行依赖它） |
| `tests/unit/test_cninfo_api.py` | `??` | — | — | 20,203 B；`CW-2.27F` RED 契约测试 | **与分支 blob `7d6eb615…` 逐字节相同**；`.pytest_cache` 显示 07-26 曾被收集运行 | 无敏感内容 | `preserve_active_work`（同上） |
| `tests/unit/test_cninfo_api_fixture_contract.py` | `??` | — | — | 5,848 B；`CW-2.27E / Gate 4.1` fixture 装载契约 | **与分支 blob `521f3285…` 逐字节相同** | 无敏感内容 | `preserve_active_work`（同上） |
| `tests/fixtures/cninfo/byd_fy2024_announcement.json` | `??`（`.gitignore` 有 `!tests/**/*.json` 豁免） | — | — | 2,273 B；BYD 002594 FY2024 **公告 API 响应 fixture（已脱敏，公开披露元数据）** | **与分支 blob `64bcf21b…` 逐字节相同**；由 `scripts/capture_byd_fy2024_fixture.py` 生成（脚本 docstring 自述） | 低：公开公告元数据，无 PDF 原文、无 cookie/token（脚本自称已 strip） | `preserve_active_work`（同上） |
| `tests/fixtures/cninfo/synthetic_empty_from_real_schema.json` | `??` | — | — | 392 B；合成空响应 fixture | **与分支 blob `60d7ece5…` 逐字节相同**；同一脚本产出 | 低（合成数据） | `preserve_active_work`（同上） |
| `scripts/capture_byd_fy2024_fixture.py` | `??` | — | — | 8,544 B；`CW-2.27E / Phase 4 Gate 4.1` 只读采集脚本（docstring：仅授权后运行、只写 fixtures 目录） | **不在任何分支上**（`git show codex/…:scripts/…` 不存在）→ fixture 的唯一出处线索 | 含官方 API 调用逻辑；不含密钥 | `unique_evidence_preserve` |
| `companies.txt` | `??` | — | — | 137 B / 5 行；`--companies` 批量输入列表（股票代码+名称） | 与 unstaged README `--companies` 文档对应；根目录非敏感 | 低（公开股票名单） | `preserve_active_work` |
| `a_share_companies.txt` | `??` | — | — | 3,898 B / 192 行；A 股公司清单 | 同上（批量下载输入） | 低（公开股票名单） | `preserve_active_work` |

**staged ↔ unstaged ↔ untracked 对应关系（问题 3/4 的直接回答）：**

1. **两血统并存**：staged adapter/CLI = pre-budget v1.1.0（blob 均不在历史中）；分支 2 commit = 同源 WIP + budget 层（1.2.0）。唯一例外：staged `test_company_wiki_adapter_cli.py` 与 `947e839` 版逐字节相同。
2. **staged 集合不自洽**：staged 测试 import `src.cninfo_api`（untracked）；若只提交 staged 四件套，测试 import 即失败。staged adapter 对 cninfo_api 的导入是惰性（discover() 内），运行期同样依赖 untracked 文件。
3. **unstaged 一半在支撑 adapter**：`downloader/models`（CW-2.27D LoadState 管道，模块级依赖 untracked `transport_states`）、`logger`（stdout→stderr，配 JSON 契约）、`browser`（CW-2.27H）、`test_downloader`（CW-2.27D 测试，且断言 1.1.0）。
4. **unstaged 另一半是独立下载器工作**：`--companies` 文档（README+companies.txt）、下载校验（`_verify_downloads`+`main.py`+`config_template`）、e2e round 报告（`official_e2e_test`+`test_official_e2e_contract`↔`e2e_official_report_round*.json`）、`mapping` 异常传播改动（意图不明）。
5. **5 个 untracked 文件内容已由分支引入**（`transport_states`、`test_cninfo_api`、`fixture_contract`、2 个 fixture 逐字节相同）；`cninfo_api.py`、4 个 staged blob、2 个 AM worktree blob、capture 脚本为**分支/base 中不存在的独有内容**。

## 6. 未跟踪/ignored 工件及空间线索

| 目录/文件 | Git ignored/untracked 状态 | 文件数/总字节（低成本测量） | 创建/消费证据 | 是否唯一审查/测试证据 | 可再生证据 | 结论/未决 |
|---|---|---:|---|---|---|---|
| `tests/fixtures/cninfo/`（2 JSON） | untracked（ignore 豁免） | 2 / 2,665 B | 由 `scripts/capture_byd_fy2024_fixture.py` 生成；被 `test_cninfo_api*` 消费 | 分支上已有相同内容 → 本副本非唯一 | 是（脚本需授权重跑） | 内容已入分支；本地副本为 WIP 运行所需 → `preserve_active_work` |
| `scripts/`（1 py） | untracked | 1 / 8,544 B | 脚本自述产出上述 fixture | **是**（唯一 fixture 出处记录，分支上无） | 否（唯一） | `unique_evidence_preserve` |
| `companies.txt`、`a_share_companies.txt` | untracked | 2 / 5,035 B、197 行 | README `--companies` 输入 | 否 | 手工清单 | `preserve_active_work` |
| `src/cninfo_api.py` | untracked | 1 / 20,179 B | staged adapter + 测试的运行依赖 | 独有（pre-budget 血统，分支无此版本） | 否 | `preserve_active_work`（血统裁决） |
| `.pytest_cache/` | ignored | `nodeids` 21,071 B + `lastfailed` 294 B 等；mtime 2026-07-26 | pytest 自动产物 | 是（唯一仓内 pytest 运行痕迹，见 §8） | 部分（重跑可再生，但旧结果不可再生） | `unique_evidence_preserve`（至少保留到报告被采纳） |
| `e2e_official_report.json` / `_round1` / `_round2` | ignored（`*.json` 规则） | 3 / 3,721 B；mtime 2026-07-25 | `tests/e2e/official_e2e_test.py`（unstaged 版带 `--report-suffix`）产出 | **是**（唯一 E2E 成功收据：07-25 `overall_success=true`、3 cases） | 否（历史运行结果不可再生） | `unique_evidence_preserve` |
| `downloads/` | ignored | 顶层为多公司名目录（仅列名，未读取内容/未统计 PDF） | 下载器输出目录；CWP findings 称 `windows_downloads` 指向此处（外部引用） | 疑似真实公司 PDF 存档 | 是（可重新下载） | `generated_candidate_review`（删前须验证消费者） |
| `logs/`（仓库内） | ignored | 已列目录：约 140 个 `debug_page_*.png` 调试截图（5–586 KB 每个）、`failed_downloads.json` 2,220,456 B、`progress.json` 3,066 B（07-26）、`codex_e2e_diag_20260724_*.log` 2 个 | 下载/调试运行产物（05 月为主 + 07 月） | `codex_e2e_diag` 日志为 07-24 诊断残留；非测试收据 | 是（截图/日志可再生） | `generated_candidate_review` |
| `src/stock_orgid_mapping.json` | ignored | 1 / 31,432 B；mtime 07-31 | MappingManager 本地 orgId 缓存 | 否 | 是（爬虫可重建） | `generated_candidate_review` |
| `end2end_test/` | 跟踪 6 个文件（含豁免的珂玛科技 PDF 基线）+ ignore 规则覆盖其余 test_results | 未逐项统计（非 dirty 目录） | base 即有（`dcf2c64`/`31147bb` 提交过基线） | 跟踪部分是 E2E 基线的一部分 | 部分 | `no_change`（跟踪部分）；忽略部分 `generated_candidate_review` |
| `.ruff_cache/`、`__pycache__/`（多处） | ignored | 未统计 | 工具缓存 | 否 | 是 | `generated_candidate_review` |
| 仓库根外（**非 git 仓库**）：`.claude/settings.local.json`、`.codegraph/`（codegraph.db 等）、`.mimocode/`（.cron-lock）、`.benchmarks/`（空）、`logs/progress.json`（175 B，05-17） | 不受本仓 git 管理 | 各 1–4 文件；未读内容 | 本机工具状态 | 否 | 多数可再生 | `owner_decision_needed`（不在 git 审计范围，处置归 owner） |
| 仓库根外 `nul`（字面文件名） | 不受 git 管理 | 1 / 893 B；mtime 2026-05-17 | 疑似 `> nul` 重定向在 Windows 生成的字面文件；`[IO.File]::Exists` 返回 False（保留名怪异），内容未读 | 否 | 不明 | `owner_decision_needed` |

未做：全盘递归扫描、PDF/公告原文读取、敏感内容 hash、下载目录逐文件统计。

## 7. PWF 与 commit 记录对照

| PWF 位置/plan id | PWF 声明状态/最后时间 | 关联 SHA/工作树 | Git/现存测试/CI 收据核验 | 一致/冲突/不确定 |
|---|---|---|---|---|
| 本仓 `.planning/.active_plan` | **不存在**（`Test-Path` false；Glob `**/.planning/**` 无结果） | n/a | — | 一致于“无 PWF”事实 |
| 本仓根 `task_plan.md` / `progress.md` / `findings.md` | **均不存在**（`Test-Path` + Glob `**/{task_plan,progress,findings,handoff*}.md` 全空） | n/a | — | 同上；lane 要求“若不存在要写明”——已写明 |
| PWF/plan/handoff/CI 文件全仓搜索 | Glob 未找到任何 plan/handoff 文件；**无 `.github/` 工作流**（`Test-Path` false） | n/a | 本仓无 CI 记录可读 | 同上 |
| 卡号/阶段注释（代码内，非 PWF 文件） | `CW-2.27D`（Phase 3，downloader/models/test_downloader）、`CW-2.27E`（Phase 4 Gate 4.1，capture 脚本/fixture 契约测试）、`CW-2.27F`（Phase 5，cninfo_api/adapter 测试）、`CW-2.27H`（Phase 7/8，browser/downloader） | 全部位于 **dirty/untracked 工作树**，无一在 base commit 中 | 代码注释是唯一线索；无对应计划文件可对照 | 不确定（卡本体在 CWP 侧，未打开 CWP 仓） |
| 仓外 CWP findings.md（`docs/plans/repository-state-audit-2026-10-04/findings.md` L15/L29） | “CWP PWF 记有 budget provider 集成、**62 项测试**和 **BYD 真实 CNINFO E2E**”；`config/source_acquisition.yaml` 指向 `../StockInfoDLSimple/cwp-cninfo-bounded-budget`、`stockinfo-cninfo` **1.2.0** | 指向 worktree `cwp-cninfo-bounded-budget@8ed5fdd` | 本地侧部分吻合：分支 adapter 版本确为 1.2.0、worktree clean；但 **62 项测试与 BYD 端到端在本仓无任何收据**（无绑定 8ed5fdd 的 pytest/CI/E2E 报告；cwp worktree 内无 `.pytest_cache`、无 report、无 logs） | **不确定——外部引用需总指挥核验**（按 lane 禁令未打开 CWP 仓） |
| 仓外 findings.md L15 “此仓本地没有找到根级 task_plan.md” | 与本轮实测一致 | — | 一致 | 一致 |

## 8. 已有测试、CI、E2E 证据（仅查记录，不运行）

| 命令/Workflow/报告 | 绑定 SHA | 结果与日期 | 是否覆盖 branch-only / dirty 行为 | 限制 |
|---|---|---|---|---|
| `.pytest_cache/v/cache/nodeids`（约 220 个 test id 收集记录） | **无 SHA 绑定** | mtime 2026-07-26 22:25；含 `test_cninfo_api*` 相关 id 31 处、`company_wiki` 相关 23 处 | 覆盖 **dirty WIP 时期**（07 月）的部分测试收集；**不覆盖**分支 budget 测试的存在性无法区分（id 前缀重叠，`test_cninfo_api_budget` 无法与 `test_cninfo_api` 区分统计） | 仅缓存、非报告；不能证明当前工作树状态 |
| `.pytest_cache/v/cache/lastfailed` | 无 SHA | 3 个失败：`test_storage.py::test_load_corrupted_returns_none` + `test_cninfo_api.py` 的 2 个 filter 测试；mtime 2026-07-26 11:27 | 说明 07-26 一轮 pytest 曾有 3 failed（含 cninfo_api 2 个） | 无通过数/总数/耗时；无命令行记录 |
| `e2e_official_report.json` | 无 SHA；绑定 `config_sha256=57aa95e8…`（`config_e2e_official.json`） | 2026-07-25T17:52:33；**`overall_success=true`，case_count=3，directory_compare “Perfect match”**，playwright | 针对 07-25 工作树的官方 E2E；**不覆盖**分支（分支 10-04 才创建） | 报告无 git SHA；cleanup 信息含真实 PDF 文件名/size/sha256（此处仅引用存在性） |
| `e2e_official_report_round1.json` / `_round2.json` | 无 SHA | 2026-07-25 17:51 / 17:53 | 同上（round2=1312 B 与主报告同尺寸，疑似同一次双跑） | 同上；分轮功能本身是 unstaged WIP 的产物 |
| CI（GitHub Actions 等） | n/a | **无 `.github/`、无任何 workflow 文件** | n/a | 本仓无 CI 证据 |
| 分支 commit 自带测试收据 | `947e839`、`8ed5fdd` | commit message 无 body、无测试声明；`cwp-cninfo-bounded-budget` worktree 内无 `.pytest_cache`/report/logs | **分支-only 行为无仓内测试收据** | 与 CWP 外部“62 项测试”声明无法对账（需总指挥核验） |
| CWP 外部记录（62 项 provider tests、真实 BYD 10-K 端到端） | 据称绑定 CWP 侧运行，指向本仓 worktree | 未核验 | 未知 | **外部引用需总指挥核验**；本卡未打开 CWP 仓、未运行任何测试 |

## 9. 建议的后续处置类别（不执行）

每项一个初步类别；均为分类建议，非操作指令。

| 对象 | 类别 | 证据 |
|---|---|---|
| `codex/cninfo-bounded-budget`（2 commits，已 push） | `merge_candidate` | base 是祖先（0/2 计数、cherry 全 `+`、无 patch-equivalent）；CWP 生产配置据称消费其 1.2.0 CLI；合入前需集成测试 + 与 owner WIP 血统对账 |
| 默认 checkout 的 staged adapter 4 件套 + 对应 worktree 编辑 | `preserve_active_work` | owner WIP（07-25 冻结）、blob 均不在历史；无任何 PWF/commit 表明被弃置 |
| unstaged downloader/models/browser/logger/test_downloader（CW-2.27D/H） | `preserve_active_work` | 支撑 adapter 三态/校验/JSON 契约；含分支上没有的独有改动 |
| unstaged README/main/config_template/e2e×2/mapping | `preserve_active_work` | 独立下载器功能与文档 WIP（mapping 意图待 owner 说明） |
| untracked `cninfo_api.py`（pre-budget 独有 blob） | `preserve_active_work` | 运行依赖 + 独有内容；与分支 1.2.0 的取舍 → 总指挥/owner 决策 |
| untracked 且与分支逐字节相同的 5 文件（transport_states、test_cninfo_api、fixture_contract、2 fixtures） | `preserve_active_work`（内容本身 `already_in_base` 于分支） | hash 比对一致；但 WIP 运行依赖本地副本 |
| untracked `scripts/capture_byd_fy2024_fixture.py` | `unique_evidence_preserve` | fixture 唯一出处；分支上不存在 |
| untracked `companies.txt` / `a_share_companies.txt` | `preserve_active_work` | `--companies` 功能输入，配 README WIP |
| ignored：`e2e_official_report*.json`、`.pytest_cache` | `unique_evidence_preserve` | 唯一历史测试/E2E 收据，不可再生 |
| ignored：`downloads/`、`logs/`、`stock_orgid_mapping.json`、`__pycache__`、`.ruff_cache`、`end2end_test` 忽略部分 | `generated_candidate_review` | 疑似可再生运行产物；删前须验证消费者（downloads 被 CWP windows_downloads 引用——外部核验） |
| live 远端 `main` / `feature/local-changes` / `改版新下载器` | `owner_decision_needed` | 对象不在本地、禁 fetch；且同远端属 StockInfoDownloader 叙事（该仓已排除），本卡不评估 |
| 仓库根外 `nul`、`.claude/`、`.codegraph/`、`.mimocode/`、`.benchmarks/`、`logs/progress.json` | `owner_decision_needed` | 非 git 管理，归属/意图无仓内证据 |
| base `v2-clean-rewrite@1693045` 与其 remote-tracking | `no_change` | 本地与 live 精确一致、工作树无 base 文件改动（全部改动为上表新增/修改项） |

**不做**：任何恢复、清理、合并、cherry-pick、删除、分支移动；后续施工由总指挥另立计划。

## 10. 检查命令与结果（脱敏）

全部为只读；均以 `git -C <path>` 或 `cd` 后只读子命令执行，退出码 0 除非另注。

- `git status --short --branch`（两个 worktree 各一次）→ 0；dirty/clean 判定来源。
- `git rev-parse HEAD`、`git branch -vv --all`、`git for-each-ref`、`git worktree list --porcelain` → 0。
- `git symbolic-ref/rev-parse refs/remotes/origin/HEAD` → fatal（本地无此 ref，预期内）。
- `git ls-remote origin` → 0（唯一网络调用，只读；未 fetch、未写 FETCH_HEAD）。
- `git log --all --decorate --oneline`、`git log --format=%B -2`、`git show --stat/--name-status`（两 commit）、`git diff --stat origin/v2-clean-rewrite...codex/cninfo-bounded-budget` → 0。
- `git rev-list --left-right --count`、`git merge-base`、`git merge-base --is-ancestor`（exit 0）、`git cherry -v` → 0。
- `git diff --cached`、`git diff`（逐文件）、`git ls-files --others --exclude-standard`、`git status --short --ignored`、`git check-ignore -v`、`git ls-files` → 0。
- `git rev-parse <blob>` + `git rev-list --all --objects | Select-String <hash>`（blob 可达性）→ 0；`git hash-object -- <file>`（**不带 -w，未写对象库**）。
- `git stash list` → 空；reflog（HEAD、branch）→ 0。
- 文件侧：`Get-Item`/`Get-ChildItem`（大小、mtime、浅层列表）、`Select-String`（标记检索）、行数统计、`Test-Path`、Glob（plan/PWF 文件全仓搜索）。
- 读取（未运行）：`e2e_official_report.json`、`.pytest_cache/v/cache/{lastfailed,nodeids}`、lane 卡、handoff 模板、审计 `findings.md`。
- 跳过/失败项：**`rg` 命令本机不存在**（改用 Glob+Grep+Select-String 等价覆盖）；`Get-Item` 对字面 `nul` 文件返回空（保留名怪异，仅记录存在与列表元数据）；未执行 fetch、未运行 pytest/任何测试、未运行 downloader/下载、未打开 company-wiki 的 CWP 配置正文。
- 未粘贴：远端 URL 已按模板精神仅在 §2 说明性质（与公开 clone 来源一致）、无凭据、无长日志、无 PDF 正文。

## 11. 交接声明

- 我只读取 lane 指定的仓库，没有改动工作树、索引、Git refs、全局配置或其他项目：**yes**（唯一写入为本结果文件；`hash-object` 未加 `-w`）。
- 我没有运行会写文件的测试、构建、下载或 provider/LLM：**yes**（只读了既有报告；未跑 pytest/E2E/downloader）。
- 本报告结论覆盖的 HEAD SHA：`1693045caeb5d72bfc83a4fa6d034802e80b0a3f`（当前 checkout `v2-clean-rewrite`）与 `8ed5fdde5e88c13470c120665ff3074a7f44a052`（`codex/cninfo-bounded-budget` tip，含 `947e839c5e99266b65674eeb080c57d0d11fd353`）。
- 需要总指挥复核的唯一事项：**仓外 CWP 声明的核验**——(a) PWF 记录的 “62 项 provider tests + 真实 BYD CNINFO 端到端” 是否存在及其绑定 SHA；(b) `config/source_acquisition.yaml` 指向 `cwp-cninfo-bounded-budget` 的 `stockinfo-cninfo 1.2.0` budget CLI 是否仍为现行配置；(c) owner 对两套 adapter 血统（主 checkout v1.1.0 WIP vs 分支 v1.2.0 budget）的最终取舍。以上均因 lane 禁令未打开 CWP 仓核验。

---

## 附：审计后变更交接（post-audit addendum，2026-10-04 19:38 +01:00）

> 本附记由同一 harness 在审计完成（约 19:10）后、依用户新指令执行改造而追加。**§0–§11 正文仍是审计时点（改造前）的如实快照**；阅读时请注意：§1、§4（主 worktree 行）、§5、§10 描述的 `4 staged / 1.1.0 血统` 状态**已成为历史**，不要据此制定后续处置。

### 变更依据与边界

- 用户指令：“统一两套版本血统：保留分支的 budget 1.2.0 血统，清理工作区 pre-budget 1.1.0 的 staged 代码”，并确认两项决策：Reading A（用分支内容覆盖主工作区，而非清空 adapter 文件）+ 备份目录 `StockInfoDLSimple\lineage-cleanup-backup-20261004\`。
- 执行时间：2026-10-04 19:10–19:38 +01:00（审计之后）。
- **未动任何 Git ref**：无 commit、无 branch 切换、无 merge/FF、无 fetch、无 stash；远端与两分支 SHA 与 §2/§3 完全一致。

### 实际执行（4 阶段）

1. **备份**（仓库外 `C:\Users\郑曾波\Projects\StockInfoDLSimple\lineage-cleanup-backup-20261004\`）：`staged_1_1_0_index.patch`（85,874 B，4 个 staged 文件）、`am_unstaged_edits.patch`（3,610 B）、`cninfo_api_prebudget_504.py`（20,179 B，git blob `c1864c7306…` 与原文件 hash 一致）、`status_before.txt`、恢复说明 `README.md`。
2. **覆盖**：`git checkout codex/cninfo-bounded-budget -- <13 paths>`（逐路径显式列出，未用通配，避免波及 11 个 unstaged 文件）。
3. **清残留**：`tests/unit/test_downloader.py` 4 处 1.1.0 → 1.2.0（函数名/docstring/patch 值/assert）；全仓 `1.1.0` 扫描零命中。
4. **验证**：13 路径 worktree+index hash 与分支 **13/13 一致**；`git diff --cached`（src+tests）对分支树 **空差异**；staged stat **13 files, +3206**（等于分支 diff）；status 形态 `A ×13 / M ×11 / ?? ×3`；离线单测 `python -m pytest tests/unit -q` → **188 passed / 0 failed（83s, exit 0）**。

### 变更后状态（以本附记为准）

| 项 | 审计时点（正文） | 现状（19:38） |
|---|---|---|
| staged | 4 文件，pre-budget 1.1.0（blob 均不在历史） | **13 文件，内容 = `codex/cninfo-bounded-budget@8ed5fdd`** |
| unstaged | 13 文件 | **11 文件**（2 个 AM 未暂存编辑被分支版取代；`test_downloader` 另改 4 行版本标记） |
| untracked | 9 文件 | **3 文件**（`companies.txt`、`a_share_companies.txt`、`scripts/`；其余 6 个转为已跟踪，内容零变化） |
| 1.1.0 血统 | 工作区中 | 仅存在于备份目录（可完整恢复） |
| refs / worktrees / 远端 | §2–§4 | **未变** |

附带发现：1.2.0 血统 6 个测试文件恰为 **62 项**（19+7+10+19+2+5），与 §7 中 CWP “62 项 provider tests” 外部声明数字吻合（绑定 SHA 仍需总指挥核验）。

### 遗留决策（与 §9/§11 一致，未变）

- 13 个 staged 的 1.2.0 文件是否提交到 `v2-clean-rewrite`、或直接 FF 合并分支——**总指挥/owner 决定，本次未执行**。
- §9 分类表中其余项（独立 WIP、ignored 工件、远端独有 heads、`nul` 等）不受本次变更影响。
- (a)(b) 两项外部声明核验仍待总指挥；(c) 血统取舍已按用户 2026-10-04 指令落定为 **1.2.0 胜出**。

## 并线实施附记（2026-10-04）

`codex/cninfo-bounded-budget` 已快进到目标分支 `v2-clean-rewrite@8ed5fdd` 并推送。隔离干净树的 provider 测试 171 passed / 21.69 秒；CWP provider contract/E2E 测试 20 passed / 4.46 秒，运行时设 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，仅出现一条既有 asyncio 配置提示。第一次 CWP pytest 在测试收集前因全局 `langsmith` 插件的 Pydantic DLL 加载错误退出；隔离插件自动发现后通过。保留 owner checkout 里其他 11 个 tracked 修改及 3 个 untracked 文件；没有改写 CWP `config/source_acquisition.yaml`。原 BYD FY2024 真实 CNINFO E2E 收据已记在 narrative-evidence-pilot PWF，本轮未重跑。
