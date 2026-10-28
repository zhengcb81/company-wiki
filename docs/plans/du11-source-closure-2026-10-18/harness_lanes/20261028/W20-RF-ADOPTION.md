# W20-RF-ADOPTION：叙述证据进入收入预测的只读采用观察

状态：READY，可立即开工。2026-10-28由ROOT分发；这是一张新的完整施工卡，不是已完成的W17/W19或ROOT物理阅读修复卡。

- 工作目录：`C:\Users\郑曾波\Projects\revenue-forecast-w20-adoption`
- 分支：`codex/w20-rf-adoption-20261028`
- 冻结基线：`0991e25d5dca667a3fdafb7bc5ebf0e546a2272b`
- PLAN_ID：`w20-rf-adoption-2026-10-28`；PWF_PLAN_ROOT：`docs/plans`
- 交接目录：`delivery/w20-rf-adoption/`
- 主仓仅只读：`C:\Users\郑曾波\Projects\revenue-forecast`

## 目标与调查起点

做一个**只读的叙述证据采用观察工具**，回答“RF拿到了哪些来源业务信息，最终预测的哪些驱动/假设/情景真正引用了它们”。来源准备或summary可读取通过不等于预测模型采用；当前ROOT PWF将actual RF adoption保持OPEN，本卡提供其离线可执行观察，不替ROOT跑真实收费预测。

先读当前SKILL、`scripts/revenue_forecast.py`、`revenue_core`/报告与snapshot的既有公开输出合同，`source_narrative_context.py`、`narrative_citation_context.py`及W16-BASIS交接。不要再实现source准备、单位转换或另一套收入预测引擎。

## allowlist与责任边界

只新增`tools/narrative_adoption_audit/`（或调查证明已有对应工具则扩展那个单一owner，必须在A写明）、`tests/test_w20_narrative_adoption*.py`、小合成fixtures、本卡PWF/delivery与本工具README。`scripts/revenue_*`、CWP reader/source preparation、配置、SKILL、schema/发布门、Dashboard报告目录API和安装器全部只读；主线ROOT后续决定是否薄接线。不修改FF、CWP、审查技能或全局副本。

本工区已稀疏检出工程/测试/docs等，省去主仓约846MB已跟踪`.planning`历史运行副本。历史所需小记录用`git show <base>:<path>`只读提取到owned scratch；不要`sparse-checkout disable`或拷贝整份历史环境。新工具/测试/本卡docs均在已检出目录内。

## 实施要求

R1. 输入为显式RF最终input/output/snapshot及显式来源/叙述公开export JSON，优先复用现有reader/validator的纯接口；不扫描物理company目录，不联网重抓，不打开生产数据库，不运行模型。CLI每次只写显式output路径；拒绝覆盖输入与原件，默认结果stdout或新文件，遵守现有工具约定。

R2. 使用真实canonical source/evidence/span/context/claim IDs，按既有资料结构解析；本地task t1等只是display key，不能跨request/source/run拼接。区分source support/context_only/unresolved，context本身不能证明假设/数字。跨源同字符串ID、错版本、错source/hash（有提供时）、路径存在但材料缺失等需可定位诊断；缺hash沿现有宽松政策记unknown，不新加预测门禁。

R3. 输出逐项来源信息→实际RF驱动/假设/场景/年度路径节点的引用映射，至少有used/not_observed/not_used_when_provable/unverifiable或与现有等价状态、关联actual IDs、报告定位和named reason。没有执行追踪不能把“输入带了摘要”写成“模型采纳”；输出引用缺失也不能自动证明模型完全没使用。保留观察范围和未知。

R4. 通过现有模型引用链识别一条信息被直接支持、仅context、多个节点复用、未进入模型等情况；不做关键词猜用、不推测模型内心，不把所有supplied source强制要求采用。某事实不影响收入预测、只是背景时可以合法未使用。资料准备失败与采用缺观察要分开。

R5. 对重复来源/多版本同公司、不同币种单位/期间/会计分部、未来目标/负面限制，工具只核已有绑定的口径/状态，不另算收入或用LLM判断因果。数值或研究结论正确性仍由现有RF验证和四审查角色负责；本工具不能自发rating或通过一份采用率签收模型经济合理。

R6. 无新DB、任务调度、权限/签名/发布授权，不改当前文件格式的历史语义；若新增观察输出，使用小型版本化report，明确是诊断而非预测许可。复用现有遍历/验证逻辑，消除硬编码字段路径分支副本；大输入要有显式资源界限，线性或可说明的O(n log n)，不能对每个span重新扫描整份报告。

## 必要测试包与端到端

先RED：同源正确采用；同display t1跨source不能假采用；context-only不能当数字证据；summary可读但final没有trace只能unknown；跨年度/币种/分部混用诊断；同证据多节点不重复计多源；旧格式缺观察兼容；有hash错配和无hash宽松诊断；未知字段不造结论；大样本n/2n计数与资源界限；输入与既有输出文件不被覆盖。

真实CLI端到端至少两类不同驱动模型：使用现有公开`revenue_forecast.py`/fixture生成真实deterministic RF产物，再调用新工具核映射；fixture来源和SourceRef明确synthetic，无真实LLM、下载、provider或母账写。另可只读回放一份已有脱敏真实RF版本，逐node人工核查观察真实性；缺材料则写NOT_RUN，不能编造actual use。同样本重复执行结果稳定且无持久增长；所有临时output恢复初态。C阶段相关短包与独审即可，不要求每commit全仓大套件。

## 总控、隔离与开始方式

ROOT（company-wiki当前主线harness）负责跨仓集成、真实收费摘要、最终公司循环及主线合并。本卡现在即可独立开工，不等待其他两卡完成。你是本卡实施owner，不是新的总控。

