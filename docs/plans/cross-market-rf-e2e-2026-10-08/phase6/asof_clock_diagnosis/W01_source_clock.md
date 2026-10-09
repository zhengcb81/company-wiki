# W01：RF 共用 source/capture/claim clock 修复卡

状态：READY FOR OWNER TDD；本诊断 agent 未施工、未运行新增测试。

## 输入与责任

- 根因：RC-ASOF-CLOCK-01；同一 RF owner 独占实施，共享 producer 扩展由 MAIN 串行固定接口。
- 实际 RED：fixed71 CWP979792e0 / RFe688b0a2，71 项144.37秒 FAIL，三市场 RF→FF reuse BLOCKED，同一 exact error；证据 `fixed71_evidence.json`。
- 固定 study as-of：2026-10-08；实际 now/read 可为 Oct9。不得通过换日期、篡改 captured_at/verified_date、删未来信息门修测试。
- 诊断时 CWP=a40eb065，RF=e688b0a2；施工前 owner 读取实际最新 HEAD/AGENTS/已有 owner 状态后建隔离 worktree，不以诊断 HEAD 冻结最终执行版本。
- 非目标：HK 旧同段正反研究角色、无 OCR PPTX fixture、下载/模型、更换 cohort、全库 source staging、生产 reconcile。本卡不借新 source admission 权限处理 clock。

允许 owner 修改 RF：新纯共用 source clock helper；下面 source/capture/evidence/narrative 责任文件及直接测试；现行 clock 文档、版本/兼容记录和安装 manifest 必需同步。禁止写 CWP 共享代码/配置、FF/Dayu、原件/生产 DB、别的 owner 工作树。本诊断目录由诊断 agent 写完即交接，主 PWF 仍 MAIN 独占。

## 现行文件与最小实施顺序

1. **先 RED**：在 `tests/test_company_wiki_source_v2.py` 的 `test_unknown_retrieval_preserved_and_actual_read_captured` 旁增加 known publication + read 次日的反例。该旧 test 的 read_at 和 as_of 都是 Sep27，未覆盖 next-day。对 reader、capture、claim 和 auto narrative claim 各写一个责任反例，不能只测新 helper。
2. **统一资格**：`scripts/contracts/source_clock.py` 汇总 `published_date <= as_of` / optional exact-version prior availability，返回一次 source eligibility；valid dates/SHA/period 保持。API 见 INTERFACE，新增用例见 tdd_plan。
3. **public raw 读取和构造**：`scripts/company_wiki_source_reader_v2.py:_validate_manifest_period`，`scripts/company_wiki_source_v2.py:_validate_manifest_dates/build_revenue_source_record_from_verified_read`。原始 retrieved_at 保留；新 capture/accessed_date 总是实际 verified read 日期；不再拿 original retrieval 当本次访问事件。source_preparation._prepare_source_ref_v2 继续走当前共用路径，不按市场加特判，不增加 provider 调用。byte SHA/size、exact SourceRef、candidate/manifest identity/period/URL 校验完整保留。
4. **formal engine**：`scripts/contracts/evidence.py:validate_source_capture` 把信息资格交同一 helper，capture 部分检查真实事件和 receipt，不另加 captured<=as_of。`scripts/contracts/document.py:validate_sources/validate_evidence_claims` 从同一 source eligibility 验证 claim，真实 verified_date 可以晚于 as_of；仍保留 future source、claim/source SHA 和 capture receipt links。collect-mode 与 fail-fast 均覆盖。
5. **actual narrative builders**：`scripts/research/input_evidence.py:_bind_narrative_span` 保留真实 read，使用共用资格；`scripts/source_narrative_context.py:_claim/consume_narrative_input` 新 claim 用真实 context read/check 日期，禁止写 verified_date=as_of。不重写现有旧 input claims；模板 placeholders 仍明确未验证，不能称 fresh evidence。narrative context 先读一次，所有 selected claim 共用已有 context，不增加逐 span 重读/OCR/模型。
6. **显式 legacy 路径**：`scripts/company_wiki_source.py:build_revenue_source_record` 也是未来门之一。按既有显式 legacy compatibility 用同一 known publication 语义；不扩大 deprecated path 存储访问，也不让旧路径成为新的默认入口。旧 artifact 按 pinned runtime 保持旧语义/字节。
7. **unknown proof**：现有 producer 公共 manifest/receipt 没字段，engine 要求 non-null publication；先具名 gap。若 MAIN 将 `source-availability-evidence/1` 纳入本包验收，须先固定 public producer 返回协议和可靠 proof 的实际解析，再由 RF 接一处；不得接收 research caller 的裸自报 proof。CWP producer 改动由 MAIN 独占，RF owner 不改邻仓。transport strict fields 只按明确版本扩展；SourceRef identity 不变，原 pub 保持 null。没有生产 proof 的 unknown source 保持 BLOCKED/gap，这不能用 fixture 包装为真实成功。
8. **版本/兼容**：记录本次 engine/validator 语义变更，更新 CHANGELOG 和 schema_compatibility 的 documented emit pairs，按实际选择版本同步当前安装副本。旧 3.7/3.8 frozen input/outputs/receipt/snapshot bytes 和 ID 不变；旧 snapshot 需要 pinned runtime 时明确保留。不要全量 rebaseline golden 或替写旧 receipt。

