# 算术R2：移除指数数值许可

AUTHOR_R2_FROZEN_PENDING_SAME_NODE_INDEPENDENT_REVIEW。初版按旧安全假设保留abs(exponent)>10；独审用15年折现、30年复利和2**11证实其会拒合法数学。R1通过/FAIL历史保留，本轮不把旧版倒签通过。

先新增3合法幂例，两仓各真实3RED。删除指数10判断，不换更大数字；原2**11错负oracle改为真实overflow1e308**11，并补复数(-1)**0.5和0**-1负例。每仓仅新正例+非法数学+相邻经济算术19P（RF0.35s/invest0.15s），4文件Ruff绿，没有重跑32/21或全仓。已有显式累计FormulaWorkBudget不变，默认None不造长度/深度/节点/数值许可；真正parser/overflow/nonfinite/invalid-node仍稳定具名拒绝。

两套共同25case文件规范后完全相同；本轮19与先前20有重叠，不累加成独立39或声称最终25全文件又跑一次。源码/测试4SHA和完整RED/GREEN日志/JUnit在JSON。RF4WIP不变，无真实原件/下载/模型/收费，ET/Stock未写。自有math-r2-c591清理收据补JSON。ROOT按同大节点安排增量独审后再发布，不commit/push/install。
