# G1e 电话会议来源使用权限合同 v1（2026-09-27）

> 本卡只冻结自动链路的权限判定和试验边界，不对任何未核实内容授予许可。上游来源/提取归 company-wiki；投资观点归 StockWiki。与 [G1e 大节点](task_plan.md)、[来源成本卡](provider_cost_and_capability_2026-09-27.md)和[端到端测试](end_to_end_test_plan.md)配套。

## 1. 输入和权威位置

正式实现采用仓库内受版本控制的只读 `provider_use_policy.v1`（精确生产位置在 G1e 实施卡冻结时确定），由来源权限负责人复核；provider HTTP 响应、工具结果、LLM 文本和用户临时命令参数均不能生成或扩权该政策。日志只记录政策 ID/hash、决策码、来源 ID，不复制授权文件内容或 API key。`config/source_catalog.yaml` 不作为测试覆盖目标。

**复用现有合同：**`source_catalog.authorization.DownloadAuthorization` 已绑定精确 provider/accession、GapPlan hash、RuntimePolicySnapshot hash、item/byte cap 和到期时间，G1e 的候选下载必须继续经过其 `validate_download_authorization()`；本权限表只补充内容使用许可，不能取代该下载收据。`RuntimePolicySnapshot` 是激活/根政策状态，不拿来冒充内容许可证。`SourceManifest` 以原件 SHA 定义 source ID；派生 TXT 使用现有 artifact/source_id 关系，增加 parent 原件 hash、转换版本和 locator 映射，不为派生文本虚构第二个原始来源。若现有 artifact 契约不支持所需 parent/locator 字段，先做兼容扩展及其审查，不能塞进不受校验的 sidecar 隐藏字段。

每条规则包含：`policy_id`、`policy_version`、`provider_id`、`origin_host/path_scope`、`content_class`、`rights_evidence_ref` 与证据 SHA、`reviewed_at`、`valid_from`、`valid_until`、`reviewer`、`permitted_actions`、`retention_scope`、`export_scope`、`revoked`。`rights_evidence_ref` 指向人工核实的条款/书面许可或发行人材料及其版本；链接可读不等于动作获准。字段缺失、版本未知、URL/内容类别不符、证据过期/撤销、政策与结果 provider 不一致均为拒绝。测试 fixture 的显式许可只在专用 run root 和 fake provider 有效，不能被生产配置加载。

动作分别为 `discover_metadata`、`automated_fetch`、`retain_original`、`derive_text`、`select_evidence`、`generate_summary`、`export_excerpt`。前一动作允许不能推导后一动作允许。`export_excerpt` 须独立记录目标受众/长度限制；完整正文跨仓复制一律不在默认范围。访问控制同时检查用户/任务授权、provider 权利和具体候选身份；三者取交集。

## 2. 当前精确决策（不是整站永久判断）

