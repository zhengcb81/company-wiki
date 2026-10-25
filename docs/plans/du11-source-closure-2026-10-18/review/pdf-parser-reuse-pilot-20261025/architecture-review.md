# PDF成熟解析器复用：现有接缝与最小适配建议

日期：2026-10-25。调查者：独立只读架构调查agent。基线：`a00c5f99146a3d6747283a09d91af4645b28ec51`。状态：**SOURCE_REVIEW_COMPLETE / RUNTIME_NOT_TESTED**。

本报告读取源码及已冻结的CF2/CF3证据，没有执行真实PDF、模型、网络、数据库写入或全量测试。ROOT另行负责真实Docling试验；本文不能作为其准确率、速度、离线可用性或生产接入已通过的证明。只写本报告及同名JSON，不修改主计划、产品、配置、原件和作者工区。

**用户最新范围：A股历史三大财报表由新浪API及W19结构化数据接口承担，不从PDF恢复。此次Docling试点先关闭OCR及表格结构模型（`do_ocr=False`、`do_table_structure=False`），只比较叙述/经营信息及其中金额、单位、期间、百分比和原因的完整性。业务经营指标表与资产负债/利润/现金流三表是不同对象；前者仅在叙述读取确有需要后才按页开启。本文的表格字段与兼容说明是未来适配边界，不是要求此次追加三表解析、启动模型或修改W19接口/作者工区。**

## 1. 已核实的现有架构

```text
SourceRef / SourceVersionReader（存储和真实字节归属）
  ├─ PDF → parse_pdf_bytes → DocumentStructure + NarrativeUnit
  └─ HTML/DOCX/PPTX → normalize_document → NormalizedDocument.structure
                     ↓
             build_observation（du-input/1）
                     ↓
        共享布局 / structure / family阅读策略 / 候选选择
                     ↓
           EvidenceSpan → 精选原语言摘要 → 现有Artifact Store
```

**现有共同接缝是DocumentStructure/NarrativeUnit，不是NormalizedDocument。** `NormalizedDocument.KNOWN_FORMATS`当前仅HTML/PPTX/DOCX，`normalize_document`不接受PDF。`NarrativeParseResult`是`DocumentStructure`的别名。不能在试点中声称已有通用PDF NormalizedDocument入口，或简单向该类塞入`format_name='pdf'`。

| 责任 | 当前真实owner | 接入含义 |
|---|---|---|
| PDF字节→原生块/表格 | `source_catalog/narrative_evidence.py::parse_pdf_bytes/_parse_pdf_document` | 当前PyMuPDF前端；适配器应输出相同源责任层的结构，不另建下游解析器 |
| 结构与选中证据 | `narrative_document.py::DocumentStructure/NarrativeUnit` | 明确原件ID、SHA、解析器、页/段/表/字符坐标、角色、语言和质量 |
| 自动化选择注入 | `automation/narrative_select.py::PdfBytesParser`、`_SelectionWork` | 已有可注入PDF callable；原Protocol列举参数少于当前parse_pdf_bytes实际扩展参数，生产接入时应统一调用协议，而非复制handler |
| 解析器和generation身份 | `automation/narrative_formats.py::parser_component` | PDF当前回落固定NARRATIVE_PARSER_NAME/VERSION，不能换后端却沿用旧身份 |
| 共享输入 | `document_understanding/observation_adapter.py::build_observation` | 从已有units投影，不重解析/重hash/改locator；保留跨来源单位归属 |
| fine geometry | `document_normalization/layout_snapshots` | 接受已有unit IDs和内存snapshot，校验坐标、字符对应、边界；不负责业务关系 |
| 原生字符范围 | `narrative_native_ranges.py` | 当前专属本地DICT块顺序/原块SHA/精确字符offset；不是PDF字节偏移 |
| 连续性证明 | `narrative_continuity.py::NativeSourceContext` | source/page/ordinal/coverage/font/frame等正证，不能只给外部paragraph就强行声称原生连续 |
| PDF重放 | `narrative_replay.py`、`verify_pdf_evidence_spans_bytes` | 同源字节重新解析并核对locator/text/role/kind/parser；目前重放固定调用本地PDF前端 |
| cache决策依赖 | `decision_inventory.py::_versions/_inventory` | 自有结构包已整包hash，PDF前端代码/feature有身份；外部发行包/模型权重/选项尚不是本试点已验证的身份 |
| 产物存储 | `narrative_artifact_store.py` | 现有源绑定和generation内容寻址产物继续使用，不接入Doclib/watch/第二库 |

