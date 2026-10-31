# W23-XIAOMI-OCR ROOT independent reception

审查对象：作者 HEAD `a517213cc57d4f9d66d00addd9dfff2f8ee9ce74`，原卡 base `de7ffe48aee3f9decfb4be6dfc2f561dcd3aa29d`。作者工区完全只读；无模型加载、OCR、下载、作者测试脚本运行、checkout/index/缓存清理。ROOT 后授权仅在 `_w22r` 修实验工具与专属测试，未提交。

**结论：历史实证 PARTIAL / 不接受“卡内完整精度比较”与原独审 0 OPEN 的背书；小米模型无效的结论同样不成立。工程修复已有限域验证，交 ROOT 复审。**

## 必须保留的历史缺陷

1. **[P1] 180 秒请求与累计 1800 秒边界被提高/突破。** `handoff.json` commands 明载 full 与 bf16 `--deadline 600`；`x1_full_f32_receipt.json` config 为 600s、16384 token，BYD p021/p022 为192.93/234.42s，仍标ok。批次1801.5966s之外，还有成功pilot68.9995s、bf16请求601.2387s；十份 X1 receipts 中可计 request 共2471.834832s，尚不含失败加载与诊断工作。原报告只披露“+0.09% in-flight overshoot”不能覆盖全部越界；`review_independent.md:690-694` 知道600s仍终审 READY。
2. **[P1] 所谓 holdout 已用于优化/成功pilot。** manifest 将 `meituan_ar_2024_p000` 标 holdout；`x1_pilot_f32_final_receipt.json` 以此页成功通过69s，之后在 full 中再跑57s，仍列holdout统计。早期 f32_ro 收据也选择此页。不能通过改标签恢复盲测；其余未调试 holdout 的独立性没有可执行封存证明。
3. **[P1] runtime/资源清单不再绑定实际 X1。** `comparison.json.run_manifest` 仍是旧 `fde39dfe`、180s/2048token/1.155GiB 与旧 X1 描述，而 arms.X1 与原始新收据为600s/16384token、不同内存cap及映射变体；precision仍填 checkpoint-native-bfloat16-cpu，实际映射 F32。`consolidate_x1_executed.py:94-95` 事后patch此结果。不能把该 run_manifest 当成一次完整同配置调用收据。
4. **[P1] 事实/条件分母错误。** `fact_scores_x1.json` eval逐页67/67事实、12/12条件，totals及comparison/handoff却写76/76、10/10。全部 holdout gold42事实，其中未跑页10事实被置0/0/0，只报已跑32；需要同时报告完整分母与完成页分母。R0声明eval59facts同样不等于最终gold67，不宜据此量化跨臂业务召回。
5. **[P2] 不足以代签完整生产阅读质量。** R0确实加载原生产配置、隔离adapter并调用真实region recovery，未发现偷偷降det/rec阈值；但 `rapidocr_r0.py:61-81` 直接按返回顺序拼接识别行/恢复行，没有生产geometry/order_page_lines组合。可以称真实引擎+恢复臂，不能把读序CER差异直接称生产完整阅读结果。业务表格结构/行列配对独立评价不足；digit-present删去所有非数字再跨串匹配（`compare.py:62-65`），会把单位/符号/邻格数字丢失看成召回，不能替代数字事实正确性。
6. **[P2] 盲冻结与负对照仍有限。** git记录支持 sample/gold 在首批提交结果前冻结（0d24c943）；无法仅用commit与boolean证明此前不存在未跟踪引擎输出。最终gold有看结果后的字符/页脚修订并明确披露，不再是原始盲gold。装饰封面并非单独无字区域输入；零编造主张仅作者文字判断，未见逐区域负对照/逐claim判定足以覆盖。未做本轮独立原图视觉复核，不代签人工gold准确性。无真实扫描/双栏/印章/公式，X2 NOT_RUN，N0为原生文字控制，报告不得当官方两阶段全榜复现。
7. **[P2] 推送字段未完成。** handoff.pushed_to_remote=null；本机 origin/codex/w23-xiaomi-ocr-20261030 ref 已是a517213c。支持已存在推送追踪记录，但本轮未联网核实远端当前状态。

