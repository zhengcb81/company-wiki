# R4 逐项修复映射：117 个原 ID 的归属与验收路由

日期：2026-09-09。状态：**PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED**。
本表是 [r4-remediation-steps.md](r4-remediation-steps.md) §6 要求的逐行映射：为 [unit-ledger.md](unit-ledger.md) 的 117 个原 ID 标注 R4 修复归属与验收路由，作为各阶段 DR 的执行输入。

规则（继承 [r4-transition.md](r4-transition.md) §4）：

1. 「原审计结论」是 2026-09-05～06 的只读审计判定，**不推断当前 HEAD 仍有同一缺陷**；「当前结果」一律**待取证**——含 2026-09-08 的 GP 尾项修复（CI 协议、real-roots 阻断、monthly/调度机制、GP-010 sections 7/7）在内的后续变化，都在对应阶段 DR 按当期输入取证后核入，不在本表预填。
2. 归属按「旧WP → R4 增量/子步骤」两级路由；同域多单元共享归属，子条款展开（原条款 hash、RED、测试路径、oracle、required 层）按 U117.03 在该阶段 DR 冻结。
3. 验收列只给路由（R4 步骤 + 测试组 + 审查层），不是结果声明；任何单元的关闭都要按 U117.06 以真实 required 结果判定。
4. 历史收据/签署字节不改；ZR-1002/1003 波次展开两项皆保留；ZR-1101/1105 对应工具已随 R9 批1+2 删除（2026-09-06），只按 O08 记退役，不从旧勾选领取。
5. 本表与 [r4-remediation-steps.md](r4-remediation-steps.md) 已经 [独立复核](r4-remediation-detail-review.md) （accepted_with_findings，P0/P1=0）：F1 已按其建议把组级引用落为子步骤区间（W04.01–.06 / W06.01–.06 / H01.01–.09）。
6. 计数口径：[r4-remediation-steps.md](r4-remediation-steps.md) 共定义 104 条编号项 = 88 条实施子步骤（H01 9 + W02–W10 56 + FC903 8 + U117 7 + X01–X08 8）+ 16 条映射行（CL01–09、AC01–07）；task_plan/progress 所称「88 子步骤」指前者。

