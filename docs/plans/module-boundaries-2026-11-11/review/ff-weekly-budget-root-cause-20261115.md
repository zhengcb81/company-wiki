# FF weekly T3 budget failure: root-cause record

Observed: 2026-11-15 16:51 UTC. Scope: read-only inspection of the RF weekly artifact, the exact FF revision used by that run, and a no-provider isolated reproduction. No FF/RF files were changed.

## Finding

The four failures in RF run 20261115T084227Z are caused by download-capable FF requests omitting the request-owned acquisition_limits object. The run used FF 1dfd81836794ec3bf73b41014a98714e97299ae8, RF f2215959d33abc76778342a95d39a8e38191da75, and CWP 0e741063f510d5bc1c5921aa192b90fab94b6064.

At the exact FF revision used by the run:

- tests/test_e2e_download.py calls run_fetch(..., allow_download=True) for the CN, US, and HK downloads, their idempotent reuse calls, and the corrupted-copy retry. Those request bodies contain no acquisition_limits.
- scripts/fetch_filing.py::_limit_arguments() returns an empty argument list when request acquisition_limits is absent. The helper still appends --allow-download, so CWP receives acquisition intent without the three ceilings.
- CWP source_catalog.cli::_run_ensure_command() requires a complete budget for --allow-download. A no-network temporary-wiki reproduction with the offline no-op adapter returned this exact structured stderr before provider execution: bounded provider access requires --max-download-bytes, --max-download-seconds, and --max-download-cost-usd.
- The matching CWP contract tests explicitly preserve this behavior: complete ceilings are required for provider access; missing or partial ceilings are rejected. This is the intended bounded-acquisition contract, not an unnecessary approval gate.
- Follow-up on 2026-11-15 17:02 UTC: the two focused CWP budget contract tests passed, 2 passed in 3.49 seconds. No provider was invoked.

This explains the weekly run's ensure exited 1, fatal, provider_started=null, and downloads=0. The corrupted-copy test's first reuse-only call is distinct; its second call requests acquisition and omits the same required ceilings.

## Correct owner and repair

The repair belongs to filing-fetch, not CWP or RF report code:

1. Add a complete, finite acquisition_limits object to every download-capable request in tests/test_e2e_download.py, including requests reused with allow_download=True. Values should follow the configured provider/resource policy and the existing per-test deadline, not relax or bypass CWP validation.
2. Ensure the production FF acquisition path supplies the same public request contract. Do not make CWP invent limits or weaken the required-budget contract.
3. Rerun the opt-in real-download T3 suite only after the request fix; retain the isolated temp wiki and verify reuse, byte identity, and zero residual staging.
4. RF owner records the weekly not-ok run in RF canonical PWF. ROOT records the cross-repo cause here and keeps M3 open until owner evidence and exact refs are reconciled.

The filing-fetch docs/implementation/handoffs/P5-FF/HANDOFF.md already records the missing-limit fixture mismatch as a pre-existing baseline issue and assigns the mainline repair to FF. A later local FF main ref is d694d11; its tracking ref remains 1dfd818, and the visible local delta includes the FF1 envelope lane. ROOT did not modify that active FF worktree. The weekly failure itself is bound to 1dfd818, not the later local ref.

## Limits of this reproduction

The no-network missing-budget reproduction is diagnostic only; it did not download or invoke StockInfoDLSimple/Dayu. A supplementary positive-path smoke with explicit ceilings exceeded 60 seconds and was interrupted; it is not counted as a pass. The existing focused CWP contract tests are the evidence for the budget rule. The full real-provider T3 suite still requires the FF owner repair and a bounded rerun.
