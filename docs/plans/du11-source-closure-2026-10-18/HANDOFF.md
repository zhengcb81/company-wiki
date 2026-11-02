# 当前交接 — 整改清单逐项核对已归总

PLAN_ID=du11-source-closure-2026-10-18；PWF_PLAN_ROOT=docs/plans。唯一状态[CURRENT_STATUS](CURRENT_STATUS.md)/json，目标[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)。ROOT管集成/PWF；不新增外包或小节点许可。

## 先看什么

1. [逐项对照表](review/architecture-quality-20261101/implementation-results/checklist-verification-20261102/checklist.md)及同名JSON：原41项完整，T01再展开8入口；三份只读独立核对及ROOT源码/证据对照都在同目录。
2. 三个本次新增遗漏的`residual-repair.json`、`residual-binding-repair.json`及各自独立增量报告。旧报告里的BEFORE_ROOT_REPAIR是原反例，不能当新补修的当前状态，也不能抹掉。
3. 主机器状态内`R7.checklist_verification`和源码精确CI。本次新源码精确CI成功。StockWiki无remote，本次只签本地主线，不要求用户反复授权或虚构推送。

## 已做与未做

原Q01–Q14：13项在定义工程范围完成，Q11保留跨进程/跨时间接收字节校验；R7原27项工程处置均对应当前实现。新补修将SourceExport JSON解码与transport读取预算分开，将paid response保存与HTTP显式预算对齐，并取消opaque冻结元数据的ledger重复顶帽。54P/33P/23P分三批；包含真实loopback大body→decoder死→unknown→新lease/无凭证恢复1POST/1reservation。它是技术E2E，不是公司事实验收。大原文quote、407864B实际_frozen_binding独立验证另见两份增量独审。

可选未做只有本清单所列两项：PDF部署同inode双hash、consumer-spy200样本缺sample_limited；不作为主线前置。日常CWP9/FF11/RF12和invest短域、完整CI分工不回退；不要再造daily=CI恒等测试或每commit全量。150/150已检安装文件匹配只是该范围，不是所有技能的盘点。

## 唯一下一步

按T4-source-note-parent-plan.md冻结去公司化父链正反例并在来源树owner根修，再单H1原90s/16M/112复验；随后新版真实摘要、paid中断/同跨run零重复与同artifact实际RF采用。

T4详见review/architecture-quality-20261101/implementation-results/T4-source-note-parent-plan.md：三个已选view仍继承旧p34(4)标题，12/12不能代父链正确；去公司化正反例保真实上级/金融note嵌套，不按公司/备注号过滤。后按C-preparation新独立catalog/AUTO只读引用原件，配置真摘要、prepared中断/同跨run0重复及同artifact实际RF采用。R4六共因、研究/检测进化、固定八家/三家clean保持。

## 操作边界

正常宿主C:/Miniconda/python.exe -B -X utf8；Git/原子link走支持的宿主执行，不改ACL/完整性、不提取Git凭证。测试先保存结果，再核绝对路径/非reparse清自有UUID目录。已存在资料与他人WIP不删；RF四assurance保持初始SHA，CWP外来hook仅mode差不stage。Dayu/IQS/Dashboard其他owner不动；StockWiki仅本次明确2文件，勿扩其研究功能。模型/预算按配置，unknown费用不得猜0或重POST。