| 原ID | 原痛点 | 原审计结论 | 域 | 旧WP | R4 归属 | R4 步骤 | 验收路由 | 当前结果 |
|---|---|---|---|---|---|---|---|---|
| CA-001 | P01/P10 | HISTORICAL_ONLY | 完成资格（证据真源） | WP00 | A 证据规则 + D 最终效果核验 | A01/A08、U117.05–.07、X07 | E01–E13 类负例经真实资格消费者 | 待取证 |
| CA-002 | P01/P10 | PARTIAL | 完成资格（证据真源） | WP00 | A 证据规则 + D 最终效果核验 | A01/A08、U117.05–.07、X07 | E01–E13 类负例经真实资格消费者 | 待取证 |
| CA-003 | P01/P10 | PARTIAL | 完成资格（证据真源） | WP00 | A 证据规则 + D 最终效果核验 | A01/A08、U117.05–.07、X07 | E01–E13 类负例经真实资格消费者 | 待取证 |
| CA-004 | P01/P10 | HISTORICAL_ONLY | 完成资格（证据真源） | WP00 | A 证据规则 + D 最终效果核验 | A01/A08、U117.05–.07、X07 | E01–E13 类负例经真实资格消费者 | 待取证 |
| CA-101 | P01/P10 | PARTIAL | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-102 | P01/P10 | PARTIAL | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-103 | P01/P10 | CONTRADICTED | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-104 | P01/P10 | PARTIAL | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-105 | P01/P10 | CONTRADICTED | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-106 | P01/P10 | PARTIAL | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-107 | P01/P10 | CONTRADICTED | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-108 | P01/P10 | CONTRADICTED | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-109 | P01/P11 | CONTRADICTED | 完成资格（状态机/收据/scenario） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| CA-201 | P01/P10 | CONTRADICTED | 调度/报告/告警/soak | WP12 | D（运行与观测收尾） | D06/D08、O05–O07 | O05/O06/O07 | 待取证 |
| CA-202 | P01/P10 | CONTRADICTED | 调度/报告/告警/soak | WP12 | D（运行与观测收尾） | D06/D08、O05–O07 | O05/O06/O07 | 待取证 |
| CA-203 | P01/P10 | PARTIAL | 调度/报告/告警/soak | WP12 | D08（weekly T3） | W03.06 + X03；weekly 机制已修待自然累积 | P06、O07 | 待取证 |
| CA-204 | P01/P10 | CONTRADICTED | 调度/报告/告警/soak | WP12 | D（运行与观测收尾） | D06/D08、O05–O07 | O05/O06/O07 | 待取证 |
| CA-205 | P01/P10 | CONTRADICTED | 调度/报告/告警/soak | WP12 | D（运行与观测收尾） | D06/D08、O05–O07 | O05/O06/O07 | 待取证 |
| CA-206 | P01/P10 | CONTRADICTED | 调度/报告/告警/soak | WP12 | D08（自然 soak） | 自然 7/2/1/1（GP-009 累积中：3/7、0/2、1/1、1/1） | O07 | 待取证 |
| CA-301 | P01/P10 | CONTRADICTED | 干净旅程/三公司/ratchet/legacy 退出 | WP13/WP14 | X + D（放量与退出） | X02–X04、D09/D10 | X02–X04、O08 | 待取证 |
| CA-302 | P01/P10 | CONTRADICTED | 干净旅程/三公司/ratchet/legacy 退出 | WP13/WP14 | X + D（放量与退出） | X02–X04、D09/D10 | X02–X04、O08 | 待取证 |
| CA-303 | P01/P11 | PARTIAL | 干净旅程/三公司/ratchet/legacy 退出 | WP13/WP14 | X + D（放量与退出） | X02–X04、D09/D10 | X02–X04、O08 | 待取证 |
| CA-304 | P01/P11 | CONTRADICTED | 干净旅程/三公司/ratchet/legacy 退出 | WP14 | D（legacy 删除门） | R9 批3（3a 已撤销 2026-09-10；仅剩 3b/3c，需替代路径 + FC-705 门）+ O08 | O01/O02/O08 | 待取证 |
| CA-305 | P01/P10 | CONTRADICTED | 干净旅程/三公司/ratchet/legacy 退出 | WP13/WP14 | X + D（放量与退出） | X02–X04、D09/D10 | X02–X04、O08 | 待取证 |
| CA-306 | P01/P10 | PARTIAL | 干净旅程/三公司/ratchet/legacy 退出 | WP13/WP14 | X + D（放量与退出） | X02–X04、D09/D10 | X02–X04、O08 | 待取证 |
| ZR-001 | P01/P11 | HISTORICAL_ONLY | 完成资格（registry 基础） | WP00 | A08 + U117 | A08、U117.01–.04 | U117.05 | 待取证 |
| ZR-002 | P01/P11 | HISTORICAL_ONLY | 完成资格（registry 基础） | WP00 | A08 + U117 | A08、U117.01–.04 | U117.05 | 待取证 |
| ZR-003 | P01/P11 | HISTORICAL_ONLY | 完成资格（registry 基础） | WP00 | A08 + U117 | A08、U117.01–.04 | U117.05 | 待取证 |
| ZR-004 | P01/P11 | HISTORICAL_ONLY | 完成资格（registry 基础） | WP00 | A08 + U117 | A08、U117.01–.04 | U117.05 | 待取证 |
| ZR-1001 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1002 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | U117（波次展开） | U117.01–.04（1002/1003 两项皆保留） | U117.05 | 待取证 |
| ZR-1003 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | U117（波次展开） | U117.01–.04（1002/1003 两项皆保留） | U117.05 | 待取证 |
| ZR-1004 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1005 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1006 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1007 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1008 | P01/P10/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1009 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-101 | P01/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-102 | P01/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-103 | P01/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-104 | P01/P11 | PARTIAL | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-105 | P01/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1101 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP14 | D09（已退役） | R9 批1+2 已删工具/测试（2026-09-06）；退役记录按 O08 | O08 | 待取证 |
| ZR-1102 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1103 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP00 | A08 + U117 + D07 | A08、U117.02–.05、D07 | U117.05、O06 | 待取证 |
| ZR-1104 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP14 | D08/D10（自然窗口） | 自然 7/2/1/1 窗口（GP-009 累积中） | O07 | 待取证 |
| ZR-1105 | P01/P10/P11 | CONTRADICTED | 完成资格（registry/状态机） | WP14 | D09（已退役） | R9 批1+2 已删工具/测试（2026-09-06）；退役记录按 O08 | O08 | 待取证 |
| ZR-201 | P02 | PARTIAL | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-202 | P02 | PARTIAL | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-203 | P02 | CONTRADICTED | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-204 | P02 | CONTRADICTED | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-205 | P02 | CONTRADICTED | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-206 | P02 | PARTIAL | 数据湖读取/policy/eligible | WP02 | A + B | A02–A04、B01–B09、W02.01–.06 | L01–L12 | 待取证 |
| ZR-301 | P05/P06 | PARTIAL | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-302 | P05/P06 | PARTIAL | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-303 | P05/P06 | CONTRADICTED | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-304 | P05/P06 | CONTRADICTED | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-305 | P05/P06 | CONTRADICTED | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-306 | P05/P06 | PARTIAL | worker/队列/生产链 | WP04/WP06/WP01 | C + D | C04–C07、W04.01–.06、W06.01–.06、H01.01–.09 | P03/P04/P07、O04 | 待取证 |
| ZR-307 | P05/P06 | PARTIAL | worker/队列/生产链 | WP00 第6条 | FC903 修复线 | FC903.01–.08 | FC903.05/07 | 待取证 |
| ZR-401 | P03/P04 | CONTRADICTED | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-402 | P03/P04 | PARTIAL | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-403 | P03/P04 | CONTRADICTED | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-404 | P03/P04 | CONTRADICTED | filing 供应链（修订/授权/失败） | WP00 第6条 | FC903 修复线 | FC903.01–.08 | FC903.05/07 | 待取证 |
| ZR-405 | P03/P04 | PARTIAL | filing 供应链（修订/授权/失败） | WP00 第6条 | FC903 修复线 | FC903.01–.08 | FC903.05/07 | 待取证 |
| ZR-406 | P03/P04 | CONTRADICTED | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-407 | P03/P04 | CONTRADICTED | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-408 | P03/P04 | PARTIAL | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-409 | P03/P04 | PARTIAL | filing 供应链（修订/授权/失败） | WP03 | B（期间版本）+ C（显式更新/下载） | B04、C06/C09、W03.01–.06 | L07、P05/P06 | 待取证 |
| ZR-501 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-502 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-503 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-504 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-505 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-506 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-507 | P07 | CONTRADICTED | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-508 | P07 | CONTRADICTED | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-509 | P07 | PARTIAL | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-510 | P07 | CONTRADICTED | broker/HTML 真实语义与外发边界 | WP05/WP07 | C（解析）+ D（放量） | W05.01–.06、W07.01–.06、C09/C10 | L10、P05/P08、M08 | 待取证 |
| ZR-601 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M + wiki 上游事实 | W08.01（ZR601–604 拆上游提取/身份/冲突/export/消费子条款） | M01/M07 | 待取证 |
| ZR-602 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M + wiki 上游事实 | W08.01 子条款展开 | M01/M07 | 待取证 |
| ZR-603 | P09 | CONTRADICTED | 上游资产事实/单位/权属 | WP08 | M + wiki 上游事实 | W08.01 子条款展开 | M01/M07 | 待取证 |
| ZR-604 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M + wiki 上游事实 | W08.01 子条款展开 | M01/M07 | 待取证 |
| ZR-605 | P09 | CONTRADICTED | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-606 | P09 | CONTRADICTED | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-607 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-608 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-609 | P09 | CONTRADICTED | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-610 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-611 | P09 | PARTIAL | 上游资产事实/单位/权属 | WP08 | M（wiki 负责来源事实） | M01–M03、W08.01–.07 | M01–M03、M07 | 待取证 |
| ZR-701 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-702 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-703 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-704 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-705 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-706 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-707 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-708 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-709 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP13 | X（三仓真实旅程） | X03/X04（紫金真实旅程 join） | AC01–AC07 | 待取证 |
| ZR-710 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-711 | P08/P09 | PARTIAL | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-712 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-713 | P08/P09 | CONTRADICTED | 模型/generator/发布/回测 | WP09/WP10 | M | M03–M06、W09.01–.07、W10.01–.06 | M04–M07 | 待取证 |
| ZR-801 | P10 | PARTIAL | 真实 E2E/三仓旅程 | WP13 | A/B/C/D/M 分栏验收 | X03/X04、AC01–AC07 | AC01–AC07、X03/X04 | 待取证 |
| ZR-802 | P10 | PARTIAL | 真实 E2E/三仓旅程 | WP13 | A/B/C/D/M 分栏验收 | X03/X04、AC01–AC07 | AC01–AC07、X03/X04 | 待取证 |
| ZR-803 | P10 | PARTIAL | 真实 E2E/三仓旅程 | WP13 | A/B/C/D/M 分栏验收 | X03/X04、AC01–AC07 | AC01–AC07、X03/X04 | 待取证 |
| ZR-804 | P10 | PARTIAL | 真实 E2E/三仓旅程 | WP13 | A/B/C/D/M 分栏验收 | X03/X04、AC01–AC07 | AC01–AC07、X03/X04 | 待取证 |
| ZR-805 | P10 | CONTRADICTED | 真实 E2E/三仓旅程 | WP13 | X（真实下载 T3） | X03（CN/HK/US 首次+复用）+ W03.06 | P06、X03 | 待取证 |
| ZR-806 | P10 | CONTRADICTED | 真实 E2E/三仓旅程 | WP13 | X（三仓真实旅程） | X03/X04 | AC01–AC07 | 待取证 |
| ZR-901 | P10/P11 | CONTRADICTED | CI/质量门 | WP11 | D07（CI 字节绑定） | D07；2026-09-08 real-roots 已转阻断（GP-006），待 DR 取证核入 | O06、X05 | 待取证 |
| ZR-902 | P10/P11 | PARTIAL | CI/质量门 | WP12 | D06/D08（调度与账本） | D06/D08；2026-09-08 daily/weekly/monthly 机制已修（GP-008/009），待 DR 取证核入 | O05/O07 | 待取证 |
| ZR-903 | P10/P11 | PARTIAL | CI/质量门 | WP11 | 每改动的适用测试 + D07 | D07、CL01–CL09 对应映射 | O06、X05 | 待取证 |
| ZR-904 | P10/P11 | CONTRADICTED | CI/质量门 | WP11 | 每改动的适用测试 + D07 | D07、CL01–CL09 对应映射 | O06、X05 | 待取证 |
| ZR-905 | P10/P11 | CONTRADICTED | CI/质量门 | WP11 | D07 | D07 | O06 | 待取证 |
| ZR-906 | P10/P11 | PARTIAL | CI/质量门 | WP11 | 每改动的适用测试 + D07 | D07、CL01–CL09 对应映射 | O06、X05 | 待取证 |
| ZR-907 | P10/P11 | PARTIAL | CI/质量门 | WP11 | D07（drift patrol） | D07；2026-09-08 已入本地门（GP-006），待 DR 取证核入 | O06 | 待取证 |

