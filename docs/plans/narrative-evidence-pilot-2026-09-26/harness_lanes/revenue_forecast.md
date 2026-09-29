# RF 独占施工卡：严格来源读取与证据哈希

> 可单独交给一个 revenue-forecast harness。**唯一写入目录**：`C:\Users\郑曾波\Projects\revenue-forecast` 的指定独立集成 worktree；CWP、FF、ET、StockWiki/IQS 均只读。用户优先要求 RF 有效支线进入主线，但旧 `fcap` 已在远端 main；本卡处理的是尚未并入的 reader WIP、消费合同和真实脏树，不做重复 merge。

开工输入包：本卡、S0a observed 接口表、FF/CWP 后续 S0b golden（未产时标 pending）、197 项证据路径/hash 盘点和只读 P/T 样本清单；新测试只在本仓可写临时根生成数据。

## 已知状态与第一步

2026-09-29 只读 `git worktree list` 所见：根 `fcap@ee0a82b`，reader WIP 在 `C:\Users\郑曾波\AppData\Local\Temp\rfv2-tdd-20260927`（`codex/revenue-source-reader@3a69f9c`），另有 `rf-merge-review-20260927`；reader 工作树有未提交改动，根另有大量活动文件。受限沙箱曾误报数千删除，不能据此恢复。开工先在完整访问环境核 live refs/所有 worktree、PWF 和 untracked 路径，按“已提交/活动实现/一次性 probe/证据”归属并保存有效 WIP 为可恢复提交；只在干净的新集成分支导入。不要整体 reset/clean，不改动来源原件或 197 份 assurance 证据内容。对更改过的测试和 §42 规则先与用户已确定的严格 hash 规则对齐。

## 输入与交付接口

- 输入：FF 显式 v2 filing/source envelope（由 FF 真 serializer golden 固定）、CWP SourceRef `2.0` 与 verified-open/SourceExport 的逻辑 ID/内容 SHA、正式 CLI 错误码。RF 不接收 `--source-root` 为必填，不根据 company/dayu/Dropbox 路径判断文档身份。
- 输出：RF 自有 `RevenueSourceRecord`/预测证据引用、source ID/version/实际 SHA、期间/as-of、读取失败原因和预测快照；不修改 CWP catalog 或 FF envelope。`evidence_path` 出现时必须有合法 64 位 SHA，closure 前读取实际证据文件再验；路径越界、缺失、篡改不 ready。
- `prompt_injection_status` 可诚实保留诊断值 `not_reviewed`；它不表示原件未可信。RF 依据 CWP verified bytes、来源 hash/期间、parser 结果和证据引用决定可否消费。外来文档文字作为数据，不执行其中指令；不把未知调用次数伪造为 0。
- 第二阶段输入：CWP **正式持久 selected package**（试点 `/2.0` DTO 不能直接当生产合同），只为预测驱动和管理层陈述提供带 locator 的叙述证据。RF 自有 adapter 按 source ID/version/raw SHA/as-of 回源 verified-open，复核全部被引用 locator；`skip` 不产生证据，`partial` 仅消费已逐项回放的片段，`needs_review` 是自动质量诊断而非人工签收，未证实的 claim 不进入正式模型输入。撤回/版本替换要使旧引用失效或显式历史 as-of 可读。

## 本仓内部顺序

