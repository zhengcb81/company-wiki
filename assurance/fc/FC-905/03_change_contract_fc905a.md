# FC-905-a Change Contract — 可信 capture 回执（producer 侧基础设施）

> Owner: company-wiki · Base triplet: revenue `b9994dc` / filing `959d04c` / wiki `fd4f50b`
> Dependencies: FC-904 (accepted) · 分拆批准：2026-08-11 用户批准 FC-905-a/b（runbook §10）
> FC-905-b（revenue/filing 消费侧去硬编码 + not_reviewed 阻断 + 篡改 mutation 套件）后续实施

## Intended behavior delta (observable)

The resolution envelope gains three trusted-evidence fields so consumers never
fabricate capture/safety counts:

- `prompt_injection_status` — from the document's **review receipt**
  (`documents.metadata_json["prompt_injection_review"]`): `not_detected` /
  `detected_and_ignored`, or the explicit `not_reviewed` when no receipt exists
  (never faked).
- `parser_calls` / `llm_calls` — from the **producer_events journal**
  (append-only, written by a SQLite trigger on artifact INSERT):
  count(event_type='parser') / count(event_type='llm') for the resolved
  document.  When no store is available → `None` (evidence absent, never 0).

## Components

1. **`producer_events` table + trigger** (store.py `_DDL`, idempotent):
   - table: event_id PK, document_id, artifact_role, producer_name,
     producer_version, event_type ('parser'|'llm'|'other'), created_at.
   - `CREATE TRIGGER IF NOT EXISTS trg_artifact_producer_event AFTER INSERT
     ON artifacts`: appends one event per artifact INSERT with the role→type
     mapping (normalized/sections→parser, summary/consumer_analysis→llm,
     else→other).  Zero producer-code changes; the journal cannot be bypassed.
2. **`prompt_injection.py`** (new): `record_prompt_injection_review(con,
   document_id, *, status, reviewer, evidence_sha256, now)` (writes the
   receipt into documents.metadata_json; validates status enum + reviewer
   non-empty + sha256 evidence) and `read_prompt_injection_review(store,
   document_id) -> dict | None` (None = not reviewed).
3. **`producer_events.py`** (new): `count_producer_events(store, document_id)
   -> {"parser_calls": int, "llm_calls": int}` (SELECT COUNT over the journal).
4. **`resolver.py`**: `ResolutionEnvelope` gains `prompt_injection_status`
   (default "not_reviewed"), `parser_calls`/`llm_calls` (default None);
   `build_resolution_envelope(..., store=None)` reads review + counts for the
   matched document when a store is provided (zero-write).
5. **CLI/close-gap wiring**: resolve/ensure/close-gap pass
   `store=catalog.store` to the envelope builder.

## Forbidden changes

- Faking `prompt_injection_status` (absent receipt must be `not_reviewed`).
- Claiming parser/llm counts without the journal (store absent → None, never 0).
- Touching producer code (normalizer/llm_summarizer/section_extractor) — the
  trigger journals without code changes.
- Any write in the resolve/envelope path (envelope reads only).

## Expected call-edge delta

- NEW production read paths: build_resolution_envelope → read_prompt_injection_review
  + count_producer_events (store-backed). Review receipt write via CLI (new
  `review-prompt-injection` command) or direct helper.

## Side-effect budget

| Effect | Budget |
|---|---|
| catalog writes (envelope path) | 0 |
| artifact INSERT-triggered journal rows | 1 per artifact INSERT (production producers) |
| external root writes | 0 |
| deletions | 0 |

## Rollback

`DROP TRIGGER trg_artifact_producer_event; DROP TABLE producer_events;`
plus revert commits (review receipts live in documents metadata — reversible
by rewrite).

## Diff budget

~4 touched/new source files + tests (≤350 lines). Exceeds → split further.
