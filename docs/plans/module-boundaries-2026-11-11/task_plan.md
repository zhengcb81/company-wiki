# 模块边界收口计划

## Goal

从当前各模块架构出发，定义有限、可验收的模块化与解耦范围；用公开接口、独立安装/隔离测试、owner 状态归属和 TDD 完成边界封装，再恢复原主线。父计划为 `../du11-source-closure-2026-10-18/`。M0原为规划；用户随后明确授权A1调查、清理和有限并线，执行结果见reconciliation.md。

## Current Phase

### Phase A1 — 各模块工作区与未并线提交核销
**Status:** complete

2026-11-11用户新增授权：逐模块调查未提交及已提交未并线改动；确认归属后可删除无用改动，尽量并入正确主线；余项必须写进原施工卡。ROOT负责所有Git/清理变更，各路审查只读。保留下载原件；已证明需保留的有效代码和正在施工内容先分类，不能用整仓reset/clean代替调查。

步骤：新鲜Git refs/worktree/dirty盘点 → PWF/commit/交接与patch-equivalence逐项归因 → 删除确认无用内容/并线有依据且可验收分支 → 余项逐卡归属/顺序/测试 → 独立核对与发布。

证据集中在review/repo_reconciliation_20261111/；新架构实现仍按五卡后续执行，本节点仅做用户新要求的仓库整理与并线。

结果：8仓390个分支/remote refs、253工区、7tag、2stash已调查并分责；FF B34与Dashboard边界修复独审/定向回归后已入main、推origin。清理确定测试目录约216MB、7个空旧工区、source-facts重复源码、已吸收stash及生成物；未接收能力/有价值WIP全部加入原五卡A0和ROOT清单。A1 complete只代表本次核销交付，不代表所有历史工区清空或M1/M2完成。

### Phase A / M0 — 当前架构、接口与完整施工图
**Status:** complete

三路只读代码调查及ROOT对账已完成。五卡和接口矩阵已通过独立方案审查（PASS），两项阻断及三项精确性建议全部修复；本轮只改计划。证据：review/cwp_architecture.md、acquisition_architecture.md、research_architecture.md、root_baseline.md。

- [x] CWP 479个src文件/7包+根35模块清单；FF/ET/SID/RF/StockWiki/Audit/Dashboard实际模块图。
- [x] 当前实现、已证明能力、确定缺口、风险和未运行验证分开；原D4/D5/P3结果限定范围保留。
- [x] architecture.md/interface责任、boundary_matrix.json和acceptance E01–E09有限出口。
- [x] 五张互斥仓库卡、worktree基线/写集合、测试先行、独审、交接格式与合流规则。
- [x] 方案独审与修复、父计划状态对齐及文档JSON/链接/工区互斥检查完成；本轮以正常Git文档提交交付，实际发布版本看Git历史。

### Phase B / M1 — 五个owner并行TDD与模块交付
**Status:** in_progress（ROOT已完成并线MB-RF的B1安全子范围；RF B2和其他四条lane仍待实施）

MB-RF当前主线为 `6341759b9cdfd13e8aa7d51d5c755e361046da0c`：compare实现 `e060a8607` 已在先前提交进入main；部署/来源回归测试 `058be4fd6` 已通过171 passed、1 skipped及独立审查并进入main；最新PWF记录也已推送。B37剩余scope/subject/verified-compare不在主线，候选跨私有接口及固定IFRS/财年/单分部假设，继续按卡内B2重做。MB-CWP、MB-FF、MB-ET、MB-SID目前仍未派发。

任务卡见 dispatch.md。保持现有跨仓wire，作者各自A→B→C连续实施；不是每一步等ROOT批准。

| Owner | 本轮有限任务 | 独立验收 |
|---|---|---|
| CWP | CWP-01协议外OCR配置、02隐藏预算、03类型导入、04实际安装、05根/状态/模型边界分类 | 七责任逐项说明，公开替身/安装/恢复/原件保护 |
| FF | FF-01六operation及job/三表隔离，02command/config组装 | 真subprocess+无邻仓环境；已满足允许NO_CHANGE |
| RF | RF-01旧越层工具分发、02core/report依赖、03历史profile与默认隔离；继续B37公开scope/subject/verified-compare | 已并入compare与部署/来源回归子范围；剩余公开合同跨会计准则、财年、多分部，且保留job命令；纯计算/报告golden、来源/目录/job公开端口、安装 |
| ET | ET-01纯合同/进程与provider分离，02固定表示限额复现根修 | worker CLI成功/错误/unknown/预算/取消 |
| SID | SID-01typed错误贯通，02metadata反向依赖 | 纯API、稳定wire/过滤语义、staging-only |

ROOT在此期间准备组合清单/样本，在自己的StockWiki隔离工区按reconciliation.md接收C38/B03合同差额；Audit只验证，Dashboard由原owner接续。ROOT不写五卡lane源码、不派竞争Dashboard任务。每条卡交付前独审并修复；接口兼容可及时并main/推送，无须积压到全部卡完成。

### Phase C / M2 — ROOT组合与整个架构阶段关闭
**Status:** pending

1. 锁各模块交付commit和正式runtime形态；选择真实本地样本/已有报告/三表快照并冻结必需点。
2. 核对Dashboard选用release代码根与数据根，不把缓存remote、main或旧配置当现行部署事实。既有owner处理必需release并线。
3. CWP卡交付后ROOT才改组合runner，按acceptance E01–E09一次运行。已有D4/D5/reader替换证明按用例复用；不重复收费全文测试。
4. 集中独审，不通过的格交给对应owner修复并复跑受影响部分。无必需skip；可选诊断不作许可，真实失败不改成PASS。
5. 各正确主线/remote对齐、当前自有测试目录恢复、交接证据完整、PWF CLOSED；立刻回父计划R4/T4→新版摘要→真实缓存→RF实际采用→公司循环。

此阶段不等待未来所有研究问题消失；其验收范围在矩阵里。新业务质量问题进入父计划，不无限延长解耦阶段。

## Next Step

下一步继续MB-RF B2：先建立跨会计准则、财年和多分部的公开scope/subject合同测试，再用RF owner公开reader实现并接回CLI，保留 `import-rf-job`。其余四张卡可独立启动，A0差额已写在各卡。ROOT继续按reconciliation.md负责StockWiki接收、Dashboard组合和各仓最终并线；原业务循环仍暂停。

## Decisions

- 主线质量问题与模块边界分别记账；不以全文摘要/研究质量作为架构阶段永远延后的出口。
- 不新增人工许可、逐步签收或 Python 运行时防反射沙箱。
- 保留原件、现有配置和外部 harness 工作区。
- 采集审查最初建议只派FF/SID最小卡；ROOT依据用户“每模块设计解耦”要求，将已确认ET协议反向依赖和SID下层导入上层纳入本轮，形成五卡。没有确认缺陷的StockWiki/Audit仍先验证，避免强制改写。
- 同理RF core/report职责纳入同一RF作者，历史B34兼容不全面迁移。Sina只在CWP owner，金融数值不转回PDF抽取。

## Errors Encountered

| 观察 | 原因与处理 |
|---|---|
| 外仓Git普通沙箱status报work-tree/Permission denied | ROOT宿主只读重查成功，记录真实WIP；不是源码缺陷 |
| installed PWF resolver按旧PWF_PLAN_ROOT=docs/plans静默无结果 | 当前脚本变量语义不同，改用显式-PlanRoot与PLAN_ID，已正确解析本目录；不改技能/不增加许可 |
| CodeGraph部分当前文件不在索引 | 记录覆盖限制，用文件列表与已定位文件读补齐；未运行init/重建索引 |
