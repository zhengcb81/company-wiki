# R1进度

ROOT于2026-10-31从946537d0d75ac36b22ac0bb24e0f484a896b4c95建独立稀疏工程，只有4个已知计划seed，0原件/模型复制，0真实推理。作者接手自行A/B/C，不改ROOT共享PWF。

2026-11-01 R1执行：
- 工具：ROOT已修统一入口/父watchdog/持久缓存/身份；本轮新增 campaign 账本(tools/ocr_comparison/campaign.py)，跨进程TDD 12/12(预算闭合、恢复零重复推理、耗尽诚实not_run、损坏拒绝)。
- 样本：7页新文档(中微AR2025 p29、药明AR2022 p10、金山雲FY2025 p003/p012含9列真实表格、壁仞AR2025 p30、Berkshire 2007 p1/p5)，全部避开旧14页与旧pilot页；独立agent凭PNG核gold(14,624字/171事实/98条件/301数字token)，含1次页面替换的版本化修订(任何引擎运行前)。冻结提交970532af。
- campaign：首轮账本口径后被终审纠正（见下）；最终账本见 comparison/handoff。R0 7/7(macro strict CER 0.1022, 数字token召回0.9117)；N0 7/7(0.1178/0.997)；旧页pilot R0 19.4s；X1F尝试1在cap 1.142GiB下加载MemoryError；平台修复后尝试2(cap 1.602GiB)加载成功~97s后generate分配失败并原生崩溃，job peak 1.753GiB>cap(OPEN平台问题)；X2 NOT_RUN。公式合成夹具R0仅1/4公式符号保真。事实计数口径经终审重写（币种窗口+可达分母+双口径），最终见 comparison.json。
- 清理：页PNG已删(manifest保留SHA与渲染脚本)；模型资产只读复用未复制。deviation：A2 pilot 在冻结后补做(旧页R0)，旧页从未在新页gold冻结前被OCR，盲性成立。

2026-11-01 R1 第二轮（终审修复）：
- 平台修复：R1-setup 要求的 20dd0143（OCR 平台资源隔离/跨平台）已 cherry-pick 入分支（-x），job_limit 改为平台中立，59 项测试全绿。
- gold：独立复审发现药明页真实错字（客户对公→客户对公司的服务需求，跨行），已按 revision 3 版本化纠正并记录时机/分母影响；退场页 p001 归档；重新计算全部指标（不重推引擎）。
- 事实口径：fact_match 重写——币种 12 字窗口强制匹配（人民币/美元陷阱用例为 False）、数字仅计入自匹配可达条目（25 条 nil/拼写条目单列）、事实/条件同时报告 surface 与 numeric-anchor 两个口径（R0: 149/171 surface、161/171 numeric、条件 89/98、数字 273/276）。
- X1F：fix 后工具链下重跑一次（attempt 2，带完整 receipt）：cap 1.602 GiB，模型映射加载 ~97s，第 1 页 generate 分配失败、第 2 页原生 AV 崩溃（wall 106.5s）。receipt 记录 job peak 1.753 GiB > cap —— Job Object 上限未按预期约束，列为交 ROOT 的 OPEN 平台问题。attempt 1（fix 前工具链）保留披露。不提出任何小米质量结论。
- 账本：统一 campaign 账本 spent 1406.5/1800s；两处账务缺陷如实披露（首轮 R0 零秒行=少计，重测 144.15s；attempt2 崩溃后旧逻辑对 6 个未开始页各记 180s=多计 1080s，append-only 保留；代码已改为未开始页记 0）。历史 2471.83s 另列。
- 控制：新增空白负对照（R0 输出 0 字符=无编造）；公式夹具逐行判定 1/4 保真、缺符号单列；缓存命中实证（cache_hit=true/inference_runs=0/0 计费）。
- 报告：build_r1_delivery.py 单一来源生成 comparison.json/md + handoff.json/md（含 run_manifest、page_identity_provenance、per-stratum、eval/holdout split、X2 分母、R0 生产读序 caveat、receipts 目录）。
- 其他：P4 receipt 侧写已恢复；页 PNG 已删（SHA/渲染脚本保留）；分支已推送；独审 15 项正在复核。