核实依据是上述源码，不是运行推断。CodeGraph用于结构入口；其`parse_pdf_bytes` callers返回空，尽管源码存在显式调用，因此本报告不把空结果解释成“无生产调用”。两次猜测文件名不存在及首次layout projector路径猜错属调查导航错误，没有产品运行失败。

## 2. 最小接入路线：先试验，再选一种生产owner

### 本轮试验（建议，尚未实现）

使用ROOT自有隔离工具读取相同SourceRef字节，对少量关键**原始页号**调用已安装Docling SDK。在内存适配到既有`DocumentStructure`和`NarrativeUnit`，通过同一`build_observation`及阅读策略做对照。原DoclingDocument只保留在本次进程/临时目录；持久化小型对照结果、实际引文和定位，不保存全文MD/JSON和全套页图。

试验适配器可在本轮review工具目录，不应为了试运行先扩公共schema或新增生产provider。先比较输出再决定生产接口，失败则保留真实诊断。

### 达标后的生产选择（两个互斥职责，不默认双跑）

1. **外部结构增强现有units**：如果Docling能可靠给原生列表/段落/父子边界，且能与现有块建立正证的多对多映射，则只将已验证结构投影到现有units。保留现有文本/locator/replay，避免换证据身份。无可靠映射时只记未对齐诊断，不能模糊文本匹配后静默造父子关系。
2. **外部PDF前端直接产units**：如果现有块文本断行本身成为瓶颈而Docling明显更好，则Docling作为显式新PDF解析器产新units。替换当前调用边界，并同时补parser_component、replay、dependency绑定；旧版本仍按旧前端重放。Docling局部字符跨度定义为其命名的提取视图跨度，不能复制成旧DICT的原块offset。

两种模式都继续同一个共享引擎和多份阅读策略。不得再建“Docling专用金融分析/公司规则”、第二selector或第二数据库。若只疑难页需要重型解析，应由现有页面planning承接；同一页只选一个正文owner，另一结果只作结构证据/对照，不能把两套全文并集后去重当融合。

## 3. 建议统一输入契约（不新增人工许可）

以下是未来适配函数的职责说明，不宣称现有公开API已支持全部字段：

| 字段 | 含义 |
|---|---|
| source_id/source_sha256/verified bytes | 沿用存储层已打开的不可变原件。内容与SHA必要的一次校验在源入口承担；adapter不重新查实体/期间/权限 |
| source page_count + requested_pages | 原件页数及1-based物理页号集合。Docling page_range是否1-based须由ROOT实际核对；禁止导出子PDF导致页号重排而没映射 |
| parser identity | 自有adapter name/semver、Docling/core/backend发行版本、选项规范化digest、实际模型/权重版本或digest、OCR开关和语言、输出模式 |
| limits/account | 复用调用方WorkBudget及deadline；另外明确子进程wall-time/内存/产物空间上限，外部GPU/模型工作不能伪报成零逻辑工作 |
| reading request | 现有页面/几何意图，仅表达任务，不变成人工authorization文件 |
| runtime composition | 已安装引擎/模型资源由部署层提供，缓存模型不进入SourceRef；无环境时有明确错误，不能静默联网下载/换后端 |

推荐内部适配结果为`DocumentStructure`，并附在已有`layout_coverage/layout_diagnostics`中的小型实际producer/范围事实。暂不加外部公开wire字段；生产接入若现有字段不能表达外部parser identity，应集中扩现有owner并测兼容，不能临时塞任意绝对路径或整份外部JSON。

## 4. 输出和证据契约：必须守住的边界

