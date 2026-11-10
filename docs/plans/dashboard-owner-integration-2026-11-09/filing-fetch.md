# Filing Fetch 实施单

工作目录为 `C:/Users/郑曾波/Projects/filing-fetch`。写域为 FF 的请求适配、公开 job CLI、FF 部署合同及测试。来源目录、CWP 配置、StockWiki 及 RF 通过公开接口接入。归属和批次见 [总计划](task_plan.md)。

## FF-JOB · ff-job/1 并线状态已核销

- `origin/main` 当前为 `f65e6ca75fbce0616e65870f0aea78b793ef883c`，已包含 `ff-job/1` 公开 CLI、作业存储/runner、协议和测试；与本地历史候选比较，远端已有同一 `scripts/ff_job.py` 入口及更新后的周边实现与回归。P2 并线无需再 cherry-pick 旧候选。
- FF 本地 `main` 已对齐 `origin/main`。原七提交候选完整保留在 `codex/ff-job-facade-01`（HEAD `154c292cb25293afd090aec4ef8859c2bb2b150d`），其中的交接与独审记录可用于追溯；它是归档候选，不是待发布主线。
- 该候选的原独审曾记录一个开放 P3（F-08）；当前主线代码比候选更新，不能把旧审查当作当前版本的审查结论。若 Dashboard 后续需要核对残余窗口，应以当前 FF `main` 为对象重测。
- 并线后快门：P2 精确候选 quality workflow `42746994685` 成功，push hook 11 项通过；本轮没有确认此次 main 对齐后的完整远端 CI 新运行。

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

## FF P2 · 跨市场请求合同验收（2026-11-10 更新）

- FF 把用户选定的挂牌市场、issuer-link、期次、文种及 `as-of` 传给 CWP；CWP 回来的原件来源市场仍由已验 `SourceRef` 决定，不会被请求挂牌市场覆盖。issuer 范围下有多个目标挂牌时保留歧义，不按 ticker/name 自选；CWP 没有经验证关系时具名拒绝。
- 独立审查通过，无阻断项。跨市场定向套件 11 项和 M3 兼容回归 21 项通过，Ruff、mypy public contracts、host-assumption guard 与 `git diff --check` 通过。真实端到端还从 `US:BABA`、`US:BILI` 身份请求 `source_market=HK` 的 FY2025 年报；请求使用来源市场原生表单 `FY`，成功取得 `HK:09988` 与 `HK:09626` 原件，并由 CWP Reader 实读验证完整 SHA。相同请求二次执行均由 CWP 复用，0 download、0 HTTP/provider 启动。测试回执见总计划 `validation/p2_cross_market_e2e_receipt.json`。
- 提交 `f65e6ca75fbce0616e65870f0aea78b793ef883c` 已从 `origin/main` 的 `7d8392eb98c50a6d6d27d06d9d7fabee913fe484` 普通快进推送到 `origin/main`；远端候选分支保留为同一 SHA。合并时 FF push fast-gate 11 项通过。FF 完整本地套件仍有 8 项已在精确基线 `58627a66e6c9603f836aaea20b6924a7dd8aa14d` 复现的既有失败，不归因于本次 P2；精确 P2 候选的 GitHub `quality` workflow [42746994685](https://github.com/zhengcb81/filing-fetch/actions/runs/42746994685) 已完成并成功。主线发布后再次运行的本地 hook 仍显示完整 CI pending，故不据此宣称刚触发的 main run 已通过。
- FF 没有改 CWP 数据或代码。CWP owner 已通过 SEC 20-F 原件为这两个真实样本登记有 SHA 来源绑定的关系；FF 只消费该公开关系，不自行推断或写入身份。对未证明的关系和含糊 issuer scope，FF 保留 CWP 给出的 incomplete/ambiguous 结果。P2 的 supported-path 真实数据验收已完成；全市场历史关系数据覆盖不是本阶段的隐含承诺。
