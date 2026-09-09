# filing-fetch planning 独立只读审计

审计日期：2026-09-04。审计者：独立子代理 `filing_planning_audit`。

范围：`C:/Users/郑曾波/Projects/filing-fetch` 根目录及全部源码子目录的 planning-with-files 文档和关联计划/审计文档。完整读取 planning-with-files SKILL.md 后执行。源仓始终只读；没有修改收据、Git 配置、生产资源，没有运行测试、E2E、下载或网络。本文件是主代理明确授权的新审计产物，不是历史收据的替代品。

## 1. 逐文件全文阅读覆盖

只发现 **1 组 planning-with-files 三件套**。核对使用递归源目录枚举、隐藏源目录和 Git 文件清单；排除 `.git`、`.mypy_cache`、`.pytest_cache`、`.ruff_cache`、`__pycache__`、`.benchmarks`、`.runs` 等生成物目录。关联计划/审计文件共 **9 份、732 行，全部完整读取**。

| 相对 filing-fetch 的文件 | 行数 | 建议 |
|---|---:|---|
| `task_plan.md` | 232 | 历史封存；保持原文，通过外部状态入口解释 |
| `findings.md` | 61 | 历史封存；不重写旧缺陷清单 |
| `progress.md` | 26 | 历史封存；不回写旧测试记录 |
| `TERMINAL_NOTICE.json` | 13 | 保持原样 |
| `assurance/fc/FC-903/03_change_contract.md` | 62 | 已审契约，保持原样 |
| `assurance/fc/FC-903/11_implementer_receipt.json` | 120 | 已审证据，保持原样；外部记录 hash 绑定不一致 |
| `assurance/fc/FC-903/12_reviewer_receipt.json` | 79 | 已审证据，保持原样 |
| `assurance/fc/FC-903/REVIEWER_REPORT.md` | 79 | 已审报告，保持原样 |
| `e2e/E2E_DESIGN.md` | 60 | 活动设计说明需要纠偏 |

支持证据另读：`tools/verify_plan_claims.py`、`pyproject.toml`、`.github/workflows/quality.yml`、`.githooks/pre-commit`、`.pre-commit-config.yaml`、实际 `.git/hooks/pre-commit`、`tests/e2e_support/isolated_wiki.py`、`e2e/run_companies_reuse_only_e2e.py`。关联 revenue state 仅解析状态与计数，没有在本子任务中逐份审核其 117 项依赖收据。

### 审计前 SHA-256

| 文件 | SHA-256 |
|---|---|
| `task_plan.md` | `0d29452185825a6f54b00457256f2bedd51ee2582ba336133c97396f09523cd6` |
| `findings.md` | `f0448d98914791396e4e3f9389fe680117d102ed75fc0c907117775de3f381c7` |
| `progress.md` | `ffaf579b80059798fd3a03f14b1830edff5f11aea03168bd2cbdc4779734f41d` |
| `TERMINAL_NOTICE.json` | `b3f3ceb22f17e8a174bf5bd535bddef619132c9e6d72277eae3eea1e4eac9103` |
| `assurance/fc/FC-903/03_change_contract.md` | `c18ffc626652bef8a799a77ca425b69a4af14293afedb751fe923f517ff3e09a` |
| `assurance/fc/FC-903/11_implementer_receipt.json` | `010699cab407eb20aafd7f985ed494e262d84f2fd0c3c479e83c2c1ed96f089d` |
| `assurance/fc/FC-903/12_reviewer_receipt.json` | `bcfb14e30b2f82ae1520b929f87a8fb732653f992eed35ef360a55c5589334d3` |
| `assurance/fc/FC-903/REVIEWER_REPORT.md` | `6d2dfe9caa6ff86e4b0cbd067a47f996dbee90bae9dd3baecef9192c7ea14bcc` |
| `e2e/E2E_DESIGN.md` | `3775907219a315a2db781321ab2801a8ce5bf3b7dfcda65c166b505bd61933d0` |

## 2. 真实最新状态

