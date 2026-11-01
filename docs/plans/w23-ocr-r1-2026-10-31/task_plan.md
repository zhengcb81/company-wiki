# W23-OCR-R1

PLAN_ID=w23-ocr-r1-2026-10-31; PWF_PLAN_ROOT=docs/plans。唯一入口TASK_CARD.md。

状态READY_TO_DISPATCH；ROOT预置四seed，未跑模型/下载/正式试验。

## 阶段

- A 全局累计合同/新gold与未曝光样本冻结：done（r1_gold.json 7页，独立agent凭原图核；旧页pilot R0 19.4s）
- B 单campaign真实对照与恢复：done（账本226.1/1800s；R0/N0 7/7；X1F尝试1因卡上限<实测固定开销MemoryError；缓存跨进程恢复已TDD）
- C 独立全面审查/修复/交接：in_progress（15项OPEN已修并推送；复审中）

## Next Step

核HEAD/status/AGENTS与TASK_CARD，读取ROOT正式接收记录，然后开始A，不等小节点签收。
