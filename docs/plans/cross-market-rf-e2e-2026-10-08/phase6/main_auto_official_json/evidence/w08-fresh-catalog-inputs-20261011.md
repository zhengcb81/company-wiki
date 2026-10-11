# W08 新隔离来源库：精确输入与现有能力（只读，2026-10-11）

状态：READ_ONLY_PREPARATION。仅针对既有中微/腾讯/微软32个exact原件；没有新scope/config/DB/原件写入、scan、provider/model或Git/install操作。读取旧三库使用sqlite mode=ro/query_only；只取32 SHA对应的关系和元数据，未打开/重哈希原件。身份cache只读3个小JSON并经现有public SecurityMasterStore.load/Resolver验证resolved，未refresh。本文不改已冻结的provenance交接。

## 1. 选择结论

建议新owned TEMP中为三家公司分别新建catalog、canonical原件写根、AUTO、work；旧原件用readonly roots精确register，**不复制原catalog DB，也不用整湖scan**。旧32 SourceRef的document/source ID由真实SHA定义，register原字节后可保持身份；新Ref和读取策略仍由public reader实际签出，不手造带缺字段的Ref。

“旧mFresh catalog readonly+新AUTO”确实适合只读query/open/现有artifact回放，并省掉登记和事实重放；但这轮要新增0.7叙述版本、official JSON import/project/persist。NarrativeArtifactVersionStore发布需要写catalog的narrative_artifact_versions等表，official projection也写其所属catalog；新AUTO并不能把这些写入隔离到另一个库。FF reuse_only在query not_found时还会调用CWP local prepare（可能登记/metadata修复）；因此不能保证旧catalog只读不变。现有模型没有“readonly旧catalog+另一个artifact catalog”的公开联合查询绑定，不能临时发明跨库facade绕过。

本方案新库需要重放既有source-facts，避免弱侧栏重建后把已真实澄清的出版/身份/期间丢掉。真实缺口继续unknown，不把所有旧资料强行改active/合格；新库登记不是SQLreactivate旧生产记录。

## 2. Root映射与精确原件表

所有路径均为**来源owner登记输入**，不是RF/FF消费者的物理路径接口。消费者仍用SourceRef/SourceExport及source reader。表中SHA前12位在这32份中唯一，完整原Ref/SHA在对应M3 execution/source_ledger.json和旧sources表；不重复输出32份完整metadata。各选一个首位置，共32原件，另2处same-SHA US年报位置仅作为备选。

旧root的真实基址（新config映射为readonly，root_id可重命名但相对路径不改）：

- `company_raw`：每公司的 `C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/<company>/companies`；新config改名`prior_scope_raw`，kind=directory/read_only=true。它不是新canonical写根。
- `existing_company_raw`：`C:/Users/郑曾波/Projects/company-wiki/companies`；kind=directory/read_only=true。
- `existing_dayu_portfolio`：`C:/Users/郑曾波/Projects/dayu-agent/workspace/portfolio`；kind=dayu_portfolio/read_only=true；不改Dayu代码/元数据。
- `existing_dropbox_stock`：`C:/Users/郑曾波/Dropbox/Stock`；kind=directory/read_only=true。
- 新scope单独`company_raw`：`<new-company-root>/companies`，kind=company_raw/read_only=false；供真实新下载和86 JSON import使用，不将旧mFresh树设成写目标。

沿旧config的reusable_root_kinds=[company_raw,directory,dayu_portfolio]。旧RootSpec未声明adapter_id；不要为这些既有弱legacy sidecars突然加sidecar_filing_v1严格admission。新exact register按现有同kind/storage责任进行，metadata不足由下面同SHA source-facts负责；这不是移除原件验真。


### CN-688012（7个原件）

