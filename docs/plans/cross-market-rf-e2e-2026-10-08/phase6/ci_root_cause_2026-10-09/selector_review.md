# Independent changed-unit selector review

All concrete findings were corrected and independently confirmed. Read-only normal OS review used uniquely owned temporary probes. No source/config changes, network, keys or raw document access; every probe temp root was removed.

## Correction checks

- All five subprocess/importlib/runpy alias forms trigger the conservative fallback when their source changes.
- An unchanged computed import consumer is selected alongside its static consumer. Actual selected pytest and full pytest both detect the same failing assertion.
- Literal relative import and run_path consumers were initially omitted. Their corrections now retain both consumers; dotted literal imports with function aliases remain resolvable.
- Uncertain consumers cannot hide a changed source with no known unit consumer; that case still falls back to all units.

## Range, failure and cleanup checks

Real git ranges include earlier source changes before a final documentation commit, and both rename endpoints. New branches and unavailable bases return full-unit fallback. A real failing pytest returned 1; main propagated 1 and constructed exactly one combined suite with one tests/unit argument and contract smoke retained. Owned pytest basetemp and fixture roots were removed.

## Fast commit and known CI failures

Commit hooks remain static. Declaration parity catches the declared-but-missing runtime dependency independently of installed packages. Current source-selection probes include the known migration, frozen narrative binding and PPTX consumers. Documentation-only selection returns before graph construction. GitHub CI continues every unit test.

No remaining actionable finding in this reviewed scope. AST selection is an optimization, not behavioral or complete-coverage proof. No large suite was repeated. Detailed probe bodies, selections, failures, timings and cleanup checks are in selector_review.json.
