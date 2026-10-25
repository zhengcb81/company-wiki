# W18-CWP-HOLDOUT 独立审查总记录（2026-10-25）

三位未参与实现的独立审查 agent，四轮审查，全部原报告保留于 `delivery/w18/review/`：
`agent-1-gold-reviews.json`（源侧 gold）、`agent-2-tool-reviews.json`（工程/H项）、
`agent-3-replay-verification.json`（独立重放）。

## 审查轮次与结论

| 轮次 | 审查对象 commit | 范围 | 结论 | 发现 |
|---|---|---|---|---|
| R1 gold 初审 | 6a3f14c4 | 8样本锚点逐字+语义+prior_use+先冻结 | PASS_WITH_FINDINGS | 113/113锚点全过；1×P2+5×P3 |
| R1 工程初审 | 6a3f14c4 | 全diff+H01-H11+独立跑测试+收据一致性 | PASS_WITH_FINDINGS | H01-H11全PASS；6×P3 |
| R1 重放验证 | 6a3f14c4 | 新scratch真实样本重放+失败清理链+双反例 | PASS | 0缺陷；3×info |
| R2 gold 复审 | 351ba6ae→349a5548 | v2/v3修正逐项+新锚点重验+归档blob比对 | PASS | 3×P3（N1-N3） |
| R2 工程复审 | 349a5548 | D1-D6独立抽验+gold版本化纪律 | PASS | 4×P3（N1-N4） |
| R3 终审 | faa488a7 | v3.1残留补清+N1-N4修复聚焦确认 | 双PASS | gold侧无新问题；工程侧1处措辞（已按其原文修入28f06a9a） |

## 全部 finding 处置（无未解决项）

**gold（agent 1）**：F1(P2 禁真命题)→v2反转禁令方向且不增设无锚句依据禁令；F2(引句截断)→补全；
F3(preserve数值无锚覆盖×6)→扩跨/同伴锚（113→116锚，116/116重验）；F4(prior_use枚举)→补FC-504、
n5改注临时输出；F5(解释性措辞×3)→恢复原文；F6(禁令串真值括注)→移reason（v2+v3+v3.1全清，终扫残留=0）；
N1(台账漏登)→补登；N2(5处残留括注)→4/5首轮+1顺手+1终审后补清；N3(台账措辞)→修正。
v1 oracle 内容归档于 gold/archive-v1/，字节级以冻结提交 5e4488bb git blob 为准，v1 attempts 仍可重放。

**工程（agent 2）**：D1(选择器代际)→双盖章+CLI参数+findings披露；D2(零网络常量)→by-construction注明；
D3(重复SHA)→拒绝+新测试；D4(越界路径)→JSON refused；D5(损坏result)→原始错误记录+收据落盘+证据保全；
D6(DU-BENCH import根)→入档并断言。N1(行尾绑定)→LF稳定pin（8/8==HEAD blob==归一工作树）；
N2(归档措辞)→修正；N3(盖章参数)→取job实值；N4(异常契约)→结构校验后检查。

**重放（agent 3）**：真实样本独立重放与基线逐字节一致（排除计时）；0.2s超时正确判timeout无result；
cleanup_owned拒删foreign目录；同out-dir重跑旧attempt五文件逐字节不变；否定/条件错配与期间单位错配
双反例确认词匹配只产生机械可见性+not_reviewed，recall判FAIL/PARTIAL，不代签业务通过。

## 审查员独立执行的关键链（非读日志）

- agent 1：PyMuPDF/python-docx/HTMLParser 独立重提取全部8原件，116锚逐字复验（两轮）；
  git blob 比对归档；跨样本期间链逐原件核对。
- agent 2：自建中性场景实测 D3/D4/D5 行为；独立复跑 pytest（20/20×3次）与 ruff；
  从DU gold+du5+m1重建排除SHA池全量grep零碰撞；收据SHA哈希复核。
- agent 3：新scratch独立重放真实样本+基线逐字节对比；失败/清理/不覆盖链实操；
  构造否定/条件与期间单位错配双对抗fact验证H08口径。

## 最终绑定

- 最终代码 commit：faa488a7（v3.1+N1-N4）；文档收尾 commit：28f06a9a（措辞修正，按审查员原文）。
- 复审最终测试：pytest 20/20、ruff 0、verify_anchors 116/116、git status clean。
- 关键文件 SHA（faa488a7 时点）：runner e2c7c6bd…、worker 9c8967e1…、manifest.json faa488a7时点后因
  LF重锚更新（见 gold_corrections policy 行的绑定语义）、gold_corrections 9c6cf8be→28f06a9a更新。