| SHA12 /kind | 登记root及精确relative path | 当前publication /事实来源 |
|---|---|---|
| `182e2062fed9` /semi_annual_report | `existing_company_raw` / `中微公司/raw/financial_reports/semi_annual/2026-08-19_cninfo_1225482884_2026年半年度报告.pdf` | 2026-08-20；verified sa-599e8a3196ab44509320b27916d488da；sidecar=有 |
| `19cdb41e03b2` /prospectus | `existing_company_raw` / `中微公司/raw/prospectus/中微公司：首次公开发行股票并在科创板上市招股说明书.pdf` | 2019-07-16；verified sa-71870aa9190c4801924de4aadb934eda；sidecar=有 |
| `3273711fbb79` /annual_report | `existing_dropbox_stock` / `工业与信息化/电子/中微公司/中微公司：2024年年度报告.pdf` | unknown；无verified source-facts（侧栏/原登记）；sidecar=无 |
| `91ae4978b694` /semi_annual_report | `existing_company_raw` / `中微公司/raw/financial_reports/中微公司：2025年半年度报告.pdf` | 2025-08-29；verified sa-bfb4112397e84a37bee5ae1fa3007b5c；sidecar=有 |
| `ab7bb0076b2a` /quarterly_report | `existing_company_raw` / `中微公司/raw/financial_reports/中微公司：2026年第一季度报告.pdf` | 2026-04-28；verified sa-28ccb00b0ee748fa835fe83af9ed63cb；sidecar=有 |
| `d64c410832f2` /annual_report | `existing_company_raw` / `中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf` | 2026-03-31；verified sa-ff5a05286e134126adb94b74c6f1c494；sidecar=有 |
| `0c5481a9e5f8` /other | `company_raw` / `中微公司/raw/other/unknown-date_official_0c5481a9e5f8e9f14348cddef5f60f2212b651685190078520908216c9526116_SEMI July 2026 semiconductor equipment forecast.html` | 2026-07-14；verified sa-80e63f4e15414c1582fcef66d65c746b；sidecar=有 |

### HK-00700（14个原件）

