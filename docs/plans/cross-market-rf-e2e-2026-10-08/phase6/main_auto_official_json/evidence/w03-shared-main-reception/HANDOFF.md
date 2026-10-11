# W03 shared selector 接线交接 — PASS

工作目录：`C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki`。本线自HEAD `236fca0850800445bc5d89948049c38e7c80c2fb` 开始，源/test写集已冻结；未做Git/安装/外部provider/收费模型操作。ROOT已独立完成全局default切换与公共3项大节点。

## 实际接口与责任

- 新内聚 `automation/narrative_selector_binding.py`：`bind_narrative_selector(selector=None, *, selector_version=None) -> BoundNarrativeSelector`，builtin按pure resolver解析effective version后显式partial传给实际policy。已有bound adapter保持pin，runtime冲突typed拒绝。custom沿用旧call shape，但调用者明确声明其已固定的真实policy；不检查签名、不猜函数名、不TypeError重试。编程能力声明不涉及用户授权。
- `NarrativeSelectHandler(..., selector_version=None)`：raw、official共用同一bound adapter；select结果stamp取adapter实际版本。没有package/schema扩张。
- `select_verified_projection(..., selector_version=None)`：在complete-empty早返回前解析版本；native parent/role/whole field locator/whitespace/partial保持。
- `NarrativeRuntimeDependencies.selector_version` 给select与verify同一effective pin；`NarrativeVerifyHandler(..., selector_version=None)`严格验证本runtime pin，其bundle继续既有`versions.selector`字段。
- factory `_runtime_snapshot`只decode真实frozen binding一次，读取`execution_versions.selector`及现有generation map。frozen缺失/未知selector typed拒绝且发生在HTTP model构造前。无binding的真正direct调用使用current。现有 `_generation_values`仅兼容私有调用seam，production factory不重复调用/解码。
- resolver读取recorded supported version并显式传给pure selector，保持既有实际raw/parser/ordered evidence replay检查；未知/缺失recorded版本仍为`NarrativeEvidenceResolveError`。

## 8个锚点的固化测试

| 锚点 | 本线测试与证据 |
|---|---|
| 旧0.6全有序指纹 | `test_raw_frozen_policy_executes_actual_spans_and_verifies_under_default_drift[0.6.0]`：实际66,324B TXT SHA，旧pure完整fingerprint `11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f`；实际AUTO另经真实material extraction后比较全span。 |
| 新raw0.7实际执行与generation | 同raw参数0.7真实召回“90% of the tasks”，对照旧0.6缺失；history generation实际0.6/0.7哈希不同且新请求`find_reuse_pin`为None。 |
| Raw/official同pin、角色/partial | `test_runtime_registers_select_and_verify_with_same_effective_version` + `test_official_actual_version_keeps_native_parent_roles_whitespace_partial_and_replays`：真实双API页、缺第三页显式partial、原始whitespace、两个parent真实bytes、全locators replay。新0.7召回无product名词的行业出口许可答复、旧0.6不召回。真正mixed公共CLI由ROOT public3补全。 |
| Frozen0.6漂移下执行/verify | raw在global0.7下pin0.6真实运行与tag一致；verify正确pin通过、另一policy明确DEPENDENCY_INVALID；factory从frozen selector传runtime并单decode。 |
| 旧finished只读、unfinished拒绝 | `test_actual_finished_06_history_readonly_and_new07_cannot_reuse_old_generation[1/2]`：实际生产batch/worker/loopback/publish/store先完成旧0.6，切global0.7只读恢复；AUTO/catalog完整SQL dump、预算、结果及原件bytes不变，无新增HTTP POST；非terminal旧run NEW_RUN_REQUIRED。ROOT另做真实freshchild/mixed公共history。 |
| Unknown typed、空official不得绕过 | factory unknown/missing frozen用实际mixed role + forbidden model constructor；runtime无写入；`test_complete_empty_projection_does_not_bypass_unknown_version`的真实issuer-bearing空native source在早返回前拒绝unknown。 |
| Custom旧shape/partial/TypeError/conflict | `test_custom_legacy_shape_explicit_pin_and_version_aware_partial_are_real` + `test_custom_missing_declaration_conflict_and_internal_typeerror_do_not_retry`：0.6旧shape/0.7显式partial实际内容不同；无声明和adapter冲突typed；内部TypeError精确只调用一次。 |
| 真实resolver旧/新 | `test_real_transcript_resolver_uses_recorded_version_full_ordered_rows[0.6.0/0.7.0]`：真实TXT、完整ordered rows/groups/reasons/locators重放一致；unknown typed拒绝，原件bytes不变。ROOT公共search/lookup/full fingerprint补全。 |

## TDD、回归与静态结果

