# Findings

Frozen W06 covers RC10 (missing primary publication evidence), RC11 (title-null source manifests and omitted title correction vocabulary), and RC28 (US FY26 annual local metadata gap, specific root unresolved). These are separate problems and require independent producer evidence.

The mFresh root currently contains CN-688012, HK-00700 and US-MSFT. The lane has performed no network/model calls and has not modified original bytes, catalogs or source/config files.

Real RC28: current local preparation tries five prior-year annuals for a FY2026 request. FY2021/FY2022 actual DEI uses unsupported `ixt:datemonthdayyearen`; its errors are incorrectly marked targeted and veto discovery. Removing this stage in a process-only experiment exposes a second 26-metadata-groups versus 16-original-candidates cap collision. Separating those concerns reaches the truthful no-matching-period outcome. See the exact three causal runs in `annual_gap_replay.json`.

RC11: all three real FY26 quarterly HTML head titles are exactly `10-Q`, but public title remains null because title is missing from the source fact correction vocabulary; form_type is also omitted despite having an existing assertion column.

RC10: current local originals prove document identity but no exact public event day. CN PDF production date, HK month/production dates and separate results release are not publication evidence for the exact source version. Keep unknown; no existing raw re-download is warranted by this finding.

`IMPLEMENTATION_HANDOFF.md` defines an exclusive common write set, request relevance contract, finite storage discovery abstraction and 18 planned TDD checks. Three owned TEMP catalogs were restored, all protected SHA/mtime checks match, zero external/model/download calls occurred.
