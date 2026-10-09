# 原三家公司 Fresh 来源准备

状态：只读准备完成；**真实研究、FF 下载和来源登记均 NOT_RUN**。仅中微688012、腾讯00700、微软MSFT，as-of=2026-10-08。未选择新 cohort、未恢复公司池抽样。

当前上下文引用 CWP a901b67f、RF e688b0a2；CWP 接线期间本次观察 HEAD 已推进为 e93e0745。这些不是最终执行 HEAD 冻结；正式运行前 MAIN 重新记录安装版本、配置与有效预算。

## 立即可交接的选择

| 公司 | 已存在，必须零下载 | 必要登记/元数据准备 | 真正未定位的目标 |
|---|---|---|---|
| 中微 | FY2024/2025、2025H1/2026H1、2026Q1、2019招股书；条件适用的融资/收购预案；9月10日官方网络问答 JSON | 已有 dated SourceRef 正常公共读取/登记；2024年报原件真实但 retired，须恢复官方元数据后隔离登记；网络问答保留真实 JSON 表示，不能伪作原始 HTML/TXT | 本节点无必要财报下载项。2026Q3不得凭期间已结束视为截止日前可用 |
| 腾讯 | FY2024/2025 中文年报；2026H1英文122页、Q2英文9页release、September2026 corporate overview archive原件 | production H1 not_found 是未登记；extensionless archive用官方local import零下载。H1报告/overview精确公开日保留未知或旧断言，另取 primary publication proof | 无必要财报下载项；最新call/provider本次未执行，不能以旧译中纪要冒充原语言TXT |
| 微软 | FY2024/2025 SEC HTML；FY2026Q1/Q2/Q3 SEC 10-Q；FY26Q4官方release/call/metrics HTML；FY27全图PPTX；已登记motley_fool原语言TXT | 三10-Q raw真SHA/原iXBRL issuer及FY/Q已验；纠正Dayu HK/FY旧metadata后隔离官方import。PPTX保持OCR partial。TXT publication未知且不是官方HTML同版本 | **FY2026 10-K**：官方索引已证实存在；在当前catalog、目标Dayu目录及明确的封存索引/27cases来源中未定位raw。未来由当前RF→FF US/Dayu→CWP完成一次有界下载；本次未调用 |

微软FY2026 10-K由SEC目标列表证明：公开2026-07-29，期末2026-06-30，primary HTML列示8,585,501 bytes。这个数是发行人索引列示大小，不是本地已下载量或SHA；web原文打开受4MiB工具上限限制。[SEC filing index](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/0001193125-26-323660-index.htm)

腾讯当前官方列表明确有2026 Interim Report及2024/2025年报；未带日期的列表不证明中期报告精确公开日。[Tencent financial reports](https://www.tencent.com/investors/financial-reports/) 旧receipt的2026-08-12是报告/董事会/release印刷日期线索，不能把capture2026-10-08当publication。Overview旧2026-09-16来自官方文件名断言，需保留该证据强度，不能升级为另有公开事件。

## Catalog not_found 与原件缺失

实际公共 `SourceVersionReader.query_local/query_ref/describe_version/verify_version` 覆盖14个精确版本。24个sealed archive对象逐一读取SHA匹配；另外3个sealed SourceRef由当前公共reader验真。原3公司的27个来源条目全部列在 `sealed_cases_sources.json`；无复制原件。两份delivery/archive索引均237 entries，未发现微软FY26 10-K原始HTML。缺失判断仅限明确配置根与这些封存对象，正式运行开头还须重新查询库存。

中微2024年报14,285,291 bytes与微软三份10-Q均实际存在，public query_ref返回`blocked/source_not_active`。只读audit查明：2026-08-01因`legacy sidecar lacks source_url`做Phase15.6治理，2026-08-07再由reconcile-retire正式退休；无restore记录。原件SHA真实，故属于**旧capture metadata治理退休**，没有坏SHA/原件删除的实证。对应PWF `catalog-space-remediation/progress.md`、commit c266a136及每份audit行已记录在 `retired_source_diagnosis.json`。不解除生产标志；是否需要通用storage reconcile交由MAIN。

微软三10-Q原始iXBRL明确CIK0000789019、FY2026/Q1-Q3、各报告期末；它们足以反证旧sidecar的market=HK和Q2 FY2025。中微2024年报旧行2025-04-17与次级公开线索2025-04-18冲突，本次没有得到可验证的精确primary publication URL/date，manifest保留null，不猜。

## Storage 到消费接口

`manifest.json` 为每家公司提供entity/display_name/market/security_id身份payload；canonical_entity_id未解析则null，不编URN。raw路径仅用于storage准备映射；研究agent仅获得writer返回的公共SourceRef和manifest。

哈希名archive对象没有扩展名，不能仅调用register_sources就假称capture-ready。storage应使用现有 `official_source_cli` 的 `official-source-import-request/1` + `--input-file`，显式提供真实MIME/title/kind/period/publication证据，校验原SHA/bytes，生成隔离catalog的SourceRef，download_events=0。capture_receipt记录当次真实local import事件/时间，不伪造HTTP下载；旧历史capture与primary publication分别保留。配置/生产DB/raw不改。

旧网页tool snapshots/交互JSON不是原始HTML；application/json import还须符合现有transcript_material输入，不能假定任意wrapper可登记。现有ref的原件正常走公共reader，未来RF不拼物理路径。

## 官方替代及限制

微软FY27 deck公开日2026-09-02有已保留的MAIN primary调查和SEC Item7.01支持。[SEC 8-K](https://www.sec.gov/Archives/edgar/data/789019/000119312526380280/d291965d8k.htm) 可独立捕获[SEC文本Exhibit99.1](https://www.sec.gov/Archives/edgar/data/789019/000119312526380280/d291965dex991.htm)补第7/18页OCR漏读；必须是新的真实raw SHA/SourceRef，不等于PPTX c02f4e…，不宣称两版本数字或正文完全一致。

官方FY26Q4 transcript HTML可作为原语言管理沟通；保留其独立日期与字节身份。[Microsoft official call](https://www.microsoft.com/en-us/Investor/events/fy-2026/earnings-fy-2026-q4) 原FMP exact ET结果是`unavailable/provider_entitlement_required`；可读envelope不含HTTP status，保留既有ET402限制背景，不补造402 HTTP receipt，不盲重试。motley_fool TXT不是ET成功凭证，官方HTML也不证明该TXT同版。

腾讯旧earnings-presentation .pdf实际987bytes HTML，不能算PDF成功；已有corporate overview是另一份替代IR材料。HK旧FF interim的fatal以及US旧schema调用失败属于旧执行证据，未用于推断当前能力。本次不调用provider、不收费、不做OCR。

## 文件

- `manifest.json`：最小来源组、零下载期间、唯一已证实的新下载目标、接口/身份DTO。
- `catalog_query.json`：公共查询/ref/精确验真和未资格化候选。
- `sealed_cases_sources.json`：27封存来源、24archive真SHA、legacy alias映射。
- `local_unregistered_candidates.json`：真原件SHA/bytes、iXBRL身份/期间、metadata冲突。
- `retired_source_diagnosis.json`：4份retired真实审计/机制/来源PWF与Git依据。
- `primary_publication_proofs.json`：primary观察；当前web观察不是历史raw capture。
- `registered_storage_locations.json` / `storage_target_paths.json`：仅storage准备使用。

仅输出本独占目录。生产source_catalog.yaml前后SHA不变；SourceCatalog读后close，sqlite使用mode=ro；未安装/下载/写原件/修改代码/执行旧模型。旧RF产物只用于控制和溯源，不能代替fresh研究。
