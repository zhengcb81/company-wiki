# Legacy 本地原件复用：只读共因诊断

## 结论

现有机制足以读取 **active、身份/期间/历史日期合格的本地原件**，URL 未知仅是 capture metadata sparse，当前 CWP resolver 不再据此强制下载。但历史 Phase15.6 将 metadata 不足与真实撤回一起压成 `retired`：这四份原件被 active-only 查询提前排除，不能进入后续真实字节/身份核验。普通扫描和显式小组登记保持 retired；没有自动本地重新资格化步骤。真实 FF `fetch_if_missing` 因此可能重复进入 discovery/fetch；hash 去重发生在下载后，不能节省该下载。

这是历史状态迁移与当前 composition 的缺口。不能用“文件不存在”解释，也不能把所有 retired 都恢复为 active。当前 status 判断对 withdrawn/损坏来源有必要；需要依据可信退休历史、真实 bytes 和来源事实重新资格化 metadata-only 退休源。

另一个共因：已有 company_raw 同 SHA 的 `official-source-import` 在 dedup 时恢复 active，却不写新的 source facts。它不能独自纠正旧 HK/FY25 声明。外部 Dayu/Dropbox 原件的 local import 可用零下载复制入 canonical 路径；已有 canonical 原件则还需要 metadata reconciliation。两者均不应覆盖 immutable sidecar 或 Dayu metadata。

## 实际输入与读写边界

起始代码 HEAD `979792e0a4105b18aed06dc7053f7bc239de6865`；收尾 main 为 `a40eb065da1bb21d231d2644449e2ecd8a2f98d6`，这段 HEAD 间 source_catalog 无 diff。结构调查使用现有主仓 CodeGraph，随后读取已经定位的实际文件；没有创建新索引。

`actual_raw_readonly_observations.json`：四个明确原件逐一重算实际 SHA/size；生产 SQLite 只以 mode=ro 做四个 document/audit 的定点 SELECT；微软三份 HTML 调用当前 `verify_sec_primary` 验证实际 iXBRL FY/Q/period/CIK。每份不超过20MiB。0 original/catalog writes、0网络/下载/模型。

| 原件 | SHA 开头 | 当前状态与实际证据 |
| --- | --- | --- |
| 中微2024年报 | 3273711f | PDF实际14,285,291B，SHA正确；retired，缺source_url治理历史；原件封面说明FY2024，不代替publication日期证据。 |
| MSFT FY26Q1 | c963d750 | 5,597,461B；实际DEI FY2026/Q1/2025-09-30/CIK789019；retired。 |
| MSFT FY26Q2 | a60bb6a0 | 7,483,278B；实际DEI FY2026/Q2/2025-12-31/CIK789019；retired。 |
| MSFT FY26Q3 | 76945a2c | 7,731,948B；实际DEI FY2026/Q3/2026-03-31/CIK789019；retired。 |

全部有Aug1 `legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)`，随后Aug7 reconciliation retirement；没有 restore audit。9499是既有治理批次记录，不是本诊断重新批量扫描/处理数。旧Dayu sidecar的HK及FY25声明与真实SEC身份/期间冲突，必须保留原声明并以有定位的 source facts 纠正，不能从请求或文件名填新值。

## 实际调用链与责任

