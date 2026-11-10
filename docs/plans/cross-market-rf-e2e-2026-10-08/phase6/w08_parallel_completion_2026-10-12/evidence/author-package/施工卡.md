# W08-CWP-G2-REPLAY：G2摘要—公开读取—RF消费的可复现离线联调包

## 可以现在独立启动

- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/w08/cwp-g2-replay`（已准备，不是原主仓）
- 所属项目：`company-wiki`；固定基线：`122bbe3ba142979a2e478f886eb25de76edf2e00`
- 分支：`codex/w08-cwp-g2-replay`；PWF：`.planning/w08-cwp-g2-replay/`
- 先读本卡、同目录HANDOFF_CONTRACT.md与INPUTS.json；不取消稀疏checkout，不拉入旧大体积.planning/assurance/output。
- 本包预算：外网provider/LLM调用0；不要读取真实凭证或恢复暂停母目标。无需等待另外两个W08包。

## 唯一可写集

- `tools/narrative_g2_replay/**`
- `tests/unit/test_w08_narrative_g2_replay.py`
- `tests/fixtures/w08_narrative_g2/**`
- `docs/handoffs/w08-cwp-g2-replay/**`
- `.planning/w08-cwp-g2-replay/**`

未列入写集均只读，包括旧断言/初始input/主线/安装及其他包。ROOT专属母PWF、W04 core、G2真实付费、主线/安装/CI。

## 当前上下文与排他边界

ROOT正在修W04核心selector的18既有边界FAIL；src/scripts/旧tests归ROOT，此包**只写新工具、新测试、新小fixture**。现在能开发联调框架与冻结基线；不等W04，不把当前已知失败改成期望或最终质量通过。交工后ROOT用已修W04重跑同CaseSpec、再实际配置LLM的G2。无需等RF/Audit新包。

已有tools/g2_acquisition_chain_e2e.py只覆盖采集；本包不重写它/FF矩阵。参考tests/integration/test_narrative_batch_cli_e2e.py、test_narrative_generation_reuse.py、test_narrative_batch_cross_run_e2e.py、test_narrative_runtime_e2e.py与tests/support/narrative_batch_fixtures.py；已有有限AUTO Store/lease/generation/outbox/子进程Worker就是唯一运行机制。不得再搭任务库/摘要引擎。

## 实施细则

1. A固定真实公开命令和native DTO：当前source_catalog CLI、finite narrative batch CLI、narrative read/rationale、RF scripts/company_wiki_narrative_reader.py与narrative_source_preparation.py。先逐个--help、读原integration fixture确认参数，不按记忆造CLI。记录module实际路径/固定code SHA；源码输入是本工区和input/runtime/rf固定快照，不读canonical WIP。
2. 建最小一组公司fixture；内容明确synthetic、业务事实和表格/套话对照。类型覆盖年报、半年报、季报、招股、增发/可转债、IR、原语言TXT电话会。可把增发/可转债合为同一CaseSpec组但各自typed请求要实跑。PDF/HTML/TXT由真实现有parser处理；不把所有类型改成txt冒签PDF。正文小到足够检验来源→span→summary绑定，不声称真实召回率。
3. 通过实际canonical import/scan或当前公共source接口登记，仅生成隔离catalog/AUTO/配置/companies。不能手填已验SourceRef、直接写DB假装公共入库成功。目录路径仅在storage/bootstrap处理，消费者使用SourceRef/公开reader。
4. 用现有loopback model fixture/配置式HTTP模拟模型边界；真实finite worker/摘要选择/verify/publish/read链必须运行。不mock整层；stub只回确定性原语言draft。请求不带真实key，环境最小白名单，禁止公网，translation calls=0。此节点不验证供应商模型质量。
5. CaseSpec至少：业务内容可定位并实际进入summary；财务纯表格/格式套话无有价值经营信息时明确skip/无summary；招股/融资document_kind保持；TXT原文SHA/语言不变且没有PDF转换；低质量/错误locator/坏summary证据不算verified。
6. 真实第二run复用：相同版本/spec没有重复model POST，仍fresh公开read/locator验真；换有效source版本或选取策略应失效，不能缓存复用错版本。用少量现有场景，不在每份文档重复全41采集矩阵。
7. 真实RF只读消费固定代码快照，使用公开narrative reader/source preparation入口；只验证有效证据读入、缺口/语言/period保留，不建正式预测、不写RF/StockWiki、不编economic claim。明确read成功、draft有无支持、是否真实model调用三个不同事实。
8. 既有W04已知失败要按case/status/root_cause/真实复现记录；产品不能修时交PARTIAL。工具oracle要能拒绝空case、删必需组、自报PASS无原始receipt、坏SHA/locator、第二run有新POST、未恢复scratch。expected独立固定，不根据输出重写。

## 测试与公开交付入口

B集中：python -B -m pytest -q tests/unit/test_w08_narrative_g2_replay.py。先oracle行为RED，再实现。只mock工具错误边界；不每个case跑全仓。
C实现公开python -B tools/narrative_g2_replay/run.py --rf-project ABS_FIXED --owned-root ABS_NEW --out-root ABS_NEW，参数/README一次定义并实际启动。同批次至少两种格式和上述类型typed矩阵，第二run零模型POST，实际RF消费与失败恢复；batch采用单一绝对deadline，建议180秒、单子命令30秒，超限真实PARTIAL/NOT_RUN。不用提时限掩盖重复初始化；重型E2E手动大节点，不改CI/hooks。

产物schema=narrative-g2-replay/1：scope/code_binding/case_specs/cases及request/result/关键artifact SHA/locator/actual model calls、原始与派生字节、cleanup/remaining。supplier_fixture=true、llm_semantic_quality=not_evaluated、source_truth_verified仅说明本地实际原件验证范围，不能把synthetic身份等同真实公司。原始报告一份压缩小bundle＋摘要（≤8MiB），临时派生和自建原件恢复成原样；不复制生产数据湖。报告不可用out目录已存在文件覆盖。

ROOT收后提供--rf-project指向当前已验固定RF，以及已修CWP再验；若需profile配置或core修复，列接口建议不越界。后续真实MiMo/DeepSeek/MiniMax配置调用、累计预算、真实公司G2/G4/G5由ROOT执行。本包0收费调用，不修改production config、不同步安装、不原地rebase ROOT。

## 交工

按本地HANDOFF_CONTRACT.md正常commit并STOP；交给ROOT卡号、实际branch/HEAD和handoff绝对路径。允许如实PARTIAL，不以只测wrapper冒签原生E2E。
