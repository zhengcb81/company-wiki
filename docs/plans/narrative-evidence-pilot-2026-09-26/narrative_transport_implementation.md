# N3a：持久叙述包跨进程读取

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 范围和顺序

E-B 已实现内容寻址工件、projector 和 `narrative-bundle/2.0`，本步复用它们。仅改 company-wiki，不改 RF、StockWiki、IQS，不启动生产 Worker。G-A 当前主线 FF `c47c397` → CWP `2e674cc` → RF `0573c40` 的正式测试于 2026-10-03 通过（1 passed，8.69s，独立测试根退出删除）。此前 FF→ET→CWP 的 191 项节点包按 Phase 58 收据引用，不重复运行。

先写合同/集成 RED，再实现精确工件读取、共享 locator replay、transport 和 CLI。只设本仓一个验收节点；消费者各自接线后才验 G-C。

## 冻结接口

- `narrative-ref/1`：`schema_version`, `artifact_version_id`, `artifact_sha256`, `byte_size`, `source_ref`。嵌套 `source_ref` 复用原始 SourceRef `2.0` 的六字段，不改变其 wire。不得输出 object key、存储根或永久路径。artifact version 必须精确读取，不能被同原文的新摘要替换。
- `narrative-reference-request/1`：`schema_version`, `source_ref`。仅发现该原文最新 visible 包并给出严格 reference；这是 metadata reference，不宣称原文/as-of已验证。
- `narrative-read-request/1`：`schema_version`, `narrative_ref`, `as_of_date`, `expected_source`。`expected_source` 必须含 `canonical_entity_id`, `market`, `security_id`, `document_kind`, `fiscal_year`, `fiscal_period`；null 明确表示该字段无请求约束，非 null 必须匹配当前 manifest。不能将 unknown 补成用户想要的身份/期间。
- `as_of_date` 为有效 ISO 日期。历史使用必须同时具备可解析的 publication 和 UTC retrieved_at，二者不得晚于该日末；未知公开时间具名拒绝，不能用 call date、生成日期或文件名替代。工件可以在之后生成，用现存原文做历史查询。
- `narrative-read-receipt/1`：成功输出 `status=ok`, `narrative_ref`, `as_of_date`, `manifest`, `source_read_policy_sha256`, `read_at`, `locator_count`, `selection_status`, `quality_status`, `replay_status=verified`。质量状态原样保留，不把 partial/needs_review 升为 verified。拒绝仅输出 `schema_version`, `status`, `reason`。

## 每层责任

1. Store：增加按 artifact version ID 精确读取，只允许 visible，核真实 artifact SHA/size、当前 active primary source；既有 latest 内部接口保持。
   正式 CLI 使用独立只读 facade，复用 ReadOnlyCatalogReader，不构造 CatalogStore、不初始化/迁移 schema、不取得 BEGIN IMMEDIATE 写锁。缺库拒绝且不创建目录/数据库；测试核主库和现存 WAL 内容不变。SQLite mode=ro 允许运行时空 WAL/SHM 缓存，不能用 immutable 忽略真实未 checkpoint 数据；所有测试缓存退出清理。
2. 共享 replay：从已有 verifier 提取 PDF/TXT/HTML/JSON 原文 locator、material lineage/byte bindings 的核验；新 transport 与生成 verifier 使用同一规则，不调用私有 handler。
3. Transport：核严格 canonical bundle/预算/引用 → 当前 SourceVersionReader 实开原文并核 SHA → 当前 manifest 与请求约束、日期 → 所有 locator 回放 → 再核 source 当前状态。bundle 的生成 policy pin 保留为 lineage；读取使用当前 policy，不因迁根改变逻辑引用。
4. CLI：`company-wiki-narrative-read --config ... --operation reference|read`，stdin 有界 UTF-8 JSON、拒绝重复键/NaN/未知字段。reference stdout 返回 canonical reference、stderr metadata-only receipt；read stdout 是精确持久 bytes（不补换行，消费者自行验 hash），stderr 一行 bounded receipt。错误 exit 2，stdout 空；配置路径只作部署注入，不进入数据对象。CLI 不打印异常或原文。

## 测试和交付

- 单元：strict reference/request、坏版本/字段/类型/hash、超限/重复 JSON key；旧 artifact reference 不随新版变化，prepared 不可读。
- 集成：原件与工件篡改、撤回/primary替换、错身份/期间、未来/未知日期、生成policy旧但当前policy可读、skip/partial质量、locator/JSON byte binding错误。
- 本仓节点：正式生成/持久化 → CLI子进程 → stdout hash/receipt → PDF及TXT/原JSON locator回放。使用已有真实样本 oracle（可访问才跑，不把合成PDF冒充真实财报）；缺样本明确保留真实样本项。未知publication JSON必须拒绝历史read。
- 仅用唯一独立短测试根，测试前后所用原件SHA一致；结束删本次DB/WAL/cache/下载产物和进程，不更改生产配置/catalog。开发期间跑受影响测试，交付时一次节点包与静态门，不重复全仓coverage。
- 生成当前producer golden并记字段/CLI/测试命令，交RF、StockWiki各仓owner薄adapter。CWP本步通过不等于G-C完成；生产Worker继续paused。
