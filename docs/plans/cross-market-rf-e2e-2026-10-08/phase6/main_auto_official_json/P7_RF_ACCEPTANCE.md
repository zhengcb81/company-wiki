# P7-RF MAIN 接收、并线与发布验收

状态：**engineering accepted / published / installed verified**。真实公司研究与 R16/R17/R18/W09 仍需后续复验。

## 发布事实

RF canonical main 与远端最新 `47f497ad9dee9dc47f66fca37016e9ba6b6b6f33` 一致；精确 [CI38096229764](https://github.com/zhengcb81/revenue-forecast/actions/runs/38096229764) success。源修复提交 `e929185c` 的精确 CI38096020406 也 success。普通 commit/fast-forward/push，无 no-verify/force；RF三个 assurance owner 未提交 SHA/状态与 output 文件列表保持。

外包源码与交接183c9534接收后，MAIN真实发现并修两项关系根因：calibration适用期间须关联实际native output/消费FY单元；共享PID的support按业务×情景×年份取实际作用域，保多校准和各自claim、不借用其他业务。源数值、计算、confidence与有效历史measurement/真实跨期桥不变，无新权限/签收/共享参数禁令。

## 真实验收与边界

- 原接收25责任PASS；period反例RED4FAIL→119PASS/7subtests及四组真实离线build→validate/compute/Markdown/snapshot→diagnostics。scope反例RED3FAIL→35PASS，保存原scope攻击实际CLI A支持/B不借用；独立六探针全部PASS。上述计数有重叠，不相加。
- 最终普通pre-push/CI同一快清单284PASS/2subtests，43.76秒。此次两个现成新责任文件纳入同一清单，避免只在单次验收保护根因；没有新增工作流/全覆盖/生产目录测试/小节点门。
- 九个已接受runtime/docs定点两实际安装根18文件；502其他文件SHA保持。.claude junction复用.agents，无整目录覆盖。
- fresh `-I -B` 两实际安装根各五原生样本：可选research未提供、A范围不得支持B、company范围合法共享、同步FY2031反例降级、真实历史FY2025→FY2026 bridge。40业务CLI+2版本+1工程fixture factory全部exit0，15.0735秒。版本4.2.1、计算/Markdown、snapshot与支持诊断一致；42installed子进程真实代码来自安装根。551安装文件全部SHA不变、7input/helper保持、自有TEMP移除，外部网络/provider/model/费用0。
- 两次先期driver错误分别为ENGINE_VERSION入口猜错与snapshot要求合法fixture缺省字段；保留真实失败/部分原生回执，修工程driver使用公开版本与真实compute.forecast_version，不改fixture/产品/安装、不把driver错误叫产品缺陷。

原raw日志bytes与旧交接SHA保留；仅卡内证据属性防Git换行破坏哈希，并定点7文件索引刷新。旧失败独立报告原样保留，新增fixed-review。未处理原845MB planning历史清理，不混同原件。

## 接口与剩余任务

`economic-support-diagnostics/1` 可选只读，不声称推断经济真相；未提供optional operating research的旧流程保留。真实公司的三年预测、经营校准事实质量和四路审查未因工程绿关闭。P7-AUDIT尚未通知交付，MAIN不写其外包源。MAIN继续W04有界诊断与W03版本化业务筛选，再原三家公司修后真实四审/新三家泛化/loop。

证据：

- [原接收](evidence/p7-rf-reception/readonly-reception.md)
- [scope独立最终复核](evidence/p7-rf-final-review/scope-fixed-review/review.md)
- [正常发布](evidence/p7-rf-release/fast-gate-publication.json)
- [精确最新CI](evidence/p7-rf-release/fast-gate-exact-ci-02.json)
- [定点安装核验](evidence/p7-rf-install/verification.json)
- [真实安装CLI验收](evidence/p7-rf-install-probe/HANDOFF.md)
