# W04 selector 并线调查（只读完成）

## 结论

- 接收 18 文件：8 源 / 10 测试；18 行 main 与 base 无内容冲突。
- G2 配置4文件单列延后。CI两文件已main同内容，CI测试main额外有6个OCR回归正控，旧文件不得覆盖。
- 27 个直接 source/test import 已核对：包内依赖列入18写集，包外main与旧工作树依赖一致。
- 原最低 reserve 覆盖合同保持；质量排序是普通与预留各自通道内部，不能称全局质量排序。

## 每行精确三方 SHA

以下SHA不截断；`不存在`表示该commit没有该blob。完整字节数、blobID、LF normalized SHA、每行PWF出处在 integration-manifest.json。

| 文件 | 包/处理 | 旧BASE字节SHA | 当前MAIN字节SHA | 待接工作树字节SHA | main新改动/冲突 |
| --- | --- | --- | --- | --- | --- |
| .github/workflows/ci.yml | keep_current_main_ci | 9f2864979058658089bb9d4edd879e05a733404f3d1a6d1de06ec012a63359b8 | 83acf7be22008c407254cc5135b8267f58526bfdcc83cdae172827b3cf840ccf | bf270a2a7281e6b594dcdfa4ac1a0e74382cffe551a8beff02f28aceea04e27d | main已接同内容；不复制 |
| scripts/config.py | g2_configuration_deferred | 0660232b92d0b2699acb779af701416d054c52361b0ad16f935e9e98e6bc4941 | 0660232b92d0b2699acb779af701416d054c52361b0ad16f935e9e98e6bc4941 | 63c8a3982715d6b716ef01d973a067ce3c9bf0b0a26cb8405d096e216211ce5f | 无 |
| scripts/narrative_batch_configured.py | g2_configuration_deferred | b72e4a9cbd1662e7bff938cab2c66fd3635e2882f21ce739aa2c1b6a98490d0b | b72e4a9cbd1662e7bff938cab2c66fd3635e2882f21ce739aa2c1b6a98490d0b | 123ad26d54d5c3aedb0ccfbe7cbdcbf6ddb14eb4833c3d0f539f258c588a3374 | 无 |
| src/company_wiki/source_catalog/narrative_budget.py | selector_accept | 88a25a1854449224f20606e9949adda3649d77aa04b45f2c9cc7dfe07943b404 | 88a25a1854449224f20606e9949adda3649d77aa04b45f2c9cc7dfe07943b404 | ae68412ea81b8439284ee65305da440ac84b5ddb69fe69a2070920489e7b8a1b | 无 |
| src/company_wiki/source_catalog/narrative_business_groups.py | selector_accept | 4f6d8f56d961e54debcffd51a4ba0431ef70487d4aad9577aad5d909d5ac3f08 | 4f6d8f56d961e54debcffd51a4ba0431ef70487d4aad9577aad5d909d5ac3f08 | c2ced013b8823695d0a16f447e36848dcd060a2c344de322f3b425b296236402 | 无 |
| src/company_wiki/source_catalog/narrative_candidates.py | selector_accept | ff286285f0d90a0a9de3683cc633d6139a4f7f49cf8a4d99f64903a966b716b6 | ff286285f0d90a0a9de3683cc633d6139a4f7f49cf8a4d99f64903a966b716b6 | aec5e2d22c942064dea64b805e09d6b835c516af16d931e7218366e5b8ff5fa4 | 无 |
| src/company_wiki/source_catalog/narrative_evidence.py | selector_accept | a04b7d90e9b304e726036e7c14d2463bd0c680a8c2f8f9dcff768cc03c84ee3f | a04b7d90e9b304e726036e7c14d2463bd0c680a8c2f8f9dcff768cc03c84ee3f | 400ae1cd3ff3a789d307c8fc85de09839a3f9fe6cbed1d5572699535b1598b68 | 无 |
| src/company_wiki/source_catalog/narrative_finalize.py | selector_accept | 527a33be9e94514c55241cfeb03c4e4279196781e955e9483c27055445fa67f7 | 527a33be9e94514c55241cfeb03c4e4279196781e955e9483c27055445fa67f7 | 48083f0bd7c6862744667597a14818e20ef02979f1ec4615bec5670cb1f77f47 | 无 |
| src/company_wiki/source_catalog/narrative_group_candidates.py | selector_accept | c1915ce95439aac90757129cb134b20fff7150331467e6b367952f9c02785569 | c1915ce95439aac90757129cb134b20fff7150331467e6b367952f9c02785569 | 729b77bb92655fd05945980331f68e5a2f3701a1cbece7b26e4c0fc683590e7f | 无 |
| src/company_wiki/source_catalog/narrative_semantic_coverage.py | selector_accept | 不存在 | 不存在 | fd2866db2c8c831c9b74e874f7e40c021e08d44cb3a45684cb3c7d31180a72ca | 无 |
| src/company_wiki/source_catalog/narrative_stage_assertions.py | selector_accept | 不存在 | 不存在 | a7efe34bd99533302a20cfeee0c401ed77c225bfba95a203a8c4c3b1f08aea73 | 无 |
| tests/integration/test_w04_novelty_finalize.py | selector_accept | 不存在 | 不存在 | 967edc28d7e65b251fde9074d724a4c51a350308a0067eca181890df79fc2db1 | 无 |
| tests/integration/test_w04_quality_band_budget.py | selector_accept | 不存在 | 不存在 | 6359f12b4229fd624a3902eaeee393dca5802a62ca25a29811c6e69e6cf4361a | 无 |
| tests/integration/test_w04_semantic_budget_finalize.py | selector_accept | 不存在 | 不存在 | fb55bfb43c043b02446d24c709dcb0e4264c59fa419bdd15588d0f03e3ce1a8c | 无 |
| tests/unit/test_ci_push_selection.py | keep_current_main_ci | 37e848b78ea8957bd678edd90a2016b7fd26404d6b4dc655eb106413f308be81 | 698b28a86c41ea554f3212d425de8e7913ce457469f6f0d1a445de1027670569 | 85439972e1ed96678f6eebf5fe9e6c382ae7e517dad26eb31ed7a3f5eb9db9f0 | CI保留main；旧target缺新OCR正控 |
| tests/unit/test_narrative_business_recall.py | selector_accept | cadc2af6e962ee8977982c0f5334c365456bd6046a9b78cd9c67822e5d671ef3 | cadc2af6e962ee8977982c0f5334c365456bd6046a9b78cd9c67822e5d671ef3 | 9714951af67a77113969ee4794b6eb1fddf8d6623db1009c662ac228cdefe93e | 无 |
| tests/unit/test_narrative_model_config.py | g2_configuration_deferred | f3f27768425ab76fb69ade0c164da800a5cf1c1cd440578fec6275dd654d886d | f3f27768425ab76fb69ade0c164da800a5cf1c1cd440578fec6275dd654d886d | d6460baf85f3ab69ba75aecbd64719a30823afcc26df150d44b778b74635f8a6 | 无 |
| tests/unit/test_w04_llm_config_scope.py | g2_configuration_deferred | 不存在 | 不存在 | 0be78f38edb81ea1c4c475dd1b6c5479588de05328ae62b81fafbafc02612cc8 | 无 |
| tests/unit/test_w04_narrative_semantics.py | selector_accept | 不存在 | 不存在 | 03e83d6675c3e14315624e04eabea353f0eac5394112a0bc3efdede8352cda3d | 无 |
| tests/unit/test_w04_novelty_budget.py | selector_accept | 不存在 | 不存在 | fe68f44a8ac90e63a92d60b1ce8b0ae94f1f5feecba118b86f1a335d39615bbf | 无 |
| tests/unit/test_w04_selector_version_dispatch.py | selector_accept | 不存在 | 不存在 | d5409951a8f172f2f25f32cb7a40f0fcac66a789bea2a173e95cc31979fcb296 | 无 |
| tests/unit/test_w04_semantic_budget.py | selector_accept | 不存在 | 不存在 | 7eb30ac41c05094958ee05479b4de039a777f7f1c546366b904073f0806f23e1 | 无 |
| tests/unit/test_w04_stage_predicate_scope.py | selector_accept | 不存在 | 不存在 | 32e02c1a902ff2ca64cbf83b0ac46b2603d25c4cd43f07c2edd5246c86a4feab | 无 |
| tests/unit/test_w04_stage_public_assertions.py | selector_accept | 不存在 | 不存在 | c8a31dc605456c93b3c7219a9920a9552eaf0cfd9c2afc0ec3bdc8004c44771b | 无 |
| tools/changed_unit_tests.py | keep_current_main_ci | 2527cfa7acb25bdf305a701e21a8894c17f7579d0a55b8d050d4803ba953108a | 70f043361480b4c5a751814dded3d1f14cd01a5f0b64a222513113f2ffe6dd49 | a9b509f974b8556efdf1380bf0e723eb2f0e5aeebc452e65d51230ea93d0361c | main已接同内容；不复制 |

