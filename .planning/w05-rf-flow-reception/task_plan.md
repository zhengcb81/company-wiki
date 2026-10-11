# ROOT 接收 W05-RF-FLOW

PLAN_ID=w05-rf-flow-reception；owner=ROOT；与OCR、Audit写集分离。

## 目标
接收RF交付f1a782a（feat7b22bca8，base1b616622）。原件不动，0provider/LLM/费用；原FAIL留证；只在最新main隔离树实现共用时间口径修复，不按公司打补丁，不清理他人WIP。

## 大节点
- [x] A 交付Git/SHA/写集、独立反例与旧兼容核验；87 SHA匹配、120 tests+33 subtests绿，三期间语义P1穿透强输出读者。
- [ ] B 先正式RED再修复：derived的源口径与consumer绑定；解释文字不能豁免窗口/同主体重复贡献；按同一规则覆盖annual consumer；集中测试。
- [ ] C 整合最新主线的确定性端到端/独立复核，正常提交、并线、安装定点同步、推送及精确CI。

## Next Step
独立报告已收。ROOT从最新main创建rf-flow-root，检出完成后接原交付，正式RED→时间口径共因修复。额外纠正C1的CNY/USD标签、8 ignored E2E产物留证；compatibility已tracked，纳入ROOT树，不能当缺代码。已有mixed-recognition KeyError需纳入集中修复节点。

## 验收
任意真实起止日、闰年/跨年、partial/annual、窗口包含关系、重复贡献及币种单位保持正确；schema3.9与早期语义不变，3.10明确有据的区间；不得靠rationale或修改time_basis把部分期间数字冒充全年。测试临时根还原。

## 证据
docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-rf-flow-acceptance/
