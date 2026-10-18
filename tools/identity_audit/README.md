# tools/identity_audit — P3 read-only identity audit

Read-only CLI that compares what an export-side request **claims** about exact
source versions with what the frozen read side actually returns: ref binding,
bytes, identity, period, availability, evidence-span grounding and unit
notation. It emits `identity-audit-receipt/1` and never mutates the catalog,
the raw originals, or any configuration.

Lane: `P3-IDENTITY-AUDIT` (parallel-packages-2026-10-18). Baseline `4045787f`.

## Entrypoint

```
python -m tools.identity_audit --config <catalog.yaml> --request <request.json> [--out <receipt.json>] [--pretty]
```

- Exactly **one JSON line** on stdout — canonical
  (`ensure_ascii=True, sort_keys=True, separators=(",", ":")`), LF-terminated.
  `--pretty` only affects the `--out` copy (content-equivalent, indented).
- Logs go to **stderr only**. Argument errors never print usage to stdout.
- `--out` is written through a temp file + `os.replace`; a directory target is
  refused (`blocked` / `invalid_argument`).
- Exit codes: `0` all applicable checks pass · `2` at least one check `fail`
  · `3` `blocked`/`unavailable`.

## Request (`identity-audit-request/1`)

```json
{
  "schema_version": "identity-audit-request/1",
  "source_refs": [{"document_id": "...", "source_id": "...", "content_sha256": "<64 lowercase hex>", "byte_size": 123, "mime_type": "text/plain", "schema_version": "2.0"}],
  "evidence_spans": [/* EvidenceSpan.to_dict() wire shapes, schema 1.0.0 */],
  "expect": {"market": "CN", "fiscal_year": 2026}
}
```

- `expect` keys are optional; a missing key means "no expectation". An
  explicit `null` means "expect unknown" and passes only against a real
  `null` observation.
- Unknown request/ref fields, a wrong schema version, an empty `source_refs`
  array, or malformed values ⇒ `blocked` receipt with `invalid_argument`.
- Limits (frozen): `source_refs ≤ 500`, `evidence_spans ≤ 5000`, request
  bytes ≤ 16 MiB (`limit_exceeded`), receipt bytes ≤ 16 MiB
  (`receipt_too_large`).
- Duplicate JSON keys, `NaN`/`Infinity`, or non-UTF-8 request bytes ⇒
  `blocked` / `invalid_json`.

## Receipt (`identity-audit-receipt/1`)

Shell: `schema_version`, `status` (`ok|partial|fail|blocked|unavailable`),
`generated_at` (UTC, second precision, `Z`), `inputs`
(`{path: {sha256, bytes}}` binding the config file, plus the request file
when run through the CLI), `counts`
(`checked/passed/failed/not_applicable/not_evaluated`), `limitations[]`,
`sources[]`.

Each source carries `checks` with the seven frozen checks: `ref`, `bytes`,
`identity`, `period`, `availability`, `spans` (array), `unit`. Per-check
statuses: `pass`, `fail`, `not_applicable`, `not_evaluated` (both with a
`reason`), plus `source_availability_unknown` for `availability` only.
Published error codes: `p3_ref_mismatch`, `p3_bytes_mismatch`,
`p3_span_ungrounded`, `p3_identity_conflict`, `p3_period_conflict`,
`p3_unit_mismatch`, `p3_availability_fabricated` (plus shared codes).

Decision rules worth restating (card §5.4):

- `bytes` recomputes SHA-256 over the verified buffer; the reader refuses
  tampered bytes and the audit surfaces that as `bytes.fail` +
  `p3_bytes_mismatch`.
- A numeric security code whose canonical width disagrees with its own
  declared market is an identity conflict; a market's width is never
  borrowed across markets.
- A non-null `published_date` with **no** availability evidence is honest
  unknown (`detail.date_provenance="unverified"`), not fabrication; the
  check fails only on `expect` conflicts or non-`YYYY-MM-DD` values. A null
  is never rewritten into a date.
- A span is grounded only for exact `text/plain` reads
  (`structured_value is null`, no page/table coordinates) whose `raw_text`
  equals the original at `[char_start, char_end)`; anything else is
  `not_applicable` (`not_groundable_shape`) or `p3_span_ungrounded`.
- Unit tokens are matched as notation with the frozen closed regexes; no
  token ⇒ `not_applicable` (`no_unit_token_in_span`), a claimed token that
  is not in the original ⇒ `p3_unit_mismatch`. No conversion, no currency
  fill-in, no magnitude inference.

## Read-only guarantees

- The catalog is opened exclusively through `ReadOnlyCatalogReader`
  (`file:...?mode=ro`, `PRAGMA query_only=ON`); the writable store is never
  constructed.
- The config file is read to bind `{sha256, bytes}` into `inputs`; nothing
  else on disk is touched. Tests prove this with byte-level before/after
  snapshots (including mtime) of the whole synthetic tree.
- No network, no LLM calls, no API-key reads, no downloads.

## Known limitations

- PDF/DOCX span offsets are not verified; only exact UTF-8 `text/plain`
  spans are.
- Card §5.4(5) names `schema_version`/`source_url`/`captured_at`, which the
  current availability evidence does not carry; the observed evidence dict is
  passed through verbatim (`source-availability-evidence/1`).
- Unit checking is notation-only (see above).

## Integration boundary

Do **not** wire this tool into the production worker or any CI gate unless
ROOT explicitly decides to. It is an audit lane deliverable, not a pipeline
dependency.