## 验收链及可复用证据

1. 早期 WP02 STOP_PARTIAL/247PASS/真实失败保持历史记录；其业务组叶已进入后续root selector修复，不单独冒充最终验收。
2. semantic-coverage-freeze 的15文件固定共用阶段分类、原生组、公共default0.8与显式旧路由；后来 novelty/quality Phase2 7文件覆盖其中4文件，union18。5个前置源和6个未变测试的早期freeze仍精确。
3. Phase2产品freeze2db879e8744fe646caa2a44a93d89ef4b89dbbf65f5fffe4549ed4d7d21b69ed；作者10模块375PASS/13.57sec及RED/18FAIL/1FAIL都保留。
4. canonical独立工程17/17 + 完整原文组绑定4/4 PASS_WITH_SCOPE，manifest6eb7350ae7b238f2eba101ad4e239cc217e9cc6c6f5a9885af8dad6a8a22e6f7。
5. ROOT未改固定检查脚本15b06195a41a0694a8cf3ca996216686ddb3a7072ca2623eee7e4a68740b17b6，实际六原件PASS/87.4409sec，6legacy指纹/rawSHA/wholegroup/caps/omitted均保存。
6. publicdefault0.8已正式授权；独审初版optin误述已纠正并保留旧记录。直接budget/finalizer省略policy仍legacy。

