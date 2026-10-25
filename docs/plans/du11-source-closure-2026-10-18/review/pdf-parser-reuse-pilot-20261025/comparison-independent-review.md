# PDF 有限页比较独立审查

日期：2026-10-25。状态：**比较证据可用；支持有限结构增强的研究选择；不构成生产默认切换或完整业务验收**。

本次审查读取 ROOT 的冻结源页、9 项检查点、v2 原始输出和执行收据、评分、段落对齐观察，以及此前 HK13 冷热试验。独立以 `SourceVersionReader.open_version(..., purpose='preview')` 打开 3 份原件，重新验证 SHA、页数及 5 页完整原生文字与冻结快照相等；没有重跑 Docling/模型，没有下载、外发、原件复制或产品更改。独立脚本仅在内存重算结果。配置、catalog SQLite、resource_budget 的审查前后 SHA 一致；catalog 未创建写 Store。

## 1. 样本与实验含义

| 样本 | 源 SHA 前缀 | 原件页数/本次物理页 | 范围 |
|---|---|---|---|
| 金山云 2025 中报 | `4f589193fae3` | 75 / 11、13 | 研发表述、展望、行业云收入及原因 |
| 中微上市招股书 | `19cdb41e03b2` | 429 / 114、115 | 主营业务、技术实际应用、产品与应用领域经营表 |
| 北方华创 2025 年报 | `af09ac495107` | 233 / 14 | 半导体业务范围、行业数据与设备市场数据 |

完整源 SHA/逻辑 SourceRef 见 `business-pages-source.json.gz`。新页检查点声明在本轮外部输出前冻结；HK13 是此前已观察的开发样本。它们都是开发样本，**没有独立 holdout**，也未覆盖美股、多栏/跨页段落、IR/电话会或扫描件。

v2 代码实际对照 `current-native-page-emitter` 与 `docling-default`，没有执行 `docling-pdfium`。脚本虽导入 PyPdfiumDocumentBackend，但运行列表只有 default；不能将其写成“两种 Docling backend 都比较通过”。原生 comparator 直接调用 `_pdf_text_blocks/_emit_pdf_page`；仅 IPO115 另加 `_emit_pdf_tables`。**它不是完整 parse→DU→family→selection 流程。**

## 2. 九项检查逐一审查

独立重算每个检查的有序 atoms、排除项和单 item 匹配，共 18 个 engine/check 组合，与 `business-check-results.json` 全部一致。以下 “段落匹配”仅指该有限检查，不是事实真伪、原文精确引用或完整流水线准确率。

| 检查 | 原文和 Docling 输出的实际核对 | 独立结论 |
|---|---|---|
| hk-industry-cloud-closure | HK13 行业云 **人民币 1,340.4 百万元**（187.1 百万美元），对比 **2024 同期人民币 1,245.4 百万元、增加 7.6%**；IT 需求与向垂直行业复制解决方案的原因完整；同段不含公有云 23.0%。Docling `#/texts/4`。 | 段落匹配通过；本期年份来自 2025 中报上下文，摘要必须仍带该上下文，不能把 2024 写成本期。 |
| hk-rd-period-scope | HK11 报告期研发费用 **人民币 420.5 百万元**（58.7 百万美元）；**2025-06-30** 研发人员 **1,094 人**。不与上一段 **2024 年底武汉中心 620 人（含实习/外包）**混为同一人数。Docling `#/texts/4`。 | 段落匹配通过，期间/币种/范围完整。费用是期间流量，人数是时点指标。 |
| hk-outlook-not-actual | HK11 **展望下半年、将维持、将积极拥抱、旨在**等前瞻措辞保留；没有把 AI 能力/生态云需求叙述改成已实现收入，也不混入研发人数。Docling `#/texts/6`。 | 段落匹配通过；检查 atoms 较少，人工核全段确认其余前瞻措辞也保留。 |
| ipo-business-scope | IPO114 全球半导体设备研发/生产/销售，面向集成电路和 LED 客户，改善效率/成本的完整业务说明；不串下一产品表的“主要应用于”。Docling `#/texts/5`。 | 段落匹配通过。来源为招股书披露时点的业务描述，不是当前时点的独立事实核验。 |
| ipo-operating-technology | IPO114 等离子体刻蚀在一线客户 **65/14/7/5 纳米**工艺及先进封装“**有具体应用**”；MOCVD 在领先客户生产线“大规模投入量产”。Docling `#/texts/6`。 | 段落匹配通过。“有具体应用”不等于所有节点/全部客户全面量产；不能在摘要中扩大范围。 |
| ipo-operating-table-not-financial | IPO115 原生 `pdf_table_row` 为 **MOCVD设备 → LED外延片及功率器件生产**，row_cells 有产品与应用字段，table_headers 有“产品类别/图示/应用领域”，未混入下一表 VOC/空气净化。Docling 输出保留分散 texts，但 table_structure=False 的 table_data 只有空 1×1 占位。 | 原生行/列关系在本页得到证据支持；该 Docling 配置**不能取代经营表关系输出**。这不是资产负债/利润/现金流三表，不应因为新浪供三表而丢弃。 |
| annual-semiconductor-scope | NAURA14 “在半导体装备业务板块”及刻蚀/沉积/热处理/清洗/注入/涂胶显影/键合，与集成电路/功率半导体/三维集成/先进封装的业务范围保持同段；不串下一真空新能源板块。Docling `#/texts/5`。 | 段落匹配通过。 |
| annual-industry-data-unit | NAURA14 **2025 全球半导体市场 7930 亿美元、同比 21%**，AI 算力驱动保留；不串设备市场 1330 亿美元。Docling `#/texts/10`。 | 段落匹配通过。它是报告转述的行业数据，**不是公司收入或人民币**，本试验未外部验证该行业估计是否正确。 |
| annual-equipment-scope | NAURA14 **2025 全球半导体制造设备市场 1330 亿美元、同比 13.7%**，本土晶圆厂扩产/升级解释保留；不混入整体半导体 7930 亿美元。Docling `#/texts/13`。 | 段落匹配通过。同样是报告转述的行业数据，不能当公司营收。 |

