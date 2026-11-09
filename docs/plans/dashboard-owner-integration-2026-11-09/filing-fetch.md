# Filing Fetch 实施单

工作目录为 `C:/Users/郑曾波/Projects/filing-fetch`。写域为 FF 的请求适配、公开 job CLI、FF 部署合同及测试。来源目录、CWP 配置、StockWiki 及 RF 通过公开接口接入。归属和批次见 [总计划](task_plan.md)。

## FF-JOB · 发布已接受的 ff-job/1

1. 重核远端 `main`。当前已核远端 `bf7e1dab`，本地 `154c292c` 已有 FF 作业代码和交接，包含 `a34f60e` 到 `154c292` 七项提交。核实这段的写域、父链、原独审证据和当前候选代码等同。采用窄范围正常发布，保留原工作树的其他内容。
2. 用交付的定向作业测试和 FF v2 组合回归。覆盖 submit/status、意图、冲突/幂等、实际成本状态、process 失联后的只读 reconcile。验证新版 FF 仍接受旧调用请求。按本仓 CI 发布，记录完整 SHA 与 `ff-job/1` 公开合同。

## FF-1 · 绑定明确挂牌和已验来源

1. 第一轮使用实际部署 cache-only 诊断，重放 E12 US+全名，再用现有 v2 `company_query=BABA`、`market=US`、`form_type=20-F`、`mode=exact` 与请求真实财年/as-of；港股用 `09988+HK` 和适用披露文种。FF 消费 CWP 明确解析的挂牌，保留 named 歧义。Dashboard 如已有挂牌 ID，按现有 scope 组装精确请求。需要候选选择 UI 时优先用公开身份查询，仍需扩展时才版本化。
2. 同一个部署重放 RF 六路。区分身份歧义、市场绑定、正确期次确实缺档、来源补登不完整和 US provider 失败。对照 CWP 公开 `query/ensure`，避免用 FF 请求 market 填原件的 null。已证明的事实丢失交 CWP 修投影。
3. 在 `scripts/ff_source_candidate.py` 用 TDD 统一缺键和显式 null 的证据语义。现实现缺键跳过、null 判 mismatch。每个 query/ensure 测真实匹配、证据未知、明确冲突和 wrong-period。采用同一来源资格规则与具名状态，只有来源 owner 给出的充分证明可进入复用/后续工作。保持 SourceRef 的 SHA/身份/期次/as-of 合同。
4. FF 对外返回真实失败阶段。US 环境问题核对实际解释器的依赖和启用 provider，使用 FF/CWP 现有版本化诊断区分未启动、启动零 HTTP、计量未知和真实获取。依赖修复留在拥有它的项目。一个真实同条件控制例及另一个双上市通过后，交 RF 合格 `found + capture_ready` 或具名缺口。

## FF-2 · 缺档下载覆盖

E12 已证实 CLI 等价链的复用与具名拒绝。用独立临时 CWP 根、FF 配置和一个受控供应商先验真实公开链。缺档允许一次获取，CWP 入库验 SHA，FF status/成本与实际使用一致，幂等重复和第二次复用零额外获取。加入拒绝意图、超限/失败清理、重启和未知结果只读 reconcile。真实下载留给首个明确缺档业务请求，按现有限额执行并记录实际付费，可为零。标明实件测试范围和目录恢复，未发生记 NOT_RUN。

## FF-3 · 复用现有动作和意图

按 owner `allowed_actions` 渲染。queued 可 cancel，running 当前无动作，合格零支出失败/取消可 retry，unknown 支持只读 reconcile。保留 resume 的 named 不支持。filings 不支持 refresh，statements 支持。已有 UI 动态消费和合同断言，验真实发布一致即可。未来有真正暂停点时单独做兼容扩展。

## FF-4 · 部署与恢复配置

1. FF 发布记录确认实际 Python、FF 代码 SHA、`config/company_wiki.json` connector 版本、CWP 实例标识及作业目录。配置属于各自 owner。Dashboard 的 `DASHBOARD_FF_JOBS_{PYTHON,ROOT,CONFIG,DIR}` 与短请求配置分开。已有默认部署登记可复用。
2. 给 Dashboard D00 一个窄适配器修复。其 `backend/dashboard/adapters/m8_owner_jobs/ff_job.py` 在 run 传配置，在 act(reconcile) 漏传。FF 公共 reconcile 已接收 `--config`。在 Dashboard 仓用两个隔离 connector/store 先写失败用例，断言运行和只读核对同一配置及来源实例，再修转发。FF 保持自己的公开接口。
3. 在最终组合用实际 Dashboard 适配器调用 FF public CLI，验证默认/非默认根、显式不可用、复用、恢复和零重复开销。CLI 单独运行的记录按实际范围引用。

## FF P2 · 跨市场请求合同验收（2026-11-09）

- FF 现在把用户选定的挂牌市场、issuer-link、期次、文种及 `as-of` 分别传给 CWP；CWP 返回的原件来源市场仍以已验 `SourceRef` 为准，不能被请求挂牌市场覆盖。绑定不完整或有冲突时使用具名拒绝，正确跨市场发行人可复用。
- 36 项定向测试、Ruff、`git diff --check` 和独立审查通过。真实 HKEX 阿里 FY2025、B 站 FY2022 年报在隔离 CWP 快照中从 US 挂牌查询命中同一来源 SHA，且没有启动 provider 或下载。错误市场、security、period、form 和 as-of 负例均拒绝；细节见总计划 `validation/p2_cross_market_e2e_receipt.json`。
- FF 候选遵守 owner 写域，没有改 CWP 身份/来源数据。CWP 生产快照缺 LEI/ISIN 的上游事实问题仍开放，需等通用标识 feed 接通后在实际部署复验；FF 不得用 ticker/name 猜发行人或伪造 source market。
- 当前候选尚未提交；提交后在此记录确切 release SHA、远端分支及 CI 状态。
