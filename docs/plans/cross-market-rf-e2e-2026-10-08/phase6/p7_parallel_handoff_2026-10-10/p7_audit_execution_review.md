# P7-AUDIT：共用执行请求、逐文档记录与四路风险审查协议

**可以立即开工；较大的审计技能工程包。**独占 revenue-forecast-audit，跨仓只读，不依赖MAIN新AUTO或P7-RF诊断才能完成。真实公司循环不在本卡启动。

## 0. 项目、工作目录、唯一PWF

- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/p7/audit`
- branch `codex/p7-audit-execution-review`；base `78c2b1089200937a9371548f3f8a212c501fdfcd`。
- 唯一 PWF `.planning/p7-audit-execution-review/`（本次独立建设包；旧docs/plans/skill-build和公司池计划只读），三文档/本卡已放好。
- 先读本仓AGENTS、skills/revenue-forecast-audit/SKILL及相关references；应用skill-creator更新技能的要求。上游 W05和SKILL_CHECKPOINTS均复制要点于本卡，不要求别仓改接口。

```powershell
Set-Location -LiteralPath 'C:/Users/郑曾波/Projects/_harness_worktrees/p7/audit'
$env:PWF_PLAN_ROOT = (Get-Location).Path
$env:PLAN_ID = 'p7-audit-execution-review'
& 'C:/Users/郑曾波/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe' -NoProfile -File 'C:/Users/郑曾波/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1'
```

启动解析使用本机已有 PowerShell 7；旧 Windows PowerShell 5.1 缺 IsPathFullyQualified，会返回空结果，不能据此切换到别的计划。

本仓无remote，正常commit即可，禁止擅自创建公开remote。四种角色storage/fetch/process/analyst和后置expert保留，不能一agent换名冒充四独立。

工作树已有仅含本卡启动文档的 bootstrap commit；base是源码基线（HEAD祖先），不要求HEAD与base相等，不reset丢掉启动PWF。工作树源码未施工；按自己的PWF执行M1。独立目录内的 `INTERFACES.md`、`HANDOFF_FORMAT.md`、`handoff.schema.json` 和合成example已配齐，相对路径从本卡PWF解释。

## 1. 已接受工作与仍缺的共同根因

W11 precall原字节/frozen-consumed分离、capture timeout/cap、主故障保留和trust-statement已完成，不重写。当前runtime仅audit_run/numeric_audit，共同request builder、document/call/result join、来源作者辅助检查和风险覆盖诊断未实施。

继承冻结 W05的R10（scope/profile/caps/env）、R12剩余（正式交付链接）、R13（quote/actor/date/numeric覆盖）、R11矩阵消费。mapped_count有交叉，不能相加报独立问题数。当前validate_report是artifact_integrity_not_quality，结构校验弱不是“机器应该替代经济审查”的理由。

## 2. 独占写集

允许：

- `skills/revenue-forecast-audit/scripts/**`新增pure helpers与必要CLI，保留W11现有职责。
- 该技能SKILL.md、references workflow/executor/artifact-contract/rf-checkpoints/review-storage/review-fetch/review-process/review-analyst/remediation。
- 新 `tests/test_scope_request_binding.py`、`test_document_status_join.py`、`test_authoring_provenance.py`、`test_review_protocol.py`及专属小synthetic fixtures；如需旧测试补兼容，仅 `tests/test_audit_run.py`、`tests/test_numeric_audit.py`、`tests/test_precall_input_history.py` 的真实受影响断言补充，不能删旧断言。其他已有测试只运行，不修改。
- `.planning/p7-audit-execution-review/**`。

禁止：所有邻仓源码/原件/config/DB、安装副本、封存run/report/manifest/157matrix/clean streak、真实下载和付费模型、公司池循环、权限/授权JSON/人签/canary/daemon/第二任务库/第二预算账。建设PWF只放本卡目录，不覆盖旧skill-build。MAIN不同时改audit仓。

## 3. 四个共同工具与固定边界

### A. scope→实际execution request

输入已冻结scope、明确purpose、当前native request模板/业务字段、显式config/env引用；不重复来源resolver，不选provider/model。

输出真实native request bytes/SHA、argv和input argv positions，交既有capture消费同SHA副本；effective scope列实际profile、byte/time/token/cost caps及配置指纹。scope与deploy取更小限额；32/64MiB、2MiB final不能偷偷变128/128或100000000，P1不能变P2。参数歧义/缺失给具体诊断，不猜。

真实child继承所需ET工具环境；日志仅凭证变量名/presence，不保存值。scope表达请求边界，不成为授权文件；沿已有外发/配置授权执行，不重新问用户。

### B. 请求/调用/逐文档状态join

输入request索引、真实call/capture/response、SourceRef和当前acquisition-observation/1。保持现有CWP/FF/RF合同，审计仅生成小索引。

每row request_id/call_id/document或source_id/实际result locator、transport与business status分别记录。stdout存在不等于业务成功；batch部分缺SourceRef仍生成诊断row，继续后项。一个真实call可对应多文档，各文档指向自己的result，不能复制capture假充；call费用/unknown/lowerbound只计一次。covered_by必须定位实际已读资料，不把标题列表写full read。

### C. authoring/provenance诊断

只消费已打开/冻结的原片段和上游locator，不再解析PDF或重验主体。逐字连续quote比较；reordered/composite/manual OCR明确标注，不声称连续原文。保留表头/Total/单位/年季、source原actor/stream/question/answer/precollect/closing、发布日期unknown；不由data year猜December。坏项保留诊断，不能KeyError中断整批。

### D. 四路coverage与交付索引

报告v1和旧runs只读兼容。新增coverage诊断：checkpoint ID/applicable/N/A理由、declared/observed scope分列、全numeric coverage分母/已核/未核及复算位置、analyst实际独立cross-check的模型/参数/证据位置。工具经济quality_status保持not_evaluated，四独立agent才实读判断。

缺关键检查、无依据N/A、FAIL无finding、P2/P3漏处置给具体缺口；不要把一份漂亮报告或3个数字PASS当全量研究通过。聚合key=(run_id, review_attempt, role, issue_id)，local issue ID保留，跨公司同PROCESS-001不覆盖。

正式产物旁用既有write_trust_statement生成可打开链接和source/summary provenance索引，不重签、不造授权。旧report纠错写新attempt/附录，不改旧字节。这里的字段是记录与诊断，不是阻止forecast的全局发布门。

## 4. 必须落实的风险检查

更新四角色references和rf-checkpoints，baseline当前RF4.2/opt-in3.9、SourceRef2.0/default reader2.1/explicit2.2、acquisition-observation/1。运行时读真实版本；P7-RF以后增加可选诊断也不能成为本卡的外部依赖。

- storage：有价值业务正文/opaque影响、主体/限定context group、完整Q&A actor、JSON共享母页/投影、generation精确复用和current parent；工程缓存0不等于完整业务recall。
- fetch：现有原件零重复下载、各类文档正确tool、JSON非电话会、raw/projection/pointer/byte、配置缺失/unsupported/entitlement/HTTP分别、真实success/failure metadata用量和一次batch多result。
- process：每个数字的原文/币种/billion-亿/期间/单位、GMV/backlog非收入、H1/quarter不得直接annual、事实/方向/机制/幅度分开、quote/transcription/actor/date真实；所有技能步骤均有实际调用或合理不适用。
- analyst：独立operating range与转换/支持期、历史seasonality/delta/flat不是未来幅度校准、管理目标期间/CC/FX/并购控制、三年partial、物理/time/exposure jointstress、未来actual不存在时backtest0/WAPEnull。结构工具不能宣布经济假设合理。

## 5. 三大节点与TDD

M1：阅读已有W11并冻结helper样例；先RED scope、statusjoin、authoring、coverage，不重复W11已接受施工。

M2：pure helpers→小CLI→技能workflow/executor共同接线，集中GREEN。负控包括：P1→P2、caps放大、secret泄漏、业务failed有stdout、FF成功ET失败、partial缺SourceRef、重复计费、unknown变0、非连续quote、无单位表头、猜公开日、H1当annual、peer反证当支持、仅抽3数字报全量、无crosscheck analyst报告、四份各一PASS冒充无主要问题、漏P2/P3及跨run ID覆盖。每次自动独占新短attempt目录，复跑不覆盖旧证据。

全套 `python -X utf8 -B -m unittest discover -s tests -v`；技能结构按skill-creator quick_validate.py检查。网络/真实付费不进默认测试；不加新日常CI或逐小节点人审。

M3：独立offline E2E与交接。真实audit CLI→builder→既有capture→本地fake native child，child打印实际消费request SHA与非秘密env，证明记录与消费相符。合成资料与预埋错单位/错period/错actor/缺步骤/错口径等缺陷；四不同agent分批实读，expert issue→root→PWF映射，对照漏检完善检查点。平台不支持多agent时如实留此大节点给MAIN复核，不一agent换名造证据；不能以此称真实公司研究完成。

owned TEMP初始/结束比较恢复，0外部provider/model/费用，不完整备份原库。capture测试用假的公司原件和native响应，所有产物明确synthetic，不冒充真实数据。

## 6. 完成与交接

正常commit；audit无remote即 no_remote，禁止新增remote/no-verify。不自行同步.agents/.claude/.codex；列精确变更runtime闭包候选，由MAIN定点同步并集成测试。

交HANDOFF.md/JSON、PWF3、actual RED/GREEN/E2E argv/exit/log、helper样例、既有W11兼容、测试恢复、保留旧reports、0费用、仍需真实研究的检查。共同格式见总卡。工程通过不签买方质量；公司池loop与原三家/新三家仍归MAIN原计划。
