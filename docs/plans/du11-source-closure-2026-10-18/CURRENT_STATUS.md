# 当前项目状态与接手入口

**用户要求当前事项收尾后暂停（2026-10-22）。** 本轮工程与交接收尾已保存；不再启动公司、模型调用或新实施。原生目标在最终提交推送结束后执行暂停，未宣称整体计划完成。恢复只从本页与[交接文档](HANDOFF-2026-10-22.md)继续。

更新日期：2026-10-22。**这是本项目 PWF 当前状态、剩余任务和下一步的唯一入口。** 总计划`document-understanding-2026-10-13`，当前子计划`du11-source-closure-2026-10-18`，根`docs/plans`；机器状态见[CURRENT_STATUS.json](CURRENT_STATUS.json)。历史Next Step不覆盖本页。

## 当前执行状态与唯一下一步

本轮三个切面已经分清，不能把测试绿或原文重开当业务验收：

| 切面 | 当前结果 | 发布/边界 |
|---|---|---|
| W08 来源选材、业务父级、缓存依赖 | 保存候选`11502372`；集中850P在最后等价类型改动前，类型修正后185P、全src mypy366文件0错、Ruff绿 | **未验收、未并母线、未安装、未推送**。原公开cache回归仍失败，真实内容partial及数字标识误判未修。见[暂停检查点](review/r1-w08-candidate-checkpoint-20261022.json) |
| W10 逐文档原生结果投影 | 两轮独审发现的六项缺陷已共因修复；最终独审41/41，完整658项656P/2skip、另17边界P | 本地提交`71c7762`/收尾`ae13ef7`，`.claude/.agents`各39文件一致；审计技能仓**无remote**。真实12材料矩阵仍OPEN，不代签公司/预测质量。见[工程收尾](review/r1-w10-engineering-closeout-20261022.json) |
| W09 研究准备 | 新attempt`r1-remediation-02`；实际capture经SourceVersionReader读取年报/H1的10个关键页、30371B | 0模型/网络/下载/原件复制；配置和目录库未变。**尚未生成新研究输入、经营桥或运行新RF**。旧501封存逐SHA不变。见[准备收据](review/r1-w09-preparation-checkpoint-20261022.json) |

**恢复后的唯一第一步：修W08已经保留的公开cache/业务父级失败及通用事实误判，完成独立大节点审查后才并线。** 复现脚本在`C:/Users/郑曾波/Projects/company-wiki-r1-local-observation/docs/plans/r1-final3-source-semantics-20261022/review/reproduce-public-cache.ps1`，全部原断言保留。不得把换谓词的实验当原例通过，也不抬96/48000等现有限额。候选源码工作字节CRLF、Git规范LF，已保存[逐文件字节映射](review/r1-w08-candidate-byte-map-20261022.json)；候选不是精确业务签收版本。

随后按已接收W08–W12计划完成W09精确摘录/事实角色/最大驱动经营桥，采用已安装W10从实际native子结果与prepared/read/use引用重建最终矩阵，W11处理真实来源缺口，W12原公司独立四审；再药明合联→Snowflake及后续清单。专家方案14个finding出现项归并10根因，不是14个独立根因；方案接收与工程组件通过都不等于公司PASS。见[根因方案接收](review/r1-final3-plan-root-reception-20261022.json)。

W03/W07真实0.9/v5一次摘要、paid replay、激活前故障恢复/cache和公开RF消费已通过并有65项有限独立复核；**默认仍0.8**，不重复收费重跑已通过生命周期。final3四路独审仍为FAIL，501件89,049,507B与初始639封存保持原样，不能用当前W10工程绿覆盖旧业务结论。此前三仓读取诊断已发布并有精确CI绿：CWP`aa2dd822`/CI39854576322，RF`10bf6111`、FF`7f6a9268`。W08候选没有新生产CI验收，不借旧CI签候选。

用户要求的审查技能八步升级已在上一节点完成；本轮W10进一步把单据归属、阶段误判及明确版本矛盾固化为回归，现有fetch/process卡已更新。没有新增身份库、任务库、人工许可、逐材料签收或收费权威。两份安装包树SHA`f2be453617ac03359ccfffe2ebe98e5ee895deb1a6dc7e9510d0462e3d1efb0a`，对应W10收尾，旧`f50bf...`是前版历史。

