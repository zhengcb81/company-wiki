# D5-CWP-STOCKWIKI — CWP 文档解析产物端口与 StockWiki 消费

状态：**可交给一个独立 harness 实施**。这是 `du11-source-closure-2026-10-18` 的 D5 唯一外包实现包。D4 已按原定范围验收；本卡修复的是后续发现的全局边界遗漏，不重开 D4。

## 1. 目标与当前判断

把文档物理定位、原件读取、格式识别、PDF/OCR/Office 解析、规范化结构、解析质量与定位统一留在 company-wiki（下称 CWP）。StockWiki 对 CWP 文档只消费**无物理路径、带原来源身份及 SHA 的规范化文档表示**，再在自己的层做业务语义、投资研究和证据判断。

当前已确认两端之间缺少这个边界：

- CWP `SourceExportBundleV2` 主要提供 manifest 与 `EvidenceSpan`；可直接 grounding 的原文 span 当前限于 `text/plain`，不足以代表 PDF、DOCX、XLSX 的规范化页/段/表格结构。
- StockWiki 默认 provider 来源路径仍在 `ProviderSourceContext.parse_excerpt` / `localize` 后调用自身 `documents.read_document_excerpt`；`enrich-evidence` 和 `extract-document-signals` 也会走本地文档解析。由此同一原件的解析策略、结构与定位可能在两层分叉。
- StockWiki 的 `DocRootSourceContext` 和公司配置中的历史 `doc_root` 是兼容/导入路径；它们不能成为 provider 主路径的静默回退。

这并不表示 D4 失败。D4 的来源路径虚拟化验收范围成立，但“原件路径被隐藏”还没有证明“通用文档解析只由一个 owner 执行”。

2026-11-05 ROOT 只读复核：company-wiki 主线为 `8bae209b`，与远端 `origin/master` 一致；StockWiki 主仓为 `23d84586`，未见已跟踪改动。另有独立目录 `StockWiki-v2-reader`（branch `codex/source-export-v2-reader`，HEAD `0b406832`），其中是 opt-in SourceExport v2 reader/独立 CLI；该提交没有落实本卡的 `company-wiki-processed-document/1`，而其 `stockwiki/sources.py` 仍调用本地 `documents.read_document_excerpt`。因此它可供实现者了解既有 wire reader，但不算本卡三入口迁移或 CWP normalized-document port 的完成证据；不得从该目录覆盖主仓或假定默认路径已经切换。实施前仍须在目标主仓重新记录 HEAD、分支和既有 WIP。

## 2. 唯一写域和明确排除项

本卡由**同一个实现负责人**在 CWP 与 StockWiki 两个独立 worktree/分支完成，避免生产者与消费者合同分叉。

| 仓库 | 可改范围 |
|---|---|
| `company-wiki` | 现有规范化/解析产物的只读公开 port、pathless DTO/CLI adapter、CWP 本仓契约/集成测试和本卡交接资料 |
| `StockWiki` | source adapter、`run-company` / `enrich-evidence` / `extract-document-signals` 的 provider 路由、隔离的旧 `doc_root` 适配行为及本仓测试 |

不得改 RF、FF、ET、AUDIT、Dayu、IQS、Dashboard，CWP `integration/` 和 ROOT 组合 runner 也不属于本卡写域。不得改 T4/SEM、真实摘要、缓存恢复、RF 采用或固定公司循环；这些主线在 D5 总验收前暂停。不要覆盖两个仓内已有 WIP，不 reset/clean，不复制/删除生产原件，不接触密钥或调用付费供应商。

## 3. 接口与职责合同

先对照当前 SourceRef v2 与 CWP 已有规范化/解析 artifact，复用已有核心，不造第二套 parser、数据库、缓存、预算账或内部类型反射 wire。下述逻辑合同由 ROOT 冻结；实现者只把现有字段映射到该合同、补便携 fixture 和实现 port，不得悄悄改语义。若现有 normalized artifact 没有稳定的消费入口，只在其 owner 层增加薄 port/adapter；不要在 StockWiki 重实现解析器。

### 请求

