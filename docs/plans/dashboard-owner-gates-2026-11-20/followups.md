# Dashboard 业务 owner 后续回执

2026-11-20 复核现用公开接口和冻结证据。现用 Dashboard `127.0.0.1:48766` 和 IQS `127.0.0.1:8766` 首屏均返回 200。本轮交付发行人证明和读回复核，并记录正式资料登记及业务发布状态。 [Dashboard 后续五项](../../../../investment-dashboard/handoffs/owner-requests/DASHBOARD-OWNER-FOLLOWUPS-20261120.md)

## 1. CWP 发行人证明和 StockWiki 历史引用

CWP 复读用 `c596d017565326ebf5a632d0d424ad5992f34532` 的只读检出，浏览实现与当时本仓主线一致。StockWiki 证明和研究查询来自本地 `2de1f887e6487e8129956a13c5fb2fc82ce5cb6d`。返回协议为 `company-wiki-canonical-document-browse/1`。

| verifier | 发行人 namespace | CWP 证明 |
|---|---|---|
| `cn-primary-uscc/1` | `cn.uscc` | 已验证 A 股挂牌与原始披露 PDF 中的统一社会信用代码，以原件版本固定 |
| `hkex-registered-source-facts/1` | `hkex.listed-issuer` | 已验证港股挂牌、官方 HKEX 原件及其当前归属事实，发行人键由五位港股代码与规范化法定名称摘要组成 |
| `sec-primary-dei/1` | `sec.cik` | 已验证美股挂牌与 SEC 主申报原件 DEI 中的 CIK，以原件版本固定 |

`binding.status=verified` 时，`binding.stockwiki` 给查询实体、所选挂牌/市场及 `receipt_sha256`。 `binding.issuer` 给 `namespace`、`value`、`verifier`、`assertion_id`、`source_id` 和 `content_sha256`。发行人证明锚的版本也出现在 `binding.cwp_resolved_source`。目录中的每个成员有各自的 `source_ref` 和 `document_version_id`，且已通过同发行人归属核验。 `association_scope=issuer_only` 表示发行人层面的归属。证据不足或冲突时，可信成员列表不产生虚假的归属，参见 `binding.reason_codes`、`unverified_candidates` 和分页状态。

当前三对标识的含义按上表固定。兼容增加 verifier 时，消费者使用本协议的可信 producer、`binding.status`、发行人锚及成员 `SourceRef` 读回通用发行人结果。需要理解具体 namespace 语义的功能只在该功能内处理，遇到错误配对时把关联降级并保留可独立读回的原件。Dashboard `2539c9c` 已有这一消费侧修正，作者交接含 14 个用例，覆盖原四种错配和新增 verifier。现行监听端口在该修复后的发布回执仍待 Dashboard 确认。

### 真实脱敏例

从 owner 配置运行 `python -m company_wiki.source_catalog.public_canonical_browser_cli --config <CWP catalog config> --sw-python <StockWiki Python> --sw-cli <StockWiki dashboard_issuer_proof_cli.py> --sw-root <StockWiki business workspace>`，stdin 使用下列请求形状。替换实体和挂牌即复现其余两例。

```json
{
  "schema_version": "company-wiki-canonical-document-browse-request/1",
  "canonical_entity_id": "ENT_a74f8604-6e43-482f-8e91-bdd4518d5eef",
  "listing_id": "LST_c1e34bdb-fd78-48d6-b2c5-da6eba4b44b0",
  "as_of": "2026-11-20T22:00:00Z",
  "document_kinds": ["annual_report"],
  "limit": 2
}
```

| 样本 | 业务实体 / 挂牌 | 验证状态 / 展示键 | 发行人证明 assertion |
|---|---|---|---|
| 中微 688012 | `ENT_a74f8604-6e43-482f-8e91-bdd4518d5eef` / `LST_c1e34bdb-fd78-48d6-b2c5-da6eba4b44b0` | `available / verified`，`cn.uscc:…2806` | `sa-a48f9e6eac464179a38e99b07de492e0` |
| 阿里 09988 | `ENT_e4d964f0-ed84-43b5-a9c7-c9b4b38d8101` / `LST_591474dd-2778-46ce-8b42-ad5fc483d64d` | `available / verified`，`hkex.listed-issuer:09988:…2a65` | `sa-b0a7df5dbe6c441b86d35ea436384862` |
| MongoDB MDB | `ENT_41250504-734e-4460-9843-86c4e1f3851d` / `LST_2d86780f-c98e-49cc-a214-34885c8820fa` | `available / verified`，`sec.cik:…1816` | `sa-2dadd762f04f4acc864113f41095e650` |

