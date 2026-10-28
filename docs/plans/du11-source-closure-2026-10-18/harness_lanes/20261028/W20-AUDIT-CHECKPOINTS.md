# W20-AUDIT-CHECKPOINTS：审查检查点的语义、角色与信息量升级

状态：READY，可立即开工。2026-10-28由ROOT分发；这是一张新的完整施工卡，不是已完成的W17/W19或ROOT物理阅读修复卡。

- 工作目录：`C:\Users\郑曾波\Projects\revenue-forecast-audit-w20-checkpoints`
- 分支：`codex/w20-audit-checkpoints-20261028`
- 冻结基线：`33200f8c947f35be75a77de38040982724e033a7`
- PLAN_ID：`w20-audit-checkpoints-2026-10-28`；PWF_PLAN_ROOT：`docs/plans`
- 交接目录：`delivery/w20-audit-checkpoints/`
- 主仓仅只读：`C:\Users\郑曾波\Projects\revenue-forecast-audit`

## 目标与调查起点

改进审查技能对“证据可用、问题上下文、模型事实支持、实际输出质量”的区分。当前ROOT真实复验已经证明：旧自动exact-phrase没有命中，并不一定缺业务语义；管理层答复与提问前提不能使用同一支持条件；套话和一般规则虽有出处，也不应冒充有信息量的经营进展。该工作是审查工具与四角色检查点升级，不是重建CWP parser、RAG或财务模型。

先读`AGENTS.md`、`skills/revenue-forecast-audit/SKILL.md`，现有`summary_review_contracts.py/summary_review_packet.py/summary_review_import.py`、`coverage_observations.py`、`review_evidence_reconcile.py`与W17 PWF/交接；最新基线已包含carrier-scope修复，不重复发明覆盖计数器。若修改skill结构，先读本机skill-creator规范。

## allowlist与责任边界

可改本仓`skills/revenue-forecast-audit/scripts/`中的现有上述owner，以及必要的`audit_run.py`薄接线、一个必要共享helper；`references/`新增或更新本卡检查点说明、SKILL.md仅本卡相关入口；`tests/`新增本卡测试、必要已有测试；本卡PWF/delivery。不得改pool/预算/安装器、四角色数量、自动修复许可、真实runs、全局技能副本；不改其他仓的benchmark/oracle。

## 实施要求

R1. 明确复用现有packet/observations：source完整读取、证据选中、source support与context、actual sent tasks、actual emitted claim、实际RF模型采用分开报告；缺观察就NOT_OBSERVABLE/NOT_EVALUATED，不能补造步骤完成或从缺一个exact词断言漏报。

R2. 四个独立角色仍各司其职。storage审查来源/切片/有效信息；fetch审查复用与正确工具；process审查出处、数字和执行；analyst审查因果模型/假设。新检查点由相应角色引用，同一证据不重复累加成多个独立支持。expert在四报告后汇总共因，不能把源层缺陷藏到“模型摘要可选”。

R3. 既有canonical role保持原样；审查侧明确等价角色名映射与用途。management_answer与management可映射为答复观察；analyst_question/investor_question只作问题/前提context。问题即便包含正确公司/数字，也不能算管理层已确认事实。无法确认speaker时保unknown，不用company_filing洗白。混合question+answer必须绑定各自actual IDs。

R4. 为具体功能、主营组成、商业机制、真实业务原因、经营限制/负面和未来计划设计可复查的内容标准；不要要求每项都有数字或新品。泛宣传、目的模板、纯财务存量、一般会计规则不应独占经营摘要；但贷款条款、项目资金限制、履约/验收/预付款商业机制不能整类禁止。只生成有出处、可定位的finding，不为“减少套话”再造下游生产文本分类器。

R5. 语义等价证据用实际完整claim+引用审核；exact quote/词面检查只能说明锚点观察，不可自称语义验真。允许原句不同但包含同一主体、谓语、期间、数字及限定的更完整段。不能静默补充/修改冻结gold凑分，也不能以LLM无依据自动放行。给初始机械结果、独立解释及复验结论分别留证。

R6. 原语言、负面/未完成/计划、客户/股东/上市公司角色，人民币/美元/港币及元/千/百万/亿、billion等必须列成现有审查packet可直接使用的风险点；调用已有numeric/measure checker，不重写一套单位转换。重复内容建议合并但保期间/主体差异，不按文本相同删除原始引用。

## 必要测试包与端到端

至少覆盖：同义更完整段不是漏报；仅关键词相似但主体/期间/单位不同不是等价；问题前提与管理层否定；控股股东希望合作不等于上市公司已合作；泛目标vs具体无数字功能；财务背景vs实际融资限制；未来计划vs已完成；同一来源重复不算多源；缺观察不假成功；旧packet/coverage保持可读。