| 来源类 | 当前自动链路 | 理由/后继条件 |
|---|---|---|
| Motley Fool 网页 transcript | 对该站点的所有自动访问（包括 `discover_metadata`）及正文动作均拒绝；不得调用现有抓取器 | [官方条款](https://www.fool.com/legal/terms-and-conditions/fool-rules/)禁止 agents/scripts 自动访问、复制和采集；只有明确适用的书面许可经复核才可改政策 |
| Seeking Alpha 个人站点/订阅 | 对该站点的自动发现/抓取、索引、留存正文、派生与 export 均拒绝 | [官方条款](https://about.seekingalpha.com/terms)限制机器人下载/索引/抓取，个人订阅不是内容 API 许可 |
| FMP 当前 key 的 transcript endpoints | `automated_fetch`/正文处理拒绝，返回 entitlement_unavailable 终态 | 真实 MSFT canary 为 HTTP 402；未来套餐变化仍须逐 endpoint entitlement 与内容使用许可双证据 |
| SEC EDGAR 8-K/8-K/A transcript 附件 | 可按 [SEC 公平访问](https://www.sec.gov/about/developer-resources)发现元数据；正文动作逐附件 pending | SEC 实例有完整文字，但部分附件带 FactSet 版权；域名和 EX-99 类型不是全站许可证 |
| 公司 IR 自行发布的稿件 | 可人工发现元数据；正文动作逐站/逐稿 pending | 需核对站点条款、是否第三方署名及留存/摘要/export 范围 |
| 隔离 fake provider fixture | 专用 run root 内所列动作可测 | 只能是测试字节，不能复用在生产或保存外部正文 |

## 3. 决策顺序与保存合同

1. filing-fetch 先按已核实 company/CIK/security identity 和精确 FY/Q、as-of 解析候选；找不到/歧义时不请求正文。companion 失败不得改变已成功的 filing 结果。
2. 网络请求前同时检查 `automated_fetch` 与站点访问限制、用户单次下载授权及现有 `DownloadAuthorization` 对精确 provider/accession、计划/政策 hash、item/byte cap、到期的判定，再检查 URL allowlist、配额/超时/响应字节上限。任一失败均不请求正文并返回稳定终态；402/403 不进入普通重试队列。只在授权范围内把候选交给 earnings-transcripts adapter。
3. 下载后、持久化前再次检查来源 URL、HTTP 结果、公告/发布时点、FY/Q、身份、原件 mime/字节/hash、当前政策 hash/有效期及 `retain_original`；政策变化时丢弃暂存字节，不生成 canonical 文件。第三方版权标记或署名与规则不符时停在人工审查。
4. 不可变原件为 provider 返回的 HTML/PDF/TXT 原始字节，拥有独立 source ID/hash/manifest。英文 TXT 是派生产物，不翻译、不把派生 TXT 伪装成原件；保存时只写一份 TXT 与紧凑元数据：`parent_source_id`、`parent_sha256`、转换器/版本、正文 SHA、MIME、字节数和质量状态。全量逐行 locator 由固定 extractor 从 immutable raw 确定性重算，不另持久化一张重复的 offset/hash 大表；被 selector 选中的 evidence/package 才保留所需的原件 byte/DOM locator。`derive_text` 与 `select_evidence` 分别复核，query/export 必须验证 source hash 和 extractor 版本，不一致即重算或拒绝。重复原件只复用 hash，不生成新副本。

   这需要一个明确的 `transcript_text` artifact role，而不是伪装成现有 `normalized` 或 `sections`。现有 `artifacts` SQL 表接受任意 role，但 `SourceBundle` 对未知 role fail-closed，`artifact_read_model.read_artifacts()` 也会拒绝未知 role；角色注册还涉及 `ROLE_DEPENDENCIES`、`GENERATOR_REGISTRY`、`scripts/resolve_bundle.py` 和 producer-event 分类。故 G0 前可在专用 run root 的独立合同夹具验证原件/派生/hash/locator，不能把该 role 写进生产 catalog 或共享 bundle；G0 冻结 owner/API 后，再一次性审查这些消费者和迁移规则。禁止把所有行 locator 塞进 `metadata_json`，也禁止从生产 parser 的未知 role fail-closed 规则旁路。
5. 摘要与受限 export 分别复核 `generate_summary`、`export_excerpt`，并带 source ID、原件 locator、派生版本、as-of 与质量状态。rights 撤销、原件退休或政策过期后，索引/查询/导出按版本合同失败关闭，不能继续展示缓存全文。

## 4. G1e 集中端到端验收

在独立且开始时不存在的 run root 中，fake provider 经过真正的 filing-fetch 编排 → earnings-transcripts 工具边界 → company-wiki writer/catalog → TXT 选择与摘要草稿，检查一份合法 fixture 首次入库和重复复用；同一条链验证精确期次/as-of、原件与派生双 SHA、locator 回读、英文不翻译和 filing 成功而 companion 失败的独立状态。拒绝矩阵至少覆盖：无用户授权、无政策、缺少任一所需动作、政策过期/撤销、URL/证券/期间漂移、下载后政策变化、Motley Fool/Seeking Alpha 当前条款、FMP 402、正文带未覆盖的第三方署名。每个拒绝例必须断言零外部正文持久化、零摘要/导出、无无界重试。运行结束校验临时文件树与起始基线完全一致。

**G1e 放行条件：**正式 provider 至少有一个逐动作可核实的来源；原件+派生关系实现并测试；filing-fetch 正式 orchestration 与技能 schema 同步；真实 reader/locator 与 test tree 恢复通过；独立审查收据列出政策版本、样本与未覆盖来源。隔离 writer/importer 的合同测试或公开网页上的可读正文均不能单独放行。若一个正式来源也没有，保留 metadata-only 和 fake E2E 成果，G1e 标为 hold，Worker 不接此队列。
