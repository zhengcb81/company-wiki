# Task Plan: G5-CWP-CHECKS 旧工程门禁与批处理外壳整族退休

- 卡片：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g5_cwp_legacy_checks_retirement.md`
- 原仓：`C:/Users/郑曾波/Projects/company-wiki`（master，基线 `5d0ad75504a9815febc1bddbe76ae2f667c3e74a`）
- 工作树（唯一施工目录）：`C:/Users/郑曾波/Projects/_g5/cwp`，分支 `codex/g5-cwp-checks`
- 环境：`PLAN_ID=g5-cwp-checks`，`PWF_PLAN_ROOT=C:/Users/郑曾波/Projects/_g5/cwp`

## Goal

六个旧 CLI（`semantic_gate`/`architecture_gate`/`clean_env_gate`/`gold_gate`/`test_framework`/`batch_process`）
变成纯 stdlib 退休薄壳：直接调用（含 `--help`、旧参数、`python -S`）报告
`LEGACY_ENGINEERING_TOOL_RETIRED` 并 exit 78；import 与 `main()` 零初始化、零收据、零目录复制、
零模型/Store/下载器构造；有用的行为（环境隔离、真实来源质量/失败传播/来源引用反例）
迁移后继续被测试消费。

## Next Step

全部 Phase 已完成，等待 MAIN 按 `HANDOFF.md` / `handoff.json` 验收合入。

## Current Phase

Phase 5

## Phases

### Phase 0: 基线与工作树

- [x] 记录原仓 `git status --short`（G2-12 未提交改动，未复制进本工作树）
- [x] `git worktree add -b codex/g5-cwp-checks <工作树> 5d0ad755…`
- [x] 只建一处 PWF：`<工作树>/.planning/g5-cwp-checks/`，resolver 解析成功
- **Status:** complete

### Phase 1: 读源与 caller 清单

- [x] 读 `scripts/writer_policy.py`、六脚本、`tests/unit/test_hermetic_runtime.py`、
  `tests/acceptance/test_control_bootstrap.py`、`tests/helpers/gold_evaluator.py`、
  `.pre-commit-config.yaml`、`.github/workflows/ci.yml`、`.githooks/pre-push`
- [x] 全仓 grep 六模块的 import 与子进程 caller，逐函数标 retire / migrate / preserve
- [x] 结果写入 `findings.md` 与 `retirement_map.json`
- **Status:** complete

### Phase 2: 行为 RED

- [x] 新增 `tests/unit/test_g5_legacy_checks_retirement.py`：六 CLI 旧参数与 `-S` 在独立空 cwd
  下 exit 78 且零新文件/零 HTTP；import 时禁项目依赖仍成功且零初始化；
  writer_policy 类别/banner；隔离 helper 仍剥假 key、阻止 dotenv
- [x] 真实 RED 执行（旧实现返回真实结果、无 marker），记录到 `progress.md`
- **Status:** complete

### Phase 3: 实现

- [x] 六脚本改纯 stdlib 退休薄壳（仅 `from __future__` + `sys`）
- [x] `writer_policy.py` 新增这六个名字的类别与退休说明；三个 gate 移出 `CONTROL_TOOL_ALLOWLIST`
- [x] 新 `tests/support/isolated_environment.py` 承接 `clean_env_gate.sanitized_environment`
- [x] 删除 `control/architecture.json`（唯一消费者是退休工具），更新 `control/README.md`
- **Status:** complete

### Phase 4: 精确迁移既有测试

- [x] 删除 regex / source-count 资格 / 候选整树复制专属测试
- [x] 保留并补强实际来源质量、失败传播、来源引用反例
- [x] gold CLI 专属收据测试改为退休零写
- [x] 混合测试只改本族责任行，不删整份
- **Status:** complete

### Phase 5: 集中执行与交付

- [x] 一次集中执行新 unit/integration + 保留的 hermetic/common/writer-freeze/legacy caller/gold
- [x] E2E：六真实脚本 direct/main/import/-S + tmp 哨兵资料，零 receipt/派生/HTTP/模型
- [x] ruff / compileall 静态检查
- [x] 提交写集与 `.planning/g5-cwp-checks/` 六件套
- **Status:** complete

## Key Questions

1. `control/architecture.json` 是否只有退休工具消费？ → 是，全仓唯一消费者为
   `scripts/architecture_gate.py:87` 默认 `--config`，其余命中均为 `artifacts/gates/*` 历史快照。
2. 六脚本是否还有测试树之外的 caller？ → 无，见 `retirement_map.json`。
3. `PERMANENTLY_RETIRED_SCRIPTS` 是否要并入这六个？ → 否，该集合被
   `test_legacy_caller_reachability` 冻结等值断言，独立类别才是「本族责任」。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 六 stub 不 import 任何项目模块（仅 `from __future__` + `sys`） | 满足「纯 stdlib 薄壳」与「import 时禁项目依赖仍成功且零初始化」的最强解读 |
| writer_policy 新增独立类别 `RETIRED_ENGINEERING_TOOL_SCRIPTS`，不并入 `PERMANENTLY_RETIRED_SCRIPTS` | 卡片只允许改这六个名字的类别；R1–R5 冻结等值断言不得被本卡改写 |
| `blocked_message` 工程退休分支排在永久退休分支之前 | `batch_process.py` 同属两族，需 plain 与 `-S` 两条路径都报告同一 marker |
| 三个 gate 移出 `CONTROL_TOOL_ALLOWLIST` | 退休后不再是「受支持控制工具」；`is_legacy_script_cli`/`sitecustomize` 因此继续 fail-closed |
| `evaluate_architecture`/`materialize_candidate`/`is_candidate_path` 删除不迁移 | 分别是 regex 门与候选整树复制专属实现，无存活生产消费者 |
| `sanitized_environment` 迁 `tests/support/isolated_environment.py` | 卡片明确 clean_env 的环境隔离确被 hermetic 测试消费 |
| 来源引用与诚实质量反例迁到 gold evaluator 契约测试 | 卡片 §2 要求保留 gold evaluator 独立反例并禁止丢来源引用反例 |
| 删除 `control/architecture.json` | 卡片要求「确认只有退休工具消费后删除」，已确认 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| `rg` 在该 shell 不可用 | 1 | 改用 Grep 工具与 `grep -rn` |
| Write 工具拒绝覆盖未读取的模板 `task_plan.md` | 1 | 先 Read 模板再写入 |

## Notes

- 每个 Phase 状态只用 `pending` / `in_progress` / `complete`。
- 大决策前重读 Goal / Next Step。
- 任何失败先记入 Errors，再换方法，不重复同一失败动作。
