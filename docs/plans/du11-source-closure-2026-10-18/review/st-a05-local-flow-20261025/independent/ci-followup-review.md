# CI 回归跟进独立复核

结论：**PASS（本次 06c 回归修复范围）**。

## 版本与范围

- HEAD：`06c1a5839302f4e297d70a13267a8aa490eef719`
- 复核 7 个未提交产品/测试文件；其 SHA-256 与同目录 `ci-followup-review.json` 一致。
- 先前 A01/A05 终审所绑定的 17 个产品/测试 SHA、9 个 attempt05/回归证据 SHA 仍全部不变。真实样本结果没有被本次 CI 修复改写。
- 本结论只覆盖本次 128 例失败的定点回归及其 218 例修复后测试包，不代表整仓库 CI。

## 六个失败对应的根因

1. **三个零预算 PDF 用例**：旧测试约定预算为零时仍扫描并发出 80 页基础文本，仅禁止表格 finder；新实现开始在逐页读取前预扣共享 parse/select 工作量，因此按 `WorkBudget` 的明确停止契约抛出 `WorkBudgetExceeded`。现在的测试验证零预算时不访问任何原生文本页、不调用表格 finder，并验证异常维度/上限与预算耗尽状态。生产 handler 对该异常单独保留预算原因，仍以现有 `PARSER_INCOMPLETE` 终态停止，不继续扫描、不触发 selector。选择的是明确抛异常，不声称有可继续使用的解析 partial。
2. **布局桥测试 stub**：生产 layout 输出的 `du2-layout-hints/1` 始终有 `groups`，包括预算退化输出；测试替身遗漏这个必需字段。仅补齐 stub 的真实输出字段，未让产品用默认空组掩盖错误引擎输出。
3. **阅读策略编译漂移**：`reading_catalog.json` 是由 `tools/import_reading_policies.py` 生成的 runtime asset；导航上下文策略曾只写进生成文件，未写入维护源 `reading_defaults.json`。现把策略移入 defaults，并由 compiler 写入 runtime catalog。只读运行 `python tools/import_reading_policies.py --check` 得到 `catalog verified: 24 families, 14 facets`；既有和新增测试分别验证单一来源、编译保留及 drift 检查。
4. **running-furniture 断言过窄**：旧断言把模型材料必须恰有 3 个 PDF block 当成物理证明正确性的替代指标。通用导航标题现在可在语义父级已提供时从模型正文省略，所以实际块数为 2。测试改为断言精确的 parent/period/target 证据、两处对应物理 block、source-proof 中 footer 与边界 unit 的绑定，以及导航标题和重复 footer 不进入模型正文。

这四类是 6 项失败的完整归因（3 个预算用例共享同一原因）。预算修复的合法来源 SHA handler 反例先确认了原先只得到笼统“PDF解析不完整”的诊断，随后才增加异常专门映射；最终包包含该修复后的生产测试。

## 验证

- `review-ci-regression-red/red.log`：本地复现同样 6 FAIL / 122 PASS。
- `review-ci-handler-valid-red/red.log`：使用 SHA 有效的 PDF 夹具确认 handler 原先丢失预算原因，避免错误夹具导致假阳性。
- `review-ci-final2-green/final.log`：218 PASS，16.45 秒；runner 收据 17.88 秒，临时测试根目录收据确认运行后恢复为不存在。
- compiler `--check` 与 `git diff --check` 均通过。
- 运行包覆盖预算处理、生产 PDF、策略 registry/compiler、layout stub、来源引用和原 A01/A05 相关 4 份测试；没有改变原生 lane、source-proof 或 source-selection 实现。

## 剩余边界

预算耗尽选择显式抛出和生产终态失败；解析器不会返回已经读取一部分的 `NarrativeParseResult`。这与本次修复采用的“停止，不超预算继续读”契约一致。若未来希望保留中途 partial，需作为独立 parser API/状态语义设计，并覆盖中途耗尽时未发出的 lookahead 页，不能通过继续读取剩余页面实现。

本次 218 项修复包无未关闭 finding。真实 attempt05 的模型答案质量仍未审阅；RF adoption 与整个 A05 闭环也不在此 CI 复核的签收范围。
