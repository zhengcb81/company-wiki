# Progress

2026-10-09: clean cwp-formats switched from preserved 760ed472 to new branch at 8479b8ad. Read-only diagnosis saved separately in main phase6/no_ocr_fixture_diagnosis. No supplier or OCR calls.

Meaningful RED: 5 failed in 1.21s: replay inherited config; live profile unattested; native capture absent (2); full report loses captured property. Earlier setup probes hit absent sparse benchmark/identity and corrected pure fixtures. A parser identity test typo version→parser_version corrected before final RED.

First GREEN attempt: 4 PASS / 1 fixture cleanup failure (1.28s). Windows sqlite connect context commits but does not close; changed unit fixture to contextlib.closing. Runtime metadata assertions themselves passed; no provider/OCR.

Concentrated run: 34 PASS / 1 tiny fixture registration failure, 2.06s. No batch CLI/OCR/provider started because scan did not register PPTX. Replaced fixture registration with actual official_source_cli local_document import; no source/src changes. A known nonexistent test_official_source_cli/flow.py read returned missing; used actual public flow schema instead.

First actual tiny CLI: expected native failed/PARSER_INCOMPLETE, select/summarize/verify dead_letter, reservations[] and all four native budget fields 0, 3.914318s batch; test subsequently failed parser-metadata assertion because snapshot reader used pre-envelope parser_component path. Actual original receipt retained as tiny-cli-first-actual.json with parser metadata null, protection assertions unexecuted, owned root actually absent. Read-only reader corrected to current source_inputs envelope plus legacy fallback; no runtime/src/gates changes. Native tiny fixture rerun is for this concrete failed metadata assertion only.

Concentrated GREEN: 35 passed in 5.93s; no-cache Ruff green. Actual successful tiny CLI metadata in tiny-cli-actual.json; original first failed metadata assertion retained separately. Legacy binding missing normalization config keeps OCR presence unknown (not false); explicit null in fresh actual fixture remains false.

Runtime committed ff4307630f7985898341ea07360d030899957e43; scope only tool/related tests/own implementation. Old report SHA unchanged (38a15df00e1f3b16469279731495a64617b5db772fb8d4fec7c2b916306b14e5), src/config diff empty, CLI roots verified absent. HANDOFF/native tiny evidence ready; no further tests/merge.
