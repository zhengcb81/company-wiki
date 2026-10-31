# W23-OCR-R1：只补真实比较证据，不重做已修工具

状态：READY_TO_DISPATCH。用户已要求“小问题ROOT直接修，大问题给返修包”；本包只返修不能靠代码追认的实验质量缺口。W22两包不返工，W23原工具工程修复已进入ROOT代码基线。

- 独立工作目录：**`C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr-r1`**。
- 分支：`codex/w23-ocr-r1-20261031`。
- 原工区创建基线：`946537d0`，仅表示创建时点。**启动实现前须纳入已发布平台修复 `20dd0143197462be31a467cdd53bcff1a31b4d94`**（精确CI41241389817 success），不能继续使用旧Windows/Linux不兼容工具。已有本卡WIP先保留并核对冲突，不擅自reset/覆盖。后续ROOT的M8生产语义代码不属本卡范围。
- `PLAN_ID=w23-ocr-r1-2026-10-31`；`PWF_PLAN_ROOT=docs/plans`；本地唯一计划 `docs/plans/w23-ocr-r1-2026-10-31/`，先读TASK_CARD/task_plan/progress/findings。
- 交付：本工区 `delivery/w23-ocr-r1/handoff.md/json`、`comparison.md/json`、新冻结样本/gold/实际运行manifest和紧凑收据。ROOT共享PWF只读。

## 已完成的有效工作与失败证据

先读ROOT `docs/plans/du11-source-closure-2026-10-18/review/w22-w23-reception-20261031/README.md` 及其中OCR报告。原作者 `company-wiki-w23-xiaomi-ocr` 工区、原gold、raw结果、handoff保持只读，不能覆盖成“修好后的历史”。

现有RapidOCR配置与三个ONNX字节已核对。小米原始BF16与衍生F32的488个tensor存储值逐字节零扩展已核对；这不证明计算/输出等价，也不是官方榜单复现。模型真实执行过，结果不是mock；不因比较缺陷宣称模型无效。

但原试验存在：600秒请求而非卡180秒、不同调用累计已记录约2471.8秒且另有诊断、部分页235秒；实际16384输出等参数与旧manifest的2048不符；holdout页被pilot用过；X1逐页eval事实合计67而总表写76，条件12而总表写10；未跑页事实不能从完整分母静默移除。**这些只能保存为探索性资料，不能追认合规/盲测/优胜。**

ROOT已修统一X1入口、父watchdog、实际身份、跨进程持久缓存、指标/数字/错页、显式流式F32转换器、3.10与UTF8兼容，并通过中性测试。不要重写一套runner；优先复用 `tools/ocr_comparison/`。

## 写入边界

只可改 `tools/ocr_comparison/` 中本轮统一累计资源/报告完整度所必需部分，以及本卡专属 `tests/unit/test_w23_ocr_r1_*.py`、`tests/integration/test_w23_ocr_r1_*.py`、本卡计划/delivery。既有比较器测试保留；若需改只能因真实合同缺陷，不能改预期迎合模型。

禁止生产src/依赖/config、全局技能/MCP、原件/catalog/DB、W22/ROOT M8/RF/FF/StockWiki/IQS/Dayu/Dashboard、作者旧收据。图像/模型/布局处理仍封装在阅读试验层，其他层不能直接调用小米/MCP。

复用原作者已声明的模型资产：`C:/Users/郑曾波/Projects/company-wiki-w23-xiaomi-ocr/.w23_cache/hub/` 下实际snapshot（原revision `bbd8cf8d21f256b3644b44cb860f3a7cecb93c30`）。仅只读显式传入路径，不复制权重/env，不运行旧一次性脚本，不停止用户浏览器/其他harness进程以挤内存。新工区只稀疏工程与计划，0原件/模型复制。已有缓存约5.27GB含BF16与声明的F32衍生，不另下载一套。

## A：先冻结修复合同、新样本与gold

1. 核对HEAD/status/AGENTS，读ROOT验收及旧实际结果；不把旧“READY_FOR_ROOT”当已通过实证。A/B自行推进，不等ROOT小节点签收。
2. 使用旧非holdout页做**一次**运行可行性pilot；所有此前曝光页一律视为调试/回归资料，不再记为新blind holdout。保留之前gold及修正历史，新版有具体差异说明。
3. 另选约6页既有真实文档，尽可能每市场CN/HK/US两页，涵盖简中/繁中/英文、业务问答/条件否定、复杂读序或业务表格。避开旧14页、pilot页及ROOT封存未曝光holdout；优先不同原件。来源市场与文种依据实际来源身份，不按文件名猜。
4. **任何新页OCR前**，由独立agent依原图核gold，冻结source_id/SHA/页码/原图PNG SHA、事实/条件/数字单位和读序检查点，并留至少2页到最终统一运行。不得先试难度再删除页面。若缺真实扫描/双栏/某市场，保留coverage gap；退化页明确synthetic，不冒真实扫描。
5. 若发现gold错，版本化纠正并说明发生在何时、影响分母；不能改原gold或保持“当前gold在输出前冻结”的虚假标志。原生text只作核对起点，不能无视觉核对当地面真值。

