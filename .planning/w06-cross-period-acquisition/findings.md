# Findings

2026-10-11 已有真实公共入库记录带完整acquisition.request/candidate/receipt及hash/size，但steady source-fact assertion为空。二者责任脱节；旧期在resolver层已排除，却在local_reconcile被重新当作当前缺口。依赖于它的ET未启动应记前置未运行，不归ET缺陷。独立根因报告在母W06 evidence/root-ff-matrix-acceptance/root-cause-review/。

禁止方案：为测试手填verified assertion；把所有metadata字段当事实；跳过原文SHA；整个禁用local_metadata_gap；按CN/US/具体年号绕过；提高deadline/cap或放宽原case期望。应复用入库时已有事实资格并在来源层判断相关性，保持未验scan与目标损坏来源的诚实失败。
