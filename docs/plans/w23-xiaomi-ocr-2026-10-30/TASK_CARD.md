# W23-XIAOMI-OCR：真实公司文档 OCR 独立对照试验

状态：READY_TO_DISPATCH。本卡是比较试验及可复现工具，不切生产、不替代主线M8、不更改OCR/共享阅读公共接口。A/B自主实施，C交接前独立agent审查，不要求逐小步签收。

## 启动与唯一入口

- 工作目录：**`C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr`**。
- 分支：`codex/w23-xiaomi-ocr-20261030`，基线 `de7ffe48aee3f9decfb4be6dfc2f561dcd3aa29d`。
- `PLAN_ID=w23-xiaomi-ocr-2026-10-30`，`PWF_PLAN_ROOT=docs/plans`。
- 本地计划：`docs/plans/w23-xiaomi-ocr-2026-10-30/`；先读 TASK_CARD.md、SOURCE_NOTES.md、task_plan/progress/findings。
- 输出：`delivery/w23-xiaomi-ocr/handoff.md/json`、`comparison.md/json`、冻结样本/版本与紧凑测试收据。
- ROOT主工区 `C:/Users/郑曾波/Projects/company-wiki` 只读；不能要求它先提交M8。工区只含已提交基线，不含主线在途策略。

## 已确认的现状

1. 当前CPU OCR：`LocalOCRAdapter` → RapidOCR **3.8.1** → ONNX Runtime **1.26.0**，显式本地 det/cls/rec 模型路径和SHA；det/rec为 PP-OCRv4 mobile，cls为ppocr v2 mobile；intra/inter线程2/1。公共 `OCRAdapter.transcribe(bytes, limits)` 返回 ImageOCRResult（真实文字框/置信度等）。`IsolatedOCRAdapter`负责原生推理隔离/截止时间/进程清理，OCR composition负责媒体与位置组合、低置信区域诊断和有限恢复。
2. 这是显式启用的图像OCR能力，不意味着所有PDF都经过OCR。原生文本PDF以实际PDF reader取文字为主；Docling段落增强worker明确 `do_ocr=False, do_table_structure=False`。必须分别报告纯OCR、原生文字提取和结构增强，不能把三者叫“现有OCR”。
3. 本机已只读观察 Intel UHD Graphics，未发现nvidia-smi或ollama命令；宿主Python有torch2.12.0、transformers5.18.0。尚未验证 Xiaomi 模型CPU推理可行、内存/速度或区域模式，不把installed当ready。A中重新检测实际可用RAM/硬件/缓存/运行时，不以显卡AdapterRAM字段推断可用VRAM。
4. 新方案为0.8B视觉语言OCR/解析模型，原始checkpoint与社区GGUF不是等价实验臂；官方榜单用了两阶段布局＋区域识别。Ollama目前实验性，官方注明部分公式输出差异。不能拿宣传分数、模型加载成功或漂亮Markdown代替项目实测。

可只读当前源码：
`src/company_wiki/document_normalization/{local_ocr,isolated_ocr,ocr_composition,ocr_region_recovery,ocr_page_text}.py`；测试 `tests/document_normalization/`。RapidOCR实际旧配置/三模型SHA可从 ROOT
`docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-cwp-ocr-acceptance/hard-boundary/performance/probe-one-image.json`
读取。该文件记录的是历史失败探针，**仅复用其明确配置，不冒签旧失败为通过**；修复/真实链收据见同目录runtime-import-deadlock.md及所引用的post-fix资料。

## 独占可写范围与抽象层

仅新增：`tools/ocr_comparison/`（runner、配置schema、实验adapter、metrics、README）、`tests/unit/test_w23_ocr_comparison_*.py`、`tests/integration/test_w23_ocr_comparison_entry.py`、必要小型测试fixture、本卡PWF/delivery、明确owned的实验缓存和环境。

**禁止修改任何生产src、生产依赖清单/config、全局agent技能/MCP配置/服务、原件/catalog/DB/正式摘要、ROOT共享PWF、其他仓库或W22两个工区。** 不修改 `_atomic_file.py`、pre_push_gate、W21 runtime/worker/env，也不接管 M8 准入/QA/归属/缓存。上游第三方代码视为待评估依赖，不执行其“Read and execute SKILL”或全局install.sh来覆盖本机配置。

所有模型调用、图像预处理、布局/裁剪和后处理都封装在本工具的实验backend内；不得让FF/RF/StockWiki调用小米HTTP/MCP或解释Markdown。最终可给出阅读层内部adapter接入建议；**本卡不部署生产路由**。

