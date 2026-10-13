# DU2-FACETS 交接（du2-handoff/1）

机器可读交接见同目录 `handoff.json`。分支 `codex/du2-facets-20261013`，
base_sha `5a297244549d54c34f382835b876ec3d181fcd24`，实现提交
`a58c4e09e6003c899607c1194ab1e3c834b20793`（交付物+tests+C记录），本文件为第二次提交以准确
记录SHA。**未并主线、未push主线、未安装。**

## 交付（独占路径内）

- `docs/plans/document-understanding-2026-10-13/review/deliverables/facets/`：
  README、index.json、records/（14）、cases/（14）、tests/（311项结构不变量）、
  coverage_matrix.md、acquisition_requests.json（11项缺样）、c_verification/（20条真实引文
  核对记录）、tools/verify_real_quotes.py。
- `.planning/du2-facets/`：本包PWF（task_plan/findings/progress）、A/B/C结果、本handoff。
  注意：本worktree sparse-checkout 不含 `.planning/`，按 git 提示用 `git add --sparse` 显式
  入库；未改任何 sparse/config。

## A/B/C（均 exit 0）

| 节点 | 内容 | 命令 | 结果 |
|---|---|---|---|
| A | 两份语义规格+关键错误反例+合法空值规则 | pytest tests -q -k "required_context or semantic_counterexamples or legal_exits" | 81 passed / 230 deselected，5.9s |
| B | 八面/四机制集中数据+正反配对反例测试 | pytest tests -q | 311 passed，7.0s |
| C | 真实原文核对（不同市场×经营模式） | tools/verify_real_quotes.py | 20/20 引文命中，SHA 6/6、mtime 未变，1.0s |

RED 记录：数据未写时同套件 308 failed / 3 passed（空包防线生效），随后补齐数据转GREEN。

## 语义边界（必须随交接保留）

- 缺否定、错项目、未来当实际的语义反例只交**输入与期望**给 ROOT，
  `execution_status=NOT_RUN_ROOT_INTEGRATION`；本包未执行生产语义测试、未实现推理器或
  第二 summary generator。
- required_context 全部条件式：只有输出数量才要求 unit/分母；定性进度不强制补数字；
  stage/subject/role/否定/条件决定原意时不可丢。
- 机制记录只写通用机制（无公司固定产品名单）；真实公司事实仅存在于 case 原文锚定。

## 资源

模型调用 0、付费 $0、网络 0、原件复制 0；持久数据 196,871 bytes（建议≤512KiB内）；
scratch 已清理恢复，git status 可解释。

## next_root_action

导入唯一 profiles/ReadingPlan registry（不建第二策略源）→ required_context/summary_focus
交 ROOT 闭包/选择/校验 → 14 case 映射 du-gold/1（组内AND、组间OR）→ 语义反例在 B/C 真实
执行回填 → 缺样按 acquisition_requests.json 走资料获取层（不新增人工许可链）。
