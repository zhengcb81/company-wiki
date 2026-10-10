# 排他文件与共享接线

本文件细化冻结 INTERFACES.md 的实现所有权：共享入口改由 MAIN 串行接线；原功能要求没有删减。2026-10-10 三内置 agent 终止后由外部 harness 接管，MAIN 不重启它们。

## 物理目录与文件排他

### M3-JSON

允许：自己的 CWP 工作树中 source_contract/schema.py、compatibility.py、source_manifest.py、source_export.py、evidence_span.py、schemas/；source_catalog/official_json_*.py、official_source_flow.py、official_source_cli.py、canonical_writer.py、normalized_meta.py、source_reader.py；自己的 tests/contract/test_m3_official_json*.py、tests/integration/test_m3_official_json*.py 与 tests/unit/test_m3_official_json*.py。

需要其他 source 层文件时，在自己 INTERFACE_CHANGE.md 列实际文件、理由、接线 patch，交 MAIN 集成；不改本文件以自扩大写集。原 official import/project/read 路径必须最终跑通，不用独立 parser helper 代替公开入口。

### M3-USAGE

CWP 允许：source_catalog/acquisition_service.py、source_operation.py、acquisition_failure.py、download_budget.py、adapter_process.py、bounded_http.py、dayu_sdk_cli.py、tools/dayu_sdk_bridge.py、新 acquisition_observation*.py；tests/unit/test_m3_acquisition_usage*.py、tests/integration/test_m3_acquisition_usage*.py。已有受改 producer 的专属测试可追加实际责任例，但不修改 JSON/模型公共 fixture。

FF 允许：scripts/fetch_filing.py、ff_v2_envelope.py、ff_provider_cause.py、filing_contracts.py、ff_process_transport.py 与 tests/test_m3_acquisition_usage*.py、tests/test_failure_usage_continuity.py。

RF 允许：scripts/filing_fetch_client.py、filing_upstream_cause.py、source_preparation.py；tests/test_m3_acquisition_usage*.py、tests/test_source_failure_observations.py。

### M3-FLOW

RF 允许：scripts/contracts/、scripts/research/drivers.py、scripts/schema_compatibility.py、新 scripts/research/period_flow*.py 或 scripts/contracts/period_flow*.py；references/input-construction.md、新 references/m3-period-evidence*.md；tests/test_m3_period_flow*.py、test_m3_evidence_roles*.py、test_m3_schema_compatibility*.py、test_growth_driver_tree.py、test_research_evidence_roles.py。正式能力/版本文案按实际 registry 更新，不根据提案猜现有 engine 支持。

### MAIN 保留

全部 automation/models.py、store/compaction、narrative_batch_request.py、narrative_batch.py、narrative_model*、narrative_http_model.py、narrative_summarize.py、narrative_verify.py；JSON 的 automation/narrative_formats.py、narrative_select.py、narrative_replay.py、narrative_source_guard.py 公共接线；source_catalog/cli.py 总入口；RF scripts/revenue_report.py、强重算/输出公共入口、SKILL.md、CHANGELOG/发布版本、安装复制。各线给出最小接线 patch/测试，由 MAIN 最终处理。

RF 现有 assurance/runs、output 和所有 owner WIP 均禁止施工线修改。其他根 PWF、冻结审查、Dayu、StockWiki、IQS、ET 及配置/密钥/原始文档也禁止修改。

## I-JSON

SourceRef 2.0 始终代表整页原 bytes。投影另有显式版本、parent refs、issuer proof、parser/layout/version、记录 pointer/token hash 和 coverage；不复制每公司全文。旧 strict version 不偷偷加字段。问题、答复、致辞/未知角色分开，answer-before-question 使用不同 locator 同语义组。

INTERFACE_CHANGE.md 列正式 request/response JSON、schema/parser/export/version、兼容矩阵、imports、失败有限 reason、AUTO 需要的类型/路由/重放/generation patch 和具体测试命令。JSON 公共 CLI 由本线完成；AUTO 共享接线待 MAIN，必须明确分别报告。

## I-USAGE

当前既有 acquisition_usage 的 schema_version=1.0，字段严格只有 response_bytes（非负整数）与 cost_usd（非负有限 Decimal 字符串）；validated_usage 不允许额外字段。当前 acquisition-failure/1 有 usage_scope=operation、provider_started、usage_complete、acquisition_usage 和原 cause。

新设计必须明确区分实际完整值、已观察下界、未知；费用未知不能因为 budget cap=0 或未收到 invoice 写成已知0。若增加 nullable fee/request count/HTTP status/content-type/content-encoding，采用严格、有限、路径无关的 observation sibling 或显式新版本兼容，不偷偷改变旧 1.0 的字段/意义。发给 MAIN 的字段说明和真实样例构成消费者接线依据。

response_bytes 明确为已观察 HTTP 响应正文 wire bytes，不是磁盘原件/解压 entity bytes，也不是 TCP/TLS/header 全流量；统计多 metadata+body 请求的操作范围，外部 provider 内部没回执的行为诚实 unknown。FF/RF 只传递已观察 DTO，不再推测或重复验证身份/MIME。

## I-FLOW

新能力表达 period_flow + period_start/period_end，附实际财政期间定义；annual 与 point_in_time 不改原义。新版本需要支持 3/6/12 月、非12月财年与跨年；计算不暗自乘2或年化库存。旧产物只读 pin 其 emitting version。

机制证据的 claim/role/proposition/scope 与期间限定明确传给 drivers；history_base、融资背景、peer、contrary 不因 source 数量够而证明未来增长。有效同命题机制支持可以保留。新角色能力须显式 version/feature，旧结果不悄悄改。

本线提交消费者图、DTO、版本矩阵与输出/强重算需要的最小 consumer 红测/patch；MAIN 只在大集成节点串行接线。合同绿、置信度高、算术绿都不是预测幅度已验证。

## 唯一大节点联调

收到三卡后 MAIN 依 producer/feature 顺序集成，共同跑各包责任测试和共享入口端到端；正常 hooks、精确 HEAD CI 和安装 SHA 闭包。再进入真实三公司四独立审查。任务卡的自测可以独立进行，无需等另一卡；完整共享链的接收明确由 MAIN 负责。
