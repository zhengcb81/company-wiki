# W23-XIAOMI-OCR

PLAN_ID=w23-xiaomi-ocr-2026-10-30; PWF_PLAN_ROOT=docs/plans.

唯一入口TASK_CARD.md，调查依据SOURCE_NOTES.md。独立工区自基线de7ffe48推进；样本与gold在引擎输出前冻结（0d24c943）。

## 阶段

- A 现状/固定revision/资源路线/冻结样本gold：done
- B 比较器TDD/真实baseline/小米pilot：done（8469df7c）
- C 固定样本对照/holdout/清理/真正独立审查：done（fde39dfe + 独审NEEDS_FIXES→修复c62ba969）
- 终审与交接：done（独审终审 READY_FOR_ROOT / 0 OPEN；handoff.md/json 交付；分支已push a430e984）

## Next Step

无。STOP。ROOT负责接收工具/结果并决定是否在阅读层接入；X1重放需≥3.3GiB空闲RAM或GPU；M8采用/完整公司循环不由本包代签。
