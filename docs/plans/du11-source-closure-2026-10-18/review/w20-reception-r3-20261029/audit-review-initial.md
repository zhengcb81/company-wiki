# W20-AUDIT ROOT第三轮初审冻结（2026-10-29）

**原R1.INV1及R2已通过；仅原R1.INV2剩一项P2。ROOT已决定在独立工区直接定点修复，不再转用户第四轮、不增加审批。此为修复前证据，不签当前源码可并线。**

作者HEAD `5b8aa7182e7f7b219b0ef279106f1fc1886137b1`，实现 `d306ac059e249e6b600b7247ee350a33e302bcbe`。观察器SHA `6c32bd1b175da994cb9c43ac5fd4234210fd02c1145d69c0720926a1517a57d6`；交接清单26文件SHA全部匹配，工区clean。原独审r2-report为APPROVE，ROOT另做实际复核。

## 已过的节点保留

ROOT复跑原7条断言7P/0.516秒wall、上轮参数化4方法全过/0.705秒、作者W20 43P/0.627秒、numeric7P/0.967秒及公开离线synthetic CLI11步/5.405秒成功，records_complete/0 gaps。未跑全仓。显式unit不再从正文百分比借量纲，unknown unit有partial上限；R2共享material availability仍正确，均不重开。

## 一个剩余共同根因：币种局部归属边界

责任 `skills/revenue-forecast-audit/scripts/summary_checkpoint_observations.py` `_local_currency_families` L272–290，尤其L286：右窗条件写成 **`end - right < 12`**，right从end向右增长，此差值恒≤0，实际上没有12字上限。

claim `12.5亿元人民币`，源 `收入1,250,000,000` 后52字才出现 `人民币余额2元`，当前仍给第一个数绑定CNY、报scale_equivalent；参数距离20/40/80都错误。该helper自己的局部有界契约未实现，不是扩展新语义要求。

**只flip比较方向仍不足以闭合既定INV2**：内存中仅把该条件改为`right - end < 12`，远距例正确降partial，但这两个短距例仍full：

- `收入1,250,000,000和人民币余额2元`
- `收入1,250,000,000及CNY现金2元`

后面另一笔余额/现金的币种仍捐赠给未声明币种的第一个数。需要一次在共同owner处理有界与归属：只绑定与该候选数有明确局部关系的币种；多个金额间归属不明则unknown/partial。可保守处理，不要求NLP分类器/无限词典/币种推断，也不写“余额/现金/和/及”句子特例。合法 `收入1,250,000,000元人民币` 必须继续识别。单flip反事实只是内存诊断，没有修改作者源码或冒充已发布修复。

## 精确RED和ROOT修复后复验

[参数化反例](evidence/audit/test_window_bound.py)3方法：一个近邻正向控制通过，两个方法下5个subcase真实RED，[日志](evidence/audit/window-red.txt)、[收据](evidence/audit/window-red-receipt.json)。源码读取默认作者工区；ROOT修复工区可通过`W20_AUDIT_REPO`显式选择，不改断言。旧7及typed4已全绿，须保持；修复后只跑相关短包/CLI和独审，不重跑超时全量。

ROOT将从5b8 HEAD建立`revenue-forecast-audit-w20-root-final`，本审查agent不改源码。之后独审绑定实际最终commit/SHA；此初审文件保留，不用新结果改写旧RED。[单flip诊断](evidence/audit/flip-only-counterfactual.json)说明为什么要一次关闭远近两个边界。

## 清理和范围

测试自有根`.planning/w20-reception-r3-20261029/audit/temporary`原不存在、测试后恢复不存在；45文件235818B已删，peak未采样保持unknown。仅保留小probe/日志/JSON，不复制原件或SDK，不读密钥、不付费/下载/安装/并线、不改作者工区。[机器报告](audit-review-initial.json)、[测试](evidence/audit/tests.json)、[清理](evidence/audit/cleanup.json)、[SHA](evidence/audit/sha-verification.json)。反例全部synthetic，不是公司预测或真实供应商调用。主线公司循环仍暂停。