- 接受现有 SourceRef v2（schema_version、document_id、source_id、content_sha256、byte_size、mime_type）；公司/市场/期次等逻辑身份从 CWP 现有 manifest 取得，不把不存在于 SourceRefValue 的字段硬塞进请求。
- 如真实调用需要指定页/locator、续读或响应预算，定义明确的可选选择项/不透明 cursor/实际 request budget；预算遵循已有请求与运行时预算，不新增固定小字节数、页数、单元数或人工许可门。
- 请求中不接受 `root_path`、`canonical_path`、数据库内部 ID 或消费者可拼出的物理目录。

### 冻结的响应合同

producer-owned envelope 版本为 `company-wiki-processed-document/1`。该版本不得复用或改写 `SourceExportBundleV2` 的字段意义；二者可由 CWP 内部 adapter 映射。外层字段固定如下：

| 字段 | 类型/来源 | 语义 |
|---|---|---|
| `schema_version` | 字符串，固定 `company-wiki-processed-document/1` | 此 reader 的唯一合同版本 |
| `source_ref` | 现有 `SourceRefValue.to_dict()` 形状 | 精确保留 schema_version、document_id、source_id、content_sha256、byte_size、mime_type |
| `manifest` | 现有 SourceExport v2 的 pathless SourceManifestV2 projection | 为消费者提供公司/市场/期次等字段；与 source_ref 的 document_id/source_id/content_sha256/byte_size/mime_type 对齐 |
| `parser` | 对象：name/version/profile | 版本/profile 只反映会改变规范化结果的 parser/OCR/recipe |
| `status` | complete / partial / unsupported | 处理完整性；错误身份、原件缺失、deadline/I/O 沿用现有错误合同 |
| `units` | 按原文顺序排列的单元数组 | 每单元包含稳定 unit_id、kind、locator、content；表格/工作表结构化保留 |
| `continuation` | null 或 producer 可验证的不透明 cursor 对象 | 只有真实分段时使用，明确是否还有后续 |
| `quality` | 现有解析质量/缺口观察对象 | 诊断，不是读取/人工许可门 |

严禁把 legacy `SourceManifest.to_dict()` 直接放进响应：它含 `original_path`。只可用 SourceExport v2 已有的 pathless manifest projection；如果该 projection 不包含解析所需的身份字段，应先由 ROOT 说明再通过版本化合同扩展，不能偷偷泄漏路径或复制数据库字段。

- source_ref 必须逐字段保留现有 SourceRef v2 对象；manifest 使用 CWP 当前 pathless SourceManifestV2 公开字段提供公司/市场/期次身份，不发明重复字段。source_ref 与 manifest 的 document_id、source_id、content_sha256、byte_size、mime_type 必须一致。
- parser 中版本/profile 必须随实际会改变规范化结果的 parser、OCR 或 recipe 变化；不要求把无关应用发布号塞进缓存键。
- status 的语义为：complete 表示此响应包含全体已解析单元；partial 表示明确有未覆盖内容/续页/失败页，必须指出可恢复 continuation 或真实缺口；unsupported 表示 CWP 当前不能处理该格式/结构。原件不存在、身份不匹配和 deadline/I/O 错误沿用现有 CWP 错误合同，不伪装成空文档。
- unit_id 对相同 source SHA、parser/profile 版本、kind 和 locator 应稳定；units 按原文顺序输出。文本单元用文本；表格/工作表用结构化 content 保留行列/单元格边界。locator 沿用或无损映射现有 coordinates，至少保留可用 page、paragraph、table、row、column、sheet/slide 坐标，不得凭空生成坐标。
- 只有确有需要分页时，continuation 使用 producer 可验证的不透明 cursor，例如 `{"cursor":"...","has_more":true}`；任何非终页都不能标为 complete。逐页合并必须可验证无重复/漏单元。无分页时为 null。
- quality 只承载当前确有的解析/缺口观察，不作为人工审核/读取许可。坏掉的可选诊断不伪装完整，但不得否决已独立验证的来源身份。
- 便携 fixture 至少各一条 complete、partial、unsupported 正例，以及错身份/hash、未知核心版本、非终页/重复页反例。若当前 parser 根本不支持某格式，响应要诚实 unsupported，不准为通过测试伪造支持。

