# Revenue Forecast 实施单

工作目录为 `C:/Users/郑曾波/Projects/revenue-forecast`。写域为 RF 的公开作业、报告目录、研究输入消费和对应验收。使用 FF 和 CWP 的公开 DTO/CLI。Dashboard 接收 RF 的公开合同与发布 pin。归属和依赖见 [总计划](task_plan.md)。

## RF-RELEASE · 先发布公开作业与目录

1. 从真实远端 `main` 建隔离工作树。基线 `90c562ac` 已包含当前 D4 分层。以候选 `e4b38459`、`d347c4ab` 的 job facade 为参考，B31 `c1e27877`、B34 `7f1d3a99`、B37 `28d646d3` 作目录和部署依赖参考。job 候选相对主线分叉差异 415 路径。逐个追公开入口的依赖并复用当前 owner 实现。
2. 先确定可信目录根和报告读端的最小闭包。优先落 `list-reports`、精确 ReportView、成功出版的管理入口及必要的 identity/deployment ports。再窄移植 `rf_job_cli`、`rf_job_facade` 和直接依赖。按实际依赖分开提交，可先交 catalog 给 MDB；冻结后用同一候选跑全链。避免回滚现有 source/reader 端口和原模型流程。
3. 用公开命令跑 v1 submit/status/act/list、旧报告回读、部署根不一致和隔离测试。两套临时目录下，读端只看到登记在本可信根的报告。检查无跨仓目录直读、无 path 泄露、无重复引擎。保留现有 v1 适配。通过本仓 CI 与大节点复核后发布。

## RF-1 · 阿里来源与预测验收

1. 用 `0993abb3` 六路原请求、可重放回执和 MDB 对照固定复验。将 CWP identity/scope、FF 消费、provider 环境各自缺口交 owner。RF 测具名 upstream 故障与正常已绑定返回，保持 owner 名、阶段、实际计数和有用错误。
2. 只采用一条符合真实发行人、披露市场、表单、财年、as-of 的 `found + capture_ready` 来源。原始六路的覆盖证据分别保留。采用现有通用输入构建器编制 schema 3.7 或部署正式支持的兼容版本，逐项数据带来源、币种、数量级、财务期和 capture receipt。使用真实数字的正反例，保留非阿里双上市和 MDB 的回归。
3. 用已配置的实际预算和原有每公司 $1 上限中的较小值。真实付费前确认负责收费的入口确能执行限额。RF 实际运行后检查完整阶段、报告和目录采用。若来源仍不可用，明确每路剩余原因，RF 不创建虚构输入或报告。

## RF-2 · MDB 既有成功报告入册

1. 固定内容提交 `0993abb305dc86a2197b8b2aee10a3b8d8339949`、作业 `rfjob-20261108-eb9f2a3ed336`、实际发行人和可信目标目录根。区分引擎结果、冻结快照、Markdown、命令/作业收据的身份和哈希。检查 source、scope、币种和期间能从原始证据重放。
2. 确定成功出版合同。旧建议中的 `import-research-attempt` 只收封闭的失败尝试，不能登记此报告。先对 `import-research-publication` 检查真 B34 材料是否齐全；报告归档已记录其中有缺口。若现存原生 job publication 能提供等价必要事实，给 RF 新的窄原生导入路径。逐项使用真输入/收据/原报告，并经现有可信目录 owner 事务写入。缺一项必要事实而无其他原生证据时留 NOT_ADMITTED，保持读端可诊断。
3. 在临时可信目录做首登、相同报告二次导入、错误根、错 issuer/result SHA、同 ID 变更、半途失败和重试。要求同一报告只有一个登记记录，原产物逐字节相同，失败不留可见半成品。由 RF 正式管理命令按真实证据登记，避免重跑预测或换成 donor root。复验 Dashboard 调 `list-reports` 和精确 ReportView，报告 ID、源哈希、结果 SHA 与 Markdown 对得上。

## RF-3 · v2 兼容演进

先验证并补实际费用执行，复用现有 RF/供应商预算责任层。采用有限 Decimal 表示，拒绝负数和非有限金额。并发以原子预留处理实际余额，失败和恢复以原用量结算，未知支出保留 unknown。对无法实施预算的付费阶段返回明确不可用；允许已证可恢复的零新开销场景。用边界值、并发、重试、断线和已付费恢复测试。这个缺口优先于表达字段的收敛。

| v1 已登记的 10 项 | v2 计划与验收 |
|---|---|
| 无 command_id 绑定 | 持久绑定命令、请求和 owner job。冲突保持具名错误 |
| 无 started_at | 从实际 attempt 得到，排队/未知仍可空 |
| 无 ApiError | 按 owner 业务事实映射具名错误，外部说明路径无关 |
| interrupted 映射 failed | 公开区分可恢复中断，Dashboard 自己投影 |
| known cost 形状少字段 | 公开金额、币种、状态。Dashboard 自行补可空的显示字段 |
| unknown 无 updated_at | 区分事实时间与观察时间 |
| act 无幂等槽 | 同键同操作重放，冲突键和并发不同操作有确定结果 |
| list-jobs 无 cursor | 按稳定排序和固定快照分页，不混读跨快照 |
| list total 未知及简化 snapshot | 实际能证明总数才报告 exact，清楚标记未知 |
| max_cost 只验配置 | 接入真实开销限额，验证超限、取消、恢复和实际计量 |

维持 v1 消费及已登记的语义。只有 v2 owner 合同和 Dashboard 适配各自验收后才换版。文档和测试覆盖十项，不以更复杂的状态表阻断现有成功。

## RF-4 · 扩展覆盖单独排期

- EXT-02 用自然发生、真实封闭的整轮 FAILED 留证。已有允许 resume/reconcile 的失败作业可用于恢复测试。没有终态证据时标记待样本。
- EXT-03 对 W09 历史报告追加可实证的原生绑定和 lineage。保持原报告字节、历史状态及不可证的 null。
- EXT-04 按精确 ReportView、scenario、period、basis、currency/unit 核对 Low/outyears。证据不足保持 null。以上均不挡已接收的 E05/E06 范围与本轮基础发布。

## RF-5 · 复用单一交接记录

每个包记录 40 位代码 release SHA、单独的内容提交、引用的原始输入/结果/快照标识及哈希。验收记录绑定实际运行的修订。用原有证据记录或 manifest，保留历史字节与敏感配置。公开仓发布只含所需代码、测试及可公开的交接引用。