unknown publication 对通信窗口/target-publication consumers 的额外注意：`research/communication_scope.py` 与 `target_measurement.py` 目前直接消费 published_date。availability 的上界不能被当作精确 publication 代入窗口起止。缺精确 date 的窗口/target 维度保持具名 coverage gap；这些维度只处理本身可证事实。先查 callers，按需做有界适配，不把这项来源资格修复变成全仓研究重写。

CWP 精确依赖见 INTERFACE 的“公共传输放置”与“CWP producer 文件/符号”两节：默认 receipt2.1不动；显式2.2扩展仅顶层 `availability_evidence`；新 proof 模块加 source_reader_cli.main 接线。SourceVersionReader.source_reader.py/qualification 与 legacy intake/facts/eligibility owner 的必要变更由 MAIN 串行处理，RF owner 不写共享文件。

## 先写的测试

集中职责文件：

- RF `tests/test_company_wiki_source_v2.py`、`test_company_wiki_source_reader_v2.py`、`test_source_preparation.py`、`test_source_ref_v2_three_repo_e2e.py`。
- 用 CodeGraph 查现行 capture/claim/narrative/compatibility tests，再给其实际对应文件添加反例；本卡不假造不存在测试路径。新 `test_source_clock.py` 可集中 pure policy 组合，不能代替边界反例。
- CWP 已有 `tests/unit/test_source_qualification.py` 和 `tests/integration/test_current_consumer_asof_contract.py`（early/late download 与 future publication）提供 producer publication 语义；后者只验 narrative read adapter，未覆盖正式 RF source/capture/claim engine。需要一次 formal 链补齐，由 MAIN 批准具体 shared fixture owner。
- frozen runtime：已有 `test_schema_compatibility.py`/golden behavior lock；新增只针对 clock semantics 的 compatibility 证据，未相关公式/结果仍一致。

最低矩阵见 tdd_plan.json：已知发表<=asof、null/original晚采集、current read/verify晚于asof合法；future publication/future actual仍拒；未知且无可靠proof拒；未知+同SHA早proof可用但pub仍null（依赖公共producer）；unknown晚proof和跨SHA旧proof拒；具名日期冲突；新auto claim真实日期；旧 frozen/runtime 不漂移；另一个公司/格式的泛化。

## 运行与大节点

所有 RED/GREEN 先用隔离 fixture、固定 read_at/执行事件，不触碰生产、不启动 provider/LLM、不下载，不用 wallclock 变造源信息日。命令按现行 pytest 配置选直接责任文件，记录每项 actual outcome；新用例此处均 NOT_RUN。

责任测试绿后，由 MAIN 选择一次固定 scope/同三市场的真实 RF→FF→CWP reuse + formal capture/claim 跨日链（0download）；实际本次 read 日期不能 monkeypatch 成 as_of。future control 是明确真实元数据或隔离 fixture，不计作 fresh 公司成功。最后必要的大节点再跑 fixed71一次，保留 known HK/PPTX独立结果，不因本包结束重复 optional全套。

本包验收不是“CLI 成功”而已：read/source trace 真实日期与 SHA、capture/access 日期同本次 read、新 claim verified date 同实际 check，所有未来/未知/跨版本反例拒绝正确；旧 snapshots 未改、pinned runtime可用。实际 full71/fresh research 尚未完成，不在本卡宣称修复成功。

## 交接要求

正常 scoped commit，不抢共享文件。HANDOFF / handoff.json 写 owner 实际 HEAD/变更文件/API版本、真实 RED/GREEN/大节点、public producer proof 支持情况、旧 runtime兼容、安装副本同步、费用/清理与未解决项。若 unknown+proof producer 尚未提供，明确剩余依赖和安全 gap；不得把 known-publication 修复称作所有 unknown dates 已解决。
