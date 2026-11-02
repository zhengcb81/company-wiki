# R6 daily fast feedback — 独立集中审查

结论：**PASS_DAILY_TOOL_ENGINEERING_ONLY**。本次范围可以交 ROOT 正常发布候选、检查真实远端 push 与精确 CI；没有发现需阻断的 P1/P2。不是完整 CI、源语义 R4、真实摘要/缓存/RF 或整个项目完成签字。

审查人 `/root/rectification_review_a`，日期 2026-11-02。稳定工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6`，分支 `codex/architecture-fast-feedback-20261102`，实际 HEAD **`819cef31a4f2db7fa05bfe50901725f7a0dad016`**，基线 `848b4ee0`。独审前后 HEAD 一致；七份文件的原始字节均与作者和 ROOT 复制收据一致，Git blob LF 比较也全部一致；精确 SHA 与可复现探针见同名 JSON。唯一原有 WIP 是 `.githooks/pre-push` 的 100755→100644 模式差异，未改内容或模式。

## 真正修复的责任边界

旧实际 push 的 1787 case /180 秒超时记录仍保留，不能把“32 个测试文件”当作“少量测试”。新 daily `--push-checks` 仅对实际 Git 完整 ref 范围做路径分类：明确文档/计划归档范围 0 pytest，其他代码、配置、未知范围固定 **35 个原 smoke target 一次**。不再建全仓 AST 图，也不追加受影响文件。`changed_unit_tests.py` 仍是独立手工分析工具，未删除实现或其真实 selector 测试。

删除的 `test_known_push_scope.py` 专测旧日常 32 文件扩张政策，包括 smoke 外故障也必须在日常 push 阻断。随着用户明确要求恢复固定 smoke 责任，这部分政策退役是合理的；它不等于通过改断言掩盖当前 smoke 内失败。失败传播、完整 CI 和作者变更相关验证各自保留。本地输出明确 `local_fast_pass for fixed smoke only` 与 `full_validation_pending`，文档范围仅 `tests_not_run`，没有把局部通过写成全套通过。

## 独立执行与静态反控

正常宿主 `C:/Miniconda/python.exe`，Python 3.13.9 / pytest 9.1.1；候选 config/rootdir/confcutdir 显式绑定，独立探针还断言真实 `gate.__file__` 属于当前候选树。**10 passed，16.55 秒，exit 0**：3 个独立新探针及 7 个选取的既有场景，未重跑作者 173 例。

- 独立自建 Git 仓库的实际两条 ref diff：一条代码、一条文档，`changed_paths` 合并保留代码；给 `ast.parse` 加拒用反控，真实 main 仍只分发固定清单一次。
- `docs/runtime.py`、`docs/README.json`、CI YAML、陌生后缀和未知 ref 均不能按普通文档跳过；被执行 child 返回 7 时准确返回红，不提前输出局部通过。
- 原 hook 与当前工具复制到自有仓库，实际 push 到自有 bare remote：初始 smoke 绿可推；smoke 中故障令后次 push 红，远端 HEAD 不前进。纯归档文档 push 实际 0 pytest；先有未发布代码、最后一次提交仅文档仍正确阻断。
- 日常 wrapper 的实际调用参数保持 180 秒总期限、stdout 4 MiB / stderr 512 KiB、隔离 TEMP/TMP/SQLITE_TMPDIR 和禁用 pytest cache；child 返回 7 后 scratch 消失。真实 child exit 7 保留诊断，两个真实输出溢出场景均返回 125、保留最后进度并限制输出；transport exception 清理保持。
- 选测验证显式完整本地模式原有阶段顺序。另独立 AST 比较 9 项原库存/执行 owner 全等，完整模式 gate 定义、fast-mode 分支及循环执行 AST 与基线全等；CI YAML、pre-commit 配置、独立 selector、bounded-process 和 process-tree 两源均与基线字节一致。完整 CI 仍跑全 Unit 和原固定合同集合。

真实 Git 场景使用对应清单的轻量 stub，证明的是 hook/范围/子进程拒绝/远端行为，**不冒称真实产品 smoke 每项断言已重跑**。16.55 秒也不是新真实远端 push 性能收据。后两项由 ROOT 后续实际候选 push/CI记录。

## 自有入口纠正与清理

首轮 7 passed /3 failed，7.07 秒属于独审入口错误：自有 probe 选了超出原 60 单元限制的深 tmp_path；我禁用 plugin autoload 却未给 hook 子 pytest 继承 timeout 插件，子进程正确因不认识 `--timeout` 返回红。没有改产品或作者测试来换绿，只将自有 scratch 改为短路径并显式继承 `pytest_timeout`、绑定候选 config/rootdir/confcutdir，再跑上述 10 例。原输出保存在 JSON，不把它算产品 RED。

唯一 owned 根 `C:/Users/郑曾波/Projects/company-wiki/tmp/g6` 事前 absent；最终核对绝对父目录、准确末级名称和无任何 reparse 后，以 native PowerShell 删除并验证 **absent**。其中自建 Git 仓库/bare remote、JUnit、脚本与中间日志已移除；可复现脚本、测试结果和完整 SHA 留在同名 JSON。未触碰原件、模型、外来工区、配置、真实 Git/index、源语义作者文件或主 PWF。

## 非阻断小项及未验边界

`.githooks/pre-push` 和 `.pre-commit-config.yaml` 的旧文件头注释还描述自动追加 affected files；实际 hook 仍正确委托 `--push-checks`，OPERATIONS 已准确写固定 smoke。可以由 ROOT 做注释小修，不需增加门禁或重跑大域；本审查按要求未更改外来 hook WIP。

**不签**：新正常远端 push 时延、候选完整 CI、正在施工的源语义 R4、真实 H1、真实付费摘要、缓存恢复、RF 实际采用、生产 OCR 或总目标。作者旧 173 例结果作为历史收据保留，不与本轮 10 例相加声称新覆盖。

独审完成 **STOP**，ROOT 可继续正常提交/推送和精确候选 CI。
