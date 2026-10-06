# N6：质量整改与空间盘点并行总包

**三张卡已分派；空间已验收并线/推送，预算已验收并线/推3cd4960；候选线已见新交接ce61cdd，待MAIN集中验收。** 固定代码基线58b74d07dd4f8b589c134ef9060a689864a8c089，DOCSET实际merge已推master，精确CI37528050044已一次成功/75秒。N5三包已接收，不重派；已分派不代替具体live进程证据。

历史启动快照（不是当前交付状态）：启动文档曾分别提交/推远端，三个工作树当时干净：候选HEAD81d4524471c59ff053e013b181d3c227ddb8a1f0，预算HEAD949545957f0b3499f48219a124623b33ba8ba065，空间HEADec7a5735e3c47a366c6de01073e87226f02c52ae。这些都是58b之上的纯文档bootstrap，代码仍为共同基线；不要因HEAD多一条启动提交去reset。独立PWF/card均在各树里，可直接开工。

| 包 | 任务 | 独立施工目录 | 独占运行代码 | 卡 |
|---|---|---|---|---|
| N6-CANDIDATE | 经营事实召回、跨块完整事件、IR/英文，较大 | C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-candidates | candidates/context/group_candidates/neighbors与私有n6_candidate_* | [独立卡](n6_candidates.md) |
| N6-BUDGET | 固定96/160内整组去重/多样性排序，较大 | C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-budget | finalize/budget与私有n6_budget_* | [独立卡](n6_budget.md) |
| N6-FOOTPRINT | 本CWP实际空间、保留状态只读工具/实证，较大 | C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-footprint | 新tools/storage_footprint/ | [独立卡](n6_storage_footprint.md) |

源项目都company-wiki，但物理施工目录不同、Git分支不同、逻辑写文件与测试/fixture/PWF/handoff也互斥。共享Git对象，忽略的原件不复制；当前已跟踪文件逻辑总量74490854 B/树，三树合计约223MB，不复制46GB库。各线接收后核ignored剩余/需要材料，MAIN清理自建worktree，不保留永久副本。

## 接口和MAIN所有权

候选线输出既有EvidenceCandidate(unit/topics/reasons/score)与unit_id→group_id，单源/单角色/单语言/连续事件、原locator；预算线输入同形状，输出既有NarrativeEvidencePackage。候选线不决定rank/cap，预算线不造新候选/改变解析。默认字段向后兼容、未知reason降级；不互相import对方未提交实现，不merge对方分支。

MAIN独占narrative_evidence.py中的规则注入/组合、selector版本、narrative_routing/DocumentStructure/公共reader、根配置/生产状态、benchmark/golden/总PWF、正式Worker→检索→RF联调、最终合入/push/CI。外线的新Rules字段须默认值，并在main_wiring列精确函数/注入示例，不跨写共享入口。两线不得靠修改golden、增加限额或改角色/locator合同获绿。

FOOTPRINT只是存储维护层的metadata工具，输出report/1、小报告≤256KiB；不采集/删原件，不创建调度/状态库，不开启/迁移生产SQLite，不参与业务接口或两线写集。

## 并发与顺序

三卡现在即可运行，独立纯输入/夹具保证不等待MAIN接线；MAIN同期整理组合规则/版本影响与S7最终验收材料，但不抢外线4+2源文件或footprint目录。收到完整交接后先验各线边界/接口/责任测试，各线独立实际merge（本次预算先交付/发布0.3.3），MAIN每次更新实际selector身份，两质量线齐备后统一接线与一次真实9样本/正式E2E；FOOTPRINT随时单独合入不阻质量节点。

RF/ET/StockWiki/IQS/Dayu只读或不碰，不另开它们的任务。N5工具长期基准只在大节点跑，0LLM/下载/费用，剩余模型额度不消费；不增加逐helper审批。需要跨界改动只交给MAIN具体接线建议。日常CI保持已有快集合。

每卡各自完整上下文、固定base、独立PWF、测试包、精确写集、输出schema和完成标准。交接HANDOFF.md/handoff.json统一cwp-independent-handoff/1，记录代码commit、写集、RED/GREEN与命令/秒、真实/fixture、原件/生产保护、tmp恢复、calls、remaining；外线只推自己的codex分支。完整交接不等于研究语义或全项目已完成。

MAIN最终节点额外核：0.3.2已落盘final在新选择/去重代码下仍能按原evidence_id/locator读出、回放，不因新canonical组/筛选改变而把历史合法资料变成不可读。旧职责测试若与新策略冲突，由MAIN核事实/规范再调整，外线不得删断言凑绿。规则接线/版本与旧artifact兼容是MAIN剩余任务，不放给两个外线交叉写。

MAIN已完成先行[冻结旧final兼容包](../n6_main_compatibility_implementation.md)，9项/4.85秒绿，17KB历史夹具不在两质量线写集内；最终新代码并入后再跑一次。统一[33点业务解释](../n6_main_business_expectations_2026-10-06.md)保留原golden/分母，只解释经营事实、上下文与财务/provider边界。候选卡更正S07 G01为境内占比22%，原件/golden不变；外线输入副本不跨写，交接时MAIN核此语义。

MAIN的[最终业务E2E施工框架](../n6_main_business_e2e_implementation.md)独立完成：三类合成原件经正式configured Worker/RF读取/search/exact/恢复，27.65秒绿；电话会字节绑定通过CWP正式read取得，未扩RF投影。真实S01/S07/S09四个关键经营点的同入口验收已写但尚未运行，须候选/预算合入与MAIN接线后在最终大节点运行；不冒称当前质量缺口已修，也不增加外线等待。

## 2026-10-06 实际交付覆盖历史启动状态

空间7f27f63、预算18dbd0e均交付。MAIN按用户顺序先验空间，52责任项及真实限额扫描绿；预算补14个真实上下文/组ID反例后修正。候选仍独立施工。预算先独立发布0.3.3，候选合入再更新实际selector，避免已改变预算却沿用旧批次身份；最终质量节点仍等两线结合，不以手工候选推算13/33冒称真实达标。详见[MAIN验收](../n6_budget_footprint_main_acceptance.md)。


发布状态：空间cf24f34/CI37542743196全绿，预算3cd4960已推/CI37543349021全绿72秒；本地两分支均为master祖先。下一验候选ce61cdd（实现9a4b815），不是等待bootstrap或要求重新施工。
