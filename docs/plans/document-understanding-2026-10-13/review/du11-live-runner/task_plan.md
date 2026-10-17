## 2026-10-17 readonly boundary correction (ROOT C preflight)

Real CN zh-CN and US unknown language were rejected by the benchmark exact-manifest loop even though formal source preparation supports both. Keep query issuer/kind/period/as-of admission, unique SourceRef, SHA and real open; make descriptor URL/date/language differences diagnostic only. TDD corrected RED 4/4 (language-red-corrected.json); final affected 11 PASS / 0 SKIP in29.12s, Ruff PASS, frozen source SHA unchanged across run. Initial synthetic import fixture rejected locale tags and was corrected before the true RED; retain receipt. Actual source preparation and owned HK facts consumer inconsistency are documented in ROOT-owned .planning/shared-reading-production/du11/source-preflight-review.md/json. No HK facts copied into this helper, no production data/config change or paid/network call. Tool implementation frozen; ROOT performs one combined independent review with source-owner projection fix, no extra small-node gate. See language-fix-handoff.md/json.

---

## 最终软件节点（2026-10-17）

最终冻结三文件集中9PASS/0SKIP，60.51秒，前后SHA相同；Ruff PASS。8prepared输入指纹与母账完全不变。已有初始RED、fixture错误与最终绿均保留；外层终端GBK echo错误不影响已落盘pytest exit0/XML。详handoff.md/json、final-test-receipt.json。本包实现测试完成，等待ROOT独立reviewer；未commit/push，不能标独审COMPLETE。真实provider质量/metadata补全仍ROOTC。

---

# DU11 live runner — ROOT自有测试工具窄幅升级

PLAN_ID=du11-live-runner；PWF_PLAN_ROOT=docs/plans/document-understanding-2026-10-13/review。根计划引用由ROOT负责，本包不改母PWF。

目标：继续唯一phase_c_runner，不新造模型/费用客户端；新增registered_readonly来源挂载与可选单0.9验收，保留默认隔离复制的0.9→0.8历史对照。真实API由ROOT后续执行，本包0外部网络/0收费/0密钥读取。

白名单：tools/document_understanding_benchmark/phase_c_runner.py、phase_c_readonly_source.py、新tests/test_phase_c_readonly*.py与本PWF。CWP src/生产配置/原件/真实sidecar/FF/ET/RF/母费用账均不写。

A（完成）：只读核现有runner与source owner接口；基线4个新测试4FAIL（新helper/API不存在，记录为接口RED，不冒称既有metadata行为被测坏）。母账599590 tokens/385113µUSD，unknown7与FXhold保留。

B（完成）：source owner当前config roots仅把catalog_dir移到owned temp；register_sources单relative path→query_local→open_version；无原文复制/元数据补造/生产DB写。源metadata不足明确NOT_RUN0POST。追加--source-mode registered_readonly、--source-catalog-config、--selector-versions0.9.0；默认pair不变。单版本不标paired改善、默认same/crossrun0POST保持。

C（进行）：新挂载真实register/query/open及单0.9现有configured loopback lifecycle、metadata gap反控/无复制/母账去重/invalid config早拒；实际原件/母账不动。现测试有本机合成HTTPfixture，外部provider0。原件变更拒绝/真暂停outbox恢复继续复用已有独立integration案例，本工具不重复造管理器。最终测试/ruff/源SHA与独立审查由本PWF收据＋ROOT reviewer记录；未提交，由ROOT统一发布。

验收局限：合成readonly挂载真实source链与no-copy验证；已配置真实provider质量/三真实原件metadata完整性/新PDF装配仍由ROOT C节点执行。不能把本机测试当真实供应商或研究质量通过。遇真实metadata缺口不改sidecar，以NOT_RUN报告给source责任层。
