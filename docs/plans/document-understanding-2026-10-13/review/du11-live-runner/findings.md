## 2026-10-17 readonly boundary correction (ROOT C preflight)

Real CN zh-CN and US unknown language were rejected by the benchmark exact-manifest loop even though formal source preparation supports both. Keep query issuer/kind/period/as-of admission, unique SourceRef, SHA and real open; make descriptor URL/date/language differences diagnostic only. TDD corrected RED 4/4 (language-red-corrected.json); final affected 11 PASS / 0 SKIP in29.12s, Ruff PASS, frozen source SHA unchanged across run. Initial synthetic import fixture rejected locale tags and was corrected before the true RED; retain receipt. Actual source preparation and owned HK facts consumer inconsistency are documented in ROOT-owned .planning/shared-reading-production/du11/source-preflight-review.md/json. No HK facts copied into this helper, no production data/config change or paid/network call. Tool implementation frozen; ROOT performs one combined independent review with source-owner projection fix, no extra small-node gate. See language-fix-handoff.md/json.

---

# Findings

唯一旧工具是tools/document_understanding_benchmark/phase_c_runner.py；owned-runner旧入口只是wrapper。已有purpose=narrative/母费用账/同run和同AUTO跨run0POST/公开exactRef，不需第二套客户端。

source owner已经提供load_catalog_config、resolve_source_location、SourceCatalog.register_sources、SourceVersionReader.query_local/open_version；足够在临时catalog引用现存raw，保留当前root/adapter/route配置，免复制原件。新helper仅测试编排，不造RootPolicy/来源身份/期间。只读取实际原件旁已有sidecar，不回填descriptor到DB或原件。metadata不能满足exact/asof或与descriptor冲突则NOT_RUN并留原因，避免假资料通过。

单版本输出必须与paired区分：缺旧0.8时当前exactRef等于LATEST，不能沿用“旧LATEST后的历史exactRef”标记。默认pair保留原legacy_latest_ref字段。same/crossrun禁止POST逻辑均原样复用。

历史mother preflight581487已过期；ledger8 uniqueattempt后当前599590/385113µUSD。保留unknown7/FXhold，新增unknown0。只按database+attempt_id最后观察计账；不因临时DB归零。新增测试用合成账验证旧unknown baseline保留及native settlement去重，不访问真实凭证。

测试中的source_catalog config/原始合成资料/源catalog数据库完整SHA/mtime和文件集合前后相等；临时模型生命周期只使用127.0.0.1 fake server，不涉及真实供应商或模型配置变更。
