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

2026-11-01 R1 收尾：独立终审三轮（15项+8项+R3文档项）全部闭合；终审结论 READY_FOR_ROOT。唯一经验性 OPEN 为 X1F attempt2 job peak(1.753GiB) > cap(1.602GiB)（Job Object 约束未生效），已作为平台问题交 ROOT。最终交付：R0/N0 7/7、X1F 两次失败证据、空白与公式控制、单源 comparison/handoff（含 ledger 1406.5/1800s、逐层/分拆分母、货币感知事实计数、缓存命中实证）。分支 codex/w23-ocr-r1-20261031 已推送。

2026-11-01 R1 自审补充（A3 覆盖闭合）：
- 补 1 页 CN 业务问答（万华化学2021业绩说明会纪要 p3，独立gold revision 4，694可见字符/18事实/19条件/15数字），页面在任何引擎运行前转录；样本扩为 8 页（eval 6 / holdout 2），manifest revision 2 记录扩展与分母影响；R0 24.9s、N0 补跑（账本 1431.4/1800s）。
- 新增卡 C3 负对照指标：无来源行（bigram 包含率<85%），R0 38/501=7.6%、N0 5/308=1.6%，声明为编造上界（含识别错误行）。
- 资产核验：bf16 model.safetensors SHA d4551e9f 不变、fp32 衍生 mtime 早于R1、7份原件 mtime 均早于会话（零写入）。

2026-11-01 R1 终态：独立终审五轮（15+8+4+5 delta 项）全部闭合，76292e3f 确认 READY_FOR_ROOT。最终样本 8 页（CN 3 含问答、HK 3 含 9 列表格、US 2；eval 6 / holdout 2）；账本 1431.4/1800s；R0 8/8（macro strict 0.1000、数字 token 召回 0.9158、数字在场 0.9917、事实 164/189、条件 107/117、数字 288/291、无来源行上界 7.6%）；N0 8/8（0.1178/173/189）；X1F 两次失败（第二次平台修复后仍分配失败+原生崩溃，job peak 1.753GiB>cap 1.602GiB，OPEN 交 ROOT）；X2 NOT_RUN；空白负对照 0 字符；公式 1/4 保真。剩余预算 368.6s。STOP。


## ROOT R6预算/cache工具修复（非模型复测）

从d2f6e6f0新建--no-checkout sparse+read-tree独占工区；8F/6P真实X1F stub新进程RED后，最终新31P/23.02s和Ruff通过，之前108相关例P/2warnings/93.51s；二者重叠不累计。初次广域8error因未取旧两JSON，已仅补小fixture；合成4字节converter hardlink在Low沙箱拒写，宿主同域通过，未改converter；一次git sparse add不支持--no-cone参数已去重复flag，无源码副作用。ae438a32正常本地提交3文件，现待review_a新版本独审；主线未合并/推送，原件/模型/src/config零改动，所有旧run/ledger/comparison/review保留。最终新测试用TemporaryDirectory逐例恢复自有scratch和子进程，未全局清TMP或删作者PNG。


## ROOT R6新工具独审PASS，交接后STOP

ae438a32由未参与修复的review_a真正独审：原4RED重放GREEN、新增cache输出已落/marker前死亡GREEN（占用不退款、partial、runner1）、选10case 10P/4.02s，runtime3文件SHA未变，无实质P1/P2。原ledger/comparison/旧review和作者PNG保持；模型0调用/下载，实验仍PARTIAL。当前handoff已分历史requirements/limitations，绑定新报告raw/LF SHA、scope、ae438提交，不补造76292 READY；formula当前用词为1/4 formulas、6/10 symbols。分支按ROOT改名codex/architecture-w23-repair-20261101以复用既有候选CI。正常本地提交docs后STOP，ROOT后续整合稳定master/候选CI，作者不推送/并线或复跑模型。
