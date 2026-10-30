# Atomic /7 工程节点独立审查

结论：**限定工程范围修复后通过；0 OPEN P1 / 0 OPEN P2。** 不签真实 `/7` 摘要语义、真实付费/缓存验收或 RF 实际预测采用。真实与子事实覆盖的 `semantic_status`、`subfact_coverage_status` 仍为 `not_evaluated`。

本次直接修改了授权的 CWP owner 和新增永久单元测试；RF 全程只读。未改工具 observer/runner、父任务 integration、旧 captured 数据、原件、gold、生产配置、foreign hook；0 POST、0 下载、0 PDF 解析、0 提交、0 部署。

## 已修复 AP-01（P2）

`narrative_summarize._completed_result` 和 `narrative_verify._bundle` 在正式最终 claims 上重算 `assess_summary` 时，漏传 `protocol.assessor_version`。因此 `/7` decoder 虽执行 `1.1`，后续重算却默认回到历史 `1.0`。实际首轮 TDD 3 RED：最终报告版本错误，raw/projected 正式 bundle 均以 `SUMMARY_INVALID` 拒绝，不具备工程发布条件。

两处现在显式传递协议 assessor 版本。没有改变历史默认值，也没有以删除质量校验消除拒错。另修三处纯 typing：compact hints rows 注解、两处已确定 assessed prompt 的非空收窄。首轮可复查观察在 `initial-red.json`。

## 工程证据

- `final-tests.log`：40 PASS / 6.89 秒，四个限定模块；新增 `test_atomic_summary_artifacts.py` 12 个永久案例。
- `mypy.log`：11 个授权源文件 PASS；`ruff.log`：同 11 源文件及两个 atomic 测试文件 PASS。
- 实际 `_completed_result` 走语言观察 `same`、`uncertain` 两条分支后，`needs_review`、风险 ID、最终 claims hash 均保留；完成结果通过 wrapper→parse→source 重算，而非只测 decoder。
- 新 raw `2.1`、projected `3.1`、producer `1.1`、wrapper `2`、终态诊断、两类 skip、generation 与 publication effect 一致。skip 保持 model/assessment 为 null。
- 错配 assessor、报告诊断代数矛盾，以及擦除 claim 风险再重算 claims hash，均被正式 wrapper/bundle/terminal 相应边界拒绝。
- `/4`、`/5`、`/6` 永久 fixture 的 instruction/data/input SHA 逐字节断言通过；`/6` 最终完成结果仍用 `1.0`，没有增加 atomic current-action 规则。
- 原真实 `/6` bundle 在当前代码读取并完整验证通过：body SHA `c996577bbe4930bc12bd86deac68d3ed813dd2a372feee3989cc5aba9ac1d27b`，仍是 `4.2/1.0`、0 历史诊断。见 `old-six-captured-replay.json`。这不是新模型输出，也不把旧语义问题追记成新算法已发现。

## RF 只读独立复核

已读作者 `rf-atomic-wire-independent/review.md/json`、两个 changed paths 和不变公共 contract。实际三文件 raw SHA 与作者 final seal 完全相同。独立重跑 `tests/test_assessed_narrative_consumer.py`：57 PASS / 0.92 秒，禁 bytecode/cache 写入。

RF 显式 catalog 严格配对 `4.2→1.0`（7 deps/5 rules）和 `4.3→1.1`（8 deps/7 rules）；unknown/mixed 元组拒绝。公共 bundle `2.1/3.1`、producer `1.1`、22 字段 assessment 和已有 quality algebra 保持不变。没有导入 CWP、重算来源、创造人工许可或把 `not_evaluated` 改成语义通过；receipt 保持 `not_consumed`。

额外离线跨仓探针把 CWP 当前 owner 实际生成的 `/6`、`/7` raw/projected 四种 wire 交给 RF validator，四种均接受，换成另一 assessor 则全部拒绝。见 `rf-actual-producer-wire.json`，可运行 `probe_rf_wire.py` 重现。它只证明发布 wire 兼容，不代表预测消费。

## 封存与边界

`seal.json` 绑定 CWP base `f1b51f0657cc97776db37b8848e5f707d1e7df94` 上的 14 个工程文件实际 raw/LF SHA，以及 3 个只读兼容依赖；RF base `4bbf4528e108142784c81f857eb9f9ab81dfa89a` 的三文件实际 SHA。审核的是工作树具体字节，不能仅凭 base HEAD 或 pipeline completed 泛称通过。

父任务单独负责 localhost HTTP integration、observer/runner、后续真实 `/7` 与 RF 使用验收，本报告没有替代这些节点。有限 frame hints / diagnostics 是源文本观察，无法证明自然语言蕴含、独立条目无遗漏或预测参数可用性。保留上述边界后，当前审查范围没有剩余工程阻断。
