# P4-CONSUMER-CONTRACT — 任务计划

**目标**：按 card.md 交付 P4 消费端契约集成测试道（opt-in、0 下载、0 模型、跨仓只读），
基线 commit `4045787f`，worktree `company-wiki-p4-consumer-contract`，
分支 `codex/p4-consumer-contract-20261018`。

**写集**：`tests/integration/test_p4_contract/**` +
`docs/plans/parallel-packages-2026-10-18/P4-CONSUMER-CONTRACT/**`。
越界即停写并报 `BLOCKED_BY_SCOPE`。`baseline.json` 由 ROOT 负责，本卡不写。

**交付顺序**：实现提交在前，handoff 单独提交，handoff 永不引用自己的 SHA。

## 阶段

### Phase 1 — 夹具与 support 脚手架（上一上下文跨度完成）
**Status:** complete
- `fixtures/`：合成 catalog（text/plain + 无 span 的 application/pdf）、`build_fixtures.py`、`expected.json`。
- `support/`：constants/jsonio/netguard/environment/report/cwp/checks/consumer/observations/receipt/sessionreport + lane `conftest.py`。
- 探针验证：read 与 export-v2 对夹具 catalog 真跑通过（94 字节文本、manifest 23 键、`availability_evidence: null`）。

### Phase 2 — RED 前测试工具与 PWF（本跨度）
**Status:** complete
- `support/readonly.py`（会话基线快照：HEAD + porcelain + fixtures 树摘要 + 消费端仓库）。
- `report.case_name(request)`、`netguard.guard(name)`、conftest `pytest_sessionstart` 捕获基线、`p4_case(request)` 按函数名登记。
- PWF 三件套落盘。

### Phase 3 — RED：测试用例落地并真实失败
**Status:** complete
- 10 个测试模块、34 用例（card §6 A 清单全覆盖 + 收据缺失拒绝用例）。
- RED 运行保存 `red-20261018.log`：**1 failed（counts 无记录，断言消息）+ 12 errors（catalog_unavailable）+ 19 passed**。

### Phase 4 — 实现修复（补 support 接线）
**Status:** complete
- `p4_catalog_config` 把 fixtures catalog 复制到 tmp 再用（就地读会写 `catalog/state` 污染树）。
- `pytest_runtest_logreport` → `sessionreport.record_outcome`（否则收据 counts 恒为 0）。
- 缺 env 时走 `skip_or_fail`（`CWP_P4_REQUIRE=1` 变 fail）；`p4_manifest` spans 补 `unit_tokens`。
- `cwp.ensure_catalog_state()`：无 state 的 catalog 先跑 `cli --config <cfg> scan`（reader 拒绝自建库）。
- export 的 12 字段 `EvidenceSpan` 经 `cwp.wire_spans()` 生成；`bundle_sha256` 复刻生产者 `ensure_ascii=False`。
- 清理：RED 遗留生成物已确认不在提交树内（fixtures 树复核无 `state/`）。

### Phase 5 — GREEN / 全 skip / 静态检查
**Status:** complete
- `green-20261018.log`：**34 passed** exit 0；`green-allskip-20261018.log`：34 skipped、34 条可读 reason。
- `static-ruff-20261018.log`：All checks passed；`static-mypy-20261018.log`：no issues in 24 files。
- `receipt.json`：`p4-contract-receipt/1`，`partial`，checked=34/passed=34/failed=0/skipped=0/not_evaluated=4。
- 提交 1 = `cdf5be5a`（实现 + 夹具 + 日志 + 收据 + PWF），pre-commit 钩子通过，树净。

### Phase 6 — 独立审查（非作者 agent）
**Status:** complete
- 审查者 `independent-reviewer (non-author, non-ROOT)` 交付 **PASS**：报告
  `review/independent.md`（6 项强制检查逐项 PASS，绑定 39 个未改动文件 SHA + 3 个修复文件 post-fix SHA）。