- `red-focused.log/json`：最初17项，16FAIL/1PASS。真实失败含runtime缺pin端口、factory忽略frozen版本和unknown、global漂移resolver拒绝旧记录、custom helper缺失。也包含新夹具本身的issuer空列表/空间测量误比较，已明确区分，不能把这些计作产品缺陷。
- `red-corrected-fixtures.log/json`：旧store两个history基线PASS；complete-empty夹具仍有空span对象误断言，随后修为真实空raw_text（issuer-bearing fields仍存在），不改source-port语义。主线另有已保存的真正公共3项RED，见ROOT证据。
- 实现后首次新测试11PASS/6FAIL，失败是新测试比较未提取TXT和其管理层claim引用错误，不改生产定位/角色来迎合测试；修正fixture用真实extractor和管理层引用。
- `green-scoped.log/json`：98PASS/6FAIL，失败仅新测试误读既有bundle.selector，而实际合同为bundle.versions.selector；修正测试正确读取接口。
- **`green-final.log/json`：104PASS，22.88秒**（17新增责任案例+87受影响既有select/verify/retrieval/official/factory回归）。
- **`green-extra.log/json`：34PASS，5.08秒**（剩余existing empty-custom声明 + worker factory）。
- **`green-model-construction.log/json`：4PASS，2.00秒**（将unknown/missing frozen反例改成实际mixed模型路径后定点验证，拒绝发生于HTTP构造之前）。
- **`static-ruff-final.log`：13源码/test文件clean；`static-mypy.log/json`：7源码clean。** 曾在默认sandbox运行mypy触发默认`.mypy_cache/missing_stubs`权限错误，随后使用明确授权的自有TEMP缓存完成；与产品无关。
- pytest仅现有“asyncio_mode unknown”警告（plugin autoload关闭），全部测试实际通过。未改pytest/CI/配置以消除警告。

## 写集与保护SHA

仅6允许existing source + 1 cohesive helper、新unit/integration test和4必要旧fixture声明。旧fixtures变化：select cap/path custom声明0.6；empty official custom声明0.6；frozen factory binding声明实际0.6；pure official partial调用声明已有实际0.6/0.7。无断言放松。

| Shared production文件 | SHA-256 |
|---|---|
| `src/company_wiki/automation/narrative_selector_binding.py` | `23fed8698f85c2a2f28277bd38266b61ae51fbd01dc2bb783f03d60adce73a45` |
| `src/company_wiki/automation/narrative_worker_factory.py` | `73000216cff325c602b811be457f2c7e35d2c4b8ffb9b90c14c13a07160e9d69` |
| `src/company_wiki/automation/narrative_runtime.py` | `3635775b4933b998a5b79a7047b326869815ff4e187c6af2531a2814acb64d9c` |
| `src/company_wiki/automation/narrative_select.py` | `436e2500362d5c9082bdf7748a53519b232b66a44f62bd81abb4353bb9979974` |
| `src/company_wiki/automation/narrative_official_json.py` | `3dd559f183e065fbce68daa870b83c0249e34eaadff99a661a962e329693d7b3` |
| `src/company_wiki/automation/narrative_verify.py` | `dae39594f35a5f15c85c2b2398c596bd9b668df9cbc8d76b29fcc695ba579d08` |
| `src/company_wiki/source_catalog/narrative_retrieval.py` | `5318557aff5b973e92071b845910b0d3d4d0912c08f90a6c2d10cac714c04f93` |

逐项SHA见`source-before.json`/`source-after.json`。原before覆盖source/config/TXT的262项（完整集合以JSON为准），其中其余255项不变；所有shared之外的实际变更仅ROOT明确授权的pure default开关：
`src/company_wiki/source_catalog/narrative_evidence.py` current SHA `64b724df8b879b6859832facd4d18cf7f306b927611439f037c554c6e557e616`，0.6.0→0.7.0，本线未修改或恢复该文件。
生产`config/source_catalog.yaml` SHA `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`；原TXT fixture SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`均不变。

## 清理、归总与边界

所有自有w03-*-临时目录已finally检查绝对parent/前缀后删除；首次长basetemp relocation由项目已有hook记录且删除，原生日志有CW-BASETEMP-CLEANUP。测试catalog/raw/db只在owned TEMP，真实provider0次、收费model0次、安装0次、Git0次。loopback HTTP和offline fixture model只用于隔离工程验收。

本线停止source/test写集；ROOT负责最终独立复核、普通commit/push/PWF归总和exact CI。ROOT已告知public3 GREEN（3PASS55.06秒）覆盖mixed CLI→child→loopback→publish/read/reuse、真实0.6 freshchild history→0.7只读恢复、新0.7不reuse旧pin、两policy完整真实TXT与公共search/lookup；引用其独立日志，不由本线冒称亲自重跑。

这些工程结果不代替配置供应商真实摘要质量、全财报业务召回和三年预测四审。没有增加新许可/身份门，也没有新增current schema或第二registry/store。