- HEAD：`89c8bdb2cfba4d88720d005d0558f422957e8ade`，2026-09-02T21:16:19+01:00，新增 lightweight pre-commit gate。
- 审计时 Git 工作区干净；Git 读取用户全局 ignore 有权限警告，但 status/log 正常返回。
- 2026-08-31 提交 `884a380` 引入 `TERMINAL_NOTICE.json`，将根三件套标为 `closed_superseded_incomplete`，最终接管者是 `../revenue-forecast/assurance/unified_completion/state.json`。
- 直接解析该 state：`plan_status=completed`、`implementation_status=completed`、117 个 unit 全为 `accepted`。这是当前账本内容核对，不是复跑 117 项或重新验证全部依赖收据。
- `../revenue-forecast/compatibility/current.json` 的 filing HEAD 与实际 HEAD 一致；其 `updated_at=2026-08-12T00:00:00Z` 与晚期 HEAD 更新不一致，是 revenue 侧元数据审计事项。
- 2026-09-01 多次 CI 修正和 2026-09-02 pre-commit 变更在代码与 Git 中存在。没有据此声明当前 CI 或测试通过。

### 最近提交证据

| 提交 | 日期 | 内容 |
|---|---|---|
| `89c8bdb` | 2026-09-02 | lightweight pre-commit：ruff + mypy |
| `e5639a3` | 2026-09-01 | CI 安装 pytest-cov |
| `0003a78` | 2026-09-01 | line endings / CREATE_NO_WINDOW type ignore |
| `f74a18c` | 2026-09-01 | Linux CREATE_NO_WINDOW type ignore |
| `c5b7b08` | 2026-09-01 | mypy 固定 1.19.0 |
| `454f284` | 2026-09-01 | CI YAML / notices BOM |
| `884a380` | 2026-08-31 | 根 planning 三件套 terminal notice |
| `5a1c18f` | 2026-08-18 | newer_revision GAP orchestration |

历史 planning Git 证据：`2f6c18c`（2026-08-09）添加 task_plan 状态覆盖；`8714a66`（2026-08-09）三件套入库；`959d04c`（2026-08-11）FC-903 reviewer accepted；`de73a5d`（2026-08-08）harness 改名 companies-reuse-only。

## 3. 历史原文需要外部解释的漂移

### 根三件套：保持原文

- `task_plan.md:3` 指向 8/9 FCAP r2，是中间接管入口，不是最后状态入口。
- `task_plan.md:18–21` 的“当前基线”、未提交、nul、无 pyproject 是历史开始态；现在工作区干净且 pyproject 存在。
- `task_plan.md:154` 写 `completed（HK 环境阻断）`，但 `:166–172` 已写 HK FY2025 修正后跑通。
- `progress.md:14` 写 HK 阻断，`:22–25` 已追记跑通；属于历史先后记录，不应重新当成当前阻断。
- `progress.md:20–21` 的 113 tests / 96% / 未提交是历史记录。
- `findings.md:5` 的代码行数、`:38–55` 的 D1–D15 清单、`:57–61` 的 66 tests 盘点不能直接作为当前待办。

### FC-903：明确的 receipt_binding_mismatch

- `12_reviewer_receipt.json:4` 指向 implementer SHA-256：`010d0b9e9f4547ef2a71d9e7b47a90eb768744c8dca4825fe6b32ea157bdb3df`。
- 当前 implementer 文件 SHA-256：`010699cab407eb20aafd7f985ed494e262d84f2fd0c3c479e83c2c1ed96f089d`。
- 当前 implementer CRLF→LF 后 SHA-256 为 `d9fe87d1f21f6286b058fa2376101c5f95af3adc72ab0cef173e08357109dc46`，仍不匹配；不是单纯 CRLF 差异即可解释。
- 当前 reviewer receipt hash 为 `bcfb14e30b2f82ae1520b929f87a8fb732653f992eed35ef360a55c5589334d3`，与 implementer 的 `review.reviewer_receipt_sha256` 一致。
- Git 显示 implementer 文件在 `959d04c`（reviewer accepted）提交。这与回填 review 段造成旧绑定漂移的情形相容，但不足以确定原因。
- 不改原收据，不撤销或伪造历史 verdict；外部记录 hash mismatch，不能称当前两份文件已经形成完整互证链。
- `REVIEWER_REPORT.md` 已解释 caller count 2 vs 实际 1、diff budget 超 13 行两条非阻断观察；无需重写已审报告。

