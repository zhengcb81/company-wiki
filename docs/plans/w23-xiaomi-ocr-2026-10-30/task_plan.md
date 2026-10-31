# W23-XIAOMI-OCR

PLAN_ID=w23-xiaomi-ocr-2026-10-30; PWF_PLAN_ROOT=docs/plans.

唯一入口TASK_CARD.md，调查依据SOURCE_NOTES.md。独立工区自基线de7ffe48推进；样本与gold在引擎输出前冻结（0d24c943）。

## 阶段

- A 现状/固定revision/资源路线/冻结样本gold：done
- B 比较器TDD/真实baseline/小米pilot：done（8469df7c）
- C 固定样本对照/holdout/清理/真正独立审查：done（fde39dfe + 独审NEEDS_FIXES→修复c62ba969）
- 终审与交接：in_progress（独审复审中）

## Next Step

独审READY_FOR_ROOT后：删除frozen_pages、写handoff.md/json、push分支、STOP。X1=unsupported（实测cap<最小加载峰值，算术入档）；X2=not_run；最终结论限定为PARTIAL，不冒签准确率比较完成。
