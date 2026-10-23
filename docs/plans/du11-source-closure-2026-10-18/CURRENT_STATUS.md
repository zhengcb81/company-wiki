# 当前项目状态与接手入口

**已按用户2026-10-23“继续”恢复实施。** 原生目标active；ROOT修W08真实选材/context。W09研究及W11离线来源两包均已交付，ROOT正修复接收审查发现的共用问题并整合。新摘要/矩阵/W12仍待完成，原暂停快照仅保留历史。

更新日期：2026-10-24（本节点证据时间采用UTC）。**这是本项目PWF当前状态、剩余任务和下一步唯一入口。** 总计划`document-understanding-2026-10-13`，子计划`du11-source-closure-2026-10-18`，根`docs/plans`。机器状态见[CURRENT_STATUS.json](CURRENT_STATUS.json)；[交接](HANDOFF-2026-10-22.md)的暂停边界已被本次继续指令取代，其失败复现和责任分工仍适用。

## 当前执行状态与唯一下一步

**2026-10-23预算制度升级已提交、推送并安装：** 用户已明确授权累计10M tokens/USD20，公司150k/USD1仅软目标；唯一运行配置为`config/resource_budget.yaml`，旧账/metadata和全部unknown原样保留。实读母账仍1,561,352tokens/631,959microUSD，新剩余8,438,648tokens/USD19.368041。本地计算量可配置、费用/片段/字符/计算分维度诊断已实现；Audit的low误停已改提醒、18项独审通过；两份技能副本39/39一致。CWP正常push7165P/24既有skip，另146契约P；精确CI40034980056已实查completed/success（源码ab95027b）。实施与边界见[预算制度实施单](budget-regime-20261023.md)。W08业务语义、跨页与分批选材未因此验收通过，W09/W11独占工区不改。

本轮三个切面已经分清，不能把测试绿或原文重开当业务验收：

| 切面 | 当前结果 | 发布/边界 |
|---|---|---|
| W08 来源选材、业务父级、缓存依赖 | 共用语义/用途与标题节点已通过；新增裸数质量/优先级计量独审44P，项目正文/原始限制闭包独审165P；全src369/0。真实249页96片段8156字符、821万/1600万工作，两个30%各自scope正确；整体14目标仍PARTIAL | 隔离提交`1712ed10`已正常推送：完整7558P/24既有skip（403.02s），另smoke146P（47.71s）；本地与origin一致、tracked干净。未并母线、未安装。[当前收据](review/r1-w08-resume-20261023/engineering-v4.json)保留全部原RED和验收范围 |
| W10 逐文档原生结果投影 | 两轮独审发现的六项缺陷已共因修复；最终独审41/41，完整658项656P/2skip、另17边界P | 本地提交`71c7762`/收尾`ae13ef7`，`.claude/.agents`各39文件一致；审计技能仓**无remote**。真实12材料矩阵仍OPEN，不代签公司/预测质量。见[工程收尾](review/r1-w10-engineering-closeout-20261022.json) |
| W09 研究准备 / W11 来源发现 | 两包已交付并完成只读初筛。W09内容独审发现2项P2、2项P3，ROOT修角色/业务范围/场景解释投影；W11已并真实作者ancestry；普通pre-push又挡住短UTF8环境误解码，现复用既有确定性decoder，Conda37P/venv39P/同37例独审通过；37纯解析回归进入日常CI，待再次正常推送 | 作者工区保持只读，ROOT在独立写集整合。W09见[内容审查](review/r1-w09-reception-20261023/content-review.md)及[实施顺序](review/r1-w09-reception-20261023/ROOT_NEXT.md)，W11见[初筛](review/r1-w11-reception-20261023/初筛.md)。未修复并独立复核前，不记集成或研究PASS |

