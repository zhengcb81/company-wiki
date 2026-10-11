# W05-CWP-OCR 独立复核：冻结恢复、预算与几何

状态：**PASS_WITH_SCOPE**。仅签本报告固定的恢复/几何/预算范围；原生硬截止模块仍施工中，本阶段没有测试或签收。ROOT 真实来源 E2E、整包测试和 W04/RF 下游质量另管。

## 固定代码与独立结果

- 树：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`。
- local_ocr.py：`ff7db0e6aeea844c1f32d3de3f3fdfa7965e6a3cd4f3fe56d4e455efc08a574f`。
- ocr_composition.py：`9a4d517114d6bcd4b692eee4520c9fc2d16f6caa84854f348d1c655d668bd9fe`（含 ROOT 的 public wrapper 接缝；隔离模块此时未签）。
- ocr_region_recovery.py：`bc11c76be2d0fcf6ca586f9a410467e88e561e21e7bd76a73fa46b29c9b0dbe7`。
- 原 `counterexamples.py` 保持 SHA `0ee1d69c4135fd49db47fe0ca7bac2c4782a3a5617b053555bdcfd60cc8d9169`，期待未改。
- 对新冻结树执行原6行为探针：**6 PASS / 0 FAIL / 0 HARNESS_ERROR**。新 `final-counterexamples.json` SHA `26ba4e506d6b3a3ca7aee8fea8ff68ddcfa1f13cba081827b222da49d5e31e1a`；`original-counterexamples.json` 的5 FAIL原样保留。

## 逐项结论

| 原发现 | 复核结果 |
|---|---|
| OCR-I01 总预算事后校验 | `RecoveryBudget.reserve_pixels` 在每次源图和 ROI inference 前原子校验并扣费；原剩余1 pixel反例只调用原图，不运行ROI。对象在一次composer请求共享，失败推理的已预留量继续计入。 |
| OCR-I02 忽略真实 filtered remainder | evaluator 实读 crop诊断并回映射；属于原region的 dropped正文不签完整恢复。原 margin/stack 两反例都不再输出高分碎片；attempt留诊断。明确外部邻居不 veto，有formal正反测试。 |
| OCR-I03 拼接块中心映射 | 整个框须在单块真实 x/y窗口内；跨块、右padding、最后块以下拒绝。额外无法映射文字也不被悄悄丢弃后签恢复，补formal回归。原跨块位置不再伪造bbox。 |
| OCR-I04 非方形逆旋转 | 90使用原width，270使用原height；非方形真实PIL旋转的像素bbox独立期待，90/180/270均有formal覆盖，原90反例恢复正确。 |
| 原文字保留/去重 | distinct-overlap探针仍 PASS：原正确行不动，无法消歧的重复/重叠text仍报unrecovered。 |
| 缓存版本 | `region_recovery_algorithm=bounded-source-roi/2` 进入identity_manifest；新指纹与旧算法不同。schema保持兼容，fingerprint提升算法，不拿parser_version2.0.0掩盖新产物。 |

## 正式测试的审查

读取新增formal tests以及 `fix/red.log`/`fix/first-green-attempt.log`/`fix/green.log`。ROOT/修复agent执行的集中结果为37 PASS；本独立审查不重复同一包。

第一次实现后3个旧测试失败源于旧fake框 x1 超过自身chunk实际宽度，原框落在stack右padding，过去中心映射错误允许其通过。收窄这些fake框到真实chunk后，保留原成功拼接文字、错误重试/失败状态期待；不是删断言来适配错误代码。新的 padding/cross-chunk正式负例同时要求拒绝旧非法几何，证明没有恢复到旧漏洞。

## 未签范围与限制

- public `enrich_pptx` 已接 configured LocalOCRAdapter→IsolatedOCRAdapter 的请求范围，但后者此时未冻结。待 ROOT 给 SHA 后集中查看生命周期、IPC、deadline及不合作子进程反例。
- 本地模型/真实原图召回由 ROOT 新E2E证明；未重跑worker真实页，不声称已通过。
- `recall_status=unverified`、detected未知、opaque页保留仍正确；det未发现内容、保守重叠排除不代表已穷尽。
- 不是下游selector/摘要/RF财务正确性验收。
- 0 provider/付费/云OCR/模型下载；只用内存synthetic图；没有额外scratch、原件或产品写入。
