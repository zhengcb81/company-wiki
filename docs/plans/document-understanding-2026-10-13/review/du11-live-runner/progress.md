## 2026-10-17 readonly boundary correction (ROOT C preflight)

Real CN zh-CN and US unknown language were rejected by the benchmark exact-manifest loop even though formal source preparation supports both. Keep query issuer/kind/period/as-of admission, unique SourceRef, SHA and real open; make descriptor URL/date/language differences diagnostic only. TDD corrected RED 4/4 (language-red-corrected.json); final affected 11 PASS / 0 SKIP in29.12s, Ruff PASS, frozen source SHA unchanged across run. Initial synthetic import fixture rejected locale tags and was corrected before the true RED; retain receipt. Actual source preparation and owned HK facts consumer inconsistency are documented in ROOT-owned .planning/shared-reading-production/du11/source-preflight-review.md/json. No HK facts copied into this helper, no production data/config change or paid/network call. Tool implementation frozen; ROOT performs one combined independent review with source-owner projection fix, no extra small-node gate. See language-fix-handoff.md/json.

---

## 最终软件节点（2026-10-17）

最终冻结三文件集中9PASS/0SKIP，60.51秒，前后SHA相同；Ruff PASS。8prepared输入指纹与母账完全不变。已有初始RED、fixture错误与最终绿均保留；外层终端GBK echo错误不影响已落盘pytest exit0/XML。详handoff.md/json、final-test-receipt.json。本包实现测试完成，等待ROOT独立reviewer；未commit/push，不能标独审COMPLETE。真实provider质量/metadata补全仍ROOTC。

---

# Progress

2026-10-17：ROOT已批准两个tools文件、新readonly测试与自有PWF白名单；不commit/push、不修改ROOT生产源码。

A：接口TDD首次4FAIL（3个helper缺失＋selector_versions缺失），保留准确失败类。
B：首4PASS8.72s；加metadata gap/母账兼容后6PASS11.95s。
C：单0.9真实configured loopback/publicread/same+crossrun0POST独立1PASS55.07s，externalPOST0；补挂载到真实batch请求且在模型边界主动停止的反控，避免挂载函数未实际被runner消费。完整集中节点执行中。Ruff初16项测试格式问题已修，三个源/测试文件check PASS；只format新增helper/test，不全文件格式化旧runner。

真实元数据不足是公开source事实缺口，不通过改测试fixture/生产sidecar补造。真实三供应商尚未由本包调用；母账/config/原件不变。完成后交ROOT另派reviewer审最终源码SHA。