| 样本 | 证明锚 `content_sha256`，`source_id` 为 `urn:company-wiki:source:sha256:<SHA>` | StockWiki `receipt_sha256` |
|---|---|---|
| 中微 | `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5` | `6738c136f721d6e162419f3413a24242d7a2d3af9493ac7a223f90a026ef5880` |
| 阿里 | `8ab1234844b56a2be8b90d92301d0a46123c8770610e87f9462bb27b0e2b7182` | `bda965566f94c63e68dd602440a214c3bc6787290fc4f5a9cdd9795db568ecd4` |
| MongoDB | `28599d4ac1c3a821da0894ecf7a4297ba567c41ce3a604f399750b63f8dea118` | `507b7a6f95cc379b18e72032394714a37d8e922e94f2c85e27663cd9724a2ddb` |

三例关联范围均为 `issuer_only`，理由均为 `same_issuer_proven`。在上述年报筛选下，证明成员总数分别为 5、1、5。未验证候选扫描另有 `unverified_candidate_scan_truncated`。MongoDB FY2026 HTML 是另一条已验证成员，取用其自身 SHA `84dcd298…`。

独立目录定向回归 9 项通过。 `test_wrong_issuer_documents_are_not_attributed` 排除其他发行人的原件并保留已验证的原件。 `test_wrong_market_entity_never_binds` 返回 `unavailable / market_not_registered`。 `test_foreign_listing_is_refused` 返回 `unknown / listing_not_found_in_owner_package`。后两例均无可信条目。 [CWP 合约测试](../../../tests/contract/test_public_canonical_browser.py)

### 两条历史引用

- **阿里 HK FY2026**。业务实体及挂牌沿用上表。 `source_reader_cli --purpose source_export --exact-pair --include-availability-evidence --include-canonical-identity` 按固定版本打开了 4,172,424 字节，SHA 为 `e39fbf9c80866759b20cf005f8b1b54301e6ae2ec092aed1d774d954e44fb350`。 `document_id` 和 `source_id` 分别用 `urn:company-wiki:document:sha256:` 和 `urn:company-wiki:source:sha256:` 加该 SHA。旧 manifest 给出 `hkexnews`、文档键 `12207997`、代码 `09988`、FY2026 和 HKEX 披露 URL，`market` 为空。该精确版本仍缺可通过当前公开归属口的市场关联证明。已验证的 FY2025 文件 `8ab12348…` 有自己的版本。StockWiki 业务研究读到 11 条主张、16 条引用记录，状态 `partial`，旧 SHA 当前无可投影的 `SourceRef`。验收时用同一旧 SHA、HK 挂牌和已验原引文回跳。 [HKEX 原披露地址](https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0618/2026061800845_c.pdf)
- **MongoDB FY2026 10-K**。SEC accession `0001628280-26-016799`。同一原件 `84dcd298ff9c2bcea0ed49755219ae3209c7e9e2a451dd5be49fe41626a25513` 已以 2,218,293 字节的 `text/html` 精确读回，目录版本 `cwpdv1-1X-NqudGjHmIZvU3970tsZdGQ7sK-aX37es9-ojUdb4`。在 HTML 可见文本中核对了原有的 MD&A 订阅占比、前瞻性陈述中的风险条件以及 Item 1 平台描述，三段各命中一次。StockWiki 公开查询返回 `stale`，三个旧节标题引用均报告 `source_bytes_outside_owner_workspace`。CWP `narrative_transport_cli --operation reference` 用该 `SourceRef` 返回 `not_found / narrative_artifact_not_visible`。待 CWP 公开同一 HTML 原件的可读段落定位，StockWiki 回填自己持有的引用并用原三段复验。同步保留该原件在文档目录的已验证状态。

## 2. 中微 FY2025 结构化三表

FF 主线 `fcacf2e4f1858bde4490571a8931bb44d276aba8`。用 `scripts/fetch_statements.py --config <active FF owner config> --request-file <07 fixed request>`。冻结请求 `07-request-successful-sample-fy2025-pit.json` 使用 688012 CN、`period_end=2025-12-31`、`as_of_date=2026-11-20`、`point_in_time` 和 `reuse_only`。业务实体/挂牌和第 1 节中微一致。正式 FF 返回 `not_found`，HTTP 请求、响应字节和费用均为零。CWP 的正式 SourceReader 对以下三个冻结的原始数据版本均返回 `not_indexed / document_not_indexed`。原因定位到了正式原件目录登记缺项。

