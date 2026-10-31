# W23进度

2026-10-30 ROOT从de7ffe48aee3f9decfb4be6dfc2f561dcd3aa29d建稀疏独立工区，仅预置计划。未安装模型/新依赖、未运行OCR、未读新holdout/下载原件。作者在本计划更新，不改ROOT共享PWF。

2026-10-30 A阶段完成：
- 基线核验：三模型SHA与config/local_ocr.json一致（det d2a772…/cls e47ace…/rec 48fc40…，共16,189,007B）。
- 资源：i3-1220P 10C/12T，15.77GB RAM，无独立GPU（Intel UHD），无nvidia-smi/ollama。pilot上限按卡=min(8GiB committed, avail/2)执行。
- 上游冻结：GitHub b1a9bb4c…；HF bbd8cf8d…（Qwen3_5ForConditionalGeneration；本机transformers 5.18.0原生支持）。model.safetensors 1,746,937,856B SHA-256 d4551e9f…b5d5348=HF LFS blob名。新增下载1.77GB≤6GiB。
- 样本冻结（引擎输出前）：7文档/14页=8 eval+5 holdout+1 synthetic_degraded（精确SHA，pypdfium2 4.30.0@200DPI）。
- gold冻结（引擎输出前）：14页/16,387字；原生层仅作候选；美團两页全目视转录；facts数字零错配。
- 修正记录：hrjp/bili最初SHA前缀误配同名公司其他文件，引擎输出前改为精确SHA重冻结。

2026-10-30 B阶段完成（提交8469df7c）：tools/ocr_comparison 比较器（metrics/cache/base/render/runner/manifest/run_comparison/R0/X1/N0/X2声明位）+ 单测29/集成9全绿；CER/WER/数字PRF锁定TDD契约。

2026-10-30 C阶段运行与评价（提交fde39dfe）：
- Pilot：R0 ok（62.7s冷，strict CER 0.116）；X1=unsupported——卡限=min(8GiB, avail/2)=0.92GB（实测avail 1.84GB）< 最小加载峰值3.49GB（2×权重字节，算术入档pilot_x1.json），未反复超时、未抬界；X2=not_run（paddlex栈超资源界）。
- 全量14页：R0 14/14 ok（eval macro strict CER 0.1636/micro 0.1769/narrow 0.1283；数字召回0.9219/精确0.9833；holdout macro 0.1705/召回0.9367/精确0.9737）。N0 12ok+1 empty（美團封面）+1 unsupported（退化页同源不重计）。
- 修复与公平性：N0相对导入bug修复；数字token规则收紧（千位逗号后OCR空格归一为一个token，"392.0¹→392.01"仍记错数），修复后重跑全量。
- 人工事实判定 fact_scores.json：eval 36 hit/4 partial/1 miss；holdout 35/3/2；损失集中于勾选框状态、孤立行丢失（英文页乱码碎片）、o-for-0字误；无编造/循环/空白区发明。
- comparison.md/json交付；comparison.json含run manifest（代码/模型/运行时/资源/上限/缓存键轴）与N0合并来源注记。

清理：render_probe/gold_candidates/r0_outputs已删；run临时目录已回收；ROOT无新增改动（仅其他车道在途文件）。frozen_pages保留至独立审查完成后删除（审查需页图复核gold）。

2026-10-31 独立审查与修复：
- 独立审查agent（general-purpose，未用作者结论）复核15项：冻结纪律/gold双向抽查/指标独立复算/X1算术/基线公平/缓存契约/生产隔离/接口/清理均OK；判NEEDS_FIXES，5项OPEN（review_independent.md）。
- 修复：runner字段白名单改为透传（repetition/recovery/drop/cache_hit/预检算术入档，新增流水线级测试）；gold复审字符级修正（2×U+0002→"-"、2×PUA \uf052→U+2611、6页页码真移读序尾，post_review_corrections入档，引擎未重跑，评估用修正gold重算）；fact_scores账目补齐并与gold逐页核对（事实83 hit/15 partial/3 miss，条件12 hit/6 miss）；comparison.md数字与叙述更正（实测cap 0.995/0.84/1.155GiB、§5合并注记改为最终四臂同进程运行说明）。
- 修复后最终全量对照（四臂同run）：R0 14/14，eval macro strict 0.1599/micro 0.1737/narrow 0.1250，数字召回0.9219/精确0.9833；holdout macro 0.1694/micro 0.1732；区域诊断8丢弃/3恢复/0重复入档；X1预检字段(cap 1.24GB<最小峰值3.49GB)入每页记录；TDD 39项全绿。
- 清理：render_probe/gold_candidates/r0_outputs已删；run临时目录已回收；ROOT无新增改动。frozen_pages保留至终审完成后删除。

2026-10-31 终审与交接：独审复审 READY_FOR_ROOT（0 OPEN，指标独立复算<1e-6一致，39/39测试）；frozen_pages已删；handoff.md/json交付（harness-handoff/1，PARTIAL如实限定）；分支push至origin/codex/w23-xiaomi-ocr-20261030（a430e984）。STOP。
