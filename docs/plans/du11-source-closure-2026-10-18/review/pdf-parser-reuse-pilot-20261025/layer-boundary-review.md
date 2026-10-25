# PDF 方案替换的单一阅读层边界

日期：2026-10-25。源码基线：`7a63dfd6659ce43c4d1b5a9c877d56a74ed57a96`。

状态：**只读架构调查完成，建议接口未实施，后端优劣由 ROOT 真实比较决定**。本报告不宣称 Docling 或其他解析器已经通过生产验收。阅读既有 `architecture-review.md/json` 后，使用 CodeGraph 查询实际入口，再读取指定源码。没有修改产品、配置、原件、索引、作者工区；没有测试运行、网络、下载、收费 API 或提交。写入仅本报告与同名 JSON。

## 1. 对用户要求的准确解释

“封装在单一层”指**一个文档阅读职责层、一个对外服务契约和一个实现选择责任**。内部允许格式适配器、结构识别、阅读策略、选材、摘要投影及证据重放分模块；不能变成一个巨大函数，也不能让每个上层消费者自己拼一遍解析器、selector 和 replayer。

```text
RF / StockWiki / filing-fetch 等消费者
    │ 逻辑 SourceRef、文种/语言/任务意图；接收证据/摘要/覆盖诊断
    ▼
CWP 来源服务 / AUTO 编排
    │ 打开不可变原件；调度 select → summarize → verify；持久化与恢复
    │ 只调用阅读层契约，传同一个资源账户、deadline 与冻结的 opaque 实现描述
    ▼
文档阅读职责层（唯一选择 owner）
    ├─ 阅读 façade：身份、选材、摘要输入/输出验证、重放
    ├─ PDF 内部后端：当前原生 / 被实测选中的成熟工具适配器
    ├─ 共享 DocumentStructure → DU → family 策略 → EvidenceSpan
    └─ 摘要方法与配置：现有预算化模型端口；原语言、来源引用、数字保真
    │
    └─ 存储端口、通用 WorkBudget、模型调用端口（基础设施；不反向决定阅读算法）
```

允许上层表达“找 IPO 主营业务/行业/募投与风险说明”“只读某些物理页”“剩余 30 秒”，不允许上层表达“Docling 开哪个选项”“PyMuPDF full_table_scan 再跑一次”“换后端就换 prompt”。实现 ID 可以作为诊断/缓存的**不透明数据**流过编排层；读取其工具名后控制行为才是越层。

A 股历史资产负债表、利润表、现金流表继续由 **W19 新浪结构化接口**供给。这里保留经营指标表和业务叙述中的金额、单位、期间、条件、因果，不扩成 PDF 三表重建，也不修改 W19 工区。

## 2. 源码中真正存在的接缝问题

下列是当前源码证据，不是“未来可能出现”的泛泛风险。它们不证明当前单后端全部功能失效；它们证明直接换一个 PDF callable 不是合格的可替换抽象。