## 4. 活动 e2e/E2E_DESIGN.md 精确建议 patch

以下行号针对审计前 60 行文件。只修改活动设计说明，不修改源代码和历史审查收据。

### 4.1 第 1 行替换

```markdown
# filing-fetch companies-root reuse-only E2E —— 设计与当前边界
```

### 4.2 第 3 行替换并追加范围

```markdown
原始设计：2026-08-07 ｜ 状态核对：2026-09-04 ｜ harness 已实现；本次仅静态核对，未重新执行 E2E。

当前范围仅为 synthetic companies-root 的复用路径，不覆盖 dayu/Dropbox roots、latest_as_of gap plans、artifact bundles 或 consumer parser/LLM zero-call reuse。不能据此宣称三仓全链路验收完成。
```

依据：`e2e/run_companies_reuse_only_e2e.py:9` 的 `SCOPE (WU-6.3)` 已明确该边界。

### 4.3 第 10–11 行替换

```markdown
**当前结论**：文档 seed 已改为 synthetic，不再从生产 companies/ 复制；每次建立新的隔离状态目录。仍读取本地 company-wiki 代码、worker 配置，且 security-master 存在时优先复制本地快照、缺失时生成 synthetic fallback，因此不能把全部输入描述为完全独立于本地环境。
```

依据：`tests/e2e_support/isolated_wiki.py:259–262, 283–290, 331–342`。

### 4.4 第 14 行替换

```markdown
**当前范围**：断言覆盖 companies-root reuse-only 路径：
```

### 4.5 第 19–20 行替换

```markdown
5. 双跑比较 request_id 与 snapshot_sha256
6. 首轮结果与 golden 比较 status、request_id、snapshot_sha256、https_url、canonical_tail、missing 六项投影字段
```

依据：harness `:181–185, :228–234`；原“handle 逐字段一致 / 全字段”超出实际断言范围。

### 4.6 第 25 行及第 46 行历史实验加日期限定

```markdown
**历史记录（2026-08-07）**：改 US seed 字节使 golden 键变化并显式失败；本次未复跑该变异实验。
```

### 4.7 表格第 35、37、39 行替换

```markdown
| company-wiki 运行时 | 本地 `Projects/company-wiki`；CI 通过 revenue-forecast compatibility manifest 和 `ci_checkout_siblings.py` 准备 sibling runtime |
| 确定性 | 双跑仅比较 request_id 与 snapshot_sha256；golden 比较六项结果投影 |
| 网络与环境 | reuse-only harness 无下载动作；隔离 fixture 仍读取本地 worker 配置及可用 security-master，缺失 master 时使用 synthetic fallback |
```

### 4.8 第 42–43 行收窄退出码保证

```markdown
harness 显式返回：断言/golden 不匹配为 exit 1，缺少 golden 为 exit 2；其他环境异常可能抛出异常退出，不能保证全部输入/环境错误都稳定归类为 exit 2。golden 不匹配时打印字段级 diff。
```

依据：harness build/JSON 操作不存在统一异常→exit 2 封装。

### 4.9 第 49–50 行替换

```markdown
- `tests/test_e2e_isolated_wiki.py` 继续覆盖隔离实例行为细节；`IsolatedWiki.seed_market` 已改用 `SYNTHETIC_SEEDS` 写入文档和 sidecar，旧“迁移 synthetic seed”候选项已由代码演化实现。这里不据此声明当前测试已经运行通过。
```

### 4.10 第 59–60 行替换

```markdown
- 当前本地 `.git/hooks/pre-commit` 调用 `.pre-commit-config.yaml`，执行 ruff 与两个公开契约模块的 mypy；完整回归需另行执行。`.githooks/pre-commit` 保留旧 pytest/E2E/install-sync 脚本，但本次查询 `core.hooksPath` 未设置，不能称其每次提交自动执行。
- `.github/workflows/quality.yml` 在 push/PR 配置 manifest-driven sibling runtime、静态检查、类型检查、测试/coverage、config doctor、reuse-only E2E、install-sync 和 plan verifier；本次仅核对配置，未查询远端运行结果。
```

## 5. 建议新增 filing-fetch/CURRENT_STATUS.md