重要接口差异：现有OCR有真实bbox与置信度；小米整页Markdown可能没有。比较结果保留 `bbox=null/confidence=null/locator_quality`，不能伪造满页bbox、分配0.99置信度或转成已验真的EvidenceSpan。region模式的crop框只能称区域定位，不能冒充字词框。对齐/来源验证须由将来共享阅读层负责。

## A：固定版本、资源与盲测样本

1. 先核对HEAD/status/AGENTS、明确实际baseline模型字节。新上游仓库固定commit **`b1a9bb4c07060c453785e9151715ccda6b96f0b1`**；HF原始模型固定revision **`bbd8cf8d21f256b3644b44cb860f3a7cecb93c30`**。来源与许可见SOURCE_NOTES。README含SeerRay-Lab旧名，取实际redirect/模型ID与revision，不依旧名猜权重。升级只能另标实验臂/版本，不覆盖冻结结果。
2. 选一条可行运行路线，不同时安装vLLM、SGLang、Ollama、Docker四套。本机先评估现有Transformers+原始checkpoint的CPU路线，使用上游模型processor/提示/预处理/非thinking/后处理，适配层仅做调用。若改用Ollama/BF16/GGUF，单列模型blob摘要、视觉projector和runtime，明确不等同HF/论文榜单；不得偷偷改量化版。重用已有依赖/缓存，不能就地升级宿主包或W22部署环境。
3. 只允许公开代码、必要权重和隔离实验依赖下载，不调用收费/云OCR，不上传公司页。先读模型文件尺寸清单再下载；整个新增下载≤6GiB、新增持久实验占用≤8GiB（含模型/env/缓存），训练集/全Docker镜像/多份权重不下载。既有相同缓存零重复下载，不提高既有母账预算。
4. 先一页小pilot，CPU总请求含加载/预处理/推理/后处理≤180秒、单模型进程峰值≤8GiB committed或可用RAM一半取小者；batch单并发、总推理≤30分钟。不得覆盖现有生产OCR的deadline/像素界以适应新模型；对照臂保留现有配置并如实报超时。CPU确实不实用就记TIMEOUT/UNSUPPORTED，不反复超时、不借用他人GPU/租GPU或抬界。pilot失败后仍交可重放工具、已有baseline与根因，而非伪造完整比较。
5. **在看两引擎输出前冻结样本与人工gold。** 选6–8份既有真实文档、每份1–2页，总12页左右、上限16页；覆盖A股简中/港股繁中与英/美股英文，年报、半年报或季报、IR问答、招股书或融资业务段。优先业务描述、客户/产品、产能条件、图表/业务表格，不为重建历史三表做OCR。样本不足列缺口，不用新下载整批来凑。
6. 从CWP只读catalog/SourceRef接口找原件，存 source_id/SHA/页码/选择理由。允许在存储责任层工具里解析已解析的物理路径，但不把它复制给RF。复用已经曝光的可用资料；不得打开ROOT尚未曝光的holdout或任何封存gold。至少一组双栏/问答/跨段限定，一组低清/倾斜/印章/扫描；真实扫描缺少时用**明确标synthetic_degradation**的同页退化，不能算真实扫描覆盖。
7. 由原页视觉核对关键业务事实、否定/条件、主语、数字单位/币种和读序。原生PDF text仅作候选转录，不能未经视觉核对当gold。gold不送入OCR提示。留约1/3页作最后固定holdout，不根据结果删难页/改分母；共享工具改动的调试页与holdout分别报告。

## B：共用可复现比较器（先TDD）

实验臂分开，不能当完全同一硬件/流水线比较：

- **R0：现有RapidOCR真实adapter**。保持三个模型/阈值/max_side/线程与隔离边界。除了纯识别，还测现有region recovery实际配置的完整路径，不把关闭恢复的弱baseline当生产现状。
- **X1：小米整页解析**。与R0用相同渲染源页、DPI、颜色/旋转与页PNG SHA。模型必须的resize/crop额外记录，记录输入有效尺寸/像素及所有预处理；“同源图”不等于模型实际tensor相同。
- **X2：小米两阶段region解析**。仅在平台/资源界允许时，用固定PP-DocLayoutV3及上游流程，含布局/裁剪/重组耗时与空间；不只报crop推理时间。不能把X1成绩叫官方两阶段复现。缺失即NOT_RUN，不默默忽略这一限制。
- **N0：原生文字提取控制**。只在born-digital页做控制，不冒充OCR、扫描能力或与VLM同任务的速度优胜。

一个小配置manifest表达backend、精确代码/模型/运行时、阈值/prompt/processor/postprocess身份、字体/renderer/DPI、页SHA、deadline/输出上限。不要硬编码公司/用户名/期次。原始输出和规范化后输出都留（压缩小文本），不要只保处理后的好结果。