C阶段跑本仓真实公开命令的离线packet→四份独立人工/fixture报告导入→coverage/reconcile→expert输入包，fixture明确标合成，不能冒充四个agent真实研究。再由独立审查agent试读一份已有脱敏真实报告/小source packet，给出逐项检查点是否真能执行的记录。纯组件通过不签ROOT公司真实循环。使用本仓既有短单元/CLI命令，完整unittest若能稳定完成可C阶段一次运行，不加到pre-commit。

## 总控、隔离与开始方式

ROOT（company-wiki当前主线harness）负责跨仓集成、真实收费摘要、最终公司循环及主线合并。本卡现在即可独立开工，不等待其他两卡完成。你是本卡实施owner，不是新的总控。

工作只在上面的**独立工区**及它的分支。主项目目录、company-wiki、其他两卡工区、Dayu、IQS、Dashboard全部只读；不改它们的索引、配置、原件、安装技能或分支。不要切主项目的main/master，不清理它人的未提交文件，不自动合入主线。读取接口可以，禁止跨仓底层文件/数据库写操作。跨仓源码路径仅用于显式只读导入；测试资料根必须是独立fixture root，不能拿源码根当生产数据根。

先检查工区HEAD/branch/status与本卡基线一致，阅读所在仓/上级AGENTS、本卡及已有对应PWF/工具说明；允许在本工区初始化CodeGraph索引。发现基线之后已有别人改动则保留，并明确其owner，不reset。不要复制整个源仓、.planning历史运行环境、生产资料库或SDK；不要恢复全量备份作演练。

在本仓建立`docs/plans/w20-audit-checkpoints-2026-10-28/{task_plan.md,findings.md,progress.md}`（PLAN_ID见下），复制本卡为`construction_card.md`，设置PLAN_ID和PWF_PLAN_ROOT=docs/plans。它是你唯一执行队列，不改ROOT总PWF。所有测试命令显式使用宿主实际可用Python，不能把机器绝对路径写进产品。

## 三个大节点；不增加小节点审批

**A 调查/冻结预期。** 先读本仓已有实现、相应PWF与commit，逐项列本卡需求是已有覆盖、真实缺陷、还是缺可观察性；已有的复用，不为了有diff再造模块。冻结接口、数据来源、正反例和有限测试命令。记录已通过基线。A不需要等ROOT签收才继续B/C。

**B TDD实施。** 有真实缺陷先保存行为RED，再改所属共同责任层。测试覆盖跨公司/市场/文种的同一规则，禁止公司、页码、某段金标整句特判；不抬token、费用、时间、空间或并发额度，不增加人工权限、canary、授权JSON和签收链。没有缺陷可以交付有效的回归套件及明确no-code结论，不强行重构。只改本卡allowlist；遇到需要改别仓或ROOT保留模块，交付具体counterexample与期望，由ROOT处理，不能私自扩大。

**C 集成/CLI/独审/交接。** 先跑必要单元，再跑一个或少量代表性真实CLI端到端，检查真实入口和实际调用链，不能以mock函数调用次数冒充跨仓端到端。默认离线、不使用任何真实LLM或下载API、不读取密钥；历史真实资料仅只读或使用已有小范围脱敏fixture，不能假称新下载/新预测。每case有界，失败停在命名原因，修根因后只重跑相关部分，禁止反复跑超时全域。若全量本仓既有套件能够稳定短时完成，可在C一次执行；慢套件不加到每次commit。

测试都放在独立test/temporary目录，先记录初态和sentinel；完毕恢复初态，原本不存在的临时下载/数据库/请求文件/子进程须清除，已有fixture不得删改。保留小收据/压缩日志；报告前后字节/文件清单差异、owned child回收和峰值空间，不留逐页副本或大响应。未知费用、时长、外部完整性就写unknown/NOT_RUN，不能编0或PASS。

**交接前必须调用真正独立的审查agent。** 把本卡全部要求、实际diff、测试包、接口、已知局限交给它，全面审查完成度、架构/模块化、硬编码、数据/角色/期间/数字、错误路径、测试真实性和清理。作者不能换个名字自签。独审发现的本范围问题全部修复，保留初审与修复证据，再由独立agent复审最终实现；最终本范围OPEN必须为空才可交接。跨仓阻塞如实单列，不能靠把本范围缺陷移入“范围外”伪完成。

## 固定交接接口

交付目录为本仓`delivery/w20-audit-checkpoints/`。提交`handoff.md`和`handoff.json`，以及`review/initial.md/json`、`review/final.md/json`（确实无问题可只有final，但仍须独立agent实际审查）。JSON至少包含：

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
