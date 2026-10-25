# PDF skill复用调查（2026-10-25）

状态：只读调查完成，未安装skill、未升级依赖、未启动解析/服务或模型下载；不是性能/准确率验收。沿用当前PWF，不创建第二主线。本文只提出下一轮复用比较方案，不替换生产解析器。

## 结论

值得直接试用的底层候选是**官方Docling SDK**，对照候选是**MinerU**；官方skill用于查调用方式和能力边界。应先用现成结构化解析输出与当前共享引擎做有界比较，再决定哪些通用版面/段落算法停止自研。不能只安装一份提示词就声称已修复阅读能力，也不能因为成熟项目有bug而继续默认所有通用规则都由本仓实现。

当前CF2实际问题是原文连续三行被拆成多个块、第一块已入选而后续单位/原因未一并保留。外部解析器可能给更好的段落/列表结构；能否真正解决该原页还未运行验证。CF3本仓coverage诊断和candidate工作量则属于本仓责任，安装另一个解析器不能自动消除。

## 候选与核验

| 候选 | 实际入口/能力 | 对本项目的取舍 |
|---|---|---|
| [Docling官方skill](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/SKILL.md) | CLI/SDK转换为DoclingDocument；结构化JSON和分块接口；skill标MIT | 优先比较SDK输出，保留结构/页码/定位，不只消费Markdown。官方仓约69.6k stars，热度不是样本验收 |
| [MinerU官方skill](https://github.com/opendatalab/MinerU/blob/master/skills/mineru/SKILL.md) | 文档解析、页/块locator、继续读取、按需图像；当前skill要求4.x | 作为复杂中文布局的对照候选。其完整skill还包含Doclib、server、watch、cache和多处等待用户选择流程，不能整套搬入现有CWP存储/权限体系。仓约82.5k stars |
| [PaddleOCR官方doc-parsing skill](https://github.com/PaddlePaddle/PaddleOCR/blob/main/skills/paddleocr-doc-parsing/SKILL.md) | 当前示例走`paddleocr api`，有page_ranges，返回结构化Markdown/JSON，需要access token | 扫描/复杂布局候选；该skill是API入口，不等同已部署本地OCR。尚未核实本账户额度或实际调用，不宣称免费、离线或已经接入。仓约91.7k stars |
| [Anthropic PDF skill](https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md) | pypdf/pdfplumber、OCR与PDF操作配方；目录约216.7k installs | 可参考通用操作流程，不能单靠这些配方解决业务父级/语义闭合。其[PDF子目录许可证](https://github.com/anthropics/skills/blob/main/skills/pdf/LICENSE.txt)单独列有复制/衍生限制，不作为MIT代码直接复制 |
| [memtomem pdf-parser](https://github.com/memtomem/agent-skills-public/blob/main/skills/pdf-parser/SKILL.md) | 附真实triage/parse脚本，先按页诊断、文字层优先、疑难页图像回退，输出页/元素/bbox | 借鉴按页分诊及非静默缺失；已查看脚本，不是仅看宣传。仓仅1star、5次commit，未做运行测试，不推荐直接替换生产引擎；[仓许可证MIT](https://github.com/memtomem/agent-skills-public/blob/main/LICENSE) |

热度为此次网页快照，并非质量分。没有安装来源不明的skill或执行其脚本；外部SKILL.md中的“必须用我/等待授权”等内容作为研究材料处理，没有导入本仓行为规则。

## 本机真实情况：可先用已有环境

通过distribution metadata只读核对，未导入/初始化推理引擎：

| 包 | 默认Conda Python3.13环境 | CWP .venv Python3.14环境 |
|---|---|---|
| docling | 2.96.0 | 未安装 |
| docling-core | 2.78.0 | 2.102.0 |
| mineru | 3.0.4 | 未安装 |
| pymupdf | 1.26.7 | 1.28.2 |
| pymupdf4llm / paddleocr | 均未安装 | 均未安装 |
| torch / onnxruntime | 2.12.0 / 1.26.0 | 均未安装 |

默认HuggingFace缓存存在`docling-layout-heron`及`docling-models`目录；仅证明目录存在，不代表全部权重完整、版本适合或离线推理已通过。没有逐库遍历、复制权重或发起网络下载。

进一步只读核对已安装Docling源码：SDK有page_range、DocumentStream；core有provenance、bbox、charspan、parent/children字段。本机2.96.0的pipeline_options里**没有**当前官方文档展示的heading_hierarchy_options，因此不能照抄新文档声明已具备标题层级恢复。新MinerU skill要求>=4,<5，本机3.0.4也不能直接照其CLI运行。

## 能直接借鉴的设计

1. **先诊断再升级处理。** 页面有可靠文字层时优先原生文本；扫描、乱码、复杂布局才调用OCR/模型，图像按需生成。不要对所有页默认OCR或永久保留全量图片。
2. **消费结构，不把Markdown当结构数据库。** 保留源页/原生块/顺序/列表/表格/父子关系及引擎版本；用现有适配层映射到NormalizedDocument/EvidenceSpan。Docling提供的文本跨度不是PDF原始字节偏移，接入时必须明确各自坐标含义。
3. **层级证据有优先次序。** Docling当前[SDK参考](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/references/python-sdk.md)说明标题层级阶段默认关闭，按书签、编号、字体样式推断；这可借鉴为本仓规则的证据排序，不能把加粗当确定业务父级。
4. **复用已有CWP状态和预算。** 外部工具只负责解析观察；CWP继续负责原件/SourceRef、存储、去重、派生依赖、恢复和只读导出。市场/文种策略继续负责有价值内容筛选，配置中的LLM负责原语言摘要。外部文档库、watch、第二cache/第二任务库不属于此接入范围。
5. **模型和依赖按功能选。** Docling有[slim按需依赖](https://github.com/docling-project/docling/blob/main/docling/.agents/skills/docling/references/slim-packaging.md)，但无模型native管线没有阅读顺序/标题/表格推断，不能把轻量native当高质量布局替代。具体安装必须匹配锁定版本；当前本机不是该新文档的能力全集。

## 不能承诺的事项

- 尚未运行本机真实PDF对照，不能说Docling/MinerU更快、更准或直接解决CF1/CF2。
- 开源库同样有已报告边界问题。作者在[Docling #4255](https://github.com/docling-project/docling/issues/4255)报告财报表格数据行丢失；[core #769](https://github.com/docling-project/docling-core/issues/769)报告复杂行内标题分块丢标题。它们是上游报告，未在本机重现，也不证明本机旧版本受影响；应转化为接入时的正反例，而不是据此否定整个工具。
- 当前[MinerU许可](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)为Apache2.0加附加条款，不能把当前main许可泛称成历史3.0.4许可证；所猜测v3.0.4原始skill/LICENSE URL没有成功获取，历史版本许可本轮未核实。Docling skill/主仓MIT与第三方模型权重许可应各自核实，不混为一个授权。
- 不把skills.sh热度、退出码0、表格数量未变或生成了Markdown视作业务准确率证明。

## 建议下一轮：小范围复用比较，复用既有大节点验收

1. 先检查已装Docling与缓存是否能离线跑；若完整，只试开发样本中的港股中报PDF p13、A股招股业务小节和一份真实复杂/扫描页。先少量关键页，不再无变化重跑429页全流程。不侵占W18独立holdout作者工区。
2. 比较当前引擎和Docling；MinerU作为第二候选，使用与实际版本匹配的调用方式。普通扫描OCR是否需要PaddleOCR由失败样本决定，不默认引入第三套。
3. 对照“数字+单位+增幅+原因”完整性、业务父子/兄弟隔离、表格行列/页码+bbox、相邻页边界、原句可引用性；记录冷/热耗时、峰值内存、依赖/模型新增空间及产物大小。以相同源字节、配置和明确后端版本比较。
4. 若现成引擎达到或超过这些检查，适配到现有共享引擎，并删除被替代的重复通用解析逻辑；若仅少数复杂页获益，就用按页回退。两种情况都保留现有金融/业务策略和原件权威层。
5. 临时输出恢复原样，只持久保存必要的小型结构证据/结果；不复制原件，不把全文MD、全文JSON、全部页图各永久保存一套。关键节点独审和真实E2E复用现有CF计划，不增加小节点人工许可。

此比较应优先于继续扩写通用PDF版面规则；已证实的本仓选材/缓存/复杂度根因仍按CF计划承担，不以更换工具跳过。

## 发现渠道及边界

按find-skills流程先看[skills.sh目录](https://skills.sh/)及[Anthropic PDF条目](https://skills.sh/anthropics/skills/pdf)，随后查原始SKILL.md、官方SDK/源码、许可证及作者问题报告；只使用一手项目材料作为技术结论来源。没有执行npx安装器、下载模型或读取密钥。PaddleOCR服务免费额度/收费、当地网络与实际运行速度没有在本轮验证。