## 必需边界

- LPCVD>三百台只归LPCVD；同组“部分设备重复订单”不声称LPCVD专属订单。
- 钨系列/PRISMO实现验证和订单有同组主体证据；供应交期仍为条件风险，不当作已发生延迟。
- 所有body为source数据，不生成投资研究state。摘要语义和RF研究质量 not_evaluated。
- main新acquisition/scope/scanner/normalization/OCR/portability写集不与18selector文件重叠，原样保留。

## 直接依赖完整清单

| 依赖 | 处理 |
| --- | --- |
| src/company_wiki/automation/narrative_generation.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/automation/narrative_selector_binding.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/n6_budget_dedup.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/n6_candidate_completion.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/n6_candidate_operating_facts.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_budget.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_business_groups.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_business_policy.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_candidates.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_context.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_document.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_evidence.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_finalize.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_group_candidates.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_matching.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_neighbors.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_ocr_groups.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_pdf_groups.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_pdf_qa.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_project_context.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_replay.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_routing.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/narrative_semantic_coverage.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_stage_assertions.py | included_in_18_file_selector_write_set |
| src/company_wiki/source_catalog/narrative_visual_units.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/transcript_layout.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |
| src/company_wiki/source_catalog/transcript_versions.py | present_currentmain_eol_equivalent_to_old_dependency_keep_main |

## PWF/冻结/独审出处

下列文件的SHA与字节数已写入manifest，旧共享PWF均只读：

- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-selector-recall/semantic-coverage-freeze.json:5-75 — business/stage/public routing15 pre-novelty files
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-selector-recall/BUDGET_INTERFACE.md:3-11 — low-level defaultlegacy and public0.8 policy
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-selector-recall/task_plan.md — historical rootcause/failed recalls; later freeze supersedes pending nextstep
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-wp02/task_plan.md:1-43 — STOP_PARTIAL historical business leaf; final roots handled by newer phases
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-wp02/progress.md — historical247PASS and original replayFAIL retained
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/WP02_SELECTOR_INTERFACE_AMENDMENT.md:3-18 — public0.8 approved default, legacyexplicit, restored groups
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/WP02_STAGE_CLASSIFICATION_AMENDMENT.md:3-13 — stage meaning, actual vs plan/financial mechanism
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json — final7productsfreeze2db879
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-novelty-recall/phase2-real-recall/handoff.json:11-46 — RED/GREEN375PASS/ruff/mypy/failure history
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-root-novelty-recall/phase2-real-recall/concentrated-attempt3.json — 10 modules375PASS
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/independent-engineering/scope-controls.json:5-33 — correctpublicdefault/explicit0.7.1/low-levellegacy controls
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/phase2-independent/manifest.json — final independent freeze
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/phase2-independent/report.json — 17/17 independent engineering scope acceptance
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/phase2-independent/witness-inspection.json — 4/4 completegroup bound factual witnesses
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/native-novelty-six-quality-v2-execution.json — actualfixedsixPASS87.4409sec/no mutation
- C:\Users\郑曾波\Projects\company-wiki/.planning/w04-root-novelty-recall/native-novelty-six-quality-v2.json.gz — ROOT actual six raw/golden/cap/completegroup recall
- C:\Users\郑曾波\.codex\worktrees\m3-acceptance-20261010\company-wiki/.planning/w04-g2-config/handoff.json — separate G2 four files102PASS; excluded

## 后续验收

ROOT接收后只做task_plan列出的4模块普通集成一次；若发生真实阶段源三方冲突才在同批加2stage模块。此准备任务没有运行任何产品测试，不申请新许可，不重复375/6或旧独审。
