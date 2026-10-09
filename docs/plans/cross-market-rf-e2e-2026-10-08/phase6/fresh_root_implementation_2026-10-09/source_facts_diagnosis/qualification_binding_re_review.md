# W06 company binding — final independent re-review

## Decision

**PASS for the frozen W06 source responsibility.** The previously reproduced wrong-company reuse is corrected at the shared CWP qualification owner. This is independent acceptance of this delivery, not a whole-company RF forecast or a whole-repository CI claim. MAIN owns integration, normal push and aggregate CI.

- Source commit: `90723304e4c7a0115f825bfee715f9568f2079f6`.
- Tested clean worktree head: `e8afcd26fe52953b4a3a560d713d5b09c844c8df` (subsequent changes are own-PWF documents only).
- Worktree: `C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki`.
- Independent evidence: [qualification_binding_re_review_receipt.json](qualification_binding_re_review_receipt.json).

The delivery manifest's **22 source/test files and 41 artifacts** matched their exact working-tree SHA-256 and sizes. All 22 source/test files also matched the pinned source commit, allowing only the normal Git LF → Windows checkout CRLF conversion. No other normalization was permitted. Literal Git-blob and checkout byte hashes differ for CRLF files; the receipt records both hashes and this check explicitly. Source/artifact bytes, Git head and clean status remained unchanged after controls.

## Original RED reproduced without changing it

The preserved `qualification_shared_re_review_reproduce.py` was run **unchanged**, SHA `ca78ffd2ce3e0eb09efcad06b7ca32437f8ae4e2d07baac9a058b44f577746b0`:

```text
python -X utf8 -B qualification_shared_re_review_reproduce.py --code-root C:/Users/郑曾波/.codex/worktrees/audit-provider-cause/company-wiki
```

It uses normal official-source import and source-fact APIs, an existing Acme/ACME identity with CIK 12345, B original with CIK 99999 and the standard official URL `https://www.sec.gov/Archives/edgar/data/99999/000009999926000007/original.htm`. No catalog/query mock or byte corruption makes the failure.

| Actual public entry | Previous delivery | This delivery |
|---|---|---|
| `SourceVersionReader.open_version`, `filing_reuse` | Returned B original for A | `blocked / primary_issuer_conflict` |
| `SourceVersionReader.verify_version`, `filing_reuse` | Verified B original for A | `blocked / primary_issuer_conflict` |
| `SourceResolver.resolve` | `reused_equivalent` | `blocked / primary_issuer_conflict` |
| `SourceAcquisitionService.ensure` | `reused` | `blocked / primary_issuer_conflict` |
| `AcquisitionCoordinator.stage_selected` | Reused existing B catalog source | `blocked / primary_issuer_conflict` |

**5/5 PASS**, exit 0, 1.931 s. Raw originals and assertion counts remained unchanged. Supplier discovery/fetch and network were forbidden and never needed. The import and catalog query remain provisional; a matching URL/body does not manufacture the company binding.

## Independent responsibility controls

The prior 28-control harness was retained in the new receipt, with its complete modifications recorded. Changes are limited to the corrected responsibility contract: use a standard 18-digit SEC accession URL; missing company binding permits exactly one real registered-company observation; complete proof forbids that observation; add complete-proof `prepare`. Old negative controls and old FAIL artifacts were not edited.

**29/29 independent controls PASS**, 7.095 s. Separately, **3 selected existing adjacent-proof cases PASS**, 1.75 s pytest time / 2.323 s subprocess time. The selected cases cover an absent or inconsistent issuer-record binding falling back to one real observation/parse, and a complete company proof still refusing contradictory current URL provenance.

| Responsibility | Independent result |
|---|---|
| Wrong raw CIK with A provenance; wrong FY; A labels with B URL/raw | All 15 public-entry negatives refuse with the named issuer/period conflict |
| Correct missing proof: reader/resolver | One target raw stream, zero historical raw streams, one source-identity observation, one same-buffer DEI parse |
| Correct complete proof: reader/resolver/prepare | One target raw stream, zero historical raw streams, zero identity observations, zero DEI parses |
| Existing consumed-byte budget | Prior 7 B preserved; final total 445 B = 438 B target + 7 B, for all five efficiency cases |
| Exhausted bytes, expired deadline, cancellation | Six reader/resolver controls preserve finite unavailable causes; no false `not_found` |
| Unknown original DEI scope | `blocked / fiscal_period_unresolved`, not invented readiness |
| Same unknown original, `preview` / `source_export` | Exact original bytes remain readable without forecast qualification |

The missing-proof `master=1` is the first registered-company binding observation, not a redundant approval or a consumer identity DTO. The complete original DEI/company proof retains `master=0 / parse=0 / one SHA stream`. Within an operation the same verified buffer and remaining budget are reused. Independent controls instrument actual function entries and physical target/history file opens; supplier and socket guards prevent accidental acquisition.

## Root repair and boundaries

The runtime repair changes `assertion_service.py` and `local_reconcile.py` relative to the rejected 4c delivery. `_proved_sec_issuer` restores only complete actual-original proof with matching SHA, field values, DEI locators, extraction method, consistent nonempty issuer-record binding and current company/market/security labels. Official URL/provider CIK is compared with this company binding. When binding is incomplete, the common owner observes the existing identity once, then validates actual DEI from the same byte buffer. Prepare reuses that observation for the existing writer and no longer reloads the master on a complete hit.

No new permission, human signing, ledger, SQL schema, SourceRef wire fields or consumer identity request was introduced. Source query stays DB-only and provisional. Preview/export retain byte/version responsibility. Non-SEC scope, real provider acquisition and whole-company research are outside this focused re-review.

## Isolation, cleanup and limits

Child runs used a whitelisted OS environment, `PYTHON_DOTENV_DISABLED=1`, no plugin autoload and no emitted environment values or credentials. All test originals, catalogs and configuration were synthetic and created in an exclusive TEMP environment. The initial `keep.bin` baseline was restored before removing that environment. Pytest relocated its effective basetemp for Windows path length; its cleanup log and an independent existence check both confirm that effective directory is absent. The preserved reproducer's own TEMP is also absent.

Production originals/config/catalog, installed skills, FF, RF, external Dayu and IQS were not modified. External calls and paid cost are zero. Previous `qualification_shared_re_review.md`, its receipt and its exact reproducer remain byte-for-byte unchanged.

The deliberately isolated pytest invocation emits one `asyncio_mode` configuration warning because the unrelated asyncio plugin is not loaded; all three selected tests passed. No new independent production MSFT replay or whole 269-test repetition was run here. The owner's frozen MSFT receipt and 269 PASS / 3 explicit skips are corroborating delivery evidence, not relabelled as this review's executions. MAIN can now integrate W06's complete 14-runtime-file / 8-test delta and run its normal aggregate verification.