| 编号 | 真实位置 | 当前行为与影响 | 应归属 |
|---|---|---|---|
| L1 | `automation/narrative_select.py:75,473` | `PdfBytesParser` Protocol 未包含实现实际使用的 `work_budget`、`reading_context`；`_parse_pdf` 只有 `self._pdf_parser is parse_pdf_bytes` 且 selector `0.9.0` 才传这些参数。替换 callable 会丢共用账户/阅读上下文。 | 阅读层统一请求和 backend 契约；handler 不做函数对象身份分支 |
| L2 | 同文件 `:444-471` | handler 自行创建 WorkBudget 并按 selector 版本决定旧式 full_table_scan 重跑。预算注入本身合理，但重读/表格降级策略在编排中；不同实现的准入与 fallback 容易分化。 | 上层提供账户，阅读层决定内部步骤且所有尝试共用账户；旧模式仅兼容 adapter |
| L3 | `automation/narrative_formats.py::parser_component` 与 `narrative_select.py:630` | PDF 身份回落固定旧常量；PDF `_SelectionWork` 没有实际 parser identity。注入新 parser 后输出仍可带旧身份。 | 实际 backend 返回/描述 identity；同一 façade 生成身份、结果与 replay 绑定 |
| L4 | `automation/narrative_generation.py:106-164` | `parser_components` 的实际 runtime fingerprint 仅在 HTML/DOCX/PPTX normalized 分支接受；PDF carrier 忽略它。仅传新第三方版本/模型并不能进入 generation。 | 阅读 owner 生成统一 pathless component 描述；generation 层通用存储/hash，不枚举工具 |
| L5 | `source_catalog/narrative_evidence.py:2262`、`automation/narrative_replay.py:144-178` | 默认 PDF replay 固定调用当前 `parse_pdf_bytes`，选材与重放分别有可注入参数。parser/version 变更可能得到“能选不能验”或分裂的 producer。 | backend 身份、解析与 replay 三者由同一 owner 提供；旧身份走旧 replay |
| L6 | `automation/narrative_verify.py:141-181` | dependency identity 再调用 PDF 固定常量判断 active。若改 parser_component、handler 或 cache 中任一处却不统一，其余可拒绝正确输出。 | 阅读层检查“记录身份是否支持/是否与本批绑定一致”；verify 只接受检查结果 |
| L7 | `automation/narrative_select.py:591-620` | 选材材料核对直接按 `NORMALIZATION_PARSER_NAME` 分支，其他一律走 PDF replay-unit matcher。handler 了解底层 parser 家族。 | façade 的 `validate_selection(parsed, spans)` 或 read_select 内部核对；handler 保留通用来源/载荷约束 |
| L8 | `document_understanding/decision_inventory.py:153-180` | 当前 PDF 源码/feature 指纹明确枚举 PyMuPDF 前端相关模块；这作为**当前实现的阅读层内部记录**合理，但不能拿来证明外部发行版本/模型/选项已绑定。 | PDF adapter 提供实际 producer 依赖；inventory 在同一阅读层统一合并，避免 automation 再复制名单 |

`automation/narrative_runtime.py::NarrativeRuntimeDependencies` 已有一个组合根；现在只绑定 normalization，PDF select/replay 没有共享的实际运行实例。这里适合注入**一份阅读 façade/会话**，不新增第二套 runtime、任务库或配置开关链。

`source_catalog/narrative_normalization.py::NarrativeNormalization` 已示范 lazy adapter、identity/normalize/replay、deadline 和 close 生命周期，可以借用其**原则**。它当前不接受 PDF；不能声称把 PDF 塞进现有 NormalizedDocument 已经可用，也不需要为本次复用先修改所有非 PDF carrier。

## 3. 最小可实施的边界

### 3.1 对外 façade：单一阅读 owner，保持现有三阶段 DAG

建议先在既有 `source_catalog` 阅读适配职责下增加一个小 façade（建议名 `narrative_reading.py`，名称不是冻结的公共 wire schema），复用当前 DU 和摘要模块，不搬目录、不复制实现。对外只保留以下职责：

1. `describe(request)`：返回与实际选择一致的 pathless 实现/配置描述；用于冻结 generation。不能只用环境里“已安装哪些包”代替实际采用后端。
2. `select(verified_bytes, request, resources)`：在同一资源账户内读取/结构化/选材/材料核对，返回现有 selection package、真实 producer、coverage/diagnostics；实现特有后备行为在内部。
3. `summary_request(selection, request)` 与 `validate_summary(selection, response)`：复用现有 `summary_input`/model projection 与数字引用校验；上层不根据 PDF 后端换 prompt，不接收供应商解析对象。
4. `replay(verified_bytes, bound_selection, resources)`：按记录身份派发，同一 owner 核对精确文字/locator/source；不把“字符串在 PDF 里搜得到”当重放。
5. `close()`：释放进程/模型资源；同一个有限批次可以复用热实例，出错/超时必须在所属进程层结束并清理。

