# W03-A RF 最终非作者补审

**PASS_FINAL_ENGINEERING_CONSUMER_ONLY**。最终产品 `2de4b9d3ad3c032c89a1987a3b2141610ac91233`：独立补审32例 + 既有公开helper控制26例，合计 **58 PASS /0 FAIL /0 SKIP，0.82秒**；正常公共mypy **12个源码文件PASS**。未发现需要作者再修的产品问题。

## 新版本及旧封存

本报告只绑定最终单一runtime文件 `scripts/company_wiki_narrative_contracts.py`，源码物理SHA、LF映射、Git blob及运行前后状态见[机器报告](r1-w03-rf-final-supplement-20261022.json)。全差异已审；产品和独立测试字节在运行前后不变。作者后续文档更新不会替换这项源码绑定。

旧b76的 `r1-w03-rf-independent-20261022.md/json` 与其9个证据文件 **11项字节全部不变**，没有重签或回写旧报告。旧26例当时未覆盖本次两种合法current元数据，也未把该产品文件纳入原固定类型名单；旧PASS不能代签本最终版本。

ROOT本轮澄清：**as_of=None 是当前元数据读取，不可用read_at日期虚构historical as-of**。新增proof仍需真实shape/SHA和事件检查。补审在新的测试副本中，只将current晚proof的拒绝原因由历史cutoff码改为真实 `source_clock_conflict`，继续要求拒绝；历史显式as-of的 `source_availability_after_asof` 断言保持。旧封存测试未改。

## 检查结果

- 两个新合法current反例：typed publication晚于read；retrieved早于publication但proof/read事件合法。各自与legacy无proof完整context对照，除新增read_receipt.proof外完全一致；pub、retrieved和as_of=None不变。
- current proof晚于read仍以公共source_clock_conflict拒绝；retrieved晚于read矛盾仍拒绝。无proof/null的旧current语义继续保留。
- 显式historical路径仍用common qualifier：known未来/非法pub优先，unknown pub无proof、晚proof、错SHA/额外key/非法shape均不放行。projected/3根single-proof（含null）仍拒。
- 四处type-only cast均位于原 `_require` guard后：locale regex match、原始parent dict、projection pointer/record文本、locator文本。cast不改变输入值/对象身份或异常分支；四组正反控制和既有公开helper均通过，没有ignore或语义放宽。
- 现有公共mypy正常命令包含narrative合同，12个源码文件全绿；缓存仅在本次自有TEMP，不新增检查门、安装或依赖。

[证据README](r1-w03-rf-final-supplement-20261022/README.md)、[实际命令/UTC收据](r1-w03-rf-final-supplement-20261022/receipt.json)、[JUnit](r1-w03-rf-final-supplement-20261022/results.xml) 和mypy收据均保留。审查人未写RF产品或作者测试、未安装或并线、未写母PWF。0 API、0下载、$0。

## 清理与边界

`.planning/r1w3s` 初始不存在，结束后仅对该解析确认的独占根删除，已恢复不存在；文件数和字节见[cleanup.json](r1-w03-rf-final-supplement-20261022/cleanup.json)。只留紧凑测试/日志/hash，没有生产原件副本或账本改写，未冒称精确峰值已测。

本结论仅供ROOT接收最终consumer工程版本并按consumer优先顺序发布/安装。ROOT另负责真实CWP producer→RF公开CLI组合和集中并线；本补审不代签真实公司内容、0.9/v5语义、正式摘要或W07付费恢复/cache质量。后续W03-B/W07继续按总PWF推进。