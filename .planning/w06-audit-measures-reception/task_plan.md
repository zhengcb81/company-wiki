# ROOT 接收 W06-AUDIT-MEASURES

PLAN_ID=w06-audit-measures-reception；owner=ROOT；仅Audit仓库，和RF/OCR无代码写集重叠。

## 目标
接收Audit交付6a50d7e（feat098b4d03，basec099333），整合已接收W05 loop的最新main321d4c1。保留原FAIL，0真实供应商/模型/费用，不覆盖安装配置/output。

## 大节点
- [x] A 核Git/SHA/PWF与独立typed语义反例；23 SHA匹配、40+7旧测试绿，但19反例16失败，原FAIL保留。
- [ ] B 正式RED→共用measure/relationship兼容层；校验结果与输入实体、定义、kind、币种单位、期间；缺语义/来源报告不可评价，不能假PASS；比例容差尊重量纲；坏结构返回诊断而非中断整批。
- [ ] C 最新main完整包+确定性隔离E2E+独立复核；正常并线、定点同步两技能副本、更新PWF。Audit无remote，不能宣称推送远端。

## Next Step
ROOT树 audit-measures-root（从main321d创建）接原交付，不提交；集中TDD修复五类共因，再复核原16缺口。实施agent只写此树的新工具/reference/tests与本线fix证据；ROOT拥有最终独立审查、接线、提交和安装。

## 接口与验收
工具给审查agent风险事实与诊断，不成为新许可、签收、LLM或调度器。歧义不得自行猜身份、期间和经济定义。已有numeric_context与W05进度闭环保持兼容；测试目录还原。

## 证据
docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance/