- 发现并修复 3 个缺陷（提交 `025c0b71`，全部在写集内）：
  - **P4-R1** `environment.py`：`samefile(production)` 先于 `is_file()`，不存在的路径漏成裸
    `FileNotFoundError` 而非 `ProductionConfigRefused` → 先查存在性；production/穿越/相对/junction
    探针复验全部拒绝。
  - **P4-R2** `sessionreport.py`：`readonly.verify_unchanged()` 是死代码，sessionfinish 从不复查
    只读与网络尝试 → 新增 `_finish_violations()`（写收据**前**查 → 违规则 `status=fail` + exit 1）；
    阳性对照证明会触发，最终 GREEN `violations: []`。
  - **P4-R3** `conftest.py` + `sessionreport.py`：teardown 错误被丢弃 → counts 会偏离真实汇总 →
    teardown 失败按 pytest `error` 计入。
- 审查后 ruff/mypy 复跑均绿。报告 + 最终收据提交于 `5f840650`。
- 审查者确认：无 `BLOCKED_BY_SCOPE`；`findings.md`/`task_plan.md` 审查期间改动系作者（本 orchestrator）所为，
  留未 stage 待作者确认——**已确认并纳入本次交接提交**；两处过期陈述（RED 提交）已更正。

### Phase 7 — 交接与 ROOT 验收
**Status:** complete
- `handoff.md`（19 行四段式）+ `handoff.json`（INTERFACES §8 全 17 字段；42 条 `file_bindings`
  逐条 sha256+bytes 经独立脚本复算通过；4 条验收运行、`red_receipt` 首条失败 ≤300 字、7 个合成夹具、
  `scope_proof` 全 0、`independent_review` = PASS / 41 条审查绑定）。
- 交接提交 `5a651498`；交接载体提交不自引用其 SHA（INTERFACES §8 反递归规则）。
- 交付前终验：43 个 diff 路径全在写集内、无第 4 节禁触路径、`tests/integration` 除本车道 0 改动、
  收据保持审查后 `34 passed`（审查后未再运行 pytest）、树净、pre-commit 钩子通过。

## Next Step
已向 ROOT 交付（handoff.md/handoff.json）；等待 README §6 十项验收。

## Decisions Made
| 决策 | 理由 |
|------|------|
| RED 仅以日志留档，**不做 RED 提交**（原「提交 1 = RED 态」决策已作废，审查者复核后更正） | 单提交 `cdf5be5a` 交付实现；`red-20261018.log` 是真实实现前失败日志（README §6.3 只要求日志与断言消息），但无法 checkout 复现——审查报告已把它记为 known_limit |
| support 五类判定器在上一跨度已实现 | 如实记录：RED 失败集中在仍缺失的夹具隔离/收据记录接线，比较器用例当时通过 |
| fixtures catalog 复制到 tmp 后再读 | 就地读会写 `catalog/state`，污染提交树（探针实证） |
| `disclosure.pdf` 用 `git add -f` 提交 | `.gitignore:5` 的 `*.pdf` 在写集外，不改 ignore 规则 |
| 收据测试读上一轮的 `receipt.json` | 收据在 `pytest_sessionfinish` 写出，本轮测试只能验证上一轮文件 |
| 无 env 时**全部**用例 skip（含纯逻辑用例） | card §7「无 env：全 skip」的字面要求，autouse opt-in 门实现 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `read_client` 用 `path` 参数被拒 | 1 | 改用 `file_path` |
| `git worktree add` 报 exit 1 但实际成功 | 1 | 用 `rev-parse HEAD` / `--abbrev-ref` / `status --porcelain` 复核 |
| 扁平复制 `catalog.yaml` 致 `catalog_unavailable` | 2 | 整个 `catalog/` 目录一起复制，保持 `${PROJECT_ROOT}` 两级布局 |
| PowerShell `2>&1` 污染 reader 的 stdout 原始字节 | 1 | 改用 Python `subprocess.run(capture_output=True)` 驱动 |
| `write` 拒写 `__init__.py`（要求先重读） | 1 | 先用 pwsh 创建文件再读再写 |
| 读相对路径落到主线仓 | 1 | 一律用绝对 worktree 路径 |
