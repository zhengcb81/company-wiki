# PDF-C2 单行可移植性独立审查

结论：**PASS / 0 OPEN**。仅审查 `_paragraph_worker.py:51` 的 `ctypes.WinDLL` → `cast(Any, ctypes).WinDLL` 差异，不代签发布、CI、C3、原文回放或模型执行。

- 审查时 HEAD：`f1b9935bd82d19de5da76331028c87419fa12337`。
- 新 worker LF SHA-256：`5bbc41a5468bce9448c5f1b6a12c115a5bbbf307a9cc54fb59dc0eddde3c35ca`。
- 旧 worker LF SHA-256：`570d658be0b3cf6b948b972d668851ae2542964854b49f85ab8a0e86c2bda97c`。
- 旧独审快照：`docs/plans/du11-source-closure-2026-10-18/review/pdf-c2-enhancement-20261025/independent/final-review.json`，字节 SHA-256 `ef9dbc14ea77f788e6ca3c284f0abe54e4ec735a6cf52515f4629c63edf4c7e5`，保持原样；旧 F1–F5 PASS/0 OPEN 与三原件精确回放不重做。

差异只有第 51 行。`Any`、`cast` 已在第 14 行导入，调用仍由 `os.name == "nt"` 守卫；`kernel32`、`use_last_error=True`、GetCurrentProcess 和 WindowsJob 路径未变。写法与 `_process_tree.py:55` 一致。Linux 类型接口中未暴露的 Windows 动态属性通过 Any 视图访问；cast 在运行时返回同一对象。

独立核验：其余 11 份旧绑定 src/tests/pyproject 的 LF SHA 全部一致（完整清单见 JSON）；精确反向替换恢复旧 SHA 且等于 HEAD 的 worker LF 字节；仅擦除此 cast 后 AST 完全相同。轻量表达式探针确认 cast 保留 ctypes 模块和 WinDLL callable 身份，旧/新表达式 mock 调用参数完全相同。本探针未调用真实 WinDLL，也未导入 Docling 或模型。

ROOT 另行运行 Linux 全量 mypy（379 文件）；本审查未消费其收据，不据此宣称通过。正常 hooks、发布精确 CI 和 C3 仍由 ROOT 后续确认。旧模型收据不改写为新 SHA 实跑；worker 来源身份变化可能按既有绑定机制使旧增强缓存失效，属于保守复用行为。

仅写本目录的两份独审结果。源码、生产配置、原件、git index、无关 `.githooks/pre-push` mode WIP 及 W19/作者工区/RF/Dayu/IQS 均未改动；0 模型调用、0 下载、0 原件副本，未重复旧 34 测试或三源回放。
