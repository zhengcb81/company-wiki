# 事实基线与反馈校正

2026-11-09 读取 Dashboard `17da52410c4f418c6b31de6cbf59fd7be94d090a` 的三份 owner 改进文档，并核对各仓 Git 对象、相关公开入口及归档回执。

| 仓库 | 已查询的远端主线 | 与本轮有关的本地证据 |
|---|---|---|
| company-wiki | `master 5e4bc087b50fca50342fceb23923d31de1d0809b` | `62602102ae5ab9a6bba54879756b800854c941a1` 有 Dashboard owner 接口。与远端在 `source_reader.py` 有实际三方冲突。基础 G-CWP-01 三个提交与主线组合 15 项通过 |
| filing-fetch | `main bf7e1dab4aebcfe671554a4fda59705eb7fe1765` | 本地 `154c292cb25293afd090aec4ef8859c2bb2b150d` 含七个已提交的 ff-job 代码与记录。部署用的具体执行根另需核对 |
| revenue-forecast | `main 90c562ac6e305c4c5f6fba5a439851b20e0490a9` | 已接收 RF Job CLI 代码候选 `e4b38459`、交接 `d347c4ab`。主线无这些 Job/Catalog 入口，候选与主线差异混入其他开发，需按功能闭包移植 |
| investment-dashboard | 本轮只核对本地 `main 17da5241` | 仅作为独立消费侧和反馈证据。D00 管理其代码、配置和总 PWF |

## 阿里巴巴的两组证据

E12 的 FY2025 20-F 作业用了 `market=US` 和公司全名。结果为 fuzzy 待选，现有证据只证明该请求没得到唯一合格绑定。先查实际部署的候选和匹配依据，并复验明确挂牌 `US+BABA` 与 `HK+09988`。保存已证实的合法挂牌关系。证据位置为 Dashboard `.test-runs/e12-ff/run_drill.py` 和 `E12-FF-ACCEPTANCE.md`。

RF 的六路线归档在 `0993abb305dc86a2197b8b2aee10a3b8d8339949:.planning/rf-input-prep-01/evidence/alibaba-routes.json`，同时保留各 route 的请求和 stderr。六条合计零下载。

| 路线 | 已观察 | 下一步核对 |
|---|---|---|
| 1 HK FY2026 reuse | source query market mismatch | 同一部署的 CWP query 与 FF 校验，区分已验证原件市场和请求 scope |
| 2 HK FY2026 fetch-if-missing | operation market mismatch | CWP ensure 返回值与 FF v2 绑定。旧记录声称直跑 CWP 复用，原 stdout 缺失，需重取真实响应 |
| 3 HK FY2025 reuse | local_metadata_gap | 已观察的 FY2026 原件不能冒充 FY2025。核对正确期间原件或明确缺档 |
| 5/6 HK latest-as-of reuse/fetch | local_metadata_incomplete，provider 未启动 | 核对发布日、as-of、期次、官方来源身份和已登记事实 |
| 4 US FY2026 fetch | provider_failed，started=true、HTTP 0 | 区分部署环境缺 SDK、适配器能力和请求本身；用实际部署无网络检查和受控 provider 复验 |

三种市场字段分开观察。挂牌市场说明投资主体的挂牌，查询市场表达请求范围，来源市场来自原件及其已验证来源证据。CWP 当前 resolver 对有独立发行人锚的部分候选允许缺辅助市场，query/ensure 的 DTO 可投影 null。FF 的市场绑定更严格。须查清事实缺失、投影遗漏和部署不一致各发生在哪一层。

独立 CWP agent 在本地现有部署做了 cache-only 只读身份和目录探针，未调用 ensure、provider 或刷新。此部署有工作树改动，观察用于诊断。HK FY2026 精确和 latest-as-of 都可找到同一个 `e39fbf9c…`，已知 HKEX、09988、FY2026、发布日期及 capture_ready，市场字段为空。旧 acquisition 元数据缺键，当前已验证 `v2-normalized` 断言的 market 是 NULL。证据指向历史登记事实缺失。当前新件 writer 已传 market，是否仍有通用写入缺陷须由回归判定。该本地部署的 HK FY2025 和 US FY2026 请求未找到匹配；MDB FY2026 控制例存在但缺已证发布时间，capture_ready=false。所有结果按实际部署和期间分别核对。

## MDB 与作业协议