共 117 行（25 CA + 92 ZR），与 unit-ledger.md 一一对应，无漏项、无重复。
逐项证据入口见 [unit-ledger.md](unit-ledger.md) 对应行；本表不复制证据正文。

## 统计（按 R4 归属汇总，仅路由计数，不是完成度）

- A08 + U117 + D07: 23 项
- M: 12 项
- C（解析）+ D（放量）: 10 项
- B（期间版本）+ C（显式更新/下载）: 7 项
- M（wiki 负责来源事实）: 7 项
- A + B: 6 项
- C + D: 6 项
- X + D（放量与退出）: 5 项
- A 证据规则 + D 最终效果核验: 4 项
- D（运行与观测收尾）: 4 项
- A08 + U117: 4 项
- M + wiki 上游事实: 4 项
- A/B/C/D/M 分栏验收: 4 项
- FC903 修复线: 3 项
- 每改动的适用测试 + D07: 3 项
- U117（波次展开）: 2 项
- D09（已退役）: 2 项
- X（三仓真实旅程）: 2 项
- D08（weekly T3）: 1 项
- D08（自然 soak）: 1 项
- D（legacy 删除门）: 1 项
- D08/D10（自然窗口）: 1 项
- X（真实下载 T3）: 1 项
- D07（CI 字节绑定）: 1 项
- D06/D08（调度与账本）: 1 项
- D07: 1 项
- D07（drift patrol）: 1 项

## 2026-09-10 注（R9 批 3 范围）

CA-304 行中的「R9 批3」**不再包含原 3a**：owner 于 2026-09-10 正式撤销 3a（`src/company_wiki/source_catalog/artifact_backfill.py` 经完整依赖扫描定性为**受 FC-906 卡片保护的运维工具**——自带 `--mode dry-run|apply` CLI、FC-901 收据记载其 production caller 即该 CLI、被 3 个契约测试导入、冻结 v5 基线有 ZR1005-C1~C4 验收行），**未删除任何文件**。批 3 只剩 3b（`_scan_root_v1` + shadow/trace parity）与 3c（`legacy_bridge_enabled` + flags/resolver/architecture_gate），二者均需先给出替代路径与回滚，且仍需 FC-705 门 + owner 政策门。详见 revenue 侧 [r9_batch3_checklist.md](../../../../revenue-forecast/assurance/runs/2026-09-02_remaining-gap-closure/r9_batch3_checklist.md)。