| SHA12 /kind | 登记root及精确relative path | 当前publication /事实来源 |
|---|---|---|
| `1cfbaab885ce` /prospectus | `company_raw` / `騰訊控股/raw/prospectus/unknown-date_official_1cfbaab885ce9df493e82358d2a07d4dd1ef017c1190f5408081f326b4814fa6_Tencent GMTN Offering Circular 2026.pdf` | 2026-06-09；verified sa-d3a9ae4227c94b58b10dc7042fcb1027；sidecar=有 |
| `4170f80ec854` /semi_annual_report | `company_raw` / `騰訊控股/raw/financial_reports/semi_annual/unknown-date_official_4170f80ec8548ea2fb92ec04691a4b252a52de20941e48fb516baf3f98082639_Tencent Interim Report 2026.pdf` | 2026-08-25；verified sa-8f7d2c19d5754681b7e95aef2d61bdf9；sidecar=有 |
| `64d8d2038eee` /investor_relations | `company_raw` / `騰訊控股/raw/investor_relations/unknown-date_official_64d8d2038eeef993571b96bb3361b6f1a567d6e84157eb16af20d2fd9a095f0a_Tencent second-quarter and first-half 2026 results.pdf` | 2026-08-12；verified sa-465ea7e0f8194ea897aef79736e4399f；sidecar=有 |
| `70f529984a87` /annual_report | `existing_company_raw` / `腾讯/raw/financial_reports/annual/腾讯：2024年年度报告.pdf` | 2025-04-08；verified sa-b96640a0423b46e59169973c0ae99199；sidecar=有 |
| `8bf85e0cc19d` /investor_relations | `company_raw` / `騰訊控股/raw/investor_relations/unknown-date_official_8bf85e0cc19d42784ba3faec42c8ddced1b8c378fcdea6f943839fcc51823704_Tencent Announces 2025 Second Quarter Results.pdf` | 2025-08-13；verified sa-0c2e1db31da3400bb1c36b2a8d8acbe8；sidecar=有 |
| `a9b0a5d6c68d` /investor_relations | `company_raw` / `騰訊控股/raw/investor_relations/unknown-date_official_a9b0a5d6c68d6ce70b38607b8604d12fc8a150de9dac8bd8dc8679249c586389_Tencent Corporate Overview September 2026.pdf` | unknown；verified sa-62059eb355044e57ae3b56508bf9416b；sidecar=有 |
| `d19f183452e9` /annual_report | `existing_company_raw` / `腾讯/raw/financial_reports/annual/腾讯：2025年年度报告.pdf` | 2026-04-09；verified sa-f64b28bc27844a9e9eb4889eeae30479；sidecar=有 |
| `ef3baa5008e1` /quarterly_report | `company_raw` / `騰訊控股/raw/financial_reports/quarterly/2026-05-13_hkexnews_12157227_截至二零二六年三月三十一日止三個月業績公佈.pdf` | 2026-05-13；无verified source-facts（侧栏/原登记）；sidecar=有 |
| `f59bd57d4ff7` /prospectus | `company_raw` / `騰訊控股/raw/prospectus/f59bd57d4ff720ed78730926212adcad7e53da72e8e657156af8bf9ab1cd227d.pdf` | 2026-06-17；verified sa-ff8246d35c3c43168e7dd56c3a2674b5；sidecar=有 |
| `6c7326ffe15c` /prospectus | `company_raw` / `騰訊控股/raw/prospectus/6c7326ffe15c6035ea0d5275288572e8cae57b052feb38580aeed82b97246601.pdf` | 2026-06-10；verified sa-32cf147916534411a663eae612df74d6；sidecar=有 |
| `980c2b43c51f` /prospectus | `company_raw` / `騰訊控股/raw/prospectus/980c2b43c51ff2cb82afa4fa5bd4aa13f8e68d43c42139ef21561309931c5a0a.pdf` | 2026-06-17；verified sa-8b6e7ec87cda4abc8a9771ca232b1959；sidecar=有 |
| `b9eeeb4d903d` /investor_relations | `company_raw` / `騰訊控股/raw/investor_relations/b9eeeb4d903d8a15f4a3df59fbf9b513845301665991012215b0956ff5874632.pdf` | 2026-08-12；verified sa-2786a2bbbdb14c17bf2f9fde4991a9f6；sidecar=有 |
| `3443ca2fe1e7` /other | `company_raw` / `中国音像与数字出版协会/raw/other/3443ca2fe1e7680da42c45236255879f835bdf2f15186d129254e66bb992acbf.html` | 2025-01-17；verified sa-40fecaed1f6e450c878b2cddcba5f8df；sidecar=有 |
| `d5a6d246b599` /other | `company_raw` / `中国音像与数字出版协会/raw/other/d5a6d246b599a1859d2d64e302fa771d82951e51b663321a00972670b84f6840.html` | 2025-12-19；verified sa-dd5c963b13c94802b6d5b926149d440d；sidecar=有 |

### US-MSFT（11个原件）