| 表 | statement version | 新浪原页 SHA-256 | 已有离线核对 |
|---|---|---|---|
| 利润表 | `fsv-e9744c62ab97f83a9758641a9c4bcd80ecbc711a4ba2cf1c4b8ea108ccedecfc` | `2aa0b2ba42c1b449b5f8ec8868855e4f2ae707213a1e770262e9349ad92f3b20` | 3 个字段 |
| 资产负债表 | `fsv-cde3532c4e6621d0f783a0acf4f8bc4299adafea8032804e458f4735cb1fe26f` | `534dd4e09d7f682782048776b4514ae66d41b5522c8b13725c0a74bc49e5d7e2` | 3 个字段 |
| 现金流量表 | `fsv-95343586e60734e51e35176b6998c5524c3009e56f1b9ae1c988fda04cdd16b0` | `74abee7afdb45b44584858afa200458dae083d6a3df7b1c16f6d093b5df44a40` | 2 个字段 |

隔离回执为 `complete`，三表均为 CNY、合并口径，八个字段按原始十进制值及 JSON pointer 对照。owner 发布时以同一捕获原字节、原 `observed_at=2026-11-20T11:41:15Z` 和有效挂牌登记。FF 用上述公开请求读回 `complete`、相同来源及字段，验收记录保留每个版本、来源、期间、单位和口径。 [冻结 FF 回包](../../../../filing-fetch/docs/handoffs/dash-ff-20261120/evidence/02-successful-sample-fy2025-pit.response.json) [八字段证据](../../../../filing-fetch/docs/handoffs/dash-ff-20261120/evidence/05-metric-snapshot-input.json)

## 3. 药明 W12 原作业与报告入册

按 RF `origin/main@f1af219344d5c082c6ddf35ca1f804b3833a6389` 的 `report_catalog_cli.py --owner-root <RF formal root> get-run --run-id rfjob-20261120-594c00a589d1`，正式目录仍为 `not_found`。以同一版本的 `rf_job_cli.py --owner-root <W12 audit run>/execution/rfo get-status --job-id rfjob-20261120-594c00a589d1`，原作业返回 `succeeded`，三步分别为 `source-1`、`compute-1`、`publication-1`，均为 `completed`。源准备为 `reused_existing`。已有恢复证据覆盖按原 ID 查回成功状态，未验证各阶段强制中断恢复。正式入册可复用 `report_catalog_identity_cli.py import-rf-job` 和已经冻结的下列文件。 [原作业查回回执](../../../../revenue-forecast-audit/runs/w12-20261120-cn-603259/execution/rf-job-status-operation.json) [原产物核验](../../../../revenue-forecast-audit/runs/w12-20261120-cn-603259/execution/rf-executor-verification.json)

| 原件 | SHA-256 / 原目录坐标 |
|---|---|
| `rfo/artifacts/rf_jobs/jobs/rfjob-20261120-594c00a589d1/job.json` | `af60dbda7156d0b962aef183b672df8fff0aabe36c0b553e5637f9b76be33f31` |
| 同一作业的 `stages/compute/report.md` | `a2e1d0da30d74dcebaf5dfb75457a1861d2779c2be5150d61e6fda341d57f3d4` |
| `execution/rf-snapshot.json` | `5846bf1e5316180ea5f3f7665d58c6a4b2731c6259c8db2afa6930758fd9c2d3` |
| 原快照 ID | `a869880c34461d6a6982f1aa2427b11dfeacf5a456aeaa14bc086dd7a28a721b` |

归档用药明业务实体与挂牌，见下表。RF 按现有部署、原作业根、两个原文件 SHA 和原快照文件入册，再复读 `get-run` 和登记生成的报告 ID。隔离环境中已有 `registered` 与 `already_registered` 收据。正式验收对比原 job ID、attempt、报告 SHA 和快照 ID/SHA。同一原作业重复登记应返回已有绑定。

## 4. IQS 业务身份与 r25 正式结果

StockWiki `dashboard_identity_bridge_cli.py resolve --root <workspace> --entity-id <ENT> --listing-id <LST>`。三对业务实体/挂牌均在业务主库解决为 `resolved`。在 IQS 现用的 `runs/r25-live/owner-workspace`，这三个业务实体键均为 `not_found`。其正式 IQS 的 result/history 也全部为 HTTP 404 `entity_not_found`。进一步以 r25 权威搜索和查回，区别如下。