这五项是**建议职责**而不是五个必须新建的抽象类。先让 PDF read/identity/replay 合流，摘要已处于阅读职责的公共模块可继续调用；不要为包住它们另写一套模型客户端。现有 select/summarize/verify 仍分别提交 checkpoint、收据、artifact 和 outbox，facade 不接管数据库事务或 lease。

上层能够替换测试 façade，但只能整体替换，不分别注入互不相干的 parser/replayer。旧测试参数在迁移期间用一个兼容 wrapper 汇入同一 owner，并标清只用于兼容；新生产路径禁止再增加三个独立开关。

### 3.2 内部 PDF backend：成套能力，而非任意 callable

最小内部协议是 `identity / read / replay / close`。`read` 继续产生 **DocumentStructure/NarrativeUnit**，它们是当前 PDF 与共享引擎的真实接缝。

共同 request 只含：已验源的逻辑 ID/SHA、语言、标题、文种/阅读意图、1-based 物理页范围；resource context 只含现有 WorkBudget、剩余 deadline 和运行上限。上层不用接收或填写 Docling PdfPipelineOptions、模型缓存路径、PyMuPDF 文字标志、table scan 实现参数。部署配置可以选择实现，但解释、默认策略、可用性检查、内部按页路由与 fallback 都归阅读 owner。

生产选择由实测决定：

- 若选择**结构增强**，原生文本/locator/replay 保持 owner；外部段落边界只在 source/page/原序/几何/文字对齐有正证时增强。不能把 Docling charspan 伪装成旧 DICT offset。
- 若选择**新文本前端**，新 producer 必须连同单位、坐标、精确 replay 与 cache identity 一起接入；旧 producer 只保留最小 replay 兼容，不长期双跑全文再拼并。

该二选一应当是阅读层内部的确定方案，不能由 RF 或上层 handler 选择“哪个句子用哪个 parser”。确需混合页能力时也由阅读层按当前规划产生一个带明确 provenance 的结果。

## 4. 身份、缓存、重放的共用责任

阅读 owner 的实际 producer 描述至少绑定：自有 adapter/算法版本、实际第三方发行版本及 backend、规范化选项 digest、实际使用的模型 revision/digest（不含路径）、字符视图/坐标契约版本。OCR、表格、版面模型只有实际参与时才成为该次身份依赖；不能让无关已安装包改变缓存。

两层不能混淆：

- 存储层验证原件字节、身份/期间/as-of 及逻辑引用；阅读器不重新找目录/公司，不复制实体权限链。
- 阅读层负责派生文本/层级/locator 的 producer 与精确重放；源 SHA 正确不能代替这一步。

generation/cache 只保存并计算阅读 owner 给出的紧凑、规范化描述，不再按 MIME 特判“PDF 忽略 parser_components”。老 cache 无法证明新 producer 时正常失效/重算；相同 producer 移动宿主或模型目录不应失效。模型缺失时报可复现原因，不能静默联网或切换另一个实现后继续沿用已冻结身份。

摘要 projection/prompt/校验方法是阅读层的独立组件依赖；改变摘要方法应该更新这部分而不是伪造 PDF parser_version。更换 PDF 解析引擎也不能强制所有其他文种改摘要方法。

## 5. 资源与运行：接口必须诚实

WorkBudget 由当前文档/任务账户注入，并在读取、结构匹配、DU/selection 的内部步骤共享。预算耗尽、超时、某页失败都返回准确 partial/原因；fallback 不新开免费账户。模型 wall time/RSS/临时 byte 单列度量，不伪称神经推理逐算子已按 Python 工作单位精算。

重型 SDK 的启动、CPU 线程数、环境和模型资源是阅读实现的 runtime 责任；它们不能穿透到 RF/FF 的每个调用点。父进程只负责通用的截止时间、终止与清理能力，阅读 runtime 给它一个普通受限任务。有限批次复用热实例；不新增常驻服务、Doclib、watcher、第二缓存或每份 PDF 全文 JSON/MD/页图。

