# M3 共用根因修复计划

## 目标与状态

本包是独立编程专家的诊断与施工交接。覆盖旧 64 项及 M3 三市场四路 91 项发现，保持历史报告和旧矩阵字节不变。计划交付不表示工程或研究完成。

## 范围

只写本目录；只读代码、配置、原件、其他 owner 计划及审查报告。Dayu 纯外部零变更。company-wiki 只负责 source/extraction/export；研究责任留在 RF/审计研究输出；StockWiki/IQS 其他 owner 不动。不调用 provider/模型，不新增费用。

## 输入与完整覆盖

12份M3原JSON/Markdown全字节hash已复核，全部check/finding实质审阅并核相关冻结request、原件投影、native usage/model、RF input及实际code。report_inventory记录原角色逐数审计，本专家不冒称再次执行整家公司全流程。

| 输入 | 数量 | 当前处置 |
|---|---:|---|
| 旧公司finding | 64 | 30旧根逐项当前处置，旧matrixSHA不变 |
| M3公司finding | 91 | 41P1 /48P2 /2P3，全映射 |
| 原专家output carryover | 2 | 单独保留，不混旧64或新91 |
| coverage总项 | 157 | 155公司+2专家，0重复/0未映射 |
| M3实质检查/报告 | 246 /12 | 不以结构check冒研究PASS |
| 共用机制/施工卡 | 26 /9 | 根因合并，非91症状卡 |

入口：coverage.json/coverage.md、root_causes.json、old_root_dispositions.json、INTERFACES.md、work_packages/W01–09、MAJOR_NODE.md、SKILL_CHECKPOINTS.md、evidence_observation.json/verification.json。

## 阶段（本专家交付范围）

| 阶段 | 状态 | 交付 |
|---|---|---|
| 1 输入冻结与报告实读 | complete | 12 JSON/MD SHA、246checks/91finding及actual evidence/code |
| 2 共用机制与旧处置追溯 | complete | 157coverage/26roots、30旧根处置 |
| 3 接口与独立施工卡 | complete | 9cards、排他写集/共享接口/TDD/大节点/预算/恢复/安装 |
| 4 映射完整性与交付核对 | complete | verification PASS_MAPPING_ONLY、SHA交付；工程/研究不完成 |

## 后续施工依赖与owner

W02先公共JSON subject/projection/DTO与route，再W03普通内容selection；W04MAIN模型runtime独占并行。W06 CWP→FF→RF successusage顺序producer-consumer；W07合同owner与原output/assurance owner共享file串行。W05 commonrequest/ledger/skill检查点可并行purehelper后集成；W08source-only供W09独立研究。

已发布旧工程修复不重派，见W01/旧处置。源码独立worktree按normalhooks/push/exactCI后具体runtimefile定点安装；统一一次原三家修后真实全链四审，按既有顺序固定新三家泛化。初始独立根/protectedraw/config恢复、累计USD20/2M及旧unknown见MAJOR_NODE。

## Next Step

MAIN登记实际owner/worktree/HEAD，继续已有W04runtime及W02/W03/W06/W07共因TDD。此专家已完成诊断计划交付；未运行新增工程/真实收费/研究复验。

## 完成标准

157项都有唯一run/role/issue、根因/owner/card/TDD/剩余影响。工程实际完成、三年研究校准/独立接受、外部限制分别验；计划交付、wire169GREEN、数学PASS或confidence0不能代替工程全部/成熟研究完成。

## Errors Encountered

批量output曾截断，改用分批check/finding/实际字段及全bytes解析SHA；旧implementation根无task_plan/progress，采用真实分目录交接。US实际costs/acquisitionledger而非不存在的usage_ledger。新三计划引用second_cohort_generalization.md实际缺失已报告MAIN，未冻结/执行。引号/缺文件只读错误无输入变更；一次apply_patch标题匹配失败已按实际原标题重试。
