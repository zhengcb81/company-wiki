# R1 调查

历史试验只能探索性 PARTIAL，不改写旧 raw/gold。模型资产原工区只读复用；主线 M8/W22 不修改。详细根因及返修要求见 TASK_CARD。

## 本轮发现

1. 平台修复 20dd0143 是开工前置条件（R1-setup required_runtime_fix_before_start），缺它时 Linux 收集失败且 X1 入口是旧的。
2. 账本累计必须闭合到单 campaign：分 invocation 记账会丢失/重复成本；append-only 账本 + 保守计费是可行解，但“未开始页”必须记 0（已修）。
3. 真实表格页（金山雲 9 列综合亏损表）是 R0 的结构性弱点：列绑定丢失、千分逗号被读成小数点（338.857）；这是困难页补救的直接证据。
4. 小米 X1F 在本机两次均失败：cap 与实测固定开销差距 + fix 后尝试中 job peak 超过 cap（Job Object 约束未生效，OPEN 平台问题）。
5. 独立 gold 可能出现真实错字（跨行漏字），必须允许版本化纠正并重算指标；“盲冻结”不等于 gold 永远正确。
6. 表面匹配口径对分析型/转述型事实天然偏低，需同时给 numeric-anchor 口径并明确声明；币种必须进入数字身份。


## ROOT R6共因更正

四个独立RED是工具缺陷而非模型质量结论：X1只写不读cache、开始推理后无durable inflight、零预算仍进runner、非finite读写。现以单ledger短OS事务+保守reservation+同cache完成marker恢复修复。历史7个R0零秒原调用unknown，另1080过计均保留；1431.40547是账面charges，实际total elapsed=null，1800合规未证。提供的review仍NEEDS_FIXES，缺76292最终绑定；作者PNG仍存在，未盲删。新工具独审单独绑定ae438a32，不伪造旧READY。


## ROOT R6独立复核闭合

实际新工具独审PASS仅覆盖ae438 source/事务缓存边界，不能替代旧耗时合规、Job cap问题或OCR质量比较。原4RED及新增死亡窗口由独立探针重放，cache先写/settle前和marker前两个窗口均不二次推理；缺marker时费用unknown保持、已捕获文本可读且whole batch partial。当前文档历史claim与有效状态已经分开。
