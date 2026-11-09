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
