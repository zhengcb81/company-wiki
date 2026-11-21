# F2 真实场景验收（2026-11-21）

## 交付状态

| 范围 | 根因及处理 | 正式读回 |
|---|---|---|
| CWP / StockWiki 原文引文 | 原文身份由 CWP 公开验证。已验证归属的旧版可由原文直接重定位。StockWiki 记录源坐标并按发布过的发行人工作区关联读取。 | 阿里 `e39fbf9c…` 的三条 PDF 引文和 MongoDB `84dcd298…` 的三条 HTML 引文均从同一原 SHA 读回。组合入口分别返回 11、17 条主张。 |
| CWP / FF 三表 | 原先只有隔离归档，单期查回还受全历史覆盖记录约束。旧捕获和新采集统一入库，精确已验单期可由自身报表和观测证明答复。 | 中微 FY2025 `reuse_only` 返回 `complete`，采集请求和费用均为 0。 |
| RF 作业 | 冻结报告依赖的七份来源中，五份仍只在验收库。CWP 补正式原件登记，RF 走原有公开入册。 | 原 W12 首次 `registered`，重复 `already_registered`。公开作业 `complete`，attempt `succeeded`，同一报告和快照查回，预测执行 0 次。 |
| IQS / Dashboard | 业务主库和 IQS 现役库使用各自的实体键。由公开身份接口验证两端挂牌，结果由 IQS 给出。 | 药明、MDB 身份解析成功，均为结果未登记、历史 0 项。阿里在 r25 未找到对应挂牌，快扫视图为具名空状态，结果链接为空。 |
| Dashboard 指标 | 固定名单分页和正式 FF 三表构成同一 `MetricPublication`。未知数值保留待核。未发布的最新定义返回业务空状态。 | 正式首批快照可用，215 家名单、八个定义、中微一家有值。隔离筛选读尽三页得到 1 家通过、214 家待核，保存并重启结果一致。 |

## 公开复验

### 固定资料和引文

