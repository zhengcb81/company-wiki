# W07-RF-MODEL：原生模型组合压力测试包

## 可以现在开工
工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality`
分支：`codex/w07-rf-model-quality`；基线：`30ddae8ed2a457c418e63b182e7d8c9230fbf3ff`。
独立 PWF：`.planning/w07-rf-model-quality/`。先读本卡、同目录 HANDOFF_CONTRACT.md、INPUTS.json。ROOT 已准备稀疏 checkout；不要 disable sparse-checkout，旧 tracked .planning 约 846MB 与本包无关，不要拉入。主仓 assurance/output 的其他改动不属于本包。

## 为什么做
单模型与期间测试已经完成，本包补跨机制组合缺口，形成可重复工具，给母 G4/G5 的新公司预测提供数学边界证据。不要再搭第二个预测引擎，不要据合成测试宣布买方结论准确。

## 唯一写集
- 新 `tools/model_generalization_matrix/**`（run/cases/oracle/report/README 等）。
- 新 `tools/tests/test_w07_model_generalization.py`。
- 自己 `.planning/w07-rf-model-quality/**`，但 `input/**` 初始内容只读。
- 自己 `docs/handoffs/w07-rf-model-quality/**`。

其他一律只读：scripts、已有 tests/fixtures、config、CI/hooks、SKILL、安装、assurance/output。发现 core 缺陷给 ROOT 完整最小复现，不越界修；工具可交 PARTIAL，不能掩盖产品失败。

## 已确认的原生接口与上下文
- `scripts/revenue_core.py:run_forecast(data, *, mode="formal")`：工程全程显式 `mode="draft"`，不要求发布签名/供应商；不假造不存在的 CLI --mode。
- 现有 CLI：`python -B scripts/revenue_forecast.py INPUT --validate-only`，内部是 draft。选择一个合法、一个拒绝样本实际调用；不能只测自己 wrapper。
- `scripts/research_support_diagnostics.py --input INPUT --output NEWFILE` 返回 `economic-support-diagnostics/1`，按 segment/year/scenario 报支持缺口。
- formal 的 validate_published_forecast 不适用于 draft；draft 不给 invest 消费者，不伪造 publication receipt。
- 从现有 `tests/test_lifecycle_forecasts.py`、`test_industry_end_to_end.py` 的 model_document、`test_data_contract.py` 的 finalize_contract/apply_parameter_contract、`test_research_evidence_roles.py` 的 calibrated_document、scoped_calibration_support/target_measurement_comparison/M3 period/model extensions 取合法工程构造。每 case deepcopy，已有 helper 会变异输入。
- 本包 input/native-* 是 ROOT 用原生 helper、draft 与 support API 实际生成的合成样本（约178KB），只演示输入输出形状；不代表真实公司或来源真值。

## A：先固定 8 类组合及独立 oracle
每类至少一个合法可算向量与一个有意义反例/未知向量，合计至少 16 个小输入；不要生成数百同义用例。期望来自固定 CaseSpec/手算守恒式，不从被测结果生成 expected。可延用原 fixture 单位与期间校验。

| 类 | 组合 | 必查边界 |
|---|---|---|
| M01 | quantity×price×currency/unit | 同维缩放不改经济金额；CNY亿/HKD百万/USD million标签显式，不自动换汇；混单位必须拒绝或明确转换 |
| M02 | ARR stock→recognition＋late contract/churn | closing ARR 不直接当全年收入，收入按承诺的期间和确认方式进入；不能用缺数据零补 |
| M03 | capacity/demand/launch fraction | 0/有限产能、需求约束限制收入，启动比例只算一次，无无限增长 |
| M04 | dated acquisition/control＋cross-FY partial windows | 部分期间按实际原生覆盖与控制口径；缺季度不能当0，有别名不能双算年度 |
| M05 | zero-base commercial launch＋CAGR | 0基数合法启动收入可算，CAGR undefined=null；不能把 null 解释为坏预测或0增长 |
| M06 | shared shock＋joint scenarios | 共用压力一次传播；volume/price 的相关压力有联合路径，不能重复施加 shock；不强迫所有经济结构 Low≤Base≤High |
| M07 | management annual/runrate/cumulative target＋gross/net/cannibalization | 不可比目标留缺口；累计/期末不冒充当年；自身增量扣已包括收入，防双计 |
| M08 | optional operating support＋segment/year/scenario＋future actual | 某一期间有校准不推定其余支持；合法未来假设与缺actual分离，actual/WAPE未知保持null |

结合现有原生模型实际支持范围制定准确输入。接口确实不支持的组合报告 NOT_SUPPORTED 与 ROOT 建议，不能编造 API/复制公式让测试看似绿。完整预期清单在实现前写入 cases.json 或等价 CaseSpec；保存 A 的行为 RED。

## B：实现可复用有限工具
实现公开入口 `python -B tools/model_generalization_matrix/run.py --owned-root ABS_NEW --out-root ABS_NEW`，无需网络、source DB或其他新包。每个 case 实际调用原生 draft 引擎（拒绝向量可实际验证入口）；记录 native request/result、异常与 JSON pointer。用例期望/数学 oracle 和实际结果分开，未执行不能 PASS。

产出 `model-generalization-matrix/1`：case_id/vector/mode/expected/observed/assertions/status/native_refs/diagnostics，顶层计数、实际时间、恢复与残留。`source_truth_verified=false`，`economic_reasonableness=not_evaluated`。只产 source/model 工程报告，不正式研究报告。多例共用一个 fixture/setup，不每条另建任务数据库或身份审查。

集中快测命令：`python -B -m pytest -q tools/tests/test_w07_model_generalization.py`。覆盖 oracle 被错误结果欺骗、未知处理、native异常、timeout/cleanup、输入被污染；可用 monkeypatch 验证 wrapper，但 C 必须真引擎。开发过程中不重复全仓数千测试。

## C：实际离线 E2E 与验收
一次跑完固定≥16输入，附一次现有 CLI 合法/拒绝与 support CLI 的实际结果。合法结果满足手算/守恒，拒绝有合同原因，未知没有0替代；不存在未经运行的通过。全过程隔离临时目录，最终 absent/sentinel 恢复；固定 input 和只读目录 SHA 保持。

完整报告是手动大节点，不加入每次 commit/CI。交 handoff.md/json、fixture schema/CaseSpec/报告、测试记录。正常 commit，STOP 等 ROOT。预估为中等工作量，若暴露 core 缺陷先准确记录，不耗费模型调用尝试。