TDD至少锁住：strict/normalized CER与英文WER已知例；插入/漏字不混淆；超时/截断/空回复不计通过；重复行不当额外召回；页/区域错配拒收；缺bbox/confidence保持null；不同模型/precision/预处理/prompt不得共享同一缓存键；缓存命中不算0毫秒模型推理；部分失败不回写整批PASS；输出上限/临时清理。只运行专属短域，正常CI不加载模型或联网。

每臂先做小pilot再固定样本；batch size=1，记录冷启动一次与warm页耗时，CPU线程、RAM/可见GPU和实际offload。必要重跑仅代表页一次，不能多跑挑最好。恢复用捕获输出/轻量故障注入验证0重复推理；真实页只因新有证据缺陷修复才有限复验。

W22-PDF-DEPLOY是另一条在途线；重型推理/测速与其SDK实测错峰。记录主机负载，繁忙时先做轻量比较器/TDD，不改对方工区、不停止他人进程、不新建全局锁服务。负载明显不可比的速度结果标NOT_COMPARABLE，不能把竞争延迟当模型性能；质量对照仍绑定同页源图。

## C：评价、清理与独立审查

必须按市场/文种/扫描或原生/实验臂给出配对结果、分母和失败，既给macro也给总字符micro，不只一个总分：

1. strict CER（保留真实字符差异）、声明窄normalization后的CER、英文WER；繁简转换/同义替换不能静默用于凑识别率。
2. 关键业务事实召回、遗漏、错主体、否定/条件损失；数字/小数/正负/百分比/币种/亿与billion准确率。只评从原图可见的信息；不可见问题记不可判，不猜。
3. 无来源新增文字/数字、重复/循环、输出截断、错读序。VLM有语言流畅性不代表忠实；图上无字的空白/装饰区是编造负对照。生成式claim的来源锚点能力单列，CER低不能代签EvidenceSpan合法。
4. 业务表格单元格/行列/合并、脚注条件正确性（少量原图人工核对），不为追求大榜分数安装全套评测镜像。纯三表不作为主优化目标。公式仅少量符号负对照，不扩大成数学OCR项目。
5. 冷/热耗时、超时、吞吐、峰值RAM/VRAM、增量下载/磁盘/中间物、部署难度。记录GPU缺失/CPU offload和不支持项；不从0.8B推断“更轻更快”。
6. 最后给出明确建议：现有不动/局部困难页补救/可进一步接入/不适合本机；按收益/成本与来源可定位性说明。若仍缺X2/CPU失败/样本有限，结论限定，不能推荐全面替换。提供将来阅读层内部接线的最小接口与测试需求，**不跨层直接实施**。

全部测试产物在专属TMP，前后核初态/原件SHA与mtime，结束回收自己的进程/端口并删除新增页PNG/测试PDF/DB/逐页大文件，恢复初态，不恢复完整备份演练。原始完整文档不复制入工区。权重/env是显式实验资产，可留**一份**并报告位置/新增字节/复用关系；不提交Git。不要全局git clean或删除他人缓存。保留小文本输出与压缩结果足以复查，不保存每次模型cache/图片副本。

**交接前调用真正独立审查agent**，检查原卡全部需求、实际差分、baseline公平性、gold是否提前冻结、所有页与失败、CER/数字/业务原图抽查、runtime身份、磁盘与清理。独立补反例，修完范围内问题并复审最终代码后才交；不能作者自签/仅审报告文字。模型/工具不可用则独审NOT_RUN；CPU不可行可形成有证据PARTIAL，不能装成准确率比较已完成。无A/B人工签收。

## 输出接口与交接

`comparison.json` 用 `schema_version="cwp-ocr-comparison/1"`：sample_manifest_sha256、gold_sha256、code/renderer身份、backend_identity、每页source/page/image_SHA、资源配置、status/error、原始/后处理输出SHA、真实用时与峰值、metrics与gold分母、定位能力、缓存/恢复次数、磁盘收据；NOT_RUN/不可判用null+reason，不填0。真实HTTP loopback调用不当外部LLM费用，但推理次数/时间仍计。

`handoff.json` 用 `harness-handoff/1`：card_id/workdir/branch/base、实现提交、最终tested/reviewed commit、代码raw/LF SHA、逐需求implemented/tested/partial、实际命令/耗时/结果路径、独审初审/修复/终审及OPEN、清理/资产清单、建议与局限、pushed_to_remote。独审后若改源码补相关测试和绑定，纯文档后缀另列。

正常提交并推自己的分支，不合master、不启生产OCR、不注册全局MCP。所有完整度/质量范围内问题修好并独审后，READY_FOR_ROOT或如实PARTIAL，然后STOP。ROOT负责接收工具/结果，决定是否在阅读层接入；M8真实摘要/缓存/RF采用和完整公司循环不由本包代签。