- CWP `3fadcbe07` 承担发行人证明、原文读回和原生段落定位。三市场有效凭证及反例见 [F1 发行人证据](followups.md#1-cwp-发行人证明和-stockwiki-历史引用)。阿里原港股年报 `e39fbf9c80866759b20cf005f8b1b54301e6ae2ec092aed1d774d954e44fb350` 使用来源事实 `sa-3857b90f44264899b33969f27af2ad72`。正式目录同时保留该版本和既有 FY2025 版。
- StockWiki `7ab8778` 通过同一验证器记录三条阿里证据 `ev_sig_b9d41d3a79fa515f`、`ev_sig_5ad83270d1e96da0`、`ev_sig_ca5b3badb9c48d2b`，原页为 7、4、4。MongoDB 原 SHA `84dcd298ff9c2bcea0ed49755219ae3209c7e9e2a451dd5be49fe41626a25513` 的 `ev_sig_0809f37cc331644d`、`ev_sig_db53b884a11e5e6c`、`ev_sig_3f78bec66174ac7d` 对应 `loc:v1/paragraph:853`、`155`、`186`。原文由 `company_wiki.source_catalog.public_source_citation_cli` 接收固定 SourceRef 与引文再定位。StockWiki 在已验发行人下发布同一业务 profile。
- Dashboard `GET /api/v1/companies/{entity_id}/research?listing_id=…&information_as_of=2026-11-20` 验到上述六条坐标及原 SHA。历史页仍保留其他旧证据缺项和过期诊断。源文档和研究按各自公开时点能力读取。

### 结构化三表

使用 [W19 原采集观测](../w19-sina-statements-2026-10-25/inputs/research/capture/observations.json) 的采集时钟和原字节。CWP `financial_statements.cli --import-capture` 首次登记，用同一输入复跑新增版本 0。正式 FF `fcacf2e4` 复用 [固定请求](../../../../filing-fetch/docs/handoffs/dash-ff-20261120/evidence/07-request-successful-sample-fy2025-pit.json)，截止 `2026-11-20`，FY 期末 `2025-12-31`，三表均为合并口径、CNY，报告时点校验通过。八个 JSON pointer 都在 `/result/data/report_list/20251231/data/` 下。

| 表 | statement version | 正式读回 SHA-256 | `data` 内行号及字段 |
|---|---|---|---|
| 利润表 | `fsv-e9744c62ab97f83a9758641a9c4bcd80ecbc711a4ba2cf1c4b8ea108ccedecfc` | `597506c4a5a9093286e4dc26961933d8118dae6e1a7ed464c24c1e4322cbbd34` | 0 收入、47 净利润、75 基本每股收益，均为 `item_value` |
| 资产负债表 | `fsv-cde3532c4e6621d0f783a0acf4f8bc4299adafea8032804e458f4735cb1fe26f` | `534dd4e09d7f682782048776b4514ae66d41b5522c8b13725c0a74bc49e5d7e2` | 1 现金及等价物、66 总资产、121 总负债，均为 `item_value` |
| 现金流量表 | `fsv-95343586e60734e51e35176b6998c5524c3009e56f1b9ae1c988fda04cdd16b0` | `74abee7afdb45b44584858afa200458dae083d6a3df7b1c16f6d093b5df44a40` | 1 销售收现、25 经营现金流，均为 `item_value` |

冻结时对照的利润表 `2aa0b2ba42c1b449b5f8ec8868855e4f2ae707213a1e770262e9349ad92f3b20` 同样可在正式库按原 SHA 读取。两次捕获解析出相同报表版本。正式时点查询选中的是较晚的实际观测 `597506c4…`。金额单位为 CNY，基本每股收益为 CNY/share。

### W12 与快扫

- RF 发布基线 `f1af2193`，正式资料与报告目录分别由 CWP 和 RF 持有。用 `report_catalog_cli.py get-run --run-id rfjob-20261120-594c00a589d1` 及 `get-report --report-id rfjob-4cdaef1dc815b1721446209268e7bf01207836eeb14dc2c4651a8f09eab54f98` 查回。快照 `a869880c34461d6a6982f1aa2427b11dfeacf5a456aeaa14bc086dd7a28a721b`，作业、报告和快照字节 SHA 见 [冻结作业回执](followups.md#3-药明-w12-原作业与报告入册)。Dashboard 同一 `GET /forecast-runs/{run_id}` 与 `GET /reports/{report_id}` 验证通过。本次验收范围为已完成作业重读和重复入册，各运行阶段中断恢复沿用 F4 记录。
- r25 身份、业务身份及正式 IQS `296ab84` 逐家读回在 [F1 身份回执](followups.md#4-iqs-业务身份与-r25-正式结果)。组合请求通过 exact 交易场所、ticker 和两端已验证发行人匹配药明与 MDB，保留 Dashboard 公司键。无可验证映射时的 `workspace_listing_unresolved` 是页面状态。有映射而无正式评估时保留 `company_result_not_registered` 和 IQS 的既有历史。阿里缺挂牌，两家缺结果或可见历史，属于真实覆盖范围。跨键的旧 IQS 回跳在公开协议未给出确认时以独立状态表示。

### 指标发布

现役数据根 `.runtime/f4-feedback/read-listener` 的 `48766` 定义和固定快照均返回 HTTP 200。宇宙 `UNI_IQS_APPROVED_214_20261025`，名单快照 `55c7a1f4ed2247bdbe741e386653a959`，指标快照 `ms_9e0c9c0fe626417a4be49cea5e5ce1f3625e4df562924607cc5e94f7edfefd60`。同输入发布两次得到同一 ID。三页名单各 100、100、15 家。实际供数为上一节八个字段，未进入首批的公司保留 `owner_statement_not_in_publication` 待核原因。隔离公式 `revenue_total > CNY 10,000,000,000` 读尽三页，1 家通过、214 家待核。保存视图后重启读取同一快照，结果逐项相等。正式数据与隔离视图分开保存。

## 回归范围

- CWP 公开原文、注册归属、原生定位定向 104 项通过，选择字段放宽后核心 37 项通过。三表模块 136 通过、1 个跨仓显式启用项跳过，最后的三表入口测试 21 项通过。提交钩子 Ruff、mypy 通过。
- StockWiki 引用与研究关联测试 67 项通过，发行人匹配补强后引用套件 30 项通过。独审补了原摘录与来源身份的核对。测试在短路径临时库运行。
- Dashboard 定向回归覆盖身份错配、HTML 引文、日期条件、独立指标存储和发布。正式原文、现役 IQS、本机 RF 报告目录与隔离 Dashboard 从公开接口组合读回，临时数据目录已自动恢复。真实数据回归复用了留存原件，网络采集、收费 API、预测执行均为 0。
