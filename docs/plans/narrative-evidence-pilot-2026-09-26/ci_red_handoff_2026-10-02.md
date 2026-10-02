# CI Contract 红灯修复交接卡（2026-10-02）

> 给后续模型/agent 的接手说明。先按本卡继续，不要重做已完成根因分析，也不要放宽来源哈希、证据绑定或其他业务校验。用户要求：大节点验证即可，不要为每个小修改新增审查节点。

## 2026-10-02 当前状态修正（以下旧快照被本节覆盖）

- 当前远端 `master`/`origin/master` 为 `41aa176`，前两项修复提交为 `b168a2e` 与 `4c66a4e`；CI run `37043343785` 证明前 6 个失败身份已清零，剩余 FC905 PI01/PI02/PI09 的 `ModuleNotFoundError` 是依赖漏声明，已补 `cryptography>=41.0` 并推送。
- `37045273003` 是依赖修复后的旧 workflow 验证 run。最新可见 Unit/Contract 三版本及其它 jobs 的早期步骤通过，但三版 coverage step 已超过 1h46、0/3 matrix jobs 完成；匿名页面不能查看 logs，状态保持 pending。
- R4 S8 第一轮已在 `41aa176` 推送：`tests/` 收集 3,814 项；旧 workflow 每个 Python 版本都重跑全量 coverage、用 `|| true` 吞 pytest 失败，并重复执行已被 Contract 覆盖的六个 canary。`37055076384` (#166) 中 3.11/3.13 与 fast jobs 通过，3.12 Unit+Contract 通过，coverage 运行约 25 分钟仍未结束。这说明只把 coverage 从三次减为一次，仍让每次提交等待长测，不符合日常节奏。
- 当前工作树进一步将 push/PR 主 CI 改为快速阻断门（3 版 Unit+Contract、单次静态/配置检查、CLI smoke、secret scan、Markdown 检查）；把全量 `tests/` + fresh branch coverage + FC-1204 阈值完整保留到每周及手动的 `deep-validation.yml`，最长 180 分钟，失败继续由 JUnit 摘要给身份。新 push 对同 ref 的旧 CI 设 `cancel-in-progress`，防止快速提交时浪费在已过期提交上。这个分层尚未提交，需新 Actions 证明 push run 不再进入 coverage 且 fast jobs 全绿。
- `collect_news.py --help` 是 intentional frozen legacy writer，实测 exit 78；CI smoke 改成精确验证阻断输出/退出码，不把预期失败当成功命令，也不吞任何未知错误。
- `tests/contract/test_source_catalog_temp_worker_governance.py` 与 `tools/pre_push_gate.py` 的短 repo-local basetemp regression 已含在 `41aa176`。合成 coverage failure probe 验证 exit 1 + fresh source-catalog JSON；正常 commit hooks 和完整 pre-push 已通过，工作树/远端 HEAD 一致。
- 当前旧 workflow run `37055076384` (#166)：fast jobs 与 3.11/3.13 jobs 已通过；3.12 Unit+Contract 已结束，单次 full coverage 在运行（最近页面显示约 25 分钟），未见失败 annotation，但匿名日志不可读。它由新分层方案 supersede，作为耗时证据保留；最终日常门禁验收改看新 commit 的 fast CI，深度 coverage 的完整验收走单独 workflow。

## 当前事实

- 分支：`master`；上次读取时本地 `HEAD` 与 `origin/master` 都是 `1504d6a`。
- 最近远端 Actions：run `37012332197`（commit `1504d6a`）。Python 3.11/3.12/3.13 的 Unit tests 全部通过；Contract tests 三个版本均失败。
- 后续提交 `b168a2e` 的 run `37043343785` 已验证六项旧 Contract 回归不再失败；余下 PI01/PI02/PI09 在三个 Python 版本均报告 `ModuleNotFoundError`，其余 Unit/jobs 通过。根因已定位为 `cryptography` 漏列入 CI `requirements.txt`；当前工作树已补依赖清单，待本地验收与二次推送。
- 该 run 的 Contract 失败身份：
  - `tests.contract.test_zr203_reader_rewire::test_read_entrypoints_never_construct_catalog_store`
  - `tests.contract.test_zr1003_shadow_assertions::test_c2_recorded_review_unblocks`
  - `tests.contract.test_source_catalog_temp_worker_governance::test_stop_does_not_touch_unowned_live_workers_or_temporary_files`
  - `tests.contract.test_fc905_receipt_envelope::test_pi09_envelope_to_dict_deterministic`
  - `tests.contract.test_fc905_receipt_envelope::test_pi02_reviewed_detected_and_ignored_forwarded`
  - `tests.contract.test_fc905_receipt_envelope::test_pi01_reviewed_not_detected_forwarded`
- 本地有未提交修改，当前修改范围为测试、CI 诊断、门禁和本计划文档；生产原文、raw、配置和数据库没有改动。
- 本轮直接运行受影响用例：**33 passed in 9.28s**。收窄后的 `metadata-reader-contracts` pre-commit hook 实际运行并通过。
- 本轮随后对远端最新六项失败身份做独立复跑：**6 passed in 4.37s**（Windows/Python 3.13.9）；新增的短路径集成回归门也通过。
- pre-push 的 pytest 临时目录 bug 已被证实并修复于当前工作树：旧随机目录长度超过 60 字符、被 conftest 重定向到用户 Temp，且 CI gate 隐藏了重定向证据；现在使用 `tmp/pp*`，验证 `relocated=false` 和 run root 清理。
- 早先一次 `python tools/pre_push_gate.py` 曾因终端会话断开而无结果；该次进程和专属目录已清理。随后修正 basetemp 根因后，本轮完整门禁已重新运行并全部 GREEN，且真实 pre-commit hook Passed。

## 六项失败的根因与当前处理

| 失败 | 判断 | 当前工作树中的处理 |
|---|---|---|
| ZR-203 reader rewire | `d5162e5` 已有意移除 `_remediation_pending`，因为补救提案状态不再阻断读取；AST 测试仍把已删除方法列为入口。 | 从结构性入口清单移除该方法，继续检查 `resolve` 不构造 writer。 |
| ZR-1003 C2 review receipt | 测试沿用旧的“仅填 status/reviewer/evidence hash”形状；当前写入合同要求 SHA-256 格式、source/policy 双绑定、证据载荷与 hash 一致并复核扫描 verdict。 | 只修正测试 fixture，填入有效 source SHA、policy hash、evidence payload 和匹配 hash；生产校验没有放松。 |
| Worker temp governance | 测试在默认 `paused` 状态下期待 stop 删除外来 runtime/lock，和当前“暂停时保留、显式 resume 才 reconcile stale 文件”的行为矛盾；测试标题及安全描述要求不要触碰外来 worker。 | 断言外来 PID 未被终止且 runtime/lock 内容原样保留。 |
| FC905 三项 | run `37043343785` 已暴露 `ModuleNotFoundError`：测试 `_record_review` 使用 Ed25519 fixture，但 clean CI `requirements.txt` 未声明 `cryptography`；本机预装包掩盖了问题。产品 `_ed25519_verify` 也依赖此 backend，并在缺失时安全拒绝签名验证。 | 已在工作树将 `cryptography>=41.0` 加入 requirements 和 pyproject catalog/test/all extras；跑完整门禁、普通提交推送后，以新 GitHub 三版本矩阵验收。 |

## 为什么 pre-commit 没拦住

1. 这轮 Contract 失败的三项过期测试不在当时的 commit hook 三模块范围（shared reader、FC905 receipt、B10）内；hook 是按改动路径触发，不是全量 Contract CI。
2. FC905 三项虽然在重点集合中，但 WSL/Python 3.12 本机结果是通过；因此本地 hook 没有复现远端 Linux matrix 的差异。
3. pre-push gate 也只跑选定高风险 contracts，并不运行整个 Contract matrix。之前的 GREEN 只证明所选测试通过，不代表 CI 全集通过。
4. Windows 默认 `%TEMP%` ACL 会使 pytest fixture setup 失败。commit hook 现复用 `tools/pre_push_gate.py` 的短 workspace basetemp、UTF-8 和 cache-provider 设置；仍只跑三个 reader/receipt/B10 模块。完整 Unit 放在 push 前，广泛 Contract 放在远端 CI，避免每次提交运行整个矩阵。
5. 本机 pre-commit cache 位于用户配置目录且当前只读。执行 `pre-commit` 命令本身时需可写 cache；本轮用临时 `PRE_COMMIT_HOME` 完成了验证。这是本机环境问题，不是远端失败的根因。
6. 原门禁所称“短 basetemp”并不短：仓库路径约 34 字符，`.pp-` 加随机 suffix 约 36 字符，总长约 71，触发 `conftest.py` 的 60 字符重定向。成功 pytest 的输出被 `_run` 捕获，GREEN 日志未显示 `relocated=true`；本轮真实 cleanup 回执为 `removed=false`。当前修复移至 ignored `tmp/` 短 run root，并要求可见证据确认没有重定向及执行后已删除。

## 接手后按此顺序完成

1. **先确认状态和差异**：`git status --short`、`git diff --check`、查看本卡列出的工作树修改。不要 reset、clean 或改动 raw/数据库/生产配置。
2. **跑聚焦 hook**：`python tools/pre_push_gate.py --metadata-reader-contracts-only`。该命令覆盖 reader/receipt/B10 三个模块及本轮三项 Contract 回归，使用仓库 `tmp/` 短隔离目录并检查未重定向及清理。需要验证真实 hook 时再运行 `pre-commit run metadata-reader-contracts --files ...`；若默认 cache 只读，用 workspace 临时目录设置 `PRE_COMMIT_HOME`，不要把环境故障误判为测试失败。
3. **本机集成验收已完成**：本轮 `python tools/pre_push_gate.py` 全部通过，包含静态检查、全量 Unit、既定重点 Contract 和本轮三项失败回归；所有 pytest 阶段均验证 `relocated=false` 且 run root 清理完成。真实 pre-commit hook 也已通过。
4. 把修复、诊断 helper、hook 和 PWF 更新一起做一次普通提交并推送 `origin/master`；不使用 `--no-verify`、force push 或绕过 hook。用户已授权正常提交/推送。
5. **唯一最终验收点**：核对加入依赖后的新 Actions run。Unit 与 Contract 的 3 个 Python 版本以及 workflow 其他必需 jobs 均绿，任务才算完成。WSL 当前返回 `E_ACCESSDENIED` 且未发现 Docker/其他 Python minor runtime；不得仅因 Windows 本机预装包下测试通过就关闭，也不得仅因诊断 reporter 通过就关闭。
6. 最后把最终 commit、Actions run 和绿灯状态写回 `task_plan.md`、`findings.md`、`progress.md` 和本入口 README，然后停止。只在这个集成验收节点做一次整体确认，不增设逐文件/逐小步骤签收。

## 本轮未提交文件

- `.pre-commit-config.yaml`
- `tools/pre_push_gate.py`
- `tools/summarize_junit_failures.py`
- `tests/unit/test_summarize_junit_failures.py`
- `tests/contract/test_zr203_reader_rewire.py`
- `tests/contract/test_zr1003_shadow_assertions.py`
- `tests/contract/test_source_catalog_temp_worker_governance.py`
- 本交接卡和同目录 PWF 更新


## 2026-10-02 后续分层与测试分类（当前权威状态）

- 在 `41aa176` 之后的当前工作树中，`ci.yml` 将每次 push/PR 限制为三版 Unit+可移植 Contract，3.12 静态/config/计划门禁只跑一次；全仓 coverage/FC-1204 移到每周或手动 `deep-validation.yml`，180 分钟上限。新 commit 对同 ref 的过期快速 CI 执行 cancel-in-progress。
- 原 Contract workflow 整文件排除清单已换为测试级筛选：`not slow and not real_data and not requires_corpus`。此处的 `slow` 仍由 Deep Validation 运行；真实本机 catalog/raw 和外仓 golden corpus 测试由 owner 主机 opt-in 运行。不是删除用例。
- 被分类的 8 个模块本机快速筛选 **48 passed, 18 deselected in 8.60s**；FC-804 并发组单跑 **6 passed in 14.30s**。另测得 CW-2.28 一个 parser isolation case 用时 **43.32s**，同模块首三项已耗约 50s，故该完整 backfill process contract 模块标记 `slow`，14 项仍在 Deep Validation。ZR-409 合成测试恢复普通筛选，production path journey 保持数据 marker。golden corpus 测试支持 `COMPANY_WIKI_GOLDEN_CORPUS`，其他 root/catalog 支持 `COMPANY_WIKI_REAL_WIKI_ROOT`、`COMPANY_WIKI_TEST_CATALOG`。
- owner 本机真数据命令：设置 `COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS=1`，必要时指定上述路径变量，再运行 `python -m pytest tests/contract -m "real_data or requires_corpus"`。该项不是 GitHub gate，因为 runner 没有用户生产 catalog、Dropbox/Dayu 根或 RF golden corpus。
- `deep-validation.yml` 运行 `python -m pytest tests/ -m "not real_data and not requires_corpus" --cov=src/company_wiki/source_catalog --cov-branch --cov-report=json`，失败由 JUnit 汇总；只有 pytest 成功才检查 FC-1204 coverage threshold。
- 本阶段尚待：完整本机 `python tools/pre_push_gate.py`；Ruff、两 workflow YAML/invariants、`verify_plan_claims.py --plan-dir .`、`git diff --check`；之后普通 commit/push 并等新 push CI 完成。新 CI 全绿后更新此卡、task_plan/findings/progress/README 并收尾。旧 run `37045273003`/`37055076384` 是旧 workflow 耗时证据，不要求等它们结束。
- 注意：本机一次完整 Contract run 在 slow 模块标记前选中 2,134 项；过程中没有已观察到的断言失败，但因 CW-2.28 parser isolation 长耗时被主动中断，run 未完成，不能报告 PASS。唯一 run root 已清理。已有的 48 项重点增补 Contract 和 6 项 FC-804 并发分别完整通过；完整剩余矩阵由下一次 push Actions 三 Python 版本验收。

## 2026-10-02 最新状态：按用户最新指示撤销自动长测方案

本节覆盖本卡前文仍提到“weekly/manual Deep Validation”的临时方案。用户明确希望 CI 简单、失败少、单次不要几十分钟。当前交付结构如下：

- `.github/workflows/ci.yml` 单 workflow、单 job、Python 3.12、10 分钟硬上限。一次安装依赖，运行 Ruff、核心 mypy、compileall/config doctor、Unit、可移植 Contract、CLI smoke、secret scan 和 JUnit failure summary。新同 ref push 取消旧 fast run。
- 自动 Contract 选择：`not slow and not real_data and not requires_corpus`。环境依赖/慢测试未删除；在测试代码中有 marker，可供本机或人工回归。
- 3.11/3.13 matrix、独立 CLI/secret/markdown jobs、唯一 test symbol 与 plan-claim CI 门均已移除。前两者需人工按需检查；低价值文本/文档结构检查可由本机工具运行。
- 自动 weekly/manual `deep-validation.yml` 已删除。Full branch coverage 与 FC-1204 ratchet 仍可人工运行，但不由 GitHub Actions 自动启动：
  `python -m pytest tests/ -q --tb=short -m "not real_data and not requires_corpus" --cov=src/company_wiki/source_catalog --cov-branch --cov-report=json`，然后设置 `FC1204_COVERAGE_GATE=1` 运行 coverage ratchet 测试。
- 本机 `python tools/pre_push_gate.py` 七阶段 **GREEN**；Ruff、CI workflow YAML/invariants、计划 claim verifier 和 diff check 通过。8 个原整文件忽略模块 **48 passed, 18 deselected**；FC-804 **6 passed**。完整本机 portable Contract run 未完成，因 Windows parser isolation 长耗时主动停下，不得报告全套绿。已跑关键 slow parser 单测 **1 passed in 43.32s**。

**剩余唯一验收点：**正常 commit/push 后，新 GitHub fast CI 在 10 分钟硬上限内通过。检查 job 数量、实际 wall time 与失败摘要；若超过上限/出现失败，按输出定位并缩减或修复，不延长至长测。
- 新 marker expression 的最终 collection-only 为 **2,120 selected / 32 deselected in 16.96s**，57 字符 basetemp、未重定向。这个结果只确认选择集合，不要写成 2,120 tests passed。完整本机总执行未完成，等待单一 Actions run 作验收。