响应、错误、日志和游标都不能泄漏原件绝对路径、存储根、SQLite 细节或邻仓安装目录。消费者必须确认响应仍绑定请求的 source identity 与 SHA；不得对同一 buffer 重复做 owner 已完成的原始字节哈希。未知合同核心版本/核心语义给出明确 unsupported；可选诊断扩展应可忽略。

### 分层责任

- CWP 是原件、路径、字节/hash、文档类型、通用解析/OCR、页段表格结构、locator、parser cache 与 extraction quality 的唯一 owner。
- StockWiki 可以做实体/业务语义提取、经营信号与投资研究；这些结果必须引用 CWP 单元及 locator，不能在 StockWiki 再次解 PDF/Office 原件来补通用结构。
- provider 主工作流不得将原 PDF/DOCX/XLSX 下载到 StockWiki 再交给 `documents.py`。原文仍可为既有原文预览/引用功能而经公开 source port 读取，但不是本卡三个业务入口的解析输入。
- 显式用户本地导入若仍需要 `doc_root`，必须和默认 provider workflow 隔离、明确调用，并有测试证明配置残留不会触发静默目录扫描或回退。不要删除仍有调用方的兼容功能；报告确切调用方。

## 4. 实施步骤（按此顺序，不拆成更多小卡）

### A. 冻结基线与 RED 契约测试

1. 两仓分别记录分支、HEAD、工作区与已存在 WIP 路径；先使用独立 worktree，保持作者工区不动。
2. 追踪三个 StockWiki 入口的完整实际调用链和 CWP 当前规范化产物/缓存 owner；在交接记录中给出真实路径与符号，不按本卡假设硬套实现。
3. 先新增/调整端口契约测试：provider SourceRef 的 PDF/Office 处理必须来自 CWP port；模拟一旦进入 StockWiki 原件解析器即失败，确认旧实现先 RED。保留原有业务语义测试。
4. 按本卡已冻结的 `company-wiki-processed-document/1` 生成真实便携 fixture 和反例；给身份/SHA 错配、未知核心版本、partial、unsupported、可选诊断损坏、分页/重复/漏单元准备测试。

### B. CWP 生产者实现

1. 让公开 port 读取现有 CWP parser/normalizer 的 canonical artifact；只有确实缺少时才增加薄 adapter。
2. 文件查找、verified open、解析和 cache 命中均留在 CWP；外部只拿 pathless 规范化结果。读取结果在任何续读/分页下可稳定重放并保持 locator 与单元顺序。
3. 保持实际身份、原文 SHA、资源预算与失败语义；不加重复重算、结果字节硬帽或第二份缓存。
4. 完成本仓 unit/contract 测试和 CWP 对外命令/port 的临时安装、不同 cwd 测试。

### C. StockWiki 消费者实现

1. 三个 provider 默认入口都改为调用同一个可替换的 processed-document reader；只在 StockWiki 的 semantic layer 对规范化单元作业务提取。
2. 删除 provider 热路径上的“localize 原件后本地 parser”调用；保留原文预览/明确本地导入适配时，应与默认流程彻底隔离。
3. 无 CWP 邻仓路径、数据库、PYTHONPATH 时，StockWiki 单仓测试可用 fake public port；不 import CWP 内部模块或私有 DTO。
4. 确保业务结果可回链至 source ID/hash/unit ID/locator，并如实保留 partial/unsupported；解析缺失不得靠 StockWiki 静默重解析原件掩盖。

### D. 一次端到端验收与独立审查

1. 在两个 worktree 的实际 CLI/进程边界运行隔离 E2E：临时 CWP source catalog 中放入受支持的 PDF、DOCX、XLSX 代表样本（至少覆盖两种文件族；选择现有最小可靠 fixture，不为追求文件数制造长跑）。走 CWP verified source → canonical parse/cache → pathless port → StockWiki 三入口中至少一个完整业务调用；另两入口各有真实 adapter 集成用例，不能只测未调用的类。
2. 再用一份当前可读真实样本做 ROOT 只读组合复验：原件 SHA 前后相同、原件不移动/覆盖；使用临时 catalog 和隔离 StockWiki 输出/缓存；确认结果含 CWP locator、consumer 未运行本地通用 parser；无供应商付费调用。
3. 测试目录起始状态先清单化。测试新建的原件副本、catalog、缓存、输出和日志在结束后全部删除；起始已存在对象逐项 SHA/目录快照不变。把恢复结果记入一次 receipt。
4. 由未参与实现的独立审查 agent 在正式交接前做一次整体审查：检查两个仓实际 diff、三入口调用路径、合同演进、测试是否真正经过公共 port、泛化、旧 fallback、隔离恢复及声明的 SHA。发现的问题由实现者修完并做受影响域复验，随后审查最终 commit；不要每个 helper 单独签收。