| SHA12 /kind | 登记root及精确relative path | 当前publication /事实来源 |
|---|---|---|
| `2c86b6365b53` /annual_report | `company_raw` / `MICROSOFT CORP/raw/financial_reports/annual/2c86b6365b5308b546f9864cbd02f48f9baec3d050e943389accc43a5723516f.html` | 2026-07-29；无verified source-facts（侧栏/原登记）；sidecar=有 |
| `c02f4ea1a271` /investor_relations | `company_raw` / `MICROSOFT CORP/raw/investor_relations/unknown-date_official_c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4_FY27 Segments and Investor Metrics.pptx` | 2026-09-02；verified sa-2504b032b2df4e31bd648d2c7359bc94；sidecar=有 |
| `bdc90bf78dbf` /investor_call_transcript | `company_raw` / `MICROSOFT CORP/raw/investor_relations/transcripts/unknown-date_official_bdc90bf78dbf55ec.html` | 2026-07-29；verified sa-569ec3eab1a1495fbf7d4b49eb54863d；sidecar=有 |
| `8d63b8eaa344` /investor_relations | `company_raw` / `MICROSOFT CORP/raw/investor_relations/unknown-date_official_8d63b8eaa344ed736f568473bd2569c4c13fcad37f56be91347e46244924ea4e_results official communication.html` | 2026-07-29；verified sa-1782e265005a4a838074692893040a4e；sidecar=有 |
| `cf054968a148` /investor_relations | `company_raw` / `MICROSOFT CORP/raw/investor_relations/unknown-date_official_cf054968a1480ca2a4f85cfa5c378f4fc9afdafd934c6836c1c16e016e8619d6_metrics official communication.html` | 2026-07-29；verified sa-2b39634c2c4b471a8515155c3c4bc163；sidecar=有 |
| `c963d7503907` /regulatory_filing | `existing_dayu_portfolio` / `MSFT/filings/fil_0001193125-25-256321/msft-20250930.htm` | 2025-10-29；verified sa-360ce31325cc4d0c86b1ae8d8b2c8c81；sidecar=有 |
| `a60bb6a07479` /regulatory_filing | `existing_dayu_portfolio` / `MSFT/filings/fil_0001193125-26-027207/msft-20251231.htm` | 2026-01-28；verified sa-cea0ed615ff6472b9bce3e0fc8d63fff；sidecar=有 |
| `76945a2c148a` /regulatory_filing | `existing_dayu_portfolio` / `MSFT/filings/fil_0001193125-26-191507/msft-20260331.htm` | 2026-04-29；verified sa-09c68867c6a144f0b1b5303d2750157a；sidecar=有 |
| `99d693f6c154` /annual_report | `existing_company_raw` / `微软/raw/financial_reports/annual/微软_10-K_2025.htm` | 2025-07-30；verified sa-ec904d85cb404c1a85963a6444ed0200；sidecar=有 |
| 同SHA备用 | `existing_dayu_portfolio` / `MSFT/filings/fil_0000950170-25-100235/msft-20250630.htm` | 同一source原件，通常无需再register此备份位置 |
| `43829a12cc9c` /annual_report | `existing_company_raw` / `微软/raw/financial_reports/annual/微软_10-K_2024.htm` | 2024-07-30；verified sa-2700b3d86ee44ad3887192ff66fce090；sidecar=有 |
| 同SHA备用 | `existing_dayu_portfolio` / `MSFT/filings/fil_0000950170-24-087843/msft-20240630.htm` | 同一source原件，通常无需再register此备份位置 |
| `208fdd842f91` /broker_research | `company_raw` / `MICROSOFT CORP/raw/research/208fdd842f91d71ab1ee6fc5a5ec0731d55129f8a831af8380ad343ce7969554.html` | 2026-07-30；verified sa-d94cdbd71e8747eeb5aae511cb19eec0；sidecar=有 |

来源观察：32原件旧库source/primary及上述位置均active；29有verified source-facts，3无（CN FY24、HK2026Q1、US FY26 annual）。active只是目录状态，不替代下次public reader的真实字节/资格校验。生产retired或not_indexed不同于这些旧scope状态；新库不改生产状态。

## 3. public register的实际粒度与命令

现有接口 `SourceCatalog.register_sources(*, root_id: str, relative_paths: set[str], budget=None) -> ScanReport`，CLI：

```powershell
& $w08Python -B -m company_wiki.source_catalog.cli --config '<new-company-root>/config/source_catalog.yaml' register --root-id existing_company_raw --relative-path '中微公司/raw/financial_reports/中微公司：2025年年度报告.pdf'
```

每同root的多个表中路径用重复--relative-path，一次登记：CN production5/oldscope1/Dropbox1；HK production2/oldscope12；US production2/oldscope6/Dayu3。不要传公司大目录、全root或scan；不把侧栏自己当原件。

`SourceRegistrationScope`选择的是现有**source group**。company_raw/directory成对读取确切文件及.source.json，不做missing sweep；Dayu精确primary路径扩展为同accession group，读meta.json和原attachment。这是既有分组语义，不能宣称只会读那一个HTM。US三Q groups：

