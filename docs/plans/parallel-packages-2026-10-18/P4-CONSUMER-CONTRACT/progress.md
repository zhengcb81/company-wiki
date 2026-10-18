# P4-CONSUMER-CONTRACT — 进度日志

## 2026-10-18（前一上下文跨度）
- 建 worktree `company-wiki-p4-contract` @ `4045787f`，分支 `codex/p4-consumer-contract-20261018`。
- 夹具：`fixtures/catalog/`（annual-2025.txt 94B / disclosure.pdf 61B 合成件）+
  `expected.json`（`p4-fixture-expectations/1`）+ `build_fixtures.py`。
- support 全量落地并 import 验证；`conftest.py` 192 行。
- read/export-v2 探针：真实 CLI 对夹具 catalog 跑通（rc 0；manifest 23 键；
  `availability_evidence: null`；sha 与 expected.json 一致）。
- 发现：reader 自建 `catalog/state`；扁平复制破坏 `${PROJECT_ROOT}`；PowerShell `2>&1`
  污染 stdout 原始字节（改 Python 驱动）。

## 2026-10-18（本跨度）
- 读齐 support API（checks/consumer/observations/receipt/sessionreport/jsonio/constants/netguard/environment/cwp）。
- 确认 pytest 9.1.1 + pytest-timeout 在位；PWF 目录 = 本卡目录（README §6 / INTERFACES §10）。
- 落盘 PWF 三件套；新增 `support/readonly.py`（会话基线：HEAD + porcelain + fixtures 树摘要 + 消费端仓库快照）。
- conftest：`pytest_sessionstart` 增加基线捕获；`p4_case(request)` 按函数名登记（防名字漂移）。
- `report.case_name(request)`、`netguard.guard(name)` 测试工具暴露。
- **三个实现缺口（RED 实证 → 补 support）**：
  1. export CLI 要求 12 字段严格 `EvidenceSpan`（`loc:v1/chars:` 定位、派生 `span_id`/`output_sha256`）；
     手搓 span 得 `invalid_request` → 新增 `cwp.build_wire_span()/wire_spans()`。
  2. `bundle_sha256` 生产者用 `ensure_ascii=False`（探针：True→`ce2c6ca7` MISMATCH，False→`c7f56b68` MATCH）；
     `recompute_bundle_sha256` 改为复刻生产者形式（收据/handoff 仍用 §1 的 `ensure_ascii=True`）。
  3. 夹具只有 sources、无 `catalog/state`，reader 拒绝创建 → `cwp.ensure_catalog_state()` 对缺 state 的
     catalog 跑一次 `cli --config <cfg> scan`（`--config` 必须在 `scan` 前）；已有 state（ROOT 目录）不重写。
  另加：`pytest_runtest_logreport` → `sessionreport.record_outcome`（否则 counts 恒 0）；
  `p4_catalog_config` 复制 fixtures 到 tmp 再读（就地读会污染提交树）；`skip_or_fail` 标 `NoReturn`。
- **RED**：`red-20261018.log` —— 1 failed（counts 无记录，断言消息）+ 12 errors（`catalog_unavailable`）+ 19 passed。
- **GREEN**：`green-20261018.log` —— **34 passed**，exit 0；receipt `p4-contract-receipt/1`、
  `status=partial`、`checked=34 passed=34 failed=0 skipped=0 not_evaluated=4`（与 pytest 汇总一致）。
- **全 skip 验收**：`green-allskip-20261018.log` —— 34 skipped、exit 0，34 条 reason
  `P4 requires CWP_P4_CATALOG_CONFIG`（`-rs` 可读）。
- **静态**：`static-ruff-20261018.log` = All checks passed（exit 0）；
  `static-mypy-20261018.log` = Success no issues in 24 files（exit 0）。
- fixtures 树复核：只有源文件，**无 `state/` 生成物**；`git status` 仅两条写集目录（+本卡 PWF 产物）。
- 交付顺序：实现提交在前 → 非作者 agent 独立审查并修复 → 复审绑定最终 SHA → handoff 单独提交 → 交 ROOT。

## 测试/日志结果
| 制品 | 结果 |
|------|------|
| `red-20261018.log` | 1 failed + 12 errors + 19 passed（缺失实现的真实断言失败）|
| `green-20261018.log` | 34 passed，exit 0 |
| `green-allskip-20261018.log` | 34 skipped，exit 0，34 条可读 reason |
| `static-ruff-20261018.log` | All checks passed，exit 0 |
| `static-mypy-20261018.log` | no issues in 24 files，exit 0 |
| `receipt.json` | `p4-contract-receipt/1`，`partial`，checked=34/passed=34/failed=0/skipped=0/not_evaluated=4 |

## Errors Encountered
（同 task_plan.md 错误表；新增项在此追加）
| Error | Attempt | Resolution |
|-------|---------|------------|
| export `invalid_request`（手搓 span）| 1 | `EvidenceSpan.create().to_dict()` 生成 12 字段 wire span |
| `bundle_sha256` MISMATCH | 1 | 复刻生产者 `ensure_ascii=False`（探针实证两向）|
| export `catalog_unavailable` | 1 | `cli --config <cfg> scan`（全局 flag 在 `scan` 前）就地建 state |
| ruff F401 `sha256_bytes` | 1 | 删未用 import |
| mypy 3 处（`payload` 联合类型 / `Path|None` / implicit return）| 1 | 显式 `dict[str,Any]` 注解、`skip_or_fail -> NoReturn` + 终结 raise |
| 全 skip 日志看不到 reason | 1 | 验收跑加 `-rs`，34 条 reason 可读 |
