# W06-AUDIT-MEASURES 独立接收审查

## 结论

**FAIL，待 ROOT 隔离修复，不建议当前提交直接并主线或安装。** 这是工具口径校验的实证失败，不是新增人工许可。四路审查、真实出处与预测经济合理性未由本次审查签收。

交付：`codex/w06-audit-measures`，base `c0993332623637d53f059350a382d99a95ef731d`，feat `098b4d03f65bfa19a57eb5ae802f44c08d6c8dc6`，docs/HEAD `6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1`。交接 JSON 绑定 feat、manifest 位于后续 docs commit，属于正常避免自哈希的安排。工作树最终 clean。26 个新增文件均在施工卡排他写集、本线 PWF/交接内。

交接列明的 23 项 SHA/尺寸全部匹配。独立重放既有新工具 **40 tests PASS**，旧 `numeric_audit` **7 tests PASS**。未重复全库 187 套测试；交接已有其日志，当前存在确定反例，再跑全集不能解决这些漏测。两个正常对照和一个 blank relation id 负例符合期望，但 **19 个独立向量有 16 个不符合期望：11 个假 PASS、5 个未诊断异常**。向量全部明确 synthetic，不表示真实公司已经发生这些事故。

真实 CLI 另外重放三例：缺来源的转换结果和 USD 输入改成 CNY 输出的求和都 **exit=0 / overall=PASS**；缺一个 operand 的 difference 崩溃，没有结构化 report。初始/最终 owned scratch 都 absent，sentinel 不变；无 provider、模型、HTTP、费用、原件读取或生产数据修改。

## 根因与定位

产品文件：`C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures/skills/revenue-forecast-audit/scripts/financial_measure_audit.py`。

### M01 — P1：关系只算数字，没有完整约束 typed observation 的输入和输出

转换分支（357 起）只核 amount/ratio 和币种；求和（431 起）只比较 inputs 的实体/定义/币种，没有比较 result；增长（517 起）漏实体/窗口可比性；share（578 起）只核币种与非空 `scope_inclusion` 字符串。实际输出：

- Acme 的 2024 收入 `USD 1.2 billion` 转成 Other Company 的 2025 现金余额 `USD 12 亿`，**PASS**。
- 两个半年收入 USD 100+80 million，result 把实体和定义改成另一公司净利润、币种改 CNY，**PASS**。
- 一年收入 120 / 一季度收入 100 被叫成 20% 增长，**PASS**；跨两家公司年度收入也 **PASS**。
- 全年收入 flow 20 / 年末现金余额 stock 100 被叫 20% share，**PASS**。

应从 op contract 统一生成量纲、实体、定义、币种和时间约束，而不是给上述例子逐项加 company-specific if。转换保留原口径（仅允许显式 scale/FX 改变），sum 的 result 必须与输入相容且窗口等于拼接跨度；增长比较的是同一经济对象的兼容、顺序明确窗口；share 的范围包含关系不能让一串文字取代维度/时间检验。不同实体的市场份额可以合法，但必须明示范围关系而非靠名称猜；不要加第二套公司身份库或人工批准。

### M02 — P1：缺上下文的结果得到诊断，却仍返回 PASS

339 行只阻断 result INVALID；356 行计算 `result_unresolved` 后未消费；348 行 `finish()` 原样返回 arithmetic PASS。因此转换 result 缺 `source_ref` 或 flow window，都在附录有 missing 诊断而 **overall=PASS**。结果没作为 observation_checks 独立计入，`_overall()` 看不到其 UNRESOLVED。

应给 norm 保留结构/口径/来源状态，关系按所需字段合并 input/result 状态。数值能复算也只能说明 arithmetic，不得把 missing source/period 判成已完整验证。合法 future assumption/guidance 仍可存在，角色和依据不应升级为 actual；source truth 永远保持 false，由已有四审实读。

### M03 — P1：容差保护用 `max(...,1)`，小数误差可掩盖几百万倍

255 行 `ref=max(abs(expected),abs(declared),1)`。share 真值 `0.0000001`，declared `0.49`，absolute_tolerance `0.499`，均为 decimal，**PASS**。不是普通显示舍入，而是 4,900,000 倍的数量级错误。

应使用有明示显示精度依据的误差上限，保护应基于目标期望的真实量级；零值单独定义。用户传的 declared 不能把允许容差放大，纯 absolute tolerance 不应遮盖数量级错误。保持 Decimal 精度，不靠把单位改大/改小避过验证。

