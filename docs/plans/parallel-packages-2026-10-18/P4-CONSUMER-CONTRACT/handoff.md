# P4-CONSUMER-CONTRACT 交接（handoff）

## 1. 交付内容

- 车道：`tests/integration/test_p4_contract/**`（10 个测试模块 / **34 用例** + `support/` 14 个模块 + `conftest.py`）
  与本卡目录 `docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/**`（夹具、日志、收据、PWF、审查报告、交接件）。
- 分支 `codex/p4-consumer-contract-20261018`，基线 `4045787f`；`git diff 4045787f..HEAD` 全部路径 ⊆ 上述写集，
  第 4 节 ROOT 独占路径与 `tests/integration` 其他目录 **0 改动**（`disclosure.pdf` 被 `.gitignore:5` 忽略，用 `git add -f` 入库，未改 ignore 规则）。
- 提交链：`cdf5be5a` 实现（含夹具/日志/收据/PWF）→ `025c0b71` 审查修复（3 项，写集内）→ `5f840650` 审查报告 + 最终收据 → 本交接提交。
- 冻结接口按 card §5：env 五个开关、`p4-consumer-commands/1`、`p4-consumer-observation/1`、`p4-contract-receipt/1`；
  `company_wiki` 导入路径指向本 worktree（INTERFACES §10 第 2 行验收通过）。

## 2. 验收结果

- 无 env：`green-allskip-20261018.log` = **34 skipped，exit 0**，34 条 reason `P4 requires CWP_P4_CATALOG_CONFIG`（`-rs` 可读），0 个 pass。
- 有 env（`CWP_P4_CATALOG_CONFIG=<本卡 fixtures>/catalog/catalog.yaml`）：`green-20261018.log` = **34 passed，exit 0**；
  审查者独立复跑同为 `34 passed in 8.26s`。
- 静态：`static-ruff-20261018.log` = All checks passed；`static-mypy-20261018.log` = no issues in 24 files。
- 收据 `receipt.json`：`p4-contract-receipt/1`、`status=partial`、`counts {checked:34, passed:34, failed:0, skipped:0, not_evaluated:4}`、
  35 cases（34 测试 + 1 ledger 探针）、finish-time `violations: []`；`counts` 与 pytest 汇总逐键一致（审查复核）。
- RED：`red-20261018.log` = `1 failed, 19 passed, 1 skipped, 12 errors`，首条为断言
  `AssertionError: no pytest outcome was recorded - pytest_runtest_logreport must feed sessionreport.record_outcome`（非 ImportError）。
- 独立审查：**PASS**，`review/independent.md`，审查者 = `independent-reviewer`（≠ 作者 ≠ ROOT），
  card §10 六项检查逐项 PASS；修复 P4-R1（守卫先查存在性）、P4-R2（sessionfinish 只读/网络复查）、P4-R3（teardown 计数）后复跑通过，报告绑定 39 个未改动文件 + 3 个修复文件的 SHA-256。

## 3. 范围与边界证明

- **0 网络 0 模型**：`netguard` 全程 `socket` monkeypatch 抛 `AssertionError`（审查者手工开 socket 复验，attempt 记录为 `p4_network_attempted`）；
  session 级 `_finish_violations()` 在写收据前复查，最终 `violations: []`；`company_wiki.llm_client` 从未导入；收据/日志无任何模型或下载调用。
- **跨仓只读**：本仓与 `fixtures/` 树（全内容摘要）运行前后一致；消费端仓库 env 未提供 → 如实 `not_evaluated`
  （reason `P4 requires CWP_P4_CONSUMER_COMMANDS`），限制第 2 条明写。
- **不碰生产**：`config/source_catalog.yaml` SHA 与基线一致（`3d159a4e...`）、`git status -- config` 干净；
  生产 DB / `output/` / gold 0 写入；夹具 catalog 被复制到 tmp 才扫描（`catalog/state` 只落在 tmp，提交树内无 `state/`）。
- **不读密钥**：代码只 `env.pop()` 六个 key 变量（从子进程环境剥离），从不读值；收据无绝对路径与 env 值（仅 sha256 与布尔）。
- **完成定义 6**：未跑真实生产 catalog；消费端是否真实只读取决于 ROOT 提供的命令清单。

## 4. known_limits 与 ROOT 接入

- **known_limits**：① 消费端映射取决于 ROOT 提供的命令清单（未提供时消费端用例 `not_evaluated`，绝非 pass）；② 未跑生产 catalog（全部输入为本卡合成夹具）；
  ③ RED 仅以日志留档、**无 RED 提交**，无法 checkout 复现（审查者记为 known_limit，原两处过期陈述已更正）；
  ④ `counts.not_evaluated` 计**契约用例**（4 个）而非 pytest 测试数（收据 limitations 第 4 条已声明）；
  ⑤ 夹具级硬失败在 pytest 终端表现为 `errors`（exit≠0 且收据 `status=fail` 保持诚实）。
- **not_run**：真实 FF/RF 消费端仓库读取（未提供 `CWP_P4_FF_ROOT/RF_ROOT`）、真实生产 catalog、`mypy` 生产模块（本卡无新增 `src/` 生产模块）。
- **root_integration_steps**：① 提供 `consumer-commands.json` 与只读 catalog 后复跑一次；
  ② 把 `receipt.cases` 的 `fail`/`not_evaluated` 纳入发布前对照；③ P4 不进入 pre-push，由 ROOT 在大节点显式运行。
- 机器可读明细见 `handoff.json`（`file_bindings` 逐一给出交付文件 SHA-256；`handoff.json` 自身因自哈希不可能而未列入，完整性由 git 提交保证）。