pilot 观察到的冷导入与字符差异应由 ROOT 真实报告承担。本报告没有运行工具，不对具体耗时、内存或内容准确性背书。

## 6. 用少量有力测试框住抽象，不加小节点门禁

以下是**待实施测试要求，不是已通过收据**。建议在一个架构/契约批次和一个真实大节点完成；不用每个内部函数独审。

| ID | 层级 | 必须证明的外部行为 |
|---|---|---|
| LB-01 | 单元/协议 | 两个中性 fake backend（不同名称/身份）收到同一中性 request、同一预算实例和 deadline；更换实现不丢阅读意图，也无 callable `is` 特判。 |
| LB-02 | 集成 | select→材料核对→summary projection→verify 用同一冻结 producer；错 producer 被拒绝；旧身份仍按旧 replay，不误用当前默认。 |
| LB-03 | 缓存 | 同源/同实际组件恢复复用；实际 backend/选项/模型/字符视图改变失效；路径移动与无关已安装包不失效；partial 不能冒充 complete。 |
| LB-04 | 预算/生命周期 | 零预算不启动重模型；内部 fallback 不重置预算；超时终止只结束本任务子进程，close 可重入；临时目录恢复原状。 |
| LB-05 | 定位 | 原页号不重排；Docling bottom-left 与 native top-left 显式换算；多页/异源/异列不串；兼容字形可用于声明的对照视图，不能改原文 SHA、冒充旧 charspan。 |
| LB-06 | API 边界 | 泛型 fake façade 跑现有 select/summarize/verify，AUTO 不需要导入第三方 PDF 库或了解其 options；RF/FF 请求、输出协议不因 backend 交换而改变。 |
| LB-07 | 架构检查 | 小型 AST 检查只约束**本次生产边界**：engine imports/engine options/按 engine-name 控制流只在阅读内部 adapter/组合根。排除测试、试验脚本、旧 replay 明确白名单；不做脆弱的全仓关键词 grep、不禁止不透明身份字段流转。 |
| LB-08 | 真实 | 冻结源侧检查点后，同一源字节在候选方案中比较；HK 中报经营业务完整数值/单位/原因且排除相邻业务，CN IPO 主营业务/技术/风险说明，再取不同市场/文种样本；明确开发样本与 holdout，局部页 pass 不表示全文 pass。 |

真实测试检查内容质量、coverage、准确定位/旧 replay、新缓存恢复、实际时间与持久化增量；不只检查 JSON 生成或 exit=0。若候选方案质量未赢或冷启动/空间不合算，保留当前方案并记录原因是合格研究结果；不为了“用了新工具”而默认替换。

## 7. 施工顺序与完成标准

1. ROOT 完成受限真实比较，确定结构增强或新前端，并冻结**有证据的选择**。
2. 先写 LB-01/02/03 的中性契约测试，再补单一阅读 owner；迁移 L1–L7 到它的职责。L8 留阅读内部但补实际 producer 描述。
3. 让组合根只装配一个阅读对象，三阶段 job 调它；保留现有存储、预算、模型和事务 owner。主要变化是把现有决策搬到正确责任层，不复制第二条流水线。
4. 用 LB-04/05/06/07 验证失效、恢复和无越层干预；运行聚焦回归一次，解决具体风险，不反复跑超时全量。
5. LB-08 真实 end-to-end，经一次独立大节点审查，根因修完后提交推送/PWF。只有被比较证明替代且旧 replay 不依赖的规则才删除。

完成标准：从上层看来，换 PDF 阅读实现只改变阅读层部署/组件描述；SourceRef、RF/FF、AUTO 阶段、已有 artifact store 不需要出现 Docling/MinerU/PyMuPDF 特判。源/locator/coverage/资源诚实性不降低，历史三表仍走 Sina 等结构化供给。