8 个叙述检查在 Docling 中分别由一个 item 承载，而原生 page emitter 输出分片，没有某个单独 item 同时满足所有 atoms。**不能据此说当前原生共享引擎准确率为 0、漏读全部 8 项，或者 Docling 全流程准确率 100%。** 后补的当前共享引擎实际基线已经验证连续性、context group、DU/selection 会保留其中多数关系，详见下节。

经营表原生 row 的单 item 匹配只是第一步；本次进一步检查了真实 row_cells/header 与源页产品/应用字段，因此可以说“本页关系有支持”。Docling 分散文本仍在，不应夸大为“丢掉所有表格文字”；缺的是可靠行列输出。未开启 table_structure 的结果也不能证明开启后仍失败。

### 2.1 增量：当前 0.9 共享阅读流程真实基线

后补 `current-reading-bounded-baseline.json.gz` 和 `current-reading-check-results.json` 及其生成脚本已经独立审查。脚本对三份完整原件实际调用当前 `parse_pdf_bytes(selector_version='0.9.0', reading_context=..., work_budget=budget)`，再将已冻结的 5 页真实 units/metadata 投影成显式 partial view，传入**同一个预算对象**调用当前 `select_narrative_evidence`。这比 page emitter 更接近生产语义，但依然是有限页选择，不是整份报告完整选材。

| 原件 | 实际原生扫描页/units | 本次分析页/units | parse work → 总 work / 上限 | 选择覆盖 |
|---|---|---|---|---|
| HK 中报 | 75 / 2,330 | 11、13 / 67 | 307,383 → 405,734 / 16,000,000 | partial，未耗尽 |
| CN 招股书 | 429 / 14,025 | 114、115 / 52 | 420,052 → 504,184 / 16,000,000 | partial，未耗尽 |
| CN 年报 | 233 / 10,320 | 14 / 49 | 668,404 → 783,053 / 16,000,000 | partial，未耗尽 |

独立依据真实 group.evidence_ids → evidence_spans membership，重建页内有序文字、检查 atoms 和排除项；9 项结果与 ROOT 全部吻合：

- **当前叙述同组通过 6/8**：研发期间/人数、前瞻展望、IPO 主营业务、年报半导体业务、整体半导体行业金额、设备行业金额。
- **缺完整同组 2/8**：HK 行业云金额/百分比/原因闭包，IPO 刻蚀技术节点/MOCVD 量产完整段落闭包。
- **9 项 atoms 都能在整体 selected evidence 找到**。两缺组是局部关系/闭包缺失，不能说文字没读到或未选中。
- **经营表内容同组检查通过**，但当前实际 selected group 是“业务技术章节标题 + 2、MOCVD设备标题 + LED外延片及功率器件生产正文”，没有 typed `pdf_table_row`/row_cells。必须区分“同组应用关系保留”与“原生 typed 行列结构进入正式 selection”。前者已证，后者本基线**未证**；前节完整 row 来自另外显式 `_emit_pdf_tables` 的源侧能力比较，不可拿来给本路径背书。

