# W23-XIAOMI-OCR

PLAN_ID=w23-xiaomi-ocr-2026-10-30; PWF_PLAN_ROOT=docs/plans.

唯一入口TASK_CARD.md，调查依据SOURCE_NOTES.md。ROOT只预置独立工区与五个seed文件，状态READY_TO_DISPATCH，尚无Xiaomi推理、模型下载或独审。五seed可纳入首次提交。

## 阶段

- A 现状/固定revision/资源路线/冻结样本gold：done（见progress.md 2026-10-30 A条目；样本与gold均在引擎输出前冻结）
- B 比较器TDD/真实baseline/小米pilot：in_progress
- C 固定样本对照/holdout/清理/真正独立审查：pending
- 交接并STOP：pending，不把硬件不支持或NOT_RUN冒签准确率比较完成。

## Next Step

B：tools/ocr_comparison 先TDD（CER/WER已知例、缓存键、超时/空回复不计通过、null bbox/confidence、恢复0重复推理），再实现runner与R0/X1 backend，一页pilot（≤180s、峰值≤min(8GiB committed, avail/2)），然后固定样本对照。X2两阶段按资源界，不允许则NOT_RUN。