1. **内容归属**：每个unit是同一已打开原件的提取材料，source_id/SHA不换成DoclingDocument或临时JSON的hash；跨原件不能连成段落。
2. **文本**：`raw_text`按NarrativeUnit要求trim/NFC，记录真实提取结果，不塞LLM重写句。外部去连字符/合行/OCR修复属于可追踪转换，不冒充PDF原始字节或旧DICT字符offset。
3. **单位ID**：来源、解析器/版本、稳定locator、kind、文本等按单一现有工厂生成；不复用旧unit_id来装不同边界/文本。
4. **locator**：EvidenceCoordinates页1-based，段/表/行/列0-based；Docling自引用item路径可在小型metadata留原样，仅当已核页归属才映射。多页item拆成每页可验证unit/成员，不把后一页文字全部归到第一页。
5. **geometry**：必须注明单位、原点、页宽高、crop/rotation；统一到现有projector支持的坐标帧。Docling bottom-left/top-left是否实际提供要读实例核验，不能猜。缺bbox仍保留文本并标partial，不伪造单词级bbox。
6. **charspan**：明确针对Docling item.text或命名页视图。`char_start/end`必须重放同一文本视图且真实substring相等；不是PDF bytes、不是现有native_source_view。外部多页provenance的charspan与合并文本要逐项验证。
7. **表格**：行列数、合并单元格与空格保留，行标题/单位/脚注一起成为可引用成员；空单元格不是0。不能只保留Markdown管道表丢失跨行/跨列。
8. **层级**：标题/列表父级保留producer来源和推断标记。旧Docling无新版heading_hierarchy选项；不把全部加粗文字当确定父业务，不将issuer name/关键词硬编码进去。
9. **原生证明**：不得将Docling index写成`pdf_block`并捏造`block_sha256`；现有`native-pdf-range/1`和native_pdf_range_parser只认旧命名原块视图。需要外部原生范围时定义显式producer并路由对应replay，或先不启用该能力，不能绕过。
10. **覆盖**：原件429页只跑3页时`page_count=429`、`pages_read=3`，明确其余未读；`DocumentStructure.coverage_complete`不能为true。只读页范围还应记未请求/失败/空页，防止页间continuity借出范围文字。
11. **native_text覆盖**：现有`native-text-coverage/1`只接受observed/empty/read_failed/emission_failed；适配时未读页可在现有结构errors/coverage中明确partial，不捏造observed，需扩状态则集中版本化。模型检测“empty”与原始文字层确实为空也不能混为一谈。
12. **partial**：timeout/缺模型/坏page/无法定位/OCR低置信/预算耗尽各自可诊断；保留已完成且合法的unit及其partial来源状态。不能catch异常返回空doc再叫skipped_no_narrative，不能因layout失败丢已成功的文本。
13. **源可信与语义质量分开**：原文SHA正确不证明OCR/财务数字/业务关系正确；exit0也不证明内容完整。质量诊断不加逐材料审批。
14. **共享策略**：市场/年报/中报/IR/IPO/电话会的价值筛选继续由现有family registry负责；成熟parser不替代公司语义检查或金融数据责任。
15. **存储虚拟化**：adapter只接bytes/stream和逻辑ID；物理目录仍由存储owner解析。结果、日志、generation identity不得保存Projects/Dropbox绝对路径、密钥或模型缓存路径。

## 5. 重放和缓存是生产接入的一部分

已确认当前`verify_pdf_evidence_spans_bytes`不根据外部parser_name派发，而是prepare plan后再调用本地parse_pdf_bytes。仅把Docling units送入selector会出现“选材看似成功，正式持久化/恢复无法验原文”的断链。

生产接入必须将**解析与重放使用同一后端选择/identity owner**：当前NARRATIVE版本仍本地回放；新外部版本按相同源字节、锁定引擎选项和producer重放。span核对继续比较source/locator/text/role/kind/parser，不降低为“PDF里能搜到字符串”。如果模型输出非确定性或版本资源缺失，明确不可重放/需重新派生，不能让旧cache替新输出背书。

`decision_inventory`自有源码hash闭包不等于外部模型身份闭包。本轮读源码发现明确PDF模块/feature身份，但没有从中证明已绑定所有第三方发行版本/权重。生产接入应将实际后端identity纳入现有generation及decision依赖，不新建cache。至少测：同源同配置复用；实际引擎/模型/选项/adapter改变失效；换宿主路径不失效；失败partial不当complete cache；旧span仍用旧重放。仅加手工version常量不能替实际部署绑定。

## 6. 预算与恢复：不能把本地模型藏在逻辑账户之外

现有WorkBudget支持scoped子上限且先扣同一父账户；PDF layout另有至多15s范围上限，native/prose/selection共用caller账户。这些不是外部神经网络推理的逐算子计数器。

接入时诚实记录两种度量：a)页面预留、结果遍历/匹配/排序等自有算法继续扣现有WorkBudget；b)模型进程实际wall time/峰值RSS/模型与临时文件空间单列，不把两者换算或比较成“减少X%CPU”。外部调用前按当前请求范围/剩余deadline做一次准入，子进程超时终止/清理，不能依靠SDK返回后才检查。失败不重置父账户，也不另开免费重试账户。若SDK不支持中断，则隔离子进程是运行边界，不是另一个任务调度库。

缓存模型是部署资源，可以复用；每个PDF全文JSON、MD、页图、Doclib不是必须持久化内容。试验目录结束恢复原状并记录真实增量字节，原件不复制。不能一边声称按需低空间一边长期保留所有对照产物。

