# 正式中性回归交接

唯一正式新增文件：`tests/unit/document_understanding_selection/test_reading_untyped_numeric_quality.py`。

当前冻结 SHA-256：`bc9b93b1a1869369b12a403d13a67f2eee8793fc992b3d42aacf293a1c6286bf`，12328 bytes。

- 15 项通过（1.42 秒），Ruff 通过。
- 原独立 RED：`red.txt/xml` 仍为 6 FAIL / 7 PASS，未覆盖或改写。
- 第一轮正式测试启动前 ROOT 已并行实现质量出口，故第一轮正式 `formal-red.txt/xml` 尽管命名含 red，实际是 15 PASS，不作正式 RED 证明。
- 本次 `formal-final.txt/xml` 和 `formal-handoff.json` 绑定实际当前源码；8 个 owner 文件和正式测试前后字节稳定。

## 覆盖范围

6 个真实公共 selector 中性裸数行（简体 newline/tab、繁体 newline、英文 newline/tab/pipe），保留业务描述，校验原始身份与位置不变，quality flag 进入 citation support 和 scoped model view；不 monkeypatch `_understand`。

5 个负控：单值、单年标题、完整带单位多数量中文 prose、原换行 prose、英文 prose。另有手写 in-memory native descriptor，真实共享 binder/selector 处理后保留完整绑定数值47，不误加 flag。

新增两条 carrier 控制：两个原始片段被实际公共链合为一个精确 `pdf_native_range`，第二片段的裸数值格不能在压缩后失去未知质量；两不同 parent source 的 carrier/prose 并存时，仅未知 parent 带 flag，引用组不跨源，另一份完整经营 prose 不被污染。

所有公共测试锁定既有 schema、96 spans / 48000 chars / 16000000 work 上限，内部 pytest import guard 确认本 checkout。输入的 source ID、locator、原文、metadata 和原 quality 整体快照前后一致。

## 只写责任和清理

仅新增上述正式测试及本 `resume/untyped-independent` 目录报告；未改生产代码、ROOT 既有 tests、Git/索引、配置、原件、其他 harness 工区。

未读原件，未运行格式 parser，未调用网络或 LLM。requested basetemp 与实际 relocated `cw-pytest-basetemp/20261023-210756-6c8cbb28` 已验证不存在，详见 JSON 清理收据。保留历史诊断输出，不递归清理历史目录。

这只是共享 numeric-quality 工程节点证明，不代表年度14目标、跨页祖先、选材公平性、正式摘要或整轮 RF 已完成。等待 ROOT 大节点独审。