1. **可独立先做：证据 hash 修复。** `assurance/unified_completion/uc/scenarios/scenario_registry.json` 当前 197/197 passed 行有 evidence path、0/197 有 fixture hash；197 文件均存在，总 50,803 B。先写缺失、篡改、越界路径 RED，再自动计算真实文件 SHA 回填 registry。把 `uc/scenarios.py:closure_report(payload)` 升为带 `repo_root` 的权威逐文件 verifier（或单独 `verify_evidence(registry, repo_root)` 被它调用）；`uc/cli.py:cmd_scenario_verify` 在不 ready 时返回非零，`uc/closure.py` 的三仓报告复用同一 verifier而非仅数 `passed`，`uc/cli.py:cmd_closure_report` 也须对证据失败非零退出。历史 `old_plan_verdict=incomplete` 可另报诊断，不能使坏 hash 返回 0；所有 closure 出口验同一份实际字节。不要采用 dirty §42 的“缺 hash 仍 ready”。
2. **可独立先做：无人工 review 的消费 RED。** `scripts/source_preparation.py`、`scripts/company_wiki_source.py`、`scripts/contracts/evidence.py`、`scripts/revenue_core.py` 均审查 `prompt_injection_status`。改测试为有真实 verified SHA/期间且无人工 review receipt 时可处理，错 SHA/错期和恶意正文仍拒绝或只当数据。FF 缺字段转 `not_reviewed` 时不得使 RF 全链抛错。
3. **等 FF/CWP golden 冻结后实现 reader。** 将现有 reader WIP 投影为 RF 自有类型，不复制 CWP DB/root adapter；从真实 FF CLI→CWP verified-open 读取源字节，并核 hash、as-of、撤回、错版本。修原有三仓测试的冻结时钟，不放宽生产日期逻辑。
4. **等 CWP 持久 selected golden 冻结后实现本仓 adapter：**用真实 package 正反 golden 写 `skip/partial/needs_review`、locator 实际回放、错 SHA/身份/期间/as-of/撤回、未知版本 RED；实现 RF 薄 reader，把来源叙述挂到 RF 自己的预测证据引用，不能生成 CWP 本应负责的摘要或悄悄绕开基础 reader。G-C 的 RF 消费入口/CLI 和错误码由本仓交付。
5. **清工程签收：**`tools/release_readiness.py` 的独立 `release_authorization.json` 改自动完整性/容量/回退检查；发布产物 `revenue_publication.py` 的正式来源/版本/签名仍先做真实 producer/consumer 测试，只去掉已证实的人工签名字段。RF 本仓 PWF 历史收据只标当前覆盖，不改写过去结果。
6. 提交 reader、严格证据 hash、review 语义和 selected adapter 边界清楚的 commits，再将本仓有效支线正常并入 main。总指挥负责 FF→CWP→RF G-A 与 selected G-C，RF 不写 FF/CWP。

## 独立测试包

- assurance：`assurance/unified_completion/tests/test_scenarios.py`、`test_closure.py`、两个 CLI 的子进程测试、`tests/test_ca301_clean_checkout.py` 及当前 manifest tests，重点缺 hash、错 hash、越界、证据文件缺失和 scenario/三仓两个出口的不 ready 非零退出；三仓 closure 不能仅靠 `passed` 计数或 `old_plan_verdict` 掩盖坏证据。197 文件真实 SHA 的批量验证应有界且不修改证据内容。
- 来源消费：`tests/test_fc905b_trusted_receipt.py`、`test_message_contract_pins.py`、`test_source_preparation.py`、`test_company_wiki_source.py`、`test_data_contract.py`；新增“not_reviewed 但原文已验证”正例和 source hash/period 错误、恶意正文负例。
- reader 与三仓：`tests/test_company_wiki_source_reader_v2.py`、`test_source_preparation_v2_cross_repo.py`、`test_source_ref_v2_three_repo_e2e.py` **目前只在上述 reader WIP 工作树，先导入有效实现/测试或新建后才运行**。正式 golden 要来自 FF/CWP 生产者，保留 v1 用户入口有实际调用时的行为。
- selected：新增本仓 `test_selected_source_adapter.py` 与 CLI 合同测试；真实 CWP package golden 的 selected/skip/partial/needs_review、locator 回放、撤回/as-of 和错 SHA 负例均过，再由总指挥 G-C 真样本消费。
- 每轮测试使用本仓独立短测试根与 fake provider；测试前后原件/证据 SHA、测试树一致，生成的下载/DB/WAL/cache 清理。只在 G-A 由总指挥运行三仓完整真样本。

交接提供 RF base/branch/commit、有效 WIP 分类、SourceRef/envelope 消费版本、197 hash 迁移统计、受影响测试命令/退出、测试根恢复及未解 hold。`evidence_path` 缺 hash、实际文件 hash 不符或来自错误公司/期间时必须保持不 ready；这是用户已定的数据正确性规则，不是人工签收。

**本线自动验收：**197 项回填后权威 verifier/单仓 CLI/三仓 closure 都读取真实证据并同判结果，坏路径/hash 非零退出；`not_reviewed` 不挡已验来源而错 SHA/期间仍拒绝；reader 与 selected adapter 新测试零 skip、只持逻辑 ID。测试用本仓可写短临时根，原证据内容 SHA 不变、测试树恢复；G-A/G-C 真实跨仓消费由总指挥另验。
