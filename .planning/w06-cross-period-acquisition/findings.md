# Findings

最新工程接收191PASS、独立13+1PASS；原41整体40/1，剩余ET来源过滤原因被两层泛化。共用cutoff实施按已有error_code/not_found字段进行，普通空结果与provider故障分开，不引入第二验证链。正常commit静态hook查到operation_contract新增空dict缺annotation，ROOT补显式类型而非绕过hook。

2026-10-11 已有真实公共入库记录带完整acquisition.request/candidate/receipt及hash/size，但steady source-fact assertion为空。二者责任脱节；旧期在resolver层已排除，却在local_reconcile被重新当作当前缺口。依赖于它的ET未启动应记前置未运行，不归ET缺陷。独立根因报告在母W06 evidence/root-ff-matrix-acceptance/root-cause-review/。

禁止方案：为测试手填verified assertion；把所有metadata字段当事实；跳过原文SHA；整个禁用local_metadata_gap；按CN/US/具体年号绕过；提高deadline/cap或放宽原case期望。应复用入库时已有事实资格并在来源层判断相关性，保持未验scan与目标损坏来源的诚实失败。

## 2026-10-11 Cutoff独审与矩阵截止

独审39PASS/3FAIL封存3140797e；三个同根失败是坏JSON/非对象stdout抹去当前request已验证stderr usage。作者只修已有错误投影并重冻，非作者集中复验。新完整41未过：2PASS/31PARTIAL/8NOT_RUN，180秒绝对批次到期、fresh proofs未执行；旧40/1保持，原配置/原件/密钥stat/scratch恢复。matrix-deadline-diagnosis.md明确派生错误、零真实费用及原限额下一步。