本轮无新增付费/资料下载；累计仍**1,561,352 tokens/$0.631959**，余**438,648 tokens/$19.368041**，全部unknown保留。原件保留，RF原三份assurance WIP、来源配置/目录库SHA不变，Dayu/IQS未改。独占测试资料已按各收据恢复；W08残留两Temp和mypy临时缓存已精确清理。历史`.planning`未做全仓清理，不宣称本地已无所有临时物。见[保护边界复核](review/r1-pause-safety-check-20261022.json)。

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
| R1 主线 | W01–W07既有工程/真实生命周期完成；final3四审FAIL；W08候选已保存但有失败，W10工程已提交安装，W09来源准备完成；用户收尾后暂停，W08–W12整体未完 | [独立专家总览](r1-holdout-20261021/expert-remediation-overview.md)及[进度](r1-holdout-20261021/implementation-progress.json)。先TDD根修，再真实0.9/研究/四审及新公司泛化；修复样本转regression |
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
- 最近已成功CWP代码CI：[39847355377](https://github.com/zhengcb81/company-wiki/actions/runs/39847355377)，精确HEAD `755e87cd` SUCCESS。最新已推送 `aa2dd822` 的精确CI[39854576322](https://github.com/zhengcb81/company-wiki/actions/runs/39854576322)已completed/SUCCESS；不借旧CI代签。RF `10bf6111`、FF `7f6a9268`精确CI均SUCCESS，见本地读取诊断组合收据。
- 历史 `.planning` 材料及 RF 原有三份 assurance WIP 保留，本轮不是全仓清理。新原件、key、生产配置、Dayu、IQS 和旧 campaign 未修改。文档提交不递归刷新跨仓 pin，也不强求不会触发的新 CI。

## 模型与预算

当前模型表：MiMo `mimo-v2.6-flash`、DeepSeek `deepseek-flash`、MiniMax `MiniMax-M3.1-Flash`。10月18日 US 收据使用的是当时的 `MiniMax-M3`；这属于历史事实，不是当前运行配置。

2026-10-22通过既有 `append_native` / `mother_totals` 重计：累计 **1,561,352 tokens / $0.631959**（配置价格估算及保守预留），剩余 **438,648 tokens / $19.368041**。W07新增17329tokens/6701microUSD，公司累计56355tokens/16421microUSD；旧7笔和新增4笔unknown全保留，不当零、不重复加算。见[最终原生观察](review/r1-w07-live-20261022/accounting-final-observation.json)。旧1544023/$0.625258为本次调用前基数，不再当当前总数；累计授权仍2M/$20。

新运行的操作索引保存在replay attempt，初始索引曾被ROOT误追加，已按封存SHA精确恢复并实核639件全匹配，见[恢复记录](review/r1-w07-live-20261022/sealed-index-restoration.json)。有效scope用`coordinator-effective-scope-v2.json`，不能改写initial历史材料或把新账引用写回旧封存。

## 文档导航及状态规则

- 本页负责整体当前状态；[task_plan](task_plan.md)负责当前行动和历史阶段，[progress](progress.md)记录过程，[findings](findings.md)记录原因与发现。
- [10月21日专项交接](HANDOFF-2026-10-21.md)保留类型质量节点细节和验证命令；旧 [harness-handoff](review/harness-handoff.md)只作重定向入口。
- [10月18日最终交付MD/JSON](review/final-handoff-report-20261018.md)属于被取代快照；状态以本页/JSON为准，原运行与审查证据不重签、不改写。
- 后续完成节点时先更新本页/JSON及当前 `Next Step`，再追加过程；旧正文置于历史区，不再把旧任务标作当前。独立质量审查放在大节点结束，发现问题修完后交接，不添加小节点许可。
- 先前文档整理检查点646b6937的一致性独立复核见[审查记录](review/status-consolidation-review-20261021.md)及[绑定SHA的JSON](review/status-consolidation-review-20261021.json)。提交/推送结果由本轮Git记录确认，不替换历史代码CI。