## B：一次有限campaign，实际参数贯穿全链

1. 原始BF16、F32变体、R0、N0、X2分别记身份/能力。不重试已证不实用的BF16600秒配置。可直接选声明的F32路线，不把它叫官方GPU榜单或BF16数值/计算等价。
2. 本轮R1**一个统一累计1800秒推理campaign**，含R0/X1、成功/失败/pilot/重试；历史2471.8秒另列，不冲销。每请求≤180秒，剩余不足时min(180,remaining)或停止；output token/字符界显式配置并进入所有run/receipt/cache身份，不能私下抬成16384。含加载、预处理、推理、后处理；超时由父进程真实回收，不能只前后检查。
3. 现有工具仅强制单invocation1800，跨invocation累计原由caller负责；这里要用**一个campaign入口或最小持久计时状态**把累计闭合，恢复/重启不续期，不另建生产任务库/审批或人工hash许可链。状态坏/未知在途耗时保守计入，不自动重试洗掉成本。先用无模型fake backend做跨新进程TDD，再实际跑。
4. 资源仍≤min(8GiB committed, 启动可用RAM/2)，单并发、现有同源渲染/实际resize/processor/prompt/代码/模型SHA全部记实；不抬生产OCR像素、截止时间或母LLM额度。繁忙时先做轻量工作，不杀他人进程，速度结果记录负载。
5. R0保留生产隔离和region recovery；N0仅born-digital控制。X2平台/预算不适合就明确NOT_RUN，不安装第二套大栈；无X2不得比较官方两阶段排行榜或声称完全替代。小米缺bbox/confidence继续null，不能伪造EvidenceSpan。
6. 所有合法请求与缓存输出从同一capture生成manifest/逐页记录/比较报告，不再用patch脚本手工改总表。完成、超时、截断、未跑各有真实页/原因和完整分母；断点恢复通过 `--cache-dir` 实际复用，不重复推理。缓存必须绑定完整实际身份，命中保留原测量时间，不能把0ms当性能。

## C：指标、真实验收与独立终审

- 对每市场/文种/实验臂给CER strict/narrow、英文WER、全部页分母与失败；同时列已完成页条件分数和全样本覆盖分数。事实/条件/币种/量级计数从逐页记录程序求和，与总表、handoff完全一致。不能只用数字都出现证明单位/关系正确。
- 原图逐条检查关键业务事实、否定、限定、主体、数字和读序；不流畅补全看不清的字。VLM幻觉/重复/截断与表格错位单列，空白区是负对照。至少一个小公式符号控制可用合成夹具；真实样本没有公式就不冒覆盖。不能扩大为三表重建/数学OCR项目。
- 真实时限内跑不完就是TIMEOUT/NOT_RUN和PARTIAL，也可形成有效“不适合本机”的结论；不需要硬凑满成功页数。推荐只能是现有不动/少量困难页补救/进一步接入候选，不直接切生产。
- 新测试仅专属短域、fake runner、跨两进程预算/缓存；不把真实模型装进CI/每commit，不反复全仓。测试根前后恢复，删除新增PNG/PDF/DB/逐页大输出，保留紧凑原始文本/收据；模型资产只读保留一份，所有SHA/mtime不变。不得整份恢复备份演练。
- **交接前调用未参与实现的独立agent全面审原卡、代码、逐页实际输出、全部失败、gold/holdout时序、累计资源、各分母和清理；独立补反例，范围内问题全修并对最终代码复审后才交。** 不能只审措辞或作者换名自签。真实实证仍受硬件限制可PARTIAL，但理由和剩余必须具体。

交 `harness-handoff/1` 的handoff：base/实现/最终tested/reviewed commit、raw/LF代码SHA、冻结样本/gold及时间轴、实际命令/全部run与campaign ledger、逐需求done/partial/not_run、独审报告/问题闭合、清理与资产、remote状态；`comparison.json` 沿既有schema并记录campaign/实际身份与全量分母。未知用null而非0/PASS。

正常提交并推本卡分支，不合master、不改ROOT计划或全局环境。完成交接后STOP等ROOT；本卡不替ROOT签M8摘要/缓存/RF/完整公司循环。
