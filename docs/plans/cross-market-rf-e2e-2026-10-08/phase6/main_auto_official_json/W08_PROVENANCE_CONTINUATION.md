# W08 官方 JSON 原捕获来源的 producer 责任

## 已确认事实与目标

只读 operational 盘点确认 src/company_wiki/source_catalog/official_json_import.py::_commit_shared 把所有共享JSON parent的主source_url写成 https://official.invalid/shared-json；实际 validated.capture_receipt 同时存为 provenance_extensions.official_capture。无需再下载原JSON、不重写原件。必须先查 source schema、capture contract及公开export路径：真实捕获URL存在时由所属 producer 保留，不能由每个RF/FF消费者解析物理sidecar补救；缺URL保持诚实未知，不能捏造正式primary URL。

## 排他写集与界面

内部owner只允许 official_json_import.py；确有schema/type原因才必要窄改 canonical_writer.py 的 shared original 导入路径，先报告原因。只必要既有 import/writer 责任test和独立新增provenance contract test；证据独占 evidence/w08-provenance-repair/。不动P7 official_json_projection/snapshot、pure selector/shared AUTO/store、RF/audit/FF/ET、配置/raw/Git/install或中央PWF。输入继续官方import/2+既有capture_receipt，不新增许可/registry/canary或第二份payload。身份/as-of/原字节SHA仍所属层验证。

## TDD与一个大节点

1. 实读实际 capture URL 字段/所有调用方，不猜request_url/url结构。以真实capture格式的现有两issuer/两parent JSON夹具先固定公开import→持久parent SourceRecord及SourceExport实际来源信息的RED；没有网络/模型调用。缺URL和旧capture/import恢复路径明确真实语义；不能仅改expected字符串假验新route。
2. 单producer接线，优先现有原捕获字段与已验证来源元数据。不得选择JSON正文中任意URL当primary；不复制全文、不按issuer复制母页、不做逐URLHEAD检查、不编日期/名称/HTTPstatus。若旧row不可变或确无URL，保留原row/bytes，追加已有capture provenance版本引用或报告实际限制，不能覆盖旧immutable record。
3. 一次集中import/writer公开小组，断言原raw SHA/唯一母页/跨issuerparent绑定、去重二次0下载、恢复路径同原capture；公开export为消费者提供足够原来源字段。保护原件/config/旧sealed，ownedTEMP恢复，0vendor/model/fee。
4. owner冻结source/test/RED/GREEN/恢复交接。ROOT在既有正常发布大节点集中审查并normalcommit/push/exactCI，不按helper新增人工签收。若当前export已能直接给真实URL，则记录反证/使用方式而不硬改schema；不能强制为了任务造代码。

## 未完成界限

这只解决来源URL/provenance表达，不代表SSE86页新source资格、真实摘要或三家公司三年研究四审已完成。费用沿native母账含unknown保守hold；下游研究独立判断捕获日期、as-of、期间与资料经济意义。