| 层 | 当前函数/行为 |
| --- | --- |
| FF已安装入口 | `.agents/skills/filing-fetch/scripts/fetch_filing.py`: `resolve_filing`先identify；`_use_source_query`仅exact v2 reuse_only走source-query。fetch_if_missing走`_resolve_source_ref_v2`的一次ensure，保持resource ceilings；不是失败后无限第二次下载。 |
| CWP只读source-query | `SourceVersionReader._candidate_pages`只查active；`_query_local`按当前实体/market/security/FY/period/publication筛选。`query_ref`对非active具名`blocked/source_not_active`。查询不自动scan/intake。 |
| CWP resolver/eligible | `SourceResolver.resolve`调用`SourceCatalog.query_filing_candidates(source_statuses=('active',))`，再按身份、期间、as_of、候选字节与可复用root核验。`_handle`标记缺https_url，但resolve将capture_metadata_sparse作为diagnostic，仍可reused。 |
| FF read-only miss | retired被排除，返回not_found；reuse_only为0 download。它没有证明磁盘原件缺失，当前通用missing原因没有区分历史metadata retirement。 |
| FF fetch_if_missing | CLI `_run_ensure_command`构造`SourceAcquisitionService.ensure`；`AcquisitionCoordinator.select`先resolver，miss后才adapter.discover；`stage_selected`再次resolver核验，仍miss才fetch。retired在两次查找中都不可见。 |
| 本地登记 | `SourceCatalog.register_sources`→`register_catalog_sources`→`scan_catalog`；scanner `_upsert_document`遇retired只更新last_seen，locations保持retired。完善sidecar后重扫也不能自动复用。 |
| 下载/本地import后的去重 | `CanonicalSourceWriter._commit_staged`先`_reactivate_if_retired`，再`_existing_original`。后者只查company_raw且实际hash匹配，Dayu/Dropbox外部root不是这个copy dedup目标。网络下载已经在这之前发生。 |
| local official import | `import_official_source`没有provider网络，严格要求source_url和真实bytes/capture observation，调用同一writer。仅`status==imported_new`分支调用`record_source_facts`，已有canonical dedup不纠正旧facts。不能为未知URL造一个official URL。 |
| 现有恢复/纠正原语 | `store.restore_document`保留retire audit并追加restore audit，但不验原件/不改facts。`SourceCatalog.record_source_facts`真实verified open，追加hash-bound、superseding assertion，当前事实与explicit null保留；它要求active，因此两个CLI手动顺序调用不是所需原子恢复API。 |

已安装FF v2 `filing_contracts.validate_handle_metadata`明确把URL/collector/capture_ready当诊断；校验独立published_date与as_of，不把nullURL当拒绝。legacy path-bearing `validate_handle`仍要求capture_ready与HTTPS。此诊断针对当前v2链，不建议放宽legacy合同。

Dayu adapter `enrich_dayu_metadata`保留明确provider元数据；缺URL时可用完整accession+CIK+primary_document构造SEC URL。它不从现存HTML DEI自动改旧HK/FY25，且scan的retired sticky使enrichment不能修复本次退休源。CWP新fetch bridge的`verify_sec_primary`是可复用的证明能力，当前入口用于新fetch验证，不是历史本地资格化步骤。

## 本地反例：真实CWP API，offline provider seam

`local_counterexample.py`及`local_counterexample_receipt.json`验证六个责任观察：

1. active+current source_url=null：source-query found、resolver reused_equivalent，capture_ready=false/missing https_url。URL unknown本身不是当前reuse缺陷。
2. 同一完整原件被metadata-only retire后：exact ref blocked/source_not_active，business query not_found，resolver missing；scoped register后仍retired。
3. reuse_only不调用adapter；fetch_if_missing触达offline discover1/fetch1。fetch故意具名抛错，没有写download receipt、没有成功下载、没有真实网络。它证明重复获取路径可达，不伪称已完成provider capture。
4. 现有audited restore原语使已合格facts的同bytes重新可复用，URL继续null，零下载。
5. 旧HK/FY25事实 + retire + 正确current declaration的local official import：同SHA deduplicated、active、download_events0；旧HK/FY25依然存在，正确US/FY26query仍not_found。
6. 现有source-facts原语纠正US/FY26/Q2并保留unknown URL：query found、resolver reused_equivalent、真实public源读取bytes匹配，零下载。

独占短TEMP finally清理，生产source_catalog/source_acquisition/local_ocr配置SHA前后相同，网络socket guard触达0次。首个sandbox提供的TEMP因WinError5在创建fixture第一步失败，失败单据保留；没有catalog/provider代码执行。该namespace路径在普通host已不存在；后续正常owned TEMP实际执行且finally absent。未用全套测试或provider/模型。

## 现有机制是否足够

存储、真实hash验证、source facts/audit/idempotency原语基本够用；当前composition不够。不能靠每公司手动copy/import、原地改Dayu元数据、restore所有retired、删除source_status过滤或放宽as_of/identity断言完成需求。需要一个通用、有界local reconciliation节点：在真实acquisition miss之前识别metadata-only历史原件，验证并原子更正facts+恢复合格location，返回原content-addressed SourceRef；不制造download event、HTTP200或原件retrieved_at。

施工方案见 `IMPLEMENTATION_CARD.md`。本次只提供诊断/卡，没有启动实现或改生产状态。
