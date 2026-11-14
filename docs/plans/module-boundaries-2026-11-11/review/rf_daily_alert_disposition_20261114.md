# RF daily alert worktree disposition — 2026-11-14

## Scope

Repository: `C:/Users/郑曾波/Projects/revenue-forecast`
Observed main: `ec5ba0044b3252d2fc58c4a50c2fe9bc234cf5ad`
File: `assurance/runs/daily_alert.jsonl`

This file is a generated operational alert log. The only local tracked difference was three appended failed canary observations. They are preserved here before restoring the runtime log to its committed baseline; the product code and report outputs are not changed.

## Preserved observations

| Run ID (UTC) | Result | Evidence in alert |
|---|---|---|
| `20261111T210002Z` | `not-ok`, exit 1 | `bound=0 events=473`; resolver latency `5.78s` exceeded the recorded budget. |
| `20261112T210001Z` | `not-ok`, exit 1 | `bound=0 events=473`. |
| `20261113T212408Z` | `not-ok`, exit 1 | `bound=0 events=473`. |

All three reported `latest daily run reported not-ok`; no report data, customer/source document, or financial model input is represented by these appended canary lines.

## Result

After this summary was saved, the exact runtime log was restored from RF `HEAD`. Verification is a clean `git diff -- assurance/runs/daily_alert.jsonl` and no modified status for this path. The operational observations remain in this PWF receipt so the tracked runtime file can return to its original state.