## ROOT 已修通用工程缺陷

- 共同比较器 X1 原先给不存在的构造参数 `memory_cap_bytes`（原 `run_comparison.py:149-153`），交接CLI必报 TypeError。现在委托 `run_x1_batch`，保留执行receipt；主清单使用真实max token/开始资源。
- 子进程时间检查无法中断单次prefill，原parent仅 total+deadline+300s backstop。现在拒绝 >180s/>1800s 或超 card memory cap，父watchdog独立终止阻塞请求，子进程把剩余总预算传入单页并计入失败elapsed。每次独立invocation仍须调用方做累计任务预算；不伪造跨invocation全局预算账。
- 身份包含实际compute precision、模型/processor/tokenizer资产SHA、runtime版本与完整实验代码SHA；历史结果未改。缓存随runtime/代码/模型/prompt/输入/参数变化失效。
- 增加可选持久 ResultCache；实际 CLI `--cache-dir` 接入 R0/X1，每条JSON含key与payloadSHA、同目录原子写/fsync，截断/坏checksum为miss，命中保留原测量耗时且inference_runs=0。两个全新进程fake X1实际CLI只调用一次backend；未加载OCR。
- normalized micro CER 分母由原始字符总数改为normalized reference长度（原 `compare.py:116`）；重复/未知page及提供的source/page/image身份错配显式拒绝。
- 数字去重保留同值不同单位，增加显式币种前缀身份；不推断未标币种。仍只计算文本token PRF，不代替表格位置/主体/条件的语义判定。
- 原fp32 converter声称streaming却积累全模型，并隐式写固定snapshot。现在显式 `--source/--output`、1MiB流式精确字节扩展、原子拒覆盖，无torch/硬编码目录。
- CI轻依赖检查改独立新进程，不受pytest其他模块已导入torch影响；tiny mapped backend测试的torch/safetensors只在该optional测试importorskip，核心比较器测试不skip。

## 独立验证与范围

- 原始模型与F32文件全量488/488 tensor逐字节验证：所有key/shape对应，BF16每值精确零扩展成F32，无量化/改值；原文件SHA `d4551e9f6127ac9e35cff7b4f7a72a90410e03e6c8676a36f0e2b7eaeb5d5348`，F32 `ddd3b66173fe4dad520a10d23b3ce287bac84691b28e7cd6c261d15c09dcc71f`。这证明存储值一致，不证明F32/BF16算子计算或手写decode与官方generate等价。
- 作者handoff全部20条code raw/LF SHA与作者工作树一致；最终tested60d26fd8后实验代码无差分（仅后续文档），证据另存author-final-code-sha.json；未检查每一上游snapshot与远端原仓相同，未联网取新代码。
- 作者缓存47文件逻辑字节5,271,596,499，低于8GiB；两份权重分别1,746,937,856与3,493,815,312B。新增下载1.77GB依据交付metadata，未独立重建网络下载账。未清作者缓存。
- 原47+首批11测试：58 PASS，78.97s；发生于最后持久缓存补齐之前。最终新13+相关cache/runner/retry4：17 PASS、34 deselected，2.02s。未将58P误称最终60P全域，未运行模型、OCR或网络。
- 新测试真实验证空阻塞子进程被parent watchdog终止、两进程CLI零重复推理、缓存损坏、tiny checkpoint精确转换、dtype/asset身份、CER分母、币种/单位、重复/错页与构造入口。

## 交接

修复未提交，ROOT应审14个专属路径后统一提交。`integration-code-sha.json` 绑定当前未提交修复（raw/LF）；`reception-evidence.json` 保存具体分母/时间/状态；`weight-byte-verification.json` 保存全量tensor值证据。历史实证仅作exploratory PARTIAL，若要卡内结论，需重新授权/安排资源预算内的预冻结未曝光样本试验；本验收未开始新试验，也未把失败解释为小米OCR无效。