**当前唯一第一步：预算节点已发布。ROOT发布独审通过的W11来源发现并保留实际支线ancestry；W09 v3独审16P、126年度格同值，正整合RF主线并保留3份assurance WIP；W08先修独审17项中的8F共享状态问题，再继续指引前提/经营量最终独审、可信跨页祖先与固定容量选材/分批。真实249页仍整体PARTIAL，随后才正式摘要、缓存、真实RF矩阵与W12。两包作者工区保持只读。W11仅工程验收，真实来源恢复仍OPEN。** 实施细节见[ROOT后续步骤](https://github.com/zhengcb81/company-wiki/blob/1712ed10/docs/plans/r1-final3-source-semantics-20261022/NEXT_IMPLEMENTATION.md)；工区路径见新收据。未增加人工许可/新门禁，默认仍0.8，原96/48000/16M不变。

W08表格的`1712ed10`/tracked干净是该次发布快照。当前ROOT工区已三方接入预算，merge尚未提交；经营量77项原测试和指引20项原测试字节不变，指引原7F已修至20P，新反控合44P、有限相关626P，独审17项实测8F/9P，确认未来数量与收入指引未共享正确的谓词/模态/时间归属，现由同一owner重构；预算合入另审84P不抵消这8F。MERGE_HEAD仍ab95027b，不再merge/reset，未并母线或安装。跨页和选材分批仍OPEN，不把这些有限工程结果记为整份年报通过。

随后按已接收W08–W12计划完成W09精确摘录/事实角色/最大驱动经营桥，采用已安装W10从实际native子结果与prepared/read/use引用重建最终矩阵，W11处理真实来源缺口，W12原公司独立四审；再药明合联→Snowflake及后续清单。专家方案14个finding出现项归并10根因，不是14个独立根因；方案接收与工程组件通过都不等于公司PASS。见[根因方案接收](review/r1-final3-plan-root-reception-20261022.json)。

W03/W07真实0.9/v5一次摘要、paid replay、激活前故障恢复/cache和公开RF消费已通过并有65项有限独立复核；**默认仍0.8**，不重复收费重跑已通过生命周期。final3四路独审仍为FAIL，501件89,049,507B与初始639封存保持原样，不能用当前W10工程绿覆盖旧业务结论。此前三仓读取诊断已发布并有精确CI绿：CWP最新预算源码`ab95027b`/CI40034980056 success（旧读取节点aa2dd822保留），RF`10bf6111`、FF`7f6a9268`。W08候选没有新生产CI验收，不借旧CI签候选。

用户要求的审查技能八步升级已在上一节点完成；本轮W10进一步把单据归属、阶段误判及明确版本矛盾固化为回归，现有fetch/process卡已更新。没有新增身份库、任务库、人工许可、逐材料签收或收费权威。预算节点最新每份仅同步3文件并核39/39，见review/budget-regime-20261023/audit-installation.json；树SHA`f2be453617ac03359ccfffe2ebe98e5ee895deb1a6dc7e9510d0462e3d1efb0a`是W10收尾历史，旧`f50bf...`是前版历史。

本轮无新增付费/资料下载；累计仍**1,561,352 tokens/$0.631959**，最新10M/$20额度下余**8,438,648 tokens/$19.368041**，全部unknown保留。原件保留，RF原三份assurance WIP、来源配置/目录库SHA不变，Dayu/IQS未改。独占测试资料已按各收据恢复；W08残留两Temp和mypy临时缓存已精确清理。历史`.planning`未做全仓清理，不宣称本地已无所有临时物。见[保护边界复核](review/r1-pause-safety-check-20261022.json)。

## 已完成及验收边界

| 事项 | 已完成结果 | 证据及适用范围 |
|---|---|---|
| 共享引擎、阅读策略和 B2 来源闭合 | 组件已实现发布、B2复审PASS；新批次默认仍0.8，0.9正式生产切换未完成 | [B2 终审](review/b2-antecedent-final-review-20261018-v3.md)。终审当次109项；补充回归后工程记录110项，不能写成一次110项独审 |
| B2 真实来源回放 | CN 10/10、HK 7/7、US 8/8；原件/gold 不变，0 API | [CN 回放](b2-final3-20261018/cn-h1.json)、[HK/US 回放](b2-real-sources-final2-20261018/replay.json)；历史代码 `2a80acf6`，不是新公司 holdout |
| C 普通工程链路 | 三家真实运行有恢复、跨 run 缓存、FF 复用和 RF 读取通过记录 | [已提交的核心收据摘要](receipts/c-live-receipts-20261018.md)及 [JSON](receipts/c-live-receipts-20261018.json)。完整子收据在本机运行树；未对最新类型修复代码重新做真实 C |
| RF/FF DU11 交付与 P1–P4 四包 | 已接收、合入主线并发布 | [历史发布收尾](review/du11-reception-closeout.md)、[10月18日交付快照](review/final-handoff-report-20261018.md)。不代表所有相关仓库的所有分支均已清空 |
| 模型配置单一化 | provider/model/endpoint/key 环境变量名收敛到生产模型表 | [config/models.yaml](../../../config/models.yaml)；使用时读取配置，历史收据不随新模型改写 |
| 类型与代码质量节点 | `mypy src` 335条→366文件0错误；ruff、compileall 通过；单测7033通过/24跳过，相关 contract113通过 | [专项交接](HANDOFF-2026-10-21.md)。这是既有检查结果，本次文档整理未重跑全量套件；全体 contract 并非全部通过 |

### 内容验收采用的口径

用户允许正确近似数字，禁止错误数字；允许 CN 按8/10收尾。该决定不代表其他样本获得完整覆盖验收。

| 样本 | 可引用结论 | 保留的缺口 |
|---|---|---|
| CN | 8/10，critical5/7，按用户决定收尾 | 缺两条完整事实；不记为10/10，不继续为这两条反复付费试验。见[第三轮审查](review/c-content-review-20261018-cn-v3.md) |
| HK | PASS 7/7，critical6/6 | 正确约数被认可；标题式空 claim、重复描述仍是质量瑕疵。逐gold[独立审查已提交](review/c-content-review-hk-20261018.md)，不再列作缺项 |
| US | 所绑定独审为2/8，另1条 partial | 后续汇总2–4/8来自不同实验，不合并为一个最终分数；漏事实问题保留，不能用CN收尾决定代签。见[原审查](review/c-content-review-20261018.md) |

## 剩余任务

| ID | 任务与当前状态 | 后续实施要求 |
|---|---|---|
| R1 主线 | W01–W07既有工程和真实生命周期完成；旧final3四审FAIL；W08来源质量/项目正文最新有限独审44P和165P、真实14目标仍PARTIAL；W09/W11已交付、ROOT修复整合中；W10组件通过但实际矩阵OPEN；W12未开始 | 先完成本页唯一下一步，再真实摘要、RF全流程与四审；药明康德新attempt复验后依次药明合联→Snowflake及后续清单。不覆盖旧FAIL，不以提高额度掩盖代码缺陷，不把派发当交付 |
| R2 实验性补写 | W04已退役新增付费补写；有证明的历史final owner激活/费用结算和旧partial读取工程修复通过 | 保留旧partial/merged DTO、原文及全部费用，不改immutable output0、不新建multi-operation框架。普通单次真实付费后激活前恢复已在W07实测且独审通过；内容质量仍须W06，不能用cache代签 |
| R3 证据可复现性 | 核心 C 摘要、HK 报告、B2 回放已在 Git；完整 live 响应/consumer/recovery 子收据仍为本机材料 | R1 准备时核对复现所需材料和代码绑定，补足必要索引/可移植证据；不宣称 fresh clone 已可复验全过程，不提交密钥或整棵临时湖 |
| R4 工程改进候选 | 复杂度基线 C901=292、PLR0912=173、PLR0915=111；lint扩面、大模块、配置解析去重、异常卫生、覆盖率基线未完成 | 详见[专项交接第7节](HANDOFF-2026-10-21.md#7-未完成--下一步路线按性价比)。计数是既有审计基线；按实测收益安排，不自动新增覆盖率阈值或一批阻断门禁，不抢占R1 |
| R5 已知测试债 | 两份旧contract及相关实现已TDD修复、独审PASS并入master `a5214bda`（已随`feaef48a`正常push） | 最终受影响195项全绿，保留旧golden并新增current版；独审反例发现并修四条reservation读路径共因，准确字节已核对恢复入master。见[并线记录](r1-holdout-20261021/r5-integration.json)；不把113项相关 contract通过说成全体 contract通过，不以删测自动收尾 |
| R6 跨仓及清理边界 | RF/FF自身完整套件未在本机当前组合复跑；旧RF临时目录清理曾被平台拒绝 | 跨仓后续按各自环境及实际变更做大节点验证；旧未清理状态未重新核验，不声称已全清、不换通道重试旧拒绝操作 |

## 首家公司真实执行边界

正式DS摘要、RF公开读取、五分部三情景原生预测和新run缓存复用已实际运行；MiMo首调HTTP401的未知预留完整保留，未盲重试。[四路独立报告](r1-holdout-20261021/initial-audit/four-review-summary.md)均FAIL：旧0.8路径而非新共享引擎、业务遗漏/一条分部口径错拼、FF合同遮蔽错误及companion、目标发现上限、最新H1/IR/融资/Q1消费及独立量级/确认桥缺口；付费后激活前故障恢复尚未完成。1276复算零算术差错不能抵消这些问题。0新增raw；另有2次SHA核验HTTP共1,905,400B，不能将0下载说成零网络。缓存复用同一169,547B摘要且新增reservation=0，不等于故障恢复或业务覆盖通过。原件/配置复核记录保留；[封存观察](r1-holdout-20261021/initial-execution-seal.json)绑定真实manifest。

## 代码、发布和 CI 基线

- CWP W01 `a7da184e`；W04 已从独审作者提交转为主线 `e1cc1621`/`5a267d37`，交接 `2f632193`。W01 155 项独审绑定旧物理字节；后续仅 LF 归一和 CLI 局部变量改名，独立[补审](review/r1-w01-source-review-postprocess-20261022.md)证明文本/行为等价，并复跑 7 项 CLI。全 `mypy src` 366 文件 0 错误。W04合线后Optional pin类型漏检已于 `ae7b15d6`/`20a7fb0c`修复；单一完整src检查热缓存9.1秒，CI删除重复步骤。独立[最终反控](review/r1-ci-owner-final-review-20261022.md)证明旧版真RED、修复真GREEN，不靠单文件Any或无效移动HEAD探测代签。
- RF W02 产品 `768b6dd3`、W05 产品 `36433047` 已并入 main；`92b69682` 仅将两份必要回归纳入现有 smoke、让既有小型 mypy 在传递依赖修改时也触发。FF 最终主线和三仓推送/安装/新 CI 见[本轮收尾收据](r1-holdout-20261021/engineering-closeout-20261022.json)，不从历史 pin 推断实时状态。
- 当前已成功CWP代码CI：[40034980056](https://github.com/zhengcb81/company-wiki/actions/runs/40034980056)，精确HEAD `ab95027b` completed/SUCCESS。`aa2dd822`及此前的成功CI保留为历史节点，不代签未发布W08/W11候选。RF `10bf6111`、FF `7f6a9268`精确CI均SUCCESS，见本地读取诊断组合收据。
- 历史 `.planning` 材料及 RF 原有三份 assurance WIP 保留，本轮不是全仓清理。新原件、key、生产配置、Dayu、IQS 和旧 campaign 未修改。文档提交不递归刷新跨仓 pin，也不强求不会触发的新 CI。

## 模型与预算

当前模型表：MiMo `mimo-v2.6-flash`、DeepSeek `deepseek-flash`、MiniMax `MiniMax-M3.1-Flash`。10月18日 US 收据使用的是当时的 `MiniMax-M3`；这属于历史事实，不是当前运行配置。

2026-10-22通过既有 `append_native` / `mother_totals` 重计：累计 **1,561,352 tokens / $0.631959**（配置价格估算及保守预留），新10M/$20额度下剩余 **8,438,648 tokens / $19.368041**。W07新增17329tokens/6701microUSD，公司累计56355tokens/16421microUSD；旧7笔和新增4笔unknown全保留，不当零、不重复加算。见[最终原生观察](review/r1-w07-live-20261022/accounting-final-observation.json)。旧1544023/$0.625258为本次调用前基数，不再当当前总数；旧累计授权2M/$20已由用户2026-10-23明确指令升级为10M/$20，旧账未重置。

新运行的操作索引保存在replay attempt，初始索引曾被ROOT误追加，已按封存SHA精确恢复并实核639件全匹配，见[恢复记录](review/r1-w07-live-20261022/sealed-index-restoration.json)。当前有效scope用`coordinator-effective-scope-budget-20261023.json`，旧`coordinator-effective-scope-v2.json`保留历史，不能改写initial历史材料或把新账引用写回旧封存。

## 文档导航及状态规则

- 本页负责整体当前状态；[task_plan](task_plan.md)负责当前行动和历史阶段，[progress](progress.md)记录过程，[findings](findings.md)记录原因与发现。
- [10月21日专项交接](HANDOFF-2026-10-21.md)保留类型质量节点细节和验证命令；旧 [harness-handoff](review/harness-handoff.md)只作重定向入口。
- [10月18日最终交付MD/JSON](review/final-handoff-report-20261018.md)属于被取代快照；状态以本页/JSON为准，原运行与审查证据不重签、不改写。
- 后续完成节点时先更新本页/JSON及当前 `Next Step`，再追加过程；旧正文置于历史区，不再把旧任务标作当前。独立质量审查放在大节点结束，发现问题修完后交接，不添加小节点许可。
- 先前文档整理检查点646b6937的一致性独立复核见[审查记录](review/status-consolidation-review-20261021.md)及[绑定SHA的JSON](review/status-consolidation-review-20261021.json)。提交/推送结果由本轮Git记录确认，不替换历史代码CI。
