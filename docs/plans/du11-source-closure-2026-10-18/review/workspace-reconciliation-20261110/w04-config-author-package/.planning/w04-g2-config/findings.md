# Findings

- Confirmed root cause: configured CLI calls Config.load, whose production strict validation requires search credentials and wiki root. Existing pytest marker relaxes credentials and paths, masking that dependency failure.
- Full llm_for_provider also builds a complete Config for an explicit non-fallback profile. Extract LLM-only building/selection so both interfaces have one implementation.
- Explicit config paths deliberately skip dotenv; default configuration uses the existing managed MiniMax/MiMo and DeepSeek env-first rules. Do not change that contract.
- Existing mock-based CLI tests patch Config.load. ROOT authorized moving only that mock to load_llm and returning LLMConfig without changing assertions; new tests add true production subprocess coverage.

- Final 102 tests PASS with real production and fake HTTP coverage. LLM-only decoupling fixes the confirmed missing-search-key failure; no fallback policy/model guessing. FullConfig path/search strictness unchanged.
- Root-controlled sparse materialization kept config content unchanged; canonical config byte SHA verified at handoff.
