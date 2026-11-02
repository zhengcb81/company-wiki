# D4-03 — CWP 文档解析层与存储层解耦

状态：**已备妥，尚未派发。** 完成 D4-03（P2）。所有写入只在 company-wiki 仓的文档模型/解析理解目录和相应本仓测试。

## 唯一目标

让 HTML/DOCX/PPTX normalization 和共享 document-understanding engine 可独立导入/运行；纯 `NarrativeUnit`、`DocumentStructure` 和通用解析所需的会话/turn 类型不再归属于需加载 SourceCatalog 存储/采集运行时的模块。

## 写域

允许新建中性文档模型模块；修改 `src/company_wiki/source_catalog/narrative_document.py`、`source_catalog/transcript_layout.py`（仅纯 DTO/通用解析类型的兼容导出）、`source_catalog/__init__.py`（仅兼容导出策略）、`document_normalization/`、`document_understanding/` 中为隔离实际必需的直接 import，以及明确相关测试。

禁止修改 StockWiki/RF/FF/ET、SourceCatalog 业务/数据库 schema、CWP `integration/` 和 ROOT runner；不把整个 SourceCatalog 移出项目，不另造 shared SDK。不得只删异常处理或 lazy import 躲过依赖，而仍在真实 normalize/understand 调用时依赖 storage。

## 先写行为测试

1. 独立新进程屏蔽 `company_wiki.source_catalog.service`/数据库模块，实际 HTML 与小 DOCX 可 normalize、locator replay；实际 `understand_units` 可通过其纯解析/分块策略并产出版本化结构。
2. 上述测试确认 `sys.modules` 没有 SourceCatalog/store/acquisition/automation；另外用现有正常 runtime 复测同一输入保持结果一致。
3. 从旧 `source_catalog.narrative_document` 路径 import 的类型必须是新中性类本身，`isinstance`、构造、immutability、to-dict/序列化和旧消费者不分裂成两份 DTO。
4. 运行完整现有 DOCX transcript/HTML/PPTX normalization 与 D3 document-understanding 受影响小组，特别覆盖 `AnonymousTurnObserver` 的原 TXT/DOCX 行为。只有测试证明确有调用的文件才纳入写域，并在 handoff 列明。

## 通过标准与独审

不能打开/加载 SourceCatalog 实现仍可完成纯文档处理；旧导入路径兼容；无 locator/hash/文本选择行为回归。独立审查者检查反向 import 全调用链、类 identity、重放/序列化、schema 与未覆盖的动态 import；发现的缺陷全部修复再交 ROOT。只跑相关测试，不重跑 CWP 全仓。

交付 `handoff.md`：新模型 owner/旧别名映射、实际导入探针和行为测试、准确版本/commit、独审、残余的 storage-boundary 入口。生产原件/DB/配置不参与、不改不删。

