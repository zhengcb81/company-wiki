# W04 G2 LLM configuration scope

## Objective and scope

Add Config.load_llm(config_path=None, *, llm_provider=None) -> LLMConfig and use it in the configured narrative CLI. Share LLM construction, profile selection and validation with full Config; preserve legacy full Config behavior. The new interface strictly checks selected credentials in both pytest and production, and does not inspect search/wiki/schedule configuration.

Exclusive files: scripts/config.py, scripts/narrative_batch_configured.py, tests/unit/test_w04_llm_config_scope.py, own .planning/w04-g2-config. ROOT explicitly permits the existing test_configured_entrypoint_selects_provider_through_authoritative_loader mock to use Config.load_llm and return LLMConfig; all expectations remain. No production config/raw/installed/old runs/other repos changes. No external HTTP, models, providers or charges; one localhost fake HTTP integration is required by the amendment. No commit/push.

## Steps

- [complete] Write responsibility-layer tests and record actual RED before product edits.
- [complete] Extract shared LLM builder/selector/validator; add strict load_llm and switch CLI.
- [complete] Run affected config/CLI compatibility tests and lint as one major node; record GREEN/remaining failures.
- [complete] Verify diff, bounded SHA manifest, fixture cleanup and STOP handoff.

## Acceptance

Production process works with only selected fake LLM credential, absent TAVILY, nonexistent wiki root and irrelevant schedule. Missing selected credential rejects even with pytest marker; fallback never automatically selected. Exact current primary/configured fallback/explicit DeepSeek models and URLs stay unchanged. Explicit config does not search dotenv; managed default dotenv and DeepSeek env precedence stay unchanged. Invalid generation parameters are rejected through the shared validator. A spawned configured CLI makes exactly one local fake request, produces an artifact and reports actual fixture usage; no secrets in response and all original bytes preserved. Full Config retains search/wiki strict validation and legacy pytest credential relaxation.