工作只在上面的**独立工区**及它的分支。主项目目录、company-wiki、其他两卡工区、Dayu、IQS、Dashboard全部只读；不改它们的索引、配置、原件、安装技能或分支。不要切主项目的main/master，不清理它人的未提交文件，不自动合入主线。读取接口可以，禁止跨仓底层文件/数据库写操作。跨仓源码路径仅用于显式只读导入；测试资料根必须是独立fixture root，不能拿源码根当生产数据根。

先检查工区HEAD/branch/status与本卡基线一致，阅读所在仓/上级AGENTS、本卡及已有对应PWF/工具说明；允许在本工区初始化CodeGraph索引。发现基线之后已有别人改动则保留，并明确其owner，不reset。不要复制整个源仓、.planning历史运行环境、生产资料库或SDK；不要恢复全量备份作演练。

在本仓建立`docs/plans/w20-rf-adoption-2026-10-28/{task_plan.md,findings.md,progress.md}`（PLAN_ID见下），复制本卡为`construction_card.md`，设置PLAN_ID和PWF_PLAN_ROOT=docs/plans。它是你唯一执行队列，不改ROOT总PWF。所有测试命令显式使用宿主实际可用Python，不能把机器绝对路径写进产品。

## 三个大节点；不增加小节点审批

**A 调查/冻结预期。** 先读本仓已有实现、相应PWF与commit，逐项列本卡需求是已有覆盖、真实缺陷、还是缺可观察性；已有的复用，不为了有diff再造模块。冻结接口、数据来源、正反例和有限测试命令。记录已通过基线。A不需要等ROOT签收才继续B/C。

**B TDD实施。** 有真实缺陷先保存行为RED，再改所属共同责任层。测试覆盖跨公司/市场/文种的同一规则，禁止公司、页码、某段金标整句特判；不抬token、费用、时间、空间或并发额度，不增加人工权限、canary、授权JSON和签收链。没有缺陷可以交付有效的回归套件及明确no-code结论，不强行重构。只改本卡allowlist；遇到需要改别仓或ROOT保留模块，交付具体counterexample与期望，由ROOT处理，不能私自扩大。

**C 集成/CLI/独审/交接。** 先跑必要单元，再跑一个或少量代表性真实CLI端到端，检查真实入口和实际调用链，不能以mock函数调用次数冒充跨仓端到端。默认离线、不使用任何真实LLM或下载API、不读取密钥；历史真实资料仅只读或使用已有小范围脱敏fixture，不能假称新下载/新预测。每case有界，失败停在命名原因，修根因后只重跑相关部分，禁止反复跑超时全域。若全量本仓既有套件能够稳定短时完成，可在C一次执行；慢套件不加到每次commit。

测试都放在独立test/temporary目录，先记录初态和sentinel；完毕恢复初态，原本不存在的临时下载/数据库/请求文件/子进程须清除，已有fixture不得删改。保留小收据/压缩日志；报告前后字节/文件清单差异、owned child回收和峰值空间，不留逐页副本或大响应。未知费用、时长、外部完整性就写unknown/NOT_RUN，不能编0或PASS。

**交接前必须调用真正独立的审查agent。** 把本卡全部要求、实际diff、测试包、接口、已知局限交给它，全面审查完成度、架构/模块化、硬编码、数据/角色/期间/数字、错误路径、测试真实性和清理。作者不能换个名字自签。独审发现的本范围问题全部修复，保留初审与修复证据，再由独立agent复审最终实现；最终本范围OPEN必须为空才可交接。跨仓阻塞如实单列，不能靠把本范围缺陷移入“范围外”伪完成。

## 固定交接接口

交付目录为本仓`delivery/w20-rf-adoption/`。提交`handoff.md`和`handoff.json`，以及`review/initial.md/json`、`review/final.md/json`（确实无问题可只有final，但仍须独立agent实际审查）。JSON至少包含：

```json
{
  "card_id":"见卡号", "status":"READY_FOR_ROOT_REVIEW",
  "workdir":"实际绝对目录", "branch":"实际分支", "base_commit":"原始基线",
  "implementation_commits":[], "tested_code_commit":"实际受测代码commit",
  "reviewed_code_commit":"独审绑定的最终实现commit",
  "files":[{"path":"相对路径","sha256":"最终实际字节SHA"}],
  "requirements":[{"id":"本卡要求","evidence":"报告/测试节点","status":"PASS或明确未执行"}],
  "tests":[{"command":"完整命令","exit_code":0,"passed":0,"failed":0,"seconds":0,"scope":"真实范围"}],
  "review":{"agent_id":"实际独立agent","report":"相对路径","open_findings":[]},
  "cleanup":{"before":"初态收据","after":"恢复收据","restored":true,"bytes_added":0},
  "compatibility":[], "limitations":[], "root_followups":[], "remote_status":"实际状态"
}
```

上面0/true只是结构示例，必须填实测值；未测为null并解释。`tested_code_commit`/`reviewed_code_commit`应指同一最终实现；后续只加handoff文档的commit可以不同，说明两者之间源码无变化。不能拿旧版本签名覆盖新源码。以实现commit和有关文件SHA界定，不做整仓签收/许可文件。

完成进展及时commit；存在已配置远端就推本卡分支，未配置则记录，不创建公开remote。正常hooks不绕过。不要全局同步技能/安装，不提交真实公司原件、密钥、model reasoning、runs大响应和临时环境。向用户回报三个路径：工区、handoff.md、handoff.json；然后STOP等ROOT接收。ROOT会统一复验和并主线，作者不用等待其他卡签收。