父任务确认根三件套封存，使用新 `CURRENT_STATUS.md` 作为外部入口，而非修改三件套正文。以下是建议内容，源仓尚未由本审计者写入。

```markdown
# filing-fetch 当前计划状态

核对日期：2026-09-04。范围：只读核对计划、Git、静态实现及历史收据；未重新运行业务测试、E2E、下载或 CI。

## 状态入口

根 task_plan.md、findings.md、progress.md 由 TERMINAL_NOTICE.json 标记为 closed_superseded_incomplete，保持历史原文，不是当前执行队列。
统一状态入口：[三仓机器状态](../revenue-forecast/assurance/unified_completion/state.json)。
本次读取该账本得到 plan_status=completed、implementation_status=completed、117/117 units accepted；这不是对全部历史收据的重新验收。

核对基线：filing HEAD 89c8bdb2cfba4d88720d005d0558f422957e8ade，审计前 Git 工作区干净。后续文档修订不改变该代码验证基线。

## 历史文件的解释

- 根计划的“当前基线”、66/113 tests、96% coverage、未提交、无 pyproject 等均是历史记录。
- HK 阻断已在历史正文中追记 FY2025 修正后跑通；本次未复跑，不把早期阻断继续当当前状态，也不把旧跑通当当前成功。
- FC-903 review 是 2026-08-11、filing 2e47089 的历史验收，不覆盖当前 HEAD 的所有后续变更。
- FC-903 reviewer 所指 implementer SHA256 与当前文件不一致：预期 010d0b9e9f4547ef2a71d9e7b47a90eb768744c8dca4825fe6b32ea157bdb3df，当前 010699cab407eb20aafd7f985ed494e262d84f2fd0c3c479e83c2c1ed96f089d。保留原收据，状态为 receipt_binding_mismatch；原因和原始签署字节需要后续独立核对。

## 当前核对与限制

- e2e/E2E_DESIGN.md 应以 companies-root reuse-only 边界解释，不是完整三仓全链路。
- 当前本地 pre-commit 使用 .pre-commit-config.yaml 的 ruff/mypy；旧 .githooks 全量脚本未被 core.hooksPath 选用。
- 只读命令 python -B tools/verify_plan_claims.py --plan task_plan.md --progress progress.md --json 返回 exit 0、ok=true。
- verifier 仅识别 Phase 1/2/3/5/6，未识别带 completed（HK 环境阻断）后缀的 Phase 4；该结果不能证明六阶段全部经过此次验证，也不证明旧测试结果在当前 HEAD 复现。
```

## 6. 校验结果与错误记录

实际安全执行的唯一程序校验：

```text
python -B tools/verify_plan_claims.py --plan task_plan.md --progress progress.md --json
exit_code = 0
ok = true
problems = []
parsed phases = [1, 2, 3, 5, 6]
```

该程序经全文静态确认只读取 plan/progress 并输出结果；`-B` 禁止字节码写入。它没有读取 terminal notice 来改变根计划状态，也没有验证所有历史测试收据。Phase 4 后缀不匹配其 heading 正则，故被漏掉。

审计过程错误及处理：

| 问题 | 处理与结果 |
|---|---|
| Git 全局 ignore 读取权限警告 | status/log 正常返回；未改全局配置 |
| 首次 `rg --no-ignore` 进入 `.pytest_cache` 被拒 | 改为显式排除生成缓存的递归源目录枚举，完成源文档覆盖 |
| 猜测 `.github/workflows/ci.yml` 不存在 | 读取实际 `.github/workflows/quality.yml`，完整核对 |
| PowerShell `foreach ... \| ConvertTo-Json` 语法错误 | 先赋值数组再转 JSON，成功输出 9 文件完整 hash |
| `git config --get core.hooksPath` exit 1 | 表示未设置；实际 `.git/hooks/pre-commit` 全文证实当前使用 pre-commit framework |

## 7. 独立审查边界

本子任务是计划现状的独立只读审计，不是重新执行 FC-903 或统一 117 项的独立验收。父任务后续文档补丁需另行检查：应只新增外部当前状态入口、修正活动设计误述；冻结三件套、terminal notice、历史契约与收据的上述 SHA-256 应保持不变。