因此 Docling 本次相对当前引擎体现的候选增量是**两类局部完整组**，不是从 0/8 提升到 8/8 的全局改造。新结构增强实现仍须用相同语义检查点验证这两类问题真实闭合，并确保已通过的 6 类、经营应用关系和原生定位不退化。

## 3. 对齐原型：32/61 的口径和两处整段差异

独立重算 `normalized_equal`，结果确为 **32/61**。所有 8 个目标段落有原生成员对齐，分别涉及 2、4、4、5、8、4、5、6 个 native units。它们是 `NFKC + 去空白 + 去起首 bullet` 的**对照文本等价**，不是字节相等、native 字符跨度相等或已证正确业务父子关系。

29 个未对齐项的分布：

- IPO115 表区 24 项：常见是外部把 MOCVD/设备、LED/说明拆成更小 item，原生 unit 含完整词组；center-in-box 选择会重复拿同一原生 unit，不能机械一一映射。
- IPO114 表头 3 项：`产品类别/图示/应用领域` 在本原型中没有可匹配原生成员。这些仍是表区问题，不能算三个业务段落失效。
- 其余 **2 个完整非表格段落**有真正字符差异：
  1. HK11 `#/texts/3`：原文“**包括实习生和外包员工**”中两个“包”，Docling 变成私用区字符 **U+E05B ``**。NFKC 不修复；不能在通用 adapter 内按本公司“猜回包”或接受相似句就造精确引用。
  2. NAURA14 `#/texts/11`：原文 **“超级周期”**的弯双引号变成 ASCII 单引号 **'超级周期'**。这不表示业务含义必然改变，但它**不是 NFKC 等价**，不能把标点任意删除以通过精确对齐。引用/字符 offset 必须仍以原生文字为准。

原型 center-in-box + 2pt 容差只用于提出候选。生产必须还验证 source、原页、原顺序、无重叠/异列歧义、成员完整性与声明比较视图中的准确相等；被别的 item 重复认领、只有部分 unit 被覆盖或范围跨表/段落的候选不能强合并。对照字符视图若用 NFKC，应记录变换及成员范围，不能改 canonical raw_text/旧 DICT charspan。

## 4. 性能/运行证据的合理口径

v2 执行收据：总 wall **105.175 秒**，进程树 RSS 采样峰值 **1,063,116,800 bytes**；比较进程 import **84.049 秒**，Docling 5 页 convert 合计 **16.0157 秒**，原生 emit 合计 **0.6996 秒**。这不是严格全流程等功能基准：第一个 Docling 页含首次初始化，后面复用 converter；原生只 emit，不做同等布局模型/selection；导入也包括比较脚本加载的组件。不能用总 wall/5 推算生产平均时延，或宣称固定耗时加速比。

此前 HK13：冷 convert 11.448 秒、同进程热 convert 3.6483 秒；cold/warm 的 item 序列完全相同。v2 HK13 convert 2.3565 秒，文字/范围与原证据一致。冷热运行只说明本环境可复用和有明显启动成本，不能证明跨版本/重启的模型确定性或 cache replay 已实现。

收据记录 offline、new_model_downloads=0、临时根已恢复 absent，原始比较记录无 API/付费/下载/原件复制、保护文件未变；本独立审查重新验证原件与保护文件，**未重放整个父进程生命周期或复测资源峰值**。

## 5. 对方案选择的审查结论

**赞成 ROOT 选定内部混合结构增强方向：默认优先原生 canonical 文本、locator 和既有经营表能力；只有疑难结构才使用 Docling 提示，成员准确对齐后增强段落/列表边界。** 当前实际引擎已通过 6/8 叙述同组，Docling 候选增量集中于两类局部闭包；字符差异、经营表行列缺口、84 秒级本进程导入及约 1 GB RSS，均反对把重模型全量默认用于每份文档。不支持全面替换原生文字，也不支持把未对齐视为无用内容而丢弃。

