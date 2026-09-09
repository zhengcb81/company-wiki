# R4 实施细化文档：独立复核（2026-09-09）
复核者：independent review agent（非作者）
范围：r4-remediation-steps.md、r4-unit-remediation-map.md
结论：accepted_with_findings
## 发现
|ID|级别|证据|说明|
|---|---|---|---|
|F1|P2|r4-unit-remediation-map.md 行69–74（ZR-301–306）|「R4 步骤」列写组级引用「C04–C07、W04、W06、H01」，而 A 中定义为 W04.01–.06、W06.01–.06、H01.01–.09。与 B 规则2（两级路由、子条款在 U117.03 冻结）不冲突，但未落到子步骤，建议写「W04 组」或补后缀，避免各阶段 DR 误读为单条子步骤。|
|F2|P2|r4-remediation-steps.md 行14、18|§1 路线表首列以裸「H01」「FC903」作域标签，与子步骤命名空间同名。按题述表行正则统计得 117 次出现 / 105 唯一 token，而真实子步骤定义为 104 条；自动化完整性检查易把域标签误计为子步骤。建议标注「H01（组）」「FC903（线）」。|
无 P0/P1 发现；F1/F2 均为可读性/可机检性提示，不影响两文档自洽与 PLAN_ONLY 边界。
## C1 子步骤ID完整性
- 口径一（题述正则，仅 `|` 开头表行）：出现 **117** 次，唯一 token **105** 个。
- 口径二（表行首列以 ID 开头＝定义）：**104** 条唯一子步骤，**0 重复**。
- 分布：H01.01–.09(9)、W02–W07 各 6(36)、W08.01–.07(7)、W09.01–.07(7)、W10.01–.06(6)、FC903.01–.08(8)、U117.01–.07(7)、CL01–CL09(9)、AC01–AC07(7)、X01–X08(8)＝104。各组序号连续、无缺口。
- 差值解释：105 唯一 token ＝ 104 定义 + 裸「FC903」（仅作域标签，行18）；行14/18 的裸 H01、FC903 不是子步骤定义。
- 重复：定义层 0 重复；token 层 10 个 ID（W02.01–.05、W03.02、W04.05–.06、W05.01、W06.02）多次出现，均为跨行依赖引用，非重复定义。
- CL/AC 两表首列为「ID＋描述」格式（如「CL01 先canonical遮蔽健康副本」），仍构成完整定义。
## C2 117行映射完整性
- 口径修正：B 表行实际为 `| CA-001 | … |`（单元符含空格），题述 `^\|([A-Z]{2}-\d+)\|` 在 B 上命中 **0**；改用容错式 `^\|\s*([A-Z]{2}-\d+)\s*\|` 后：B=**117**、unit-ledger=**117**。
- 集合差：B−L = ∅，L−B = ∅ → **117 行一一对应，无漏项、无多余**。
- 第3列逐项比对（B「原审计结论」 vs ledger「本次结论」）：**0 处不一致**。
- 附核：25 CA + 92 ZR 与 B 行133声明一致；第2列「原痛点」0 处不一致；B 第9列「当前结果」117 行全为「待取证」（无结果声明）；B 行138–164 统计块 27 条求和 = **117**。
## C3 链接
- 相对链接共 **16** 条（A 12、B 4；URL 0、anchor 0），按文件目录解析后**全部存在，断链 0**。
- 目标含 simplified-execution-plan.md、simplified-test-matrix.md、r4-unit-remediation-map.md、execution-*-plane.md(3)、retention-independent-review.md、remediation-plan.md、filing-audit.md、../data-lake-simplification-2026-09-07/README.md、r4-independent-review.md、unit-ledger.md、r4-transition.md。
## C4 核心历史hash
- simplified-execution-plan.md：记录 `E0DCCD11…896467` / 实测 `E0DCCD11…896467` → **一致**（20155 bytes）。
- simplified-test-matrix.md：记录 `B90EF4D0…380F49` / 实测 `B90EF4D0…380F49` → **一致**（15123 bytes）。
- 即 A/B 未改动 r4-independent-review.md 所绑定的两份核心文档。
## C5 边界
- `git status --porcelain`：**0 条 ` M`**，`src/`、`tests/`、`scripts/`、`config/` 下无已跟踪修改 → **clean**。
- 未跟踪项 6 条：r4-unit-remediation-map.md、本复核文件、`.tmp-entity.py`、`.tmp-entity2.py`、`.tmp-real-docs.py`、`tools/pre_push_gate.py.bak`（后 4 项非本复核产出，仅记录）。
- `..\revenue-forecast`（C:\Users\郑曾波\Projects\revenue-forecast）6 路径逐一 Test-Path：tools/closure_gate.py、tools/closure_ledger.py、tools/receipt_validator.py、tools/verify_closure_ledger.py、tests/test_zr1101_closure_gate.py、tests/test_zr1105_closure_ledger.py → **全部 False（不存在）**。
## 声明
- 本复核为只读 + hash 计算：未修改除本文件外任何文件，未提交，未运行测试套件或任何产品命令，未使用网络。
- 结论仅绑定本次观测时点；A/B 仍为 PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED，本复核不构成实现结果、资格或完成度声明。
- 未覆盖：非本次命名空间的其他引用（A01/A08、C/D/E/O/P/L/B、GP-006/GP-010、R9 等）未逐项核，不在本复核范围。
