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
- `support/readonly.py`（会话基线快照：HEAD + porcelain + fixtures 树摘要）。
- `report.case_name(request)`、`netguard.guard(name)`、conftest `pytest_sessionstart` 捕获基线、`p4_case(request)` 按函数名登记。
- PWF 三件套落盘。

### Phase 3 — RED：测试用例落地并真实失败
**Status:** in_progress
- 10 个测试模块 ≥12 用例（card §6 A 清单全覆盖）。
- 先跑 RED：env 指向本卡 `fixtures/catalog/catalog.yaml`，保存 `red-20261018.log`，
  确认失败为断言消息（夹具隔离、unit_tokens 接线、收据缺失、counts 记录）。
- 提交 1 = RED 状态（测试 + 夹具 + 脚手架），ROOT 可 checkout 复现。

### Phase 4 — 实现修复（补 support 接线）
**Status:** pending
- `p4_catalog_config` 把 fixtures catalog 复制到 tmp 再用（就地读会写 `catalog/state` 污染树）。
- `pytest_runtest_logreport` → `sessionreport.record_outcome`（否则收据 counts 恒为 0）。
- `p4_catalog_config` 缺 env 时走 `skip_or_fail`（`CWP_P4_REQUIRE=1` 变 fail）。
- `p4_manifest` 夹具 spans 补 `unit_tokens`。
- 清理 RED 遗留的 `fixtures/catalog/state` 生成物。

### Phase 5 — GREEN / 全 skip / REQUIRE 验证与静态检查
**Status:** pending
- 带 env 跑 → `green-20261018.log`；无 env 跑 → 全 skip 且 reason 明确；
  无 env + `CWP_P4_REQUIRE=1` → 必须 fail（不是 skip）。
- `ruff check` → `static-ruff-20261018.log`。提交 2 = 实现 + 日志 + PWF 更新。

### Phase 6 — 独立审查（非作者 agent）
**Status:** pending
- 子 agent 审查：skip 不冒充 pass、counts 与真实运行一致、0 网络 0 模型（手工开 socket）、
  不写被测仓库、生产配置守卫不可绕过；修复问题；报告写 `review/independent.md`，
  绑定最终文件 SHA-256；对最终 SHA 复审。提交 3 = 审查 + 修复。

### Phase 7 — 交接与 ROOT 验收
**Status:** pending
- `handoff.md`（≤80 行四段式）+ `handoff.json`（INTERFACES §8 全字段、file_bindings 全覆盖）。
- 提交 4 = handoff。向 ROOT 报告：commit、diff --stat、测试/跳过计数、0 网络 0 模型证据。

## Next Step
Phase 3：写 10 个测试模块 → RED 运行 → 保存 `red-20261018.log` → 提交 1。

## Decisions Made
| 决策 | 理由 |
|------|------|
| RED 用两个提交表达（提交 1 = RED 态） | README §6 要求 red_receipt 是真实实现前失败日志；checkout 提交 1 可复现 |
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