| 样本 | 业务实体 / 挂牌 | r25 正式身份 | 用 r25 身份走 IQS 现用端口 |
|---|---|---|---|
| 药明 603259 | `ENT_2a41e04d-8679-4be5-9e30-3aaf89bdd00e` / `LST_f26e4cea-69f3-4525-885f-c13885c731f8` | `ENT_3ac097b9-5452-411f-ba15-d81ec2d0d12d` / `LST_80ed7414-05e6-42f2-bdba-6469582f0d3f` | 两个端点均 200，`company_result_not_registered`，历史 0 项 |
| 阿里 09988 | `ENT_e4d964f0-ed84-43b5-a9c7-c9b4b38d8101` / `LST_591474dd-2778-46ce-8b42-ad5fc483d64d` | `09988`、`9988`、`阿里巴巴`、`Alibaba Group`、`BABA` 均 `no_match` | 现有 r25 公开身份搜索未命中 |
| MongoDB MDB | `ENT_41250504-734e-4460-9843-86c4e1f3851d` / `LST_2d86780f-c98e-49cc-a214-34885c8820fa` | `ENT_b47ecd1e-ca1c-449b-96fe-7d49476fbe4b` / `LST_50d01c61-adea-4858-b5a2-0afd99176490` | 两个端点均 200，`company_result_not_registered`，历史 0 项 |

两家 200 证明 r25 路由和身份可用，正式结果登记和可见历史仍缺。草稿覆盖在这些公开端点尚无地方可证。中微已用 r25 `ENT_99deceb6-f58a-48b1-bd6b-437621015d76` / `LST_4b1d9b36-f70b-4c7b-b107-4ceb5bfa1b59` 查回固定结果 `cas_6cab1b94d8f45d42c750`（HTTP 200）。后续跨工作区跳转由 StockWiki 与 IQS 公开的发行人和挂牌关联定责，保留各自权威 ID。IQS 先查是否有原结果、草稿或观测可以登记，再报告实际覆盖。

| 样本 | 业务主库 `lookup_receipt_sha256` | r25 身份查回 SHA / 搜索 SHA |
|---|---|---|
| 药明 | `75ca62b8aa3ee6ff05483d31cbb32bff6be0dccb32de3f5e5f6ccc4832ca2860` | `06384b3c0999080c2c3279dbd427eb78728725afde5770e52b1ff6bdce41dc21` |
| 阿里 | `ecd77215d26791bafc8571b7c0fc859f60c69428fd013fbbef665047e48715f2` | `6f4cb846ca9c234b495def75b2ee7398e65b65892f9c56bfa5f2ae7859a9bc37`，按 `09988` 搜索 |
| MongoDB | `f5b66bfea57f2b5f86fdfdec6294e474d81b923800fd8089078713d626cf2c08` | `0905b93eb22b30586fa09536070e1ac41479ce0a5c13c1ab5ddf31ea8a7b7721` |

## 5. Dashboard 固定指标发布

现用 Dashboard 对 `GET /api/v1/metrics/definitions?universe_id=UNI_IQS_APPROVED_214_20261025` 返回 HTTP 503 `metric_definitions_unavailable`。同一宇宙的现用名单公开口按三页 `100 / 100 / 15` 读出 215 家，有效快照 `cfbb586270894f2b9ead6341300bcbe5`，包含 r25 中微成员。隔离指标实验使用的名单快照 ID 是 `862bf6c6b1ba401d96c643daed8ff7c9`，指标快照是 `ms_ce1e718575b681c734cc1c7184d5becf1e57ac2b54c3c8eca49083b213e64f39`。已有隔离回执覆盖八个定义、中微一家有值、214 家待核，分页及保存重启重算一致。现用宇宙和隔离回放分别引用各自的名单快照 ID。

首发由 Dashboard D04 用正式名单和 FF 正式三表组成 `MetricPublication`，写入所属运行目录。提供定义版本、截止日、值单位/期间/口径和原始指针。首批以中微一家公司为供数范围，其他成员保留待核原因。验收要求定义接口返回 200，以返回的正式快照读尽三页、定位中微原始数据、验证保存后重启恢复。RF 预测可独立登记。 [发布合同](../../../../investment-dashboard/handoffs/m7-owner-publication-20261120/handoff.md)

## 总控接回顺序

1. CWP/StockWiki 推进两条原研究引用。RF 同步用原 W12 作业入册。IQS/StockWiki 同步处理工作区身份和既有结果，分别在本仓交付。
2. CWP/FF 先使三表的精确原件和公开 `reuse_only` 可回读。Dashboard D04 再用正式 owner 供数和当前名单于自己的发布目录登记。
3. Dashboard 核对实际服务使用的代码版本，最后用同一发行人、挂牌、版本和真实端点组合复验。把代码已并线、所属数据已登记及运行时已切换分别记入交接。
