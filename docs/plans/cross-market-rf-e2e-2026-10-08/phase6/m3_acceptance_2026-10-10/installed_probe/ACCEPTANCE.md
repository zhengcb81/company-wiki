# Independent installed-runtime acceptance — 2026-10-10

Result: **18 fresh subprocess checks passed** across the `.agents` and `.codex` physical installations. The full commands, expected/actual exits, UTC times, original stdout/stderr logs and their SHA-256 are recorded in `verification.json`. No product source, installed files, production configuration, or original document was modified.

## What was actually executed

- Installed RF public CLI reports engine `4.2.0`; three half-year parameters (annual forecast driver, segment opening base, company reported base) are rejected for missing annual coverage.
- Installed RF public CLI accepts complete fiscal-year flows and writes JSON plus Markdown only inside owned TEMP. A separate fresh process computes, strongly validates both its result and the CLI artifact, and renders the report.
- The explicit H1 60 + H2 50 derived full-year input passes without scaling either original half-year fact. Its consolidated result matches the public CLI result.
- Installed FF success/error envelopes preserve `acquisition-observation/1` as a top-level sibling. Null fees remain null; reported lower bounds remain incomplete. Malformed list outcomes, null exchange counts and nonfinite fees are dropped without replacing the typed provider failure.
- Fresh installed RF consumers retain the installed FF failure observation and its independent legacy acquisition-failure object unchanged.

Every child uses `Python -I -B -X utf8`, an owned TEMP working directory and publication registry. It inserts only the selected installed `scripts` directory. Module-origin evidence proves imports from that physical installation; no repository test helper or conftest runs inside a child. The outer coordinator uses source test helpers only to author synthetic JSON fixtures.

## Restoration and installation proof

The independently compared **36 selected files** match the SHA-256 of the accepted main Git blobs recorded in MAIN's `targeted_install_plan.json`. All **590 pre-existing installed files** remain byte-identical after testing, with no new installed cache or file. The TEMP directory and its generated JSON, Markdown, publication registry and fixtures were removed. Persistent files in this package are the probe harness and bounded engineering logs only.

External provider calls, external LLM calls, paid tokens and cost: **zero**. Production originals were not opened or copied. This is engineering/installation acceptance; real-company revenue research and AUTO JSON routing remain their separate planned tasks.

## Reproduction

Run `python -X utf8 -B run_probe.py` from this directory after the installations are synchronized. It creates and restores a new owned TEMP directory. The evidence records fixture source-file hashes and the installed module paths. Re-running updates this package's evidence; preserve an existing receipt before a later campaign if its historical logs are needed.

The successful product execution preceded a formatting-only split of four outer harness statements. Both execution-time and current harness hashes are recorded; child code and test assertions did not change. Ruff now passes.