该选择仍是**实现方向**，不是生产 ready。必须遵守 `layer-boundary-review.md`：实现选择、fallback、依赖身份、read/replay/预算在单一阅读责任层；AUTO/RF/FF 不拿 Docling options，不依据后端分支重写摘要。canonical native 身份与被采用的结构提示身份都应在阅读依赖中准确绑定，不能因为未改 raw_text 就遗漏新布局模型对 selection 的影响。

## 6. 生产默认前缺少的验证（一次有边界的大节点）

1. **增强路径与已完成当前基线对照**：当前 parse→DU→family/context→选择的有限页 comparator 已完成且独立复算通过，不再列为未执行。下一步只需把新 façade 内结构增强路径接入相同源字节/环境/实际覆盖/预算，验证两缺组被闭合、其他 6 组与经营应用关系无回归；不要求最终事实必须在一个 unit 中。原生精确成员闭包、有界按需 router 与 service 成套 identity/replay/cache/budget 尚待实现；不得用已有对照成绩宣称增强已接生产。
2. **独立 holdout**：冻结未用于调规则的新公司/文种原文检查点，至少一个不同市场的美股 PDF 和一个新 CN/HK 公司；包含否定/前瞻、单位/期间、相邻业务/多栏、跨页或表+文的反例。已见过的 HK13/IPO114 不能改名成 holdout。不需要为了凑样本复制原件或全量扫描所有公司。
3. **完整链路**：增强单位→真正精选摘要→原文引用 replay→同源缓存恢复；结构提示模型/配置变化应失效，路径移动不失效；超时/未对齐仍保留原生可用结果和真实 partial，不能当 complete。摘要需要核费用/人数/行业/公司数值及“有具体应用/将/旨在”的力度。
4. **架构和资源**：换 backend 不改变上层条件分支，所有内部尝试用同一预算/deadline；冷启动何时发生、批次热复用、何种疑难触发，都由阅读层配置/能力明确。先用本次真实瓶颈证明按需入口，不因有模型而全量启用。

以上是接入大节点的必要质量验证，不是新增逐页审批或逐函数签收。当前已完成真实当前共享引擎的有限页基线；尚没有结构增强生产接线、摘要/RF、全文覆盖、cache 恢复或新 holdout 的已通过证据，PWF 必须继续保留这些剩余任务。

## 7. 无损归档增量核验

ROOT 将 4 份较大证据 JSON 保存为 gzip（mtime=0）。独审逐项检查压缩字节 SHA/长度及解压字节 SHA/长度，全部与**压缩前由本独审自行记录的版本**及 `artifact-index.json` 一致；4 份未提交明文已不存在。合计 850,969 bytes → 152,636 bytes。没有重复打开原件或运行 SDK。已读取更新后的 `current-reading-check-results.json`：经营表条目明确 `typed_row_cell_support_in_current_selection=false`、`business_relation_grade=PARTIAL_RELATION_TEXT_ONLY`，与本审查结论一致，原 same-group 命中不变。归档审查 **0 OPEN**。

## 8. 最终选型/实施细则检查

已只读检查 ROOT 的 `decision.md` 与 `implementation.md`。它们清楚区分当前 6/8 同组和外部 8/8 单段局部观察、经营文字同组与 typed row，禁止默认全量模型启动；明确原生细捕获 15 秒不能冒充 84 秒冷导入额度，C1 先将真实分层缺陷写 RED，再进入 C2；不增加逐材料许可或第二状态库。

初稿曾混淆执行前冻结与执行后实际依赖。ROOT 最终细则已通过更简单的机制补正：`describe_recipe` 在原生读取前保守冻结显式启用且可能参与的能力依赖；`actual_producer` 在 select 后只记真实参与组件/页与 fallback，进入既有依赖/收据，不改历史 manifest。启用但未调用允许额外 cache miss；完全禁用的工具不受其安装版本影响。无需增加预检全扫、第二 planner 或状态库。actual 配置/指纹必须在冻结 recipe 内，版本漂移不能冒充 fallback；replay 按 actual 文本/坐标契约并核 recipe，canonical 原文成员核对不强制重推理布局模型。对应 C1/C2 和集成测试要求均已写入。**最终文档审查 0 OPEN**，不代表生产实现/摘要/cache/RF 已通过。

终审绑定的文档字节：

- `decision.md`：5019 bytes；SHA-256 `13d1b268fb3226917835eb0a8a48256be4edc94a892e42e6974c532637e35c44`。
- `implementation.md`：10412 bytes；SHA-256 `57a04dae45e264a7eaea03adf78d8ef07cb69c58f72a53d827426a47f31a68dc`。
