# R1进度

ROOT于2026-10-31从946537d0d75ac36b22ac0bb24e0f484a896b4c95建独立稀疏工程，只有4个已知计划seed，0原件/模型复制，0真实推理。作者接手自行A/B/C，不改ROOT共享PWF。

2026-11-01 R1执行：
- 工具：ROOT已修统一入口/父watchdog/持久缓存/身份；本轮新增 campaign 账本(tools/ocr_comparison/campaign.py)，跨进程TDD 12/12(预算闭合、恢复零重复推理、耗尽诚实not_run、损坏拒绝)。
- 样本：7页新文档(中微AR2025 p29、药明AR2022 p10、金山雲FY2025 p003/p012含9列真实表格、壁仞AR2025 p30、Berkshire 2007 p1/p5)，全部避开旧14页与旧pilot页；独立agent凭PNG核gold(14,624字/171事实/98条件/301数字token)，含1次页面替换的版本化修订(任何引擎运行前)。冻结提交970532af。
- campaign：账本226.1/1800s。R0 7/7(macro strict CER 0.1022, 数字token召回0.912)；N0 7/7(0.1178/0.997)；旧页pilot R0 19.4s；X1F尝试1在cap 1.142GiB(avail 2.28GiB)下加载MemoryError(实测固定开销1.33GiB)，之后cap降至0.84GiB，未重试；X2 NOT_RUN。公式合成夹具R0仅1/4公式符号保真。事实计数程序化：R0 106/171、75/98、268/301(全分母含失败页)。
- 清理：页PNG已删(manifest保留SHA与渲染脚本)；模型资产只读复用未复制。deviation：A2 pilot 在冻结后补做(旧页R0)，旧页从未在新页gold冻结前被OCR，盲性成立。
