# W08-AUDIT-EVIDENCE：四路审查的执行证据实读与覆盖核对

## 可以现在独立启动

- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence`（已准备，不是原主仓）
- 所属项目：`revenue-forecast-audit`；固定基线：`2c49491355bd68b7ab5ed664bfd8010d9dae5a84`
- 分支：`codex/w08-audit-evidence`；PWF：`.planning/w08-audit-evidence/`
- 先读本卡、同目录HANDOFF_CONTRACT.md与INPUTS.json；不取消稀疏checkout，不拉入旧大体积.planning/assurance/output。
- 本包预算：外网provider/LLM调用0；不要读取真实凭证或恢复暂停母目标。无需等待另外两个W08包。

## 唯一可写集

- `skills/revenue-forecast-audit/scripts/review_protocol.py`
- `skills/revenue-forecast-audit/scripts/review_evidence*.py`
- `skills/revenue-forecast-audit/references/review-evidence-reconciliation.md`
- `tests/test_w08_review_evidence.py`
- `tests/fixtures/w08_review_evidence/**`
- `tools/run_review_evidence_e2e.py`
- `docs/handoffs/w08-audit-evidence/**`
- `.planning/w08-audit-evidence/**`

未列入写集均只读，包括旧断言/初始input/主线/安装及其他包。ROOT专属母PWF、W04 core、G2真实付费、主线/安装/CI。

## 当前接口和真正待补的部分

已有review_protocol.py已经检查四审checkpoint、N/A、FAIL→finding、完整issue key、numeric denominator、crosscheck和declared/observed scope；不要重新实现这些检查。其check_coverage(payload)是声明核对，没有实读每项evidence。document_status_join已有请求/调用/逐文档状态与一次费用语义，audit_run已有event/capture/check；复用结果，不再造执行库或审查器。

本包新增**报告型、可选的实际文件/执行记录核对**，用于G4/G5发现“报告齐了却没跑/没读/用旧attempt”的可观察缺口。不是重新验证公司身份、raw字节和来源资格；这些由CWP/RF责任层负责。不能凭日志证明隐藏思维、真实agent独立性或来源真值。

## 实施细则

1. 先读SKILL、references/artifact-contract.md、workflow.md、四review卡，以及audit_run/audit_contracts/review_protocol/document_status_join；固定真实run/event/report字段，未知字段原样兼容。输入由显式execution root和coverage JSON指定，不能扫描本机所有runs/原件/会话或环境密钥。
2. 增加可选CLI coverage --execution-root ABS，保留旧check_coverage(payload)和旧CLI无该参数的行为/断言。新增pure helper及reference明示路径、pointer/行locator、事件/产物引用分类、限额和输出。
3. 实读JSON/有界UTF-8文本evidence，存在文件不等于locator可解析；明确json pointer与行范围，未知PDF locator/source_id/tool-call为UNVERIFIABLE，不在本包调用SourceReader/provider/OCR。相对路径依据显式root，允许用户显式列出的外部只读artifact，禁止隐式全盘扫描。链接/逃逸路径诊断，不打开未知目标。
4. supplied hash才比较；缺hash只记录observed SHA/未签hash状态，**不要求补人工签名、不因缺hash阻断**。SHA是当前读取字节观察，不能冒称历史时点未篡改；有freeze/capture历史可据其显式引用对比。
5. 核对run/review_attempt/role实际已知字段、current报告和真实事件call IDs/输出引用；同公司旧run或旧attempt不作为本轮凭据。opaque公司id当引用、不加身份解析。command_started不等于finished，exit0不等于业务成功，output_complete=false不能称全程可复查；无真实事件列未核查而不是臆造已调用/偷懒结论。
6. numeric verified条目按value_id去重/发现重复，实读明确recompute artifact locator；相同引用重复不能增加分母覆盖。跨role同issue_id按既有完整key保留，不改W05pool状态或预算账。counter/support或数值来源真伪仅引用已有诊断，不重算预测。
7. 输出保持review-coverage/1兼容，additive evidence_reconciliation节点，逐条OBSERVED/UNAVAILABLE/UNVERIFIABLE/MISMATCH和具体refs/reasons。records_complete仍只是记录完整，quality_status=not_evaluated；四审无finding不自动经济PASS。失败范围不中断其他可检查行。
8. 用audit_contracts.write_attempt/Redactor；显式max总文件数、单件/总读取字节、时间上限（建议128件/1MiB单件/8MiB合计/30秒），超限记未核查不伪造完整。不得全套复制执行包/PDF，不读dotenv或真实key。超限是资源诊断，不是新许可。

## A/B/C测试

A先固定有真实文件/真实调用event的合法小包与反例；不能只有手填PASS四份报告。行为RED：文件存在但坏pointer、旧attempt、缺完成事件、坏hash、重复numeric证据、tool-call无可验证响应、截断stdout、opaque引用/缺hash合法保留、文件过大/输出冲突/错误恢复。
B一次集中：python -B -m pytest -q tests/test_review_protocol.py tests/test_w08_review_evidence.py；同时明确旧结构CLI回归。
C新tools/run_review_evidence_e2e.py实际调用audit_run init/event/capture、当前coverage CLI与新可选入口（先--help核参数），生成一份合法包与上述有限反例。child仅本地合成文本程序，保留真实exit/捕获日志；不启动RF/其他agent，不称它四路真实公司审查。每份新attempt输出互不覆盖，临时根absent/sentinel都恢复，固定input与原包SHA保持。

交reference/输出schema/真实CLI日志、固定反例expected→actual、缺支持locator清单和ROOT的四审接线建议。Audit没有remote，仅正常本地commit。SKILL/旧review卡/安装/loop/status_join/财务审查器/核心audit_run不写；ROOT收后接线安装。零模型/provider。

## 交工

按本地HANDOFF_CONTRACT.md正常commit并STOP；交给ROOT卡号、实际branch/HEAD和handoff绝对路径。允许如实PARTIAL，不以只测wrapper冒签原生E2E。
