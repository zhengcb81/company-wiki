# W23进度

2026-10-30 ROOT从de7ffe48aee3f9decfb4be6dfc2f561dcd3aa29d建稀疏独立工区，仅预置计划。未安装模型/新依赖、未运行OCR、未读新holdout/下载原件。作者在本计划更新，不改ROOT共享PWF。

2026-10-30 A阶段完成：
- 基线核验：三模型SHA与config/local_ocr.json一致（det d2a772…/cls e47ace…/rec 48fc40…，共16,189,007B）。
- 资源：i3-1220P 10C/12T，15.77GB RAM，无独立GPU（Intel UHD），无nvidia-smi/ollama；avail物理内存波动2–2.1GB、commit可用~10.9GB（桌面应用占大头，非W22任务）。pilot上限按卡=min(8GiB committed, avail/2)执行，pilot时实测。
- 上游冻结：GitHub commit b1a9bb4c07060c453785e9151715ccda6b96f0b1；HF revision bbd8cf8d21f256b3644b44cb860f3a7cecb93c30（模型架构Qwen3_5ForConditionalGeneration，transformers 5.8.1保存；本机transformers 5.18.0原生含qwen3_5）。model.safetensors 1,746,937,856B，SHA-256 d4551e9f6127ac9e35cff7b4f7a72a90410e03e6c8676a36f0e2b7eaeb5d5348（=HF LFS blob名），快照在工区.w23_cache/hub（未提交）。新增下载1.77GB≤6GiB预算。
- 样本冻结（引擎输出前）：sample_manifest.json，7文档/14页=8 eval+5 holdout+1 synthetic_degraded（ksy p2同页0.55x+1.3°退化，非真实扫描）。市场：CN简中4页文档、HK繁中2份、US英文电话会1份；文种：年报/半年报/季报/IR问答/可转债募集说明书/英文电话会。渲染pypdfium2 4.30.0@200DPI PNG，页SHA在manifest。
- gold冻结（引擎输出前）：gold.json（cwp-ocr-gold/1），14页/16,387字。原生文本层仅作候选：修正勾选框glyph、392.0¹脚注上标合并、页码读序、参加人行序；美團p11原生层乱序→全目视转录；美團p0无文本层→全目视转录。facts数字与full_text自动交叉核对0错配。
- 修正记录：hrjp/bili两文档最初SHA前缀误配同名公司其他文件，已在引擎输出前改为精确SHA重冻结（华锐可转债募集说明书c6ed5666…、B站电话会55d3581c…）。

下一步：B阶段TDD比较器（tools/ocr_comparison），R0/X1 pilot，固定样本对照。