### M04 — P2：JSON 形状、operand arity 和必要时间没封在纯函数边界

`seen_ids.add()`（120）、scale membership（131）、input membership（326）遇到合法 JSON 类型中的 list/dict 会 TypeError；sum 排序缺 window 会 None/date 比较错误；difference（490 起）直接索引第二项，单 operand 为 IndexError。转换多 operand 则静默忽略后者并 PASS。

应先做统一类型/arity 校验，未知/缺必要口径返回具名 INVALID/UNRESOLVED；不能把“有 finite 数值”作为 `usable` 的全部条件。不能以 blanket except 后返回 PASS 解围。CLI 对 malformed 内容仍应产出不可覆盖的结构化 report（exit=2），异常程序事故要显式区分。

### M05 — P2：版本和 as-of 合同没有实际校验

`audit_measures`（625 起）不校验 schema_version、不解析 as_of_date；`financial-measure-ledger/999` 和 `as_of_date="not-a-date"` 都 **PASS**。既有 date 字段校验只在各 observation 内。不得声称输入 schema/审查日期已符合合同。

应在 top-level 校验指定版本和明确 YYYY-MM-DD 上下文；缺上下文不要猜。`available_by` 与 target period 按补充合同分开表示；未来 guidance/assumption 不因预测期间在 as-of 之后自动失败，但来源资格未知应保留明确诊断。

## 主线 / W05 兼容与接线

Audit canonical main 为 `321d4c165575e81add3b4aa1ee9ba0a047ca6082`、clean、无 remote。它已包含 W05 pool causal closure。W06 全部 additive 新文件，与 W05 `pool_progress.py`/测试、SKILL.md 和 loop 合同无写集冲突；共用 `audit_contracts.py`、`audit_run.py`、`numeric_audit.py` 从固定 base 到当前 main 未变化，未发现 Git 文本冲突或公共 API 变更。

**这只证明并线基础，不证明新工具行为可用。** 工具尚未被四路审查调用（按卡由 ROOT 接线）。可将其接到 reviewer 3 的数字/流程检查，供 reviewer 4 判断模型合理性参考，reviewer 1/2 仍各自负责 CWP/FF。不得以工具 PASS 替代 source byte、RF 执行过程、实际预测或四份报告。

W05 pool 的 campaign/attempt/artifact binding 原封保留：measures report 是该 attempt 的额外审查证据，最终独立 findings 仍经既有 root-cause/fix/retest closure。不可另造一份 clean summary 吞掉这里的 16 个失败，也不改 pool 预算/旧已封存 runs。

## 建议 ROOT 施工顺序（一个集中大节点）

1. 在当前 main 新 ROOT 工作树接入两个原交付 commit，保留 worker 冻结树和上述失败证据；先将 19 向量变成快速可独立运行的回归测试，不能修改 expected status 换绿。
2. 实现集中 schema/normalization + typed op preconditions + status propagation + precision-derived comparisons；保留旧 numeric 工具与原测试断言。
3. 在同一集中包增加各 op 正例和反例、结果口径、exact arity、合规 future roles；不要对每个修复点跑全库、加人工审批或新增长期任务库。
4. 重放本次 19 向量、三条真实 CLI 和原 40+7；整套当前主线 audit unittest/独立 scratch E2E 在最终工程节点一次跑。只读来源真伪和经济合理性边界必须不变。
5. 达标后 ROOT 接入技能、定点安装新工具/reference、正常 commit。Audit 无 remote，不声称已远端推送；CWP 总 PWF 由 ROOT 更新并推送。之后接回 G2/G4/G5 真实公司复核，不用 synthetic 三国 ledger 签真实公司质量。

## 证据与复现

- `git-intake.json`：最终 HEAD、两原 commit、26 paths、clean、canonical main、shared dependency 未变。
- `sha-verification.json`：23 项实际 SHA/bytes 校验。
- `counterexamples.json` / `probe.py`：19 个输入、实际 report/exception、明确期望与 frozen HEAD。
- `real-cli-counterexamples.json` / `cli_probe.py`：真实 CLI 三例和 owned scratch 恢复。
- `test-replay.json` / `replay-financial-tests.log` / `replay-numeric-tests.log`：集中 40+7 绿重放。

CodeGraph 在此 worker leaf 未初始化；本次只读审查没有初始化/修改索引。直接读取施工卡已指明的新文件和 Git diff。所有新增证据均限 ROOT 专属 intake 目录，没有修改产品、安装副本、六份共享 PWF、生产配置、原件或费用账。