## 5. 完成标准

- 三个 StockWiki 默认 provider 入口使用同一个 CWP pathless processed-document port，且再无 CWP provider 的 StockWiki 本地 PDF/Office 重解析。
- CWP 是通用文档结构解析的唯一实现 owner；StockWiki 的研究语义仍由 StockWiki 承担。
- 接口不暴露物理路径/内部存储，SourceRef 身份/hash/locator/解析版本/partial 语义完整；无静默截断或假完整。
- CWP 与 StockWiki 都能独立运行各自契约测试；fake port 可替换；无邻仓源码/DB也可跑 StockWiki 单仓测试。
- A/B/C/D 相关测试与一次隔离端到端/真实只读复验全绿且无跳过；真实原件和测试初始目录恢复。独立审查绑定最终两仓交付 commit 并通过。
- 两仓分别提供一份简洁 `handoff.md` 或同一交接中的两个仓小节：起始/最终 HEAD、分支、改动目录、接口 fixture/version、真实执行命令与通过数、真实样本 SHA、临时恢复收据、独审结论绑定版本、兼容调用方与未完成限制。发现的问题在交接前修完，不留“ROOT 后修”。

## 6. ROOT 独占工作与完成顺序

外包负责人不改以下内容；ROOT 在不与该卡共享写域的 FF 仓执行：

1. ROOT 已只读追踪 FF 的 V1/V2 请求、CLI 和 Python API 当前调用方；代码证据与范围记录在本计划 [findings.md](../../../findings.md) 的 2026-11-04 复核项中：schema 2.0 CLI 选择 SourceRef v2，RF source preparation 显式带 --source-ref-v2，V1.2 是技能文档显式 legacy 示例。最终验收时按实际参与 HEAD 重核调用方清单，不把 V1 兼容分支误写成 V2 的默认生产路由。
2. canonical provider 主路径必须使用 CWP SourceRef v2，绝不把 canonical_path 交给 RF/StockWiki。V1 schema 若没有当前生产消费者，可作为隔离的版本化兼容入口保留并由现有测试覆盖；不要为追求“零旧代码”盲删。若找到真实内部生产消费者使用 V1，ROOT 应先将它迁到 V2，再考虑退役旧输出；V1 已有外部消费者时保留其显式兼容承诺并标注边界。
3. FF 单独边界子套件 `--d5-ff-route` 已由 ROOT 实施并通过 3 passed / 0 skipped，收据为 [root-d5-ff-route](../root-d5-ff-route/README.md)。外部交付到达后，ROOT 仍须在 CWP integration 中强制组合测试 CWP port → StockWiki 三个业务入口、FF schema 2.0 默认 pathless 路由和 V1 隔离；不得用该 FF 子套件或临时外包测试替代 ROOT 全局组合验证。
4. 汇总 D5 两仓最终 HEAD、FF 结果与参与版本，运行相关快速域和一次组合 E2E；做一次大节点独立总审并在结果上修复问题。
5. 更新唯一 PWF 状态、正常提交/推送各自有 remote 的改动。无 remote 仓只记录本地 commit，不擅自创建 remote。

**D5 的外包交付 + ROOT 的 FF 调用方定界 + ROOT 组合测试和最终独审全部通过，才叫“解耦完成”。** 这要求现行 V2 主路径不泄露/消费物理路径，V1 若保留也只能作为明确版本的隔离兼容合同。若某个 V1 消费者仍属于活跃内部生产链，必须先迁移，不能把兼容豁免当完成。在这之前，T4/SEM、真实摘要、缓存恢复、RF 实际采用和公司循环均不得恢复。通过后才从本计划记录的下一步重新启动原主线；D5 本身不顺带实现任何这些业务任务。