- MSFT/filings/fil_0001193125-25-256321
- MSFT/filings/fil_0001193125-26-027207
- MSFT/filings/fil_0001193125-26-191507

这3目录各有meta.json、原HTM、84B的HTM.source.json、XSD、HTM_XML，共15文件/51,772,580B（metadata/附件也在受限组中）；新register可能哈希整个这3组，不扩大至全部Dayu，也不复制这些字节。若预算仅允许primary读，现有Dayu group接口并非单文件强裁剪接口，应显式记录这一范围而非编造不存在的参数。年报已有production位置可选，通常不用另登记2个Dayu年报备用组。

确切文件注册后使用新catalog SourceVersionReader.query_ref(documentID,sourceID,SHA)取真实Ref；SourceRef身份无需通过目录名重建公司。不能直接INSERT旧documents/assertion或clone旧DB来缩短登记。

## 4. 元数据和资格的真实来源、原样重放

- 原件的.source.json由现有scanner在新catalog形成acquisition声明；不少CN/production侧栏只含源标题/market/security_id，缺原URL、期间和published_date。只register不足以复原旧实际资格。
- HK H1新raw侧栏source_url为Tencent E700_IR.pdf、published_date=null；真正已澄清publication=2026-08-25和HKEX same-SHA URL在旧 assertion sa-8f7d2c19d5754681b7e95aef2d61bdf9。其published_date证据有同SHA、HKEX官方16:53事件、实际proof_artifact `m3-20261009T184946-hk-00700/execution/h1-same-sha-proof.json`。须复用这一原proof，不能恢复旧“日期未知”，也不能把sidecar捕获时刻当出版时刻。
- CN2025年报publication=2026-03-31来自真实CNINFO announcement1225062431；H126=2026-08-20是epoch按UTC+08公告时间，不能由文件名2026-08-19代换。IPO2019-07-16来自真实announcement1206447929。这些是旧SHA-bound assertion外部证据，不是重新猜日期。
- CN FY24没有verified assertion且publication unknown；Dropbox原件没有sidecar。新register后仍metadata gap，不从Apr17/18候选或其它公司的证据fabricate资格。
- HKoverview published_date明确null，不借September标题补9/16。CADPA资料属于行业原出处，不能因为在HKscope目录里就写成Tencent管理层资料或强附security_id00700。
- US三Q对应Dayu .source.json实际只有84B，且market写HK、无真实期间；必须保Dayu native group/meta原资料并复用已有US/CIK/period/title source-facts。不能配置generic directory只读那份薄侧栏而漏meta。现有nativeDayu adapter优先group meta并提供source provenance；新库事实重放仍需要。
- US旧Q的primary-dei证据虽有原SHA/CIK issuer_record_id，但不是所有fields均带当前sec-primary-dei/1方法/primary_cik，不能偷偷补这些字段来让_reusable_sec_scope命中。原样保持后，真正filing_reuse读由当前source层原HTML DEI抽取再次核验；不要让每个消费者重复解析，也不要拿导入标签冒充原DEI观察。

现有public写入口是 `record_source_facts(*, ref: SourceRef, facts: dict, evidence: dict)`，它对新catalog已登记Ref验实际字节，append事实并原子更新query projection；不需要candidate/review/许可文件。CLI请求**精确3字段**（无schema_version）：

```json
{"source_ref":<新库真实Ref2>,"facts":<原verified assertion.evidence_json.source_fact_patch>,"evidence":<同一原assertion.evidence_json.source_fact_evidence>}
```

```powershell
& $w08Python -B -m company_wiki.source_catalog.cli --config '<new-company-root>/config/source_catalog.yaml' source-facts --request '<owned/requests/source-facts-<actualSHA>.json>'
```

读取旧proof由CWP来源owner：现有 `get_verified_assertion(old_catalog.reader, source_id, content_sha256, reader='steady')`，核同documentID/sourceID/SHA及verified可见版本，取该原patch/evidence；不由RF/FF直接SQL读物理库。SourceExport v2已有展示事实但没有全套field proof；不能反过来把manifest字段全标“原件抽取已验证”。旧proof里的locator、value、observed_at、content_sha256、proof_artifact/metadata_sha保持原样，不编一个新观察时间/URL/字段锚点，不复制旧assertion_id当新库行ID。新ID由source-facts服务分配。

