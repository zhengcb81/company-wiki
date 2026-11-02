# R7 CWP CI policy tests — consolidated and frozen

Exact CI41445012145 exposed40 instances of one retired assumption: daily push, optional AST analysis and CI remaining contracts must share the full35target list. Runtime policy now intentionally separatesDAILY9 from fullUnit+22remaining contracts. The other3source-policy failures belong to the other author and are not claimed fixed here.

## Single responsibility in tests

- `test_pre_push_gate.py` is the only mode/scheduling policy owner. It checks docs0, runtime/config/unknown/mixed ranges,379files without AST expansion, exactlyone execution, red/exception propagation and honest scope labels, CI/fullUnit separation, JUnit, deadlines/workers and actual freshscratch cleanup.
- `test_ci_push_selection.py` retains optional AST dependency/transitive/fixture/dynamicimport/pathclassification and fullGit-range parsing. Its18unknownpath cases retain classification coverage; they no longer also run an unrelated daily main assertion.
- `test_daily_push_policy.py` retains the actual isolatedGit hook E2Es. It creates the9actual daily nodes, not35unrelatedstubs. Success/failure, docs aftercode, config outside daily coverage, fullvalidation detection and missingrunner blocking remain realCLI/Git behavior.
- The duplicate-only bounds and parallel-phases files are deleted. No business, model, source or bounded-process/resource test was deleted. All6oldOCRresource inventory guarantees remain as a single requiredCIset assertion.

Original5files/839lines/134collectedcases become3files/639lines/106cases:28duplicated scheduling cases and2redundant files removed. This is ownership consolidation, not40number substitutions. Existing runtime/tool/CI/hook bytes are unchanged.

## Test-fixture quality fixes

The new scratch test first tried to force a deep pytest path through a real60unit Windows placement limit. It now observes the owner-created short temporary directory and its removal; no resource limit was raised. RealGit tests then proved outer pytest plugin settings and parent config leaked into nested fixtures. Each synthetic repo now has its own pytest.ini, explicitly loads the declared pytest_timeout plugin in its fixture-only environment, uses UTF8 and strips foreignGitcontext. A deliberately invalid foreignGit_DIR/WORK_TREE/index cannot redirect the fixture or write the foreignindex. Actual timeouts and failure assertions were preserved.

## Evidence (separate runs, not one combined pass)

- Initial short RED40F90P/3.08s; no fullUnit.
- Consolidated firstshort99P2fixtureF/2.10s; exactscratchfix+CIwiring3P/0.39s.
- RealGitfirst3fixtureF1P/6.13s; onlyfailed3afterrootisolation3P/15.15s.
- Finalshort101P/1.68s; currentmissingrunnerrealGit1P/1.22s; exactCIwiringcoveredseparately; finalmergedinventory1P/0.33s.
- Three surviving files RuffPASS. Final106unique cases are covered across these bounded runs; no single106P/fullCI/H1 claim.

## Old capability → current owner