## 7. 通过后才删除什么；现在不能删什么

| 逻辑 | 候选处理 | 判据 |
|---|---|---|
| `_pdf_text_blocks`中的backend文字/字体快照提取、相关布局采集 | 外部前端完整替换时可删除当前新版本调用，旧replay最小保留 | 同源段落/多栏/字体/页坐标及旧重放验证达标 |
| PdfLayoutCollector的PyMuPDF专属words/cells/font捕获及框架转换前半段 | 若Docling已提供同等/更好的细结构，移为一个外部producer，删除重复的当前生产捕获路径 | 字符对齐、坐标旋转、表格/空单元格/部分失败对照通过；公共projector保留 |
| 通用版面重建/块合行/悬挂bullet补缝 | 已由可靠外部段落边界解决的具体路径停止扩写并逐条删对应冗余规则 | CF2完整数字+单位+百分比+原因正例及跨段/异列负例通过 |
| 单字形与原块offset→native范围桥 | 外部直接文本模式不应并行执行；只为旧parser replay保留 | 新命名视图有自己的准确重放；不能为了删代码丢失定位 |
| 当前geometry页面planning | 外部按页处理时继续使用/简化同一planner，不再加第二planner | 能从外部结果中表达已读/未读/需OCR范围，真实用量不增 |
| family策略、来源身份、内容提取、表格单位/脚注依赖、Q&A说话人处理 | **保留并在同一owner改进** | 通用parser没有替代这些业务语义的证据 |
| CF3缺页诊断单次索引、候选/事实重复工作的优化 | **保留** | 它们已证明是共享引擎责任；换parser不消除 |
| SourceRef/存储/原件SHA/Artifact Store/共享预算/缓存恢复 | **保留** | 这是CWP基础职责，不把外部文档库搬进来替代 |

不先全仓删PyMuPDF、不复制两套长期活跃PDF全流程，不从“新parser更成熟”推出“所有原代码都冗余”。删除判据是此次任务的关键节点验收，不增加逐函数人工签收。

## 8. 最小质量包与真实验收（建议，尚未执行）

**中性单元/契约**：页号映射、paragraph/table坐标互斥、重复表格值/空格/合并单元格、跨页item、源文本charspan、Unicode/NFC、旋转/crop/frame、异源不连、同源异列不连、缺模型/超时/坏页partial。现有NarrativeUnit→EvidenceSpan必须继续strip reading_layout/native_source_view，防止大块嵌套结构随每个span复制到持久层。

**集成**：新adapter→DocumentStructure→build_observation→same family selector→span→精确backend replay→existing generation cache。包含旧版本span重放和新版本失效，不只检查Docling JSON生成。

**真实对照**：优先港股中报原页13（首块1,245.4、后块百萬元/7.6%/IT原因）、A股招股书既有业务叙述页、一个其他市场的多栏叙述样本。先关闭OCR/表格结构模型；扫描页与经营指标表仅有明确缺口时作为后续按需候选，不扩大成历史三表恢复任务。原样本是开发样本不是holdout。冻结源侧必须事实、相邻业务排除项、引用定位后再评分，先原文复核再看输出；页范围内pass不代表全文pass。模型不完整或版本不一致时标出该项NOT_RUN，不硬凑比较。

**性能/空间**：同页同源字节，记录实际后端版本、冷/热口径、wall时间、峰值RSS、模型下载0或真实新增量、临时/保留产物byte。不同版本PyMuPDF已导致14006/14025units差异，不能跨环境拿数量当质量/速度结论。真实试验具体结果由ROOT报告承担。

**一次大节点独审**：独立agent核最终adapter代码、真实输入/输出证据、金标排除项、定位/partial/cache/清理。发现共因直接修复后集中复审，不为每页或每次小改增加门禁。

## 9. 本报告结论

建议ROOT先做Docling有限页离线比较，并优先用当前`DocumentStructure`接缝评估“是否真的减少CF2断句与通用版面自研”。只有实际输出达标才选择结构增强或新前端生产模式，统一补齐解析/重放/身份/coverage，随后删除被替代路径。HTML CF1及共享候选CF3不因安装PDF技能自动完成。

本报告已经验证的是**源码接口与责任边界**；未验证Docling实际准确率、模型缓存完整性、离线解析、速度、空间、SDK page_range语义、实际bbox/charspan内容或生产全链。没有提高预算、引入新provider/服务/任务库/数据库或新增授权材料。
