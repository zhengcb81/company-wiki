# StockWiki 独立施工卡：简化重复工程测试门

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> **任务与 SourceExport v2 reader 不同。** reader 已完成交接后，可把本卡交给 StockWiki owner 单独执行。唯一写入目录是 `C:\Users\郑曾波\Projects\StockWiki` 的专用集成 worktree；company-wiki、IQS、RF、FF、ET 和已完成 reader 分支只读。StockWiki 同时只允许一名写入者：开工时若 reader 仍在写、尚未交付，或本卡允许路径与 reader 的未合并改动重叠，先停在基线盘点，不改文件。

## 目标与边界

把开发期“受影响测试”与大节点完整验收分开，移除同一大节点把全量 pytest 连续跑两遍的重复耗时。保留当前真实数据回归、覆盖率下限、Ruff、框架校验和所有投资研究状态语义。

本卡仅负责 StockWiki 工程测试入口与说明：

- `AGENTS.md`：改写验证纪律为开发时运行受影响测试；合并/发布等大节点运行一次完整 `scripts/check_all.sh`。
- `scripts/check_all.sh`：去掉重复的无覆盖 pytest 全量运行；完整测试套件仍运行一次，并在该次运行中收集 coverage；保留 Ruff、coverage 汇总与原有阈值、框架/配置验证及非零失败码。
- 最多新增一个聚焦脚本行为的测试文件，限于 `tests/` 中符合本仓现有测试风格的位置。

明确不碰 `stockwiki/review_workflow.py`、accepted/rejected 研究状态、数据/fixture、SourceExport reader、身份映射、provider/sync 功能或其它仓。accepted/rejected 是研究结论状态，不是工程签收门；它们不属于本任务的清理对象。

## 当前已知基线

只读检查 2026-09-29 发现：`AGENTS.md` 要求提交前运行 `bash scripts/check_all.sh`；脚本当前先运行 `python -m pytest -q`，又运行 `python -m coverage run -m pytest -q`，造成全量套件重复。coverage 硬门为总覆盖率至少 **73%**，且 `stockwiki/ui.py` 至少 **40%**；脚本还运行 Ruff 和 `validate-framework`。`tests/test_data_contract.py` 和真实 workspace E2E 是质量合同的一部分，不能因耗时而从完整大节点检查移除。

以上只是检查结果；开工时必须以 StockWiki live HEAD、当前 `git status` 和 `scripts/check_all.sh` 内容复核，不能直接套用历史状态。

## TDD 实施步骤

1. **确认独占写入权与输入。** 只读记录本仓 HEAD、分支、tracked/untracked 状态；确认 SourceExport reader 已由其 owner 交付并停止写入。保留全部有效文件，不运行 reset/clean。若有未归属改动或 reader 与本卡路径重叠，报告具体路径并等待 owner 释放；其余只读审查可继续。
2. **写一个行为测试并确认 RED。** 在临时小型测试仓/隔离副本中执行 `check_all.sh`，以临时 `python` shim 或本仓已有 shell-test 方法记录子命令调用。断言完整 pytest 只执行一次且是 coverage 下运行；coverage 报告、Ruff、框架校验均仍执行。加入一个失败子命令的情形，确认脚本最终退出码非零。不得在真实完整套件上额外重复运行来测计数。
3. **最小修改脚本。** 将原先独立的 `python -m pytest -q` 与 `coverage run -m pytest -q` 收敛为一次完整测试运行；coverage 统计仍使用现有配置。保留 coverage 总门 `73%`、`ui.py` 门 `40%`、Ruff、`validate-framework` 和每个 gate 的失败汇总。不得改阈值、跳过真实 workspace/data-contract 测试、或把 warning 改成静默。
4. **更新 `AGENTS.md`。** 明确开发期按改动范围运行单测/相关集成测试；提交前/大节点只运行一次全量 `check_all.sh`。说明全量套件包含真实 workspace 与 data-contract 检查，coverage 在同一轮收集。删掉“每次提交都必须另跑一遍 pytest”的重复要求，但不弱化功能质量标准。
5. **做大节点验证与交接。** 先运行脚本行为测试和受影响测试；随后一次性运行全量 `bash scripts/check_all.sh`，保留完整退出码与覆盖率结果。提交只包含本卡允许路径，报告测试命令、实际通过数/耗时、coverage 两项结果、`git diff --check`、测试工作目录清理结果及新 HEAD。

## 验收标准

- 大节点完整测试套件实际只运行一次；验证由 coverage 包裹的那一次仍执行真实 workspace E2E 和 `tests/test_data_contract.py`。
- 全量 suite、Ruff、`validate-framework` 均通过；coverage total ≥73%，`stockwiki/ui.py` ≥40%。若仓库 baseline 或环境使某项失败，报告具体失败，不降低门槛伪造通过。
- 人工签收/工程 receipt 的要求只在本卡范围内简化；StockWiki accepted/rejected、投资结论证据合同、身份正确性、真实数据测试和现有研究状态不变。
- 使用隔离测试目录；测试结束清除本卡创建的 stub、临时仓和 coverage 临时文件，并确认生产数据、reader 交付文件没有变化。
- 不因本任务要求另外一个 reviewer 或重复的人工签收；技术交接只需一段 HEAD、路径、测试和遗留项摘要。

## 交接格式

`StockWiki HEAD/branch | 修改路径 | 真实 pytest invocation 次数 | check_all 退出码 | Ruff/validate-framework | total/ui coverage | real workspace/data-contract 运行结果 | 测试临时目录已清理 | 未解决项`。

本卡完成只表示重复全量测试被移除、覆盖与数据质量门仍生效；不表示 SourceExport reader、identity、selected 或 full sync 的跨仓门自动通过。
