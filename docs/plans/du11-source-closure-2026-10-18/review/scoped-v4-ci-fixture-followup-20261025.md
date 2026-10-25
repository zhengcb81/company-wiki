# Scoped v4 CI fixture correction — independent review

## Verdict

**PASS — no P0–P2 findings.** Read-only review; the reviewer did not execute tests or call providers.

## Exact binding

- Reviewed HEAD: `bc6cebf920d57d0c9c0d5221236a9cf7639dafef`
- `git diff --binary HEAD` SHA-256: `dab37e06abcd501dcfe978812a483bbadf0a5bdc2ce2876bbc174517f23a0d9f`

## Review notes

- The stale callback that asserted `narrative-model-request/6` and returned a v5 ranking response was replaced with the shared `source_grounded_scoped_reply`, matching the selector 0.9 v4 default and `/5` request schema.
- The original recovery assertions remain: exactly one initial POST; removal of the API key before recovery; no second POST; no duplicate reservation/attempt; unchanged charge of 92 tokens / 111 micro-USD; repeated read leaves budget, database bytes and original documents unchanged.
- The PWF correctly identifies the remote failure as a stale test fixture failing before the loopback server recorded a request. It does not present this as a proven production recovery defect, and real semantic quality/RF acceptance remain open.