- MDB `rfjob-20261108-eb9f2a3ed336` 已 succeeded，内容提交 `0993abb305dc86a2197b8b2aee10a3b8d8339949` 有原输入、报告和冻结快照。作业内 publication 与可信目录入册是两个状态。旧调用 `list-reports` 的 `owner_root_missing` 也提示部署根不一致。
- 反馈 RF-2 建议的 `import-research-attempt` 针对失败研究尝试，当前实现要求 `failed/source_preparation`，回执报告列表为空。成功报告适用 `import-research-publication` 的合同。现有 MDB 作业包缺传统 B34 recorder/ledger 等原始证据的记录，须先实读验证现有作业原生 publication 能证明哪些必要事实。
- FF E12 的三个证据是 CLI 等价链。MDB FY2025 本地复用、MDB FY2024 来源待选、阿里身份待选，均为 0.00。实际 HTTP 组合和自然新下载分别留证。
- FF 作业实际按 `allowed_actions` 提供排队 cancel、合格的零支出终态 retry、unknown 的只读 reconcile。无 resume。filings 无 refresh，statements 有。部署根配置已登记，发布时复验选中的解释器、代码和 connector 配置。
- FF 当前候选绑定对缺 market 键和显式 null 走不同分支。需用来源证据统一。Dashboard 的 run 转发自定义 FF connector，act(reconcile) 当前遗漏，FF 公开命令已能接收该参数。配置缺口归 Dashboard 适配器。
- RF v1 差异以 Dashboard `handoffs/m8-executor-integrate-01/handoff.md` 及 RF facade 的实际执行为准。金额上限在原 v1 只检查配置而未证明执行，需在付费 owner 入口验证有效预算，v2 其余表达差异单独演进。

## P1 发布前独审发现的共用问题

FF 与 RF 的旧作业层都曾根据过时的 PID 文件删除锁。两个独立进程可以把对方刚获取的新锁删掉。各自 owner 使用可由操作系统在进程退出时释放的锁，在锁内重新观察并变更当前状态。RF 的活作业核对只读，恢复时复用已经验证的终态或阶段证据。

下载事件为零只说明没有观察到已提交事件。请求已派发而回执丢失时，开销及外部副作用保持未知。FF 财报和伴随电话会都要进入同一个作业的获取意图和真实证据统计。RF 有获取潜力的来源阶段在缺证据时也保留未知。保留只读核对和已证明无新增开销的安全恢复。两个 owner 分别以通用临时公司及实际进程竞态复验。

## P2 官方标识来源核对补充（2026-11-09）