- `tests/unit/test_ci_push_selection.py::test_transitive_relative_import_includes_fixture_consumers` → `tests/unit/test_ci_push_selection.py::test_transitive_relative_import_includes_fixture_consumers (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_changed_test_or_fixture_is_not_omitted` → `tests/unit/test_ci_push_selection.py::test_changed_test_or_fixture_is_not_omitted (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_nested_test_only_change_keeps_its_consumers_without_unrelated_cli` → `tests/unit/test_ci_push_selection.py::test_nested_test_only_change_keeps_its_consumers_without_unrelated_cli (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_nested_test_is_a_known_consumer_of_changed_source` → `tests/unit/test_ci_push_selection.py::test_nested_test_is_a_known_consumer_of_changed_source (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_directory_named_test_helpers_does_not_turn_helper_into_a_unit` → `tests/unit/test_ci_push_selection.py::test_directory_named_test_helpers_does_not_turn_helper_into_a_unit (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_environment_entrypoint_deleted_module_or_unknown_fixture_falls_back` → `tests/unit/test_ci_push_selection.py::test_environment_entrypoint_deleted_module_or_unknown_fixture_falls_back (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_changed_dynamic_execution_falls_back` → `tests/unit/test_ci_push_selection.py::test_changed_dynamic_execution_falls_back (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_literal_dynamic_import_is_detected` → `tests/unit/test_ci_push_selection.py::test_literal_dynamic_import_is_detected (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_unchanged_computed_import_consumer_is_kept_alongside_static_consumer` → `tests/unit/test_ci_push_selection.py::test_unchanged_computed_import_consumer_is_kept_alongside_static_consumer (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_literal_relative_import_bare_module_or_file_consumer_is_not_lost` → `tests/unit/test_ci_push_selection.py::test_literal_relative_import_bare_module_or_file_consumer_is_not_lost (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_unknown_source_dependency_falls_back_instead_of_silent_skip` → `tests/unit/test_ci_push_selection.py::test_unknown_source_dependency_falls_back_instead_of_silent_skip (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_document_only_push_does_not_run_full_units` → `tests/unit/test_ci_push_selection.py::test_document_only_push_does_not_run_full_units (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_unknown_or_runtime_nonpython_paths_cannot_become_a_test_free_push` → `tests/unit/test_ci_push_selection.py::test_unknown_or_runtime_nonpython_paths_keep_the_optional_full_unit_fallback; classification18 unchanged; actual main scheduling only in policy owner`
- `tests/unit/test_ci_push_selection.py::test_explicit_documentation_has_no_runtime_targets` → `tests/unit/test_ci_push_selection.py::test_explicit_documentation_has_no_runtime_targets (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_git_range_covers_earlier_code_and_final_document_commit` → `tests/unit/test_ci_push_selection.py::test_git_range_covers_earlier_code_and_final_document_commit (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_multiple_refs_union_and_branch_deletion` → `tests/unit/test_ci_push_selection.py::test_multiple_refs_union_and_branch_deletion (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_no_comparable_push_range_falls_back` → `tests/unit/test_ci_push_selection.py::test_no_comparable_push_range_falls_back (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_git_failure_falls_back` → `tests/unit/test_ci_push_selection.py::test_git_failure_falls_back (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_hook_and_ci_keep_fast_commit_and_use_correct_entrypoints` → `tests/unit/test_pre_push_gate.py::test_real_ci_and_hook_wiring_keeps_full_unit_and_separate_contracts`
- `tests/unit/test_ci_push_selection.py::test_push_failure_is_propagated_and_suites_are_not_duplicated` → `tests/unit/test_pre_push_gate.py::test_daily_reports_pass_only_after_its_single_child_succeeds`
- `tests/unit/test_ci_push_selection.py::test_published_summary_contracts_run_in_both_ci_and_push` → `tests/unit/test_pre_push_gate.py::test_daily_and_ci_inventories_have_distinct_responsibilities`
- `tests/unit/test_ci_push_selection.py::test_source_scope_guard_is_shared_but_full_cache_matrix_is_major_node_only` → `tests/unit/test_pre_push_gate.py::test_daily_and_ci_inventories_have_distinct_responsibilities`
- `tests/unit/test_ci_push_selection.py::test_planning_evidence_only_changes_do_not_schedule_full_ci` → `tests/unit/test_pre_push_gate.py::test_real_ci_and_hook_wiring_keeps_full_unit_and_separate_contracts`
- `tests/unit/test_ci_push_selection.py::test_planning_archive_is_not_live_behavior_even_with_code_suffix` → `tests/unit/test_ci_push_selection.py::test_planning_archive_is_not_live_behavior_even_with_code_suffix (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_mixed_live_source_and_planning_archive_keeps_actual_consumers` → `tests/unit/test_ci_push_selection.py::test_mixed_live_source_and_planning_archive_keeps_actual_consumers (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_live_unit_change_with_archived_probe_does_not_seed_unrelated_cli_tests` → `tests/unit/test_ci_push_selection.py::test_live_unit_change_with_archived_probe_does_not_seed_unrelated_cli_tests (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_only_owned_planning_roots_are_non_runtime` → `tests/unit/test_ci_push_selection.py::test_only_owned_planning_roots_are_non_runtime (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_unit_only_change_keeps_known_transitive_test_helper_consumers` → `tests/unit/test_ci_push_selection.py::test_unit_only_change_keeps_known_transitive_test_helper_consumers (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_ci_push_selection.py::test_ocr_resource_regressions_share_ci_and_local_smoke` → `tests/unit/test_pre_push_gate.py::test_daily_and_ci_inventories_have_distinct_responsibilities`
- `tests/unit/test_daily_push_bounds.py::test_daily_main_uses_identical_smoke_without_ast_selection` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_daily_push_bounds.py::test_daily_main_proven_nonruntime_range_never_starts_pytest` → `tests/unit/test_pre_push_gate.py::test_proven_documentation_range_starts_zero_tests`
- `tests/unit/test_daily_push_bounds.py::test_daily_pass_is_reported_only_after_fixed_smoke_success` → `tests/unit/test_pre_push_gate.py::test_daily_reports_pass_only_after_its_single_child_succeeds`
- `tests/unit/test_daily_push_policy.py::test_non_runtime_push_never_dispatches_a_test_runner` → `tests/unit/test_pre_push_gate.py::test_proven_documentation_range_starts_zero_tests`
- `tests/unit/test_daily_push_policy.py::test_runtime_range_runs_fixed_smoke_and_reports_narrow_scope` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_daily_push_policy.py::test_empty_stdin_is_an_unknown_range_that_defers` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once + retained optional changed_paths malformed/empty-range tests`
- `tests/unit/test_daily_push_policy.py::test_smoke_only_push_label_does_not_claim_affected_tests_ran` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_daily_push_policy.py::test_a_real_failure_in_the_ran_scope_blocks_the_push` → `tests/unit/test_pre_push_gate.py::test_daily_reports_pass_only_after_its_single_child_succeeds + preserved real Git E2E`
- `tests/unit/test_daily_push_policy.py::test_runner_start_failure_returns_nonzero` → `tests/unit/test_pre_push_gate.py::test_failed_child_launch_is_not_a_green_push`
- `tests/unit/test_daily_push_policy.py::test_green_full_local_mode_keeps_its_own_wording` → `tests/unit/test_pre_push_gate.py::test_explicit_full_mode_runs_all_stages_and_only_one_unit_collection`
- `tests/unit/test_daily_push_policy.py::test_green_push_mode_never_claims_full_or_safe` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_daily_push_policy.py::test_remote_and_full_mode_sets_are_unchanged_by_the_push_policy` → `tests/unit/test_pre_push_gate.py::test_ci_contract_phase_runs_only_the_nonunit_remainder_once + daily mode owner; retired equal-inventory assertion removed`
- `tests/unit/test_daily_push_policy.py::test_full_local_mode_runs_every_existing_stage_in_order` → `tests/unit/test_pre_push_gate.py::test_explicit_full_mode_runs_all_stages_and_only_one_unit_collection`
- `tests/unit/test_daily_push_policy.py::test_hook_keeps_the_push_entrypoint_and_adds_no_bypass` → `tests/unit/test_pre_push_gate.py::test_real_ci_and_hook_wiring_keeps_full_unit_and_separate_contracts`
- `tests/unit/test_daily_push_policy.py::test_hook_blocks_and_reports_a_missing_gate_runner` → `tests/unit/test_daily_push_policy.py::test_hook_blocks_and_reports_a_missing_gate_runner (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_daily_push_policy.py::test_pre_push_hook_is_tracked_as_executable_for_linux_worktrees` → `tests/unit/test_daily_push_policy.py::test_pre_push_hook_is_tracked_as_executable_for_linux_worktrees (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_daily_push_policy.py::test_real_push_green_fast_pass_then_blocked_by_a_ran_failure` → `tests/unit/test_daily_push_policy.py::test_real_push_green_fast_pass_then_blocked_by_a_ran_failure (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_daily_push_policy.py::test_real_docs_push_runs_no_tests_but_does_not_hide_earlier_code` → `tests/unit/test_daily_push_policy.py::test_real_docs_push_runs_no_tests_but_does_not_hide_earlier_code (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_daily_push_policy.py::test_real_push_with_missing_gate_runner_is_blocked` → `tests/unit/test_daily_push_policy.py::test_real_push_with_missing_gate_runner_is_blocked (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_daily_push_policy.py::test_real_push_defers_unknown_config_scope_and_full_run_still_finds_the_failure` → `tests/unit/test_daily_push_policy.py::test_real_push_defers_unknown_config_scope_and_full_run_still_finds_the_failure (same behavior retained; real Git fixture environment now explicitly isolated)`
- `tests/unit/test_pre_push_parallel_phases.py::test_push_dispatch_runs_one_gate_with_every_case_exactly_once` → `tests/unit/test_pre_push_gate.py::test_daily_reports_pass_only_after_its_single_child_succeeds + test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_pre_push_parallel_phases.py::test_configuration_dispatches_only_the_shared_smoke_gate` → `tests/unit/test_pre_push_gate.py::test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`
- `tests/unit/test_pre_push_parallel_phases.py::test_gate_exception_is_reported_not_swallowed` → `tests/unit/test_pre_push_gate.py::test_failed_child_launch_is_not_a_green_push`
- `tests/unit/test_pre_push_gate.py::test_fast_inventory_keeps_the_four_reuse_receipt_regressions_without_a_whole_file` → `tests/unit/test_pre_push_gate.py::test_daily_and_ci_inventories_have_distinct_responsibilities; retired exact35counter not an invariant`
- `tests/unit/test_pre_push_gate.py::test_daily_gate_has_one_total_deadline_and_last_node_diagnostics` → `tests/unit/test_pre_push_gate.py::test_total_deadline_worker_scope_and_owned_scratch_remain_real`
- `tests/unit/test_pre_push_gate.py::test_manual_full_gate_retains_its_original_deadline` → `tests/unit/test_pre_push_gate.py::test_total_deadline_worker_scope_and_owned_scratch_remain_real`
- `tests/unit/test_pre_push_gate.py::test_ci_contract_step_does_not_repeat_unit_cases` → `tests/unit/test_pre_push_gate.py::test_ci_contract_phase_runs_only_the_nonunit_remainder_once`
- `tests/unit/test_pre_push_gate.py::test_explicit_full_mode_runs_unit_once_then_only_remaining_contracts` → `tests/unit/test_pre_push_gate.py::test_explicit_full_mode_runs_all_stages_and_only_one_unit_collection`
- `tests/unit/test_pre_push_gate.py::test_daily_push_runs_only_fixed_owner_nodes_without_ci_integration_files` → `tests/unit/test_pre_push_gate.py::test_daily_and_ci_inventories_have_distinct_responsibilities + test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once`

Actual process-tree/timeout/Git child environment regressions retain their untouched existing owners (`test_pre_push_process_cleanup.py`, `test_pre_push_temp_scope.py`, `test_pre_push_full_unit_workers.py`). Source/CI/hookSHA, precise5filemanifest (null=deleted), oldabilitytable and actualrunlogs are in JSON. ROOT owns independent review/PWF/Git/publication. No source, production config, original, model or paidcall touched.

Owned `tmp/r7policy` was initially absent; measured containment/nonreparse cleanup receipt follows after all reproducible evidence is retained.

Final measuredcleanup: 2200files/1618075.0bytes removed after exactparent/nonreparse checks; all syntheticGit repos and ownedbasetemps restored absent. Final5testmanifest and protectedtool/CI/hookSHA recheckedunchanged.
