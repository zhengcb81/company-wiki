# W08-CWP-G2-REPLAY — reproducible summary → public read → RF consumption

Offline, synthetic, **zero paid calls** reproduction of the G2 chain:
canonical registration → finite narrative batch → public pathless read →
read-only RF consumption.

Report schema: `narrative-g2-replay/1`.

## Entry point

```bash
python -B tools/narrative_g2_replay/run.py \
    --rf-project <ABS_FIXED_RF_PROJECT> \
    --owned-root <ABS_NEW_WRITABLE_CONTAINER> \
    --out-root   <ABS_NEW_WRITABLE_CONTAINER>
```

- `--rf-project` — the fixed, read-only RF snapshot whose *public* reader is
  consumed. It must contain `scripts/narrative_source_preparation.py`.
- `--owned-root` — container for one uniquely named child created and removed
  by this run. Preexisting contents are preserved.
- `--out-root` — root for fresh `attempt-NNNN/` directories. An existing
  attempt is never overwritten.
- `--deadline-seconds` (default 180) — one absolute deadline for the batch.
- `--command-seconds` (default 30) — per-child-command bound.

Exit codes: `0` oracle PASS, `3` PARTIAL/UNKNOWN (honest product gap),
`1` oracle FAIL, `2` invalid record / refused to run.

Unit tests:

```bash
python -B -m pytest -q tests/unit/test_w08_narrative_g2_replay.py
```

## What really runs (no layer is mocked away)

| Stage | Real surface |
|---|---|
| Registration | `company_wiki.source_catalog.SourceCatalog.scan()` over the synthetic lake |
| Source identity | `SourceVersionReader.query_ref` / `describe_version` |
| Batch | `python -m company_wiki.automation.narrative_batch_cli` |
| Selection | the production selector `select_narrative_evidence` (v0.8.0) |
| Worker | the real finite AUTO worker / lease / generation / outbox machinery |
| Public read | `python -m company_wiki.source_catalog.narrative_transport_cli` |
| RF consumption | `scripts/narrative_source_preparation.py` from the fixed snapshot |

Only the **remote provider** is replaced: a loopback HTTP server on
`127.0.0.1` that returns a deterministic draft derived from the prompt's own
evidence. It never invents an economic fact. The request carries no real key
(`W08_G2_REPLAY_LOOPBACK_KEY`, a synthetic literal); child processes run with a
minimal, credential-free environment. No translation is performed.

## CaseSpec matrix and observed results

Synthetic originals: real text-layer PDFs (PyMuPDF) and real plain-text
transcripts. No format is faked — TXT is never converted to PDF. All content is
`synthetic: true` in its sidecar; no real company identity is claimed.

Observed on `122bbe3ba142979a2e478f886eb25de76edf2e00`:

| case | kind preserved | selection | locators | model POST |
|---|---|---|---|---|
| annual-report | `annual_report` | selected | 1 | 1 |
| half-year-report | `semi_annual_report` | selected | 1 | 1 |
| quarterly-report | `quarterly_report` | selected | 1 | 1 |
| prospectus | `prospectus` | selected | 2 | 1 |
| placement | `equity_offering_prospectus` | selected | 1 | 1 |
| convertible-bond | `convertible_bond_prospectus` | selected | 1 | 1 |
| ir-policy | `investor_relations` | `skipped_no_narrative` | 0 | 0 |
| call-txt-zh | `investor_call_transcript` | selected | 1 | 1 |
| call-txt-en | `investor_call_transcript` | selected | 2 | 1 |

`placement` and `convertible-bond` share one group but each still executes its
own typed request.

## What was observed (node C)

- **run 1**: `completed`, exit 0, **8** real loopback model POSTs.
- **run 2** (same run id, same version/spec/request): `completed`, exit 0,
  **0** new model POSTs; artifact pins identical — while still performing a
  fresh public read + locator verification.
- **Public reads**: 9/9 exit 0, body SHA equals the published pin, locators
  replayed against the original bytes.
- **RF consumption**: 9/9 reads OK through the fixed snapshot; 8 carried
  evidence, 1 (`ir-policy`) correctly carried none; language and period
  preserved; no gaps reported.
- **Cleanup**: owned container restored to its baseline, `remaining: []`.
- `provider_calls = 0`, `paid_usd = 0.0`.

Three separate facts are reported and never conflated: **read success**,
**whether a draft was supported** (selection/summary/quality status), and
**whether a real model call happened** (per-case POST counts).

## Known baseline failures (recorded, not fixed here)

Reproduced at the pinned base — 2 real W04 failures; see
`known_baseline_failures` in the report. Re-run this package on the repaired
W04 to compare the same CaseSpec matrix.

## Honesty boundaries

- `supplier_fixture: true` — synthetic, locally generated documents.
- `llm_semantic_quality: not_evaluated` — this package does not judge model
  output quality.
- `source_truth_verified` describes only what was verified locally
  (bytes/SHA/size/locator). Synthetic identity is **not** a real company.
- No production config, installation, CI, hook, or other lane was modified.


## ROOT observation upgrade (2026-10-12)

The tables above preserve the author's pinned-base observations. ROOT runs the
same CaseSpecs on the current integrated source; its receipt records actual
core/tool module hashes. Historical failures are marked `historical_not_retested`,
not falsely reported as failures reproduced on each new HEAD.

The runner now counts each source's actual loopback requests, requires the
public reader's real `replay_status=verified` and locator count, checks the fixed
operating sentence is selected, checks published claims cite actual spans and
exclude fixed boilerplate, and compares nonempty fiscal periods plus the cutoff
`2026-10-12` in RF's returned context. This is evidence binding, not supplier
semantic-quality certification; `needs_review` remains an observed quality.

Two extra **real native batches** register a separate synthetic successor TXT
(the old original stays byte-identical), then change `max_output_tokens` by one.
Each must call the model once and publish a changed exact pin which is freshly
read and replayed. Same-version reuse still must issue zero calls. Changing
model generation settings is not a claim that every selector-policy version was
tested. All child launches share the one deadline; no command starts after it.

Actual requests, batch stdout/stderr, public bundles/receipts, RF contexts and
loopback prompt/draft records are preserved in each attempt. Paths in the report
refer to these real files. ROOT archives them as one small compressed receipt
bundle and restores the whole independent test root. No original/company lake is
copied and no real credential is read. This remains a **manual major-node** tool,
not a new per-commit or CI requirement.