每个changed fact必须有matching evidence[key].value+locator；null是explicit unknown仍保留。若原fact缺证明或旧patch不能通过现有合法字段校验，记录具体gap，不用默认值补齐。对3个无assertion的来源只沿真实sidecar/native metadata；不足即partial。本文没执行record_source_facts、没有偷偷复制DB状态或旧research答案。

## 5. 身份cache实际文件与能力

- `C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/CN-688012/catalog/security_master/cn.json`：564B，1条CN，SHA `306e0f3211149a25af60a64349e8f7a3d121b0629f82dfbe16b8d3fb049fd555`；既有retrieved_at=2026-07-19T07:53:37Z。
- `C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/HK-00700/catalog/security_master/hk.json`：943B，1条HK，SHA `47ac646b27eff6400971283cef1a7908b56b0594c60a6bd7851ad860cd50abc1`；既有retrieved_at=2026-07-19T08:12:43Z。
- `C:/Users/郑曾波/AppData/Local/Temp/mFresh-me8cejn4/US-MSFT/catalog/security_master/us.json`：731B，1条US，SHA `12e0896eb1dc6b6bab1a508870a2cdb4f827a77bd44cfefb6e3cf1a8bf4d747a`；既有retrieved_at=2026-07-19T08:04:38Z。

三文件共2,238B，现有SecurityMasterStore.load(markets=(market,),require_all=True)和SecurityIdentityResolver.identify各自ticker均真实resolved，本次无refresh/写。可由ROOT未来只复制对应这1文件至各新catalog/security_master/{cn,hk,us}.json，保完整旧bytes/SHA；不抽出单record重造snapshot，不刷新全市场网络表。

Standalone identity_cli有--cache-dir；source_catalog.cli identify/resolve/ensure有--identity-cache-dir可读旧目录。但当前FF identify不传此参数，SourceResolver别名索引固定 `<catalog_dir>/security_master`，source issuer默认同一路径；CatalogConfig也没有identity-cache配置键。故仅在某一次identify指定旧cache不能替代全链默认路径。定点复制这3小文件比引入symlink/新环境变量/跨仓cache分叉更稳，也不需要新的人工门。

## 6. 两方案与真正NextStep

| 方案 | 真正可做/利点 | 限制与建议 |
|---|---|---|
| A 新catalog+readonly old roots+新AUTO/work | 原件0复制；只32原件/明确groups登记；facts与小cache复用；新增0.7 artifacts及86JSON写在新scope；原旧sealed可保持不变 | 需要29事实重放；Dayu3组metadata/附件范围明示；CN FY24等未知保留。推荐本次真实W08。 |
| B readonly旧mFresh catalog+新AUTO/work | 既有identity/facts/provenance/query和旧artifact立即读回；无需register/事实重放 | 新artifact或projection会写旧catalog；FFmiss fallback可能prepare写。不能同时要求全流程新增摘要和旧sealed完全不变。仅用于先验read-only/preflight对照，不宣称作为本轮完整新运行方案。 |

ROOT下一步只需在既有大节点：冻结新3scope路径和小root映射→复制上述每公司1身份cache→按表root分组public register→来源owner原样转用29 verified patch/proof到新public source-facts→public exact读取/复用资格检查及真实32 SHA范围→86原JSON新local import/project→既有有限configured batch/RF与四审。不加每文件人工签收，不全DB恢复演练、不改Dayu、不因老production缺index重下。

新scope创建/登记/原字节复验是将来ROOT实际执行，本报告仅给准确输入与风险，不签fresh目录已经存在，不签三家研究完成。若后续新capture合法取得缺口材料，只写新canonical根；原publication/资料经济意义仍由来源和RF所属责任层判，不用目录名授权或推断。