- CWP 的 `OfficialSecurityMasterRefresher` 当前分别读取 CNINFO、HKEX active/inactive/security code lists、SEC ticker 与 Nasdaq listed files；代码未读取 HKEX 的 ISIN 专项清单，也未读取跨标识关系源。生产快照因而只有各市场原有的本地身份键，没有足以普遍跨市场 join 的共同键。该判断来自 owner 刷新器当前实现和实际快照，不来自测试夹具。
- HKEX 官方 [Securities Lists](https://www.hkex.com.hk/services/trading/securities/securities-lists?sc_lang=en) 列出两类可下载目录：“ISINs Assigned by HKEX”与“ISINs Assigned by Other Numbering Agencies”。这是按挂牌/证券补充 ISIN 的直接候选源。它本身不证明不同市场证券属于同一发行人，且只加入该字段不能解决现有 US CIK 到其他市场挂牌的通用关联。
- GLEIF 官方 [API 说明](https://www.gleif.org/en/lei-data/gleif-api/) 提供 LEI 数据、映射标识和按字段/名称检索；其 [ISIN-to-LEI 文件说明](https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files) 则明确每日映射目前包括参与早期 NNA 新发行的 ISIN，并把 legacy ISIN 覆盖列为长期计划。GLEIF 官方 [映射概览](https://www.gleif.org/en/lei-data/lei-mapping/) 列举 ISIN、BIC、MIC、S&P CIQ、OpenCorporates、QCC、GEM 等映射伙伴/文件，没有列出 CIK-to-LEI 文件。因此 ISIN/LEI 是通用、可审计的部分桥接，不能作为所有历史上市证券的完整覆盖承诺。
- 实施判断：不应只下载 HKEX ISIN 表、再按名称或 ticker 自动并 issuer。CWP 需要拥有一个 owner 级、可版本化的 issuer/listing 关系来源合同：自动关系只由精确类型化标识匹配生成；其他关系须绑定发行人或监管文件的 HTTPS 来源、原件 SHA、locator、证券类型/挂牌、有效期及 as-of，并保留未证实/冲突状态。关系数据可以因公司而不同，但实现逻辑必须统一，不得加公司代码/别名特判，也不得用模糊名称把母子公司或 ADR/普通股混并。FF 只消费 CWP 的公开合同及保留来源市场、期间、表单和 as-of 的结果。StockWiki 是下游 owner，只有先证明身份调用不会产生依赖环，才可考虑其公开 DTO 作为独立来源；当前不把它作为 CWP 的隐式回调。
- 下一验证节点：用官方 HKEX ISIN 文件和 GLEIF 当前映射文件只读检查阿里、B 站两组证券的实际覆盖；同时核对发行人/监管文件可否提供 CIK 与具体 HK listing 的直接关系证据。覆盖不足时明确标记 `identity_link_unavailable` 并保持 P2 开放，而不是对生产快照手写样本。随后由 CWP 写通用来源 owner 与刷新/撤销规则，FF 对公开 DTO 做合同测试，最后以实际部署 cache-only 查询验收两家公司和一个冲突负例。

## P2 收口复审补充（2026-11-09）

- CWP 与 FF 的 P2 实现及独立审查已通过。阿里与 B 站离线 E2E 使用各自真实 HKEX 年报原件、GLEIF LEI/ISIN 与 ADR 发行人证据；US 挂牌可以匹配 HK 来源原件，同时严格保留来源市场、证券代码、报告期、表单类型与 as-of。负例覆盖错误财年、表单、期次、来源证券、来源市场和发布日期。测试用的临时快照未改生产安全证券主数据；当前生产快照缺 LEI/ISIN，因此生产自动跨市场联结覆盖率仍未解决，不能宣称已全面生效。
- RF 独立审查发现 `import_rf_job` 同一 job 并发注册的竞态：文件 staging 位于目录 append 锁外，失败清理可能删除另一调用已登记的 artifact。须新增 job-id OS 文件锁，覆盖已有项检查、artifact staging、catalog append 和清理；确定性回归固定“首调用已 staging 并暂停，第二调用先到达”的时序。真实入册前先修复和复审。
- 同次独审还发现 adapter 跨进程 DTO 测试、失败清理测试、SourceExport 嵌套 schema/manifest shape 校验覆盖不足。RF 直接导入 sibling 模块私有 `_read_proof`；改为 RF 公共 adapter 后保留原消费者兼容入口。
- MDB 原始工作在 `C:/Users/郑曾波/Projects/rf-input-prep-01-wt/.planning/rf-input-prep-01/job-root/artifacts/rf_jobs/jobs/rfjob-20261108-eb9f2a3ed336` 可读取。RF 的主 owner 根已有 `artifacts/report_catalog/catalog.jsonl`；导入应通过 P2 CLI 明确指定此 canonical 根，而不是把记录写入临时 worktree。复核到 job succeeded、source 复用 0 下载、compute 与 publication 均成功。要求独立 job SHA `17ec542035cb87de4c0fa718efa745ae0db9f6c0a6623621b73646c78c994ba6`、Markdown SHA `0bae0856fd4e658b456b1808bec06da937d08c5fa76b2d8e421a76fcbba20e63`；报告登记不触发预测。冻结 snapshot 可选且未导入，既有输入、结果、报告和来源证据足以满足当前目录列表/详情用途。
- 复审前实际 CLI preflight 已核对两个来源 owner：CWP SourceExport v2 ID 为 `urn:company-wiki:source-export:sha256:1d676fe067f3867d2242247ff589b678d76e8342160544406afa7a0495eebb98`；StockWiki 当前 verified identity 与 issuer proof 将 MDB 年报 URL 精确绑定，目标实体 `ENT_41250504-734e-4460-9843-86c4e1f3851d`、挂牌 `LST_2d86780f-c98e-49cc-a214-34885c8820fa`。尚未写入目录。
- RF 独立复审当前不签收并发安全性；其新发现成为真实 MDB 入册的阻断项。现已修复为 job-id OS 文件锁，并完成 RF 定向测试、独立复审及公开 CLI 入册/读回：单一 run/attempt/report、所有 SHA 可读、重放幂等且 `forecast_executions=0`。
- RF 真实 importer 首次拒绝还暴露生产合同与测试夹具漂移：`source-preparation-result/1` 的顶层只含 `schema_version/source/filing_fetch/narrative`，成功候选状态在嵌套 `filing_fetch.status`；旧实现及 fixture 都虚构顶层 `status=source_candidate`。修复两处真实校验并把 fixture 改成生产结构，避免放松其他源身份、期次、SHA 或 issuer proof 检查。首轮修复漏改 retained-attempt validator，4 项测试及时捕获，第二轮改正后 45 项通过。
- MDB 以 RF 公开 `list-reports/get-report/get-run/get-attempt` 回读，唯一 report、run、attempt、issuer/listing、source SHA、input/result SHA 均一致，revision 固定为 `c14312b6013612f2e47774cdbd1aff58387a17dc7f073129e63bbdaa1f71be01`。入册与重放均为 `forecast_executions=0`。报告本身仍有 1 条 `partial` citation、无 locator，另有 10 条显式 `quality_gaps`；此诊断保留，不把目录登记等同于研究证据无缺。
- P2 的根因范围还剩一项生产数据缺口：当前 CWP 官方身份刷新器写入 CN 统一社会信用代码、HKEX 证券 ID、US CIK，但部署快照没有跨市场 LEI/ISIN。两个真实双上市样本的 E2E 使用可验证的 GLEIF/存托凭证公开证据构造隔离快照，证明算法与负例；它不能证明生产路由已自动得到这些 issuer links。下一步需定通用权威标识的获取/刷新 owner 和过期策略，再用真实部署只读验证，不可手填公司特例。
- RF strict canonical 检查已完成：精确 `compute_input`、`compute_result`、`job.json` 的孤立 surrogate 数均为 0；input canonical hash `6169ea8aca81638d83026153474d584ca19be38c166bb71ab0ae4e76924cde59` 与 result 中记录相同，result strict payload hash `04768c2742d663e3e7ac748c9fde8c7648cc1cd0e424e4d931e150379c038816` 与自哈希相同；完整 input raw SHA `a799977ac7ee30c6be4cbc254a03bfc872064b8d5d90f3e5609c95ac02018b2d`、result raw SHA `c0dce8c3df7e49431a351de67d15847db40a4ffd7bfa140cf378db437b017963`。无需放宽 strict UTF-8 哈希合同。MDB 主目录在入册前通过 RF 公开只读 CLI 查询为 0 条，catalog revision `a2ae0e7179f9d76b47bc81788e1501ede2da25efb6a59946748556b87c295a3d`。
- 首次真实 CLI 入册未写目录，拒绝原因是 importer 错误要求 `source-preparation-result/1` 顶层有 `status=source_candidate`。真实 DTO 顶层只有 schema、source、filing_fetch，候选状态由 `filing_fetch.status=source_candidate` 承载；人工合成 fixture 之前错误地添加了不存在的顶层状态。应以 owner 的实际公开结果形状为合同，删除虚假顶层条件并使 fixture 反映真实形状；保留 nested filing 的 `reused_existing`、零下载、annual_report/FY2025 和 CWP SourceRef/manifest 校验。失败后公开 list 仍为 0 条，revision 未变。

## P2 owner 实施复核补充（2026-11-10）

- 静态检查暴露 `CompanySourceIndex` 通过伪造窄 request 与 `cast(Any)` 调用 `SourceResolver._identity_matches` 私有实现。修正为 SourceResolver 的公开 `match_source_identity` 输入契约，并将 SourceVersionReader、local_reconcile 的跨模块调用一起迁移；正常 market/security/issuer-link 判定语义一致。
- 独立审查发现公开 matcher 的无挂牌范围、仅 issuer-link 请求会错误早返为 `match`。现在明确返回 `incomplete` 并由 `test_issuer_link_without_listing_scope_is_incomplete` 锁定；最终独审通过，无 stop-ship。
- CWP 新增 SEC 20-F 挂牌证据路径仅接受已验原件、SEC accession/URL/CIK、对应官方 US listing 和 SEC 表格中的精确证券/交易所；由 canonical writer 导入并经 SourceCatalog 公共登记。没有放宽普通 official-source 流程，也不按公司名或 ticker 生成关系。
- 阿里 FY2025 与 B 站 FY2022 的真实 HKEX 原件 SHA、issuer-link 来源和零下载复用证据见 `validation/p2_cross_market_e2e_receipt.json`。CWP focused 127 passed、mypy 470 source files、Ruff 通过；FF focused 11 + M3 21 passed，两个 owner 候选已推送。完整远端 CI 尚待确认。
- 测试必须使用满足 Windows 路径长度的短临时根。默认外部沙箱临时目录会令旧 CWP acquisition 锁文件路径过长并失败；使用仓库内短路径基准后同一套件 127 项通过。测试回执确认自动临时子目录清除；手动清理了前两轮失败测试留下的自有临时目录，未改原件或业务数据。
- 当前部署 security master 文件只有 CN/HK/US 各自的身份列表，尚无普遍跨市场链接。因此本轮证明的是通用匹配、来源绑定与真实原件复用逻辑，仍不证明生产数据自动覆盖已闭环；下一步工作是 owner 级关系来源/刷新机制和实际部署只读验收。