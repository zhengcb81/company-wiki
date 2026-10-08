"""WU-1305: versioned reason taxonomy + privacy-safe metrics collector.

Every rejection/reuse/download/recompute carries a *registered* reason code
(snake_case, versioned by REASON_TAXONOMY_VERSION).  The collector aggregates
by root/route/adapter/version/role without ever recording company names,
document ids, or absolute paths — those are redacted by default (REDACT).

Telemetry export being off must not affect core behavior: the collector is
pure in-memory, append-only, and thread-safe; nothing raises when the
exporter is absent.

ZR-101 (stage taxonomy 2.0): on top of the flat v1.1 reason codes, every
registered reason is attributed to at least one of eight cross-repo stages
(identity, resolution, freshness, acquisition, safety, artifact, semantic,
consumer).  Stage events are validated fail closed: unknown codes/stages are
never silently recorded, and an N-1 consumer that only knows
reason-taxonomy-1.1 rejects a stage-taxonomy-2.0 event with a problems list
instead of crashing.
"""

from __future__ import annotations

import math
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# FROZEN N-1 FLAT TAXONOMY (do not bump when codes are added).
# tests/unit/test_stage_taxonomy.py pins this string as the N-1 compatibility contract
# ("N-1 compat: the v1.1 flat taxonomy constant is untouched") while the cross-repo
# event schema is `stage-taxonomy-2.0`; consumers of the flat taxonomy key off this
# value, so changing it is a cross-repo contract decision, NOT something a code
# addition may do on its own.  The registry itself is additive: new codes are appended
# (2026-09-15 added the 15 focus/admission codes that were previously invisible).
REASON_TAXONOMY_VERSION = "1.1"

# Canonical reason taxonomy (additive; codes are never removed, only
# deprecated) — kept in sync with admission/reuse/resolver/artifact codes.
REASONS: dict[str, str] = {
    # scan / admission
    "admitted": "candidate facts pass the profile gate",
    "identity_missing": "no canonical_entity_id or security_id",
    "kind_missing": "no document_kind",
    "period_missing": "no fiscal_year or period_end",
    "hash_missing": "no content_sha256",
    "content_hash_mismatch": "observed bytes differ from recorded hash",
    "status_not_active": "source_status != active",
    "policy_denied": "root policy does not authorize reuse",
    "non_filing_kind": "document kind is not a filing profile",
    "focus_policy_invalid_relative_path": "path traversal or absolute path",
    "focus_policy_no_allowed_category_evidence": "no allowed category evidence",
    # Focus/admission decisions that were emitted POSITIONALLY and were therefore
    # invisible to the FC-1301 gate until it was widened to AST (work package
    # fc1301-taxonomy-coverage; inventory: 17 code-like sites, 15 distinct codes).
    # Registered 2026-09-15 - additive, with the meaning the call sites give them.
    "focus_policy_explicit_document_kind": "metadata declares an allowed source document kind",
    "focus_policy_explicit_kind_not_allowed": "declared document_kind is neither regulatory_filing nor allowed",
    "focus_policy_announcement_or_notice": "title or path looks like an announcement/regulatory notice",
    "focus_policy_prospectus_keyword": "prospectus keyword in title or path",
    "focus_policy_call_transcript_keyword": "investor call transcript keyword in title or path",
    "focus_policy_strict_broker_evidence": "broker institution AND research-report semantics both present",
    "focus_policy_commentary_without_broker_evidence": "commentary/recap without strict broker evidence",
    "focus_policy_regulatory_form": "explicit regulatory form code (10-K/20-F/40-F, dayu FY/H1/H2)",
    "focus_policy_semi_annual_keyword": "semi-annual keyword in title or path",
    "focus_policy_quarterly_keyword": "quarterly keyword or Q1-Q4 form code",
    "focus_policy_annual_keyword": "annual keyword in title or path",
    "focus_policy_financial_report_keyword": "financial-report keyword, kind left as regulatory_filing",
    "focus_policy_investor_relations_keyword": "investor-relations keyword in title or path",
    "v2_profile_admitted": "candidate facts pass the v2 profile gate",
    "stale_gap_hash": "gap plan hash moved on since the binding was written",
    # reuse / latest / gap
    "download_suppressed": "reuse policy suppressed the download",
    "download_authorized": "gap plan authorized a download",
    "downloaded": "download executed once",
    "gap_not_required": "no gap to close for this period",
    "gap_authorization_expired": "download auth window expired",
    # resolver
    "exact_hit": "exact identity match resolved",
    "latest_selected": "latest-as-of handle selected",
    "latest_as_of": "latest historically eligible indexed source selected; bytes remain an open-time check",
    "no_local_match": "no indexed version satisfies the requested identity, period and publication cutoff",
    "multiple_local_matches": "multiple indexed source versions satisfy the local request",
    "one_local_match": "one indexed version satisfies the local request; bytes are not yet verified",
    "publication_date_unknown": "stored source version has no proven publication date",
    "acquisition_budget_required": "a provider execution request has no finite acquisition budget",
    "candidate_selected": "one candidate selected for the requested provider scope",
    "request_scope_allows_no_items_or_bytes": "requested provider scope has no usable item or byte allowance",
    "intra_group_repeat": "repeated narrative evidence within the same source group",
    "same_unit_repeat": "repeated narrative evidence from the same source unit",
    "maintenance_retired": "source was retired by explicit maintenance",
    "narrative_reader_unavailable": "narrative reader infrastructure is unavailable",
    "ambiguous_issuer": "token shared by multiple issuers",
    "entity_gate_rejected": "entity anchoring failed",
    # artifacts
    "artifact_selected": "valid artifact reused",
    "artifact_rejected": "artifact failed validation (reason in detail)",
    "recomputed": "artifact recompute planned",
    "stale_bundle": "snapshot mismatch invalidates the bundle",
    # ZR-502 homepage identity — verdict evidence codes
    "no_first_page_text": "no first-page text was extracted",
    "no_declared_identity_on_cover": "cover contradicts declared identity",
    "no_strong_cover_framing": "page is not recognizably a cover",
    # ZR-503 multi-entity attribution guard — verdict evidence codes
    "no_company_name_phrases": "no company-name phrase found in the text",
    # migration / bridge
    "legacy_bridge_hit": "legacy acquisition/dayu_meta container read",
    "shadow_diff": "v2 shadow read differed from legacy bridge",
    "migration_remaining": "sources still pending migration",
    "verified_v2_assertion": "verified v2 assertion read (legacy-visible)",
    # FC-1301 additions (1.1) — every emitted reason literal must be
    # registered; the audit gate below fails closed on unregistered codes.
    # adapters / acquisition
    "adapter_discovery_returned_multiple_candidates": "adapter saw >1 candidate",
    "adapter_discovery_returned_no_candidate": "adapter saw no candidates",
    "adapter_or_staging_failed": "adapter fetch or staging failed",
    "existing_catalog_source_reused_before_adapter": "catalog hit before adapter",
    "existing_catalog_source_reused_after_discovery": "catalog hit after discovery",
    "missing_source_downloaded_to_staging_pending_canonical_import": "staged download awaiting canonical import",
    "canonical_copy": "canonical writer copied bytes",
    "canonical_import_failed": "canonical import failed",
    "identity_conflict_no_download": "identity conflict suppresses download",
    "explicit_security_id_conflicts_with_verified_identity": "explicit id conflicts with verified identity",
    "download_required_but_not_allowed": "gap exists but download is not allowed",
    "only_sources_published_after_as_of_date": "all candidates publish after as-of",
    "no_existing_source_satisfies_request": "no catalog source satisfies the request",
    "reused_after_discovery": "catalog hit after provider discovery",
    # artifact binding gate
    "artifact_schema_unsupported": "artifact schema version unknown",
    "artifact_status_not_completed": "artifact status is not completed",
    "artifact_source_binding_mismatch": "artifact source does not match lineage",
    "artifact_hash_malformed": "artifact hash is not lowercase hex",
    "artifact_hash_mismatch": "artifact hash differs from bytes",
    "artifact_file_missing": "artifact file is missing on disk",
    "artifact_generator_unregistered": "generator not in GENERATOR_REGISTRY",
    "artifact_created_at_malformed": "created_at is not ISO-8601 Z",
    "artifact_created_at_future": "created_at is in the future",
    "artifact_path_outside_allowed_root": "artifact path outside allowed roots",
    "artifact_role_unknown": "artifact role not in KNOWN_ARTIFACT_ROLES",
    "artifact_source_sha_missing": "artifact source sha column is empty (fail-closed)",
    "artifact_source_sha_mismatch": "artifact source sha differs from source",
    "artifact_source_as_of_future": "artifact source as-of is in the future",
    "artifact_superseded_by_newer": "a newer artifact exists for the role",
    # worker / control plane
    "unhandled_exception": "worker cycle hit an unhandled exception",
    "cycle_failed": "worker cycle failed",
    "productive_cycle": "worker cycle made progress",
    "already_running": "operation already running",
    "control_request": "control-plane request processed",
    "persistent_pause": "worker paused persistently",
    "semantic_review_only": "semantic review path only",
    "clean_exit": "process exited cleanly",
    "no_output": "no output produced",
    # latest / gap
    "gap_already_closed": "gap closed by an earlier transaction",
    "gap_closed_by_concurrent": "gap closed by a concurrent transaction",
    # documents / scanning
    "document_not_in_catalog": "document missing from catalog",
    "source_not_in_catalog": "source missing from catalog",
    "no_original_location": "document has no original_primary location",
    "empty_text": "source text is empty",
    "unsupported_document": "document kind unsupported",
    "cannot_parse_yaml": "yaml payload cannot be parsed",
    "unexpected_path_pattern": "path pattern outside expectations",
    "focus_policy_orphan_sidecar": "sidecar without its primary file",
    # identity resolution + source-reuse decisions that were emitted POSITIONALLY and
    # stayed invisible until the FC-1301 gate resolved callees by ALL their definitions
    # (B-VR1301-01, P0: bare-name first-definition-wins mapped them onto the wrong
    # parameter list, so a brand-new code at close_gap.py:256 passed the gate GREEN).
    # Registered 2026-09-15/16 with the meaning their call sites give them.
    "one_verified_exact_identity": "exactly one verified exact identity candidate",
    "multiple_verified_exact_identities": "more than one verified exact identity candidate",
    "exact_identity_conflicts_with_market_or_exchange_hint": "exact identity contradicts the market/exchange hint",
    "no_verified_identity_candidate": "no identity candidate could be verified",
    "one_unique_strong_fuzzy_identity": "exactly one unique strong fuzzy identity match",
    "fuzzy_candidates_require_user_selection": "several fuzzy identity candidates need a human choice",
    "one_existing_source_matches_provider_identity": "exactly one source matches the provider identity",
    "latest_existing_source_matches_provider_identity": "several match; latest_as_of selected one by provider identity",
    "multiple_existing_sources_match_provider_identity": "several sources match the provider identity; ambiguous",
    "one_existing_source_satisfies_semantic_request": "exactly one source satisfies the semantic request",
    "latest_existing_source_satisfies_semantic_request": "several satisfy; latest_as_of selected one",
    "multiple_existing_sources_match_semantic_request": "several sources satisfy the semantic request; ambiguous",
    "identity_mismatch_market_or_security_id": "explicit market or security_id identity conflict",
    "matching_sources_have_unknown_published_date": "matching sources carry no published date to pick a latest",
    # gap-plan policy binding (close_gap)
    "no_runtime_policy": "no runtime policy snapshot could be loaded; fail closed",
    "stale_policy_hash": "policy snapshot hash differs from the binding's",
    # llm pipeline
    "llm_deferred": "llm summary deferred",
    "llm_global_failure": "llm pipeline failed globally",
    "fiscal_year": "fiscal-year filter applied",
    # Provider-use policy, transcript admission and source-export refusals.
    # These remain additive to frozen reason-taxonomy 1.1.
    "action_not_permitted": "provider policy does not permit the requested action",
    "allocated_staging_root_unavailable": "the authorized staging root is unavailable",
    "authorization_request_mismatch": "download authorization belongs to another request",
    "candidate_identity_mismatch": "provider candidate does not match requested identity",
    "candidate_security_identity_missing": "provider candidate lacks a verified security identity",
    "download_authorization_rejected": "download authorization failed validation",
    "download_not_authorized": "the requested provider download is not authorized",
    "download_receipt_from_future": "download receipt timestamp is in the future",
    "download_receipt_http_status_not_successful": "provider response was not a successful HTTP response",
    "download_receipt_identity_mismatch": "download receipt does not match the authorized identity",
    "downloaded_bytes_exceed_authorized_cap": "download exceeded the authorized byte cap",
    "export_scope_mismatch": "requested export scope does not match the selected source",
    "export_unavailable": "source export could not be produced",
    "invalid_date": "request date is malformed or outside policy",
    "invalid_download_receipt": "download receipt is malformed",
    "invalid_fetch_timestamp": "provider fetch timestamp is malformed",
    "invalid_now": "the supplied policy evaluation time is invalid",
    "invalid_request": "source export request is malformed",
    "invalid_request_or_candidate": "request or provider candidate is malformed",
    "invalid_source_url": "source URL is invalid or outside provider policy",
    "invalid_staging_root": "staging root is invalid or outside the allocated root",
    "missing_download_authorization": "an explicit download authorization is required",
    "staged_file_not_regular": "staged response is not a regular file",
    "staged_file_outside_allocated_root": "staged response escaped its allocated root",
    "staged_file_sha256_mismatch": "staged response hash differs from its receipt",
    "staged_file_size_mismatch": "staged response size differs from its receipt",
    "staged_file_unavailable": "staged response is unavailable",
    "unsupported_transcript_mime_type": "transcript response MIME type is not allowed",
}

_PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/][^;,\s]+|[\\/][^;,\s]*[\\/][^;,\s]+")

REDACT = "<redacted>"

# ---------------------------------------------------------------------------
# I-14-C: credential-shaped values in free-form text (exception messages).
#
# Before this, the only content-aware cleaner was ``_PATH_PATTERN`` and it was
# applied to ``StageEvent.detail`` only; ``str(exc)`` reached both
# ``worker_process_events.jsonl`` and the CLI's stderr envelope verbatim.
#
# r3 (F-I14C-07): the key is matched by a SINGLE-PASS SCANNER, not by a regex with
# nested quantifiers.  The r2 expression
# ``(?:[A-Za-z0-9]+[_-])*<atom>(?:[_-][A-Za-z0-9]+)*`` was quadratic in the number
# of ``_``/``-`` separated segments (measured: 8000 segments -> 8.9 s, 16000 ->
# >20 s), and a "linear key candidate" regex turns out to be quadratic too
# (``[A-Za-z0-9_-]+`` still backtracks once per start position when the value
# cannot match: measured 8000 -> 2.7 s, 16000 -> >20 s).  The scanner visits every
# character once, so cost is O(len(text)).
#
# A key is credential-shaped when, split on ``_``/``-``, one of its components is a
# single atom (token, secret, password, passwd, pwd, apikey, credential,
# passphrase) or two adjacent components form a known pair (api_key, access_key,
# private_key, secret_key, auth_token, access_token, session_token, bot_token,
# refresh_token, id_token, api_token, client_secret).  This covers env-var style
# names such as GITHUB_TOKEN, SLACK_BOT_TOKEN, AWS_SECRET_ACCESS_KEY and
# AWS_ACCESS_KEY_ID.  A value is redacted only when such a key precedes it; no
# claim is made about a secret with no credential-like key anywhere near it.
# ---------------------------------------------------------------------------

_SINGLE_ATOMS = frozenset({
    "token",
    "secret",
    "password",
    "passwd",
    "pwd",
    "apikey",
    "credential",
    "passphrase",
})

_PAIR_ATOMS = frozenset({
    ("api", "key"),
    ("api", "token"),
    ("access", "key"),
    ("access", "token"),
    ("secret", "key"),
    ("private", "key"),
    ("auth", "token"),
    ("session", "token"),
    ("bot", "token"),
    ("refresh", "token"),
    ("id", "token"),
    ("client", "secret"),
})

_KEY_COMPONENT_SPLIT = re.compile(r"[_-]+")
_KEY_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789_-"
)
_ASSIGNMENT_CHARS = frozenset(":=")
_INLINE_SPACE = frozenset(" \t")
# same value semantics as the r1/r2 regex: a quoted string (same line), or a run of
# non-delimiter tokens (delimiters: any whitespace, , ; & " ' |)
_VALUE_STOP_CHARS = frozenset(",;&\"'|")
_QUOTES = frozenset("\"'")


def key_is_credential(key: str) -> bool:
    """True when *key* (as written in the text) is a credential-shaped name."""
    parts = [part for part in _KEY_COMPONENT_SPLIT.split(key.lower()) if part]
    if not parts:
        return False
    if any(part in _SINGLE_ATOMS for part in parts):
        return True
    return any(
        (parts[index], parts[index + 1]) in _PAIR_ATOMS
        for index in range(len(parts) - 1)
    )


# authorization / bearer: redact everything after the key (scheme included, so a
# scheme-less "Authorization: <value>" cannot slip through).  These keys are
# fixed literals, so the pattern has no nested quantifier over the KEY and stays
# linear; its timing is measured in r3/bench_*.json alongside the scanner.
_LEFT_ANCHOR = r"(?<![A-Za-z0-9])"

# A value is a quoted string, or - since I-14-D narrowed the r1 greedy rule - a
# BOUNDED run of non-delimiter tokens (delimiters: any whitespace, , ; & " ' |):
#   _BARE_VALUE      ONE token: the assignment scanner stops at ANY whitespace,
#                    including newlines (C13: the r1 rule crossed newlines and
#                    deleted the whole remaining diagnostic block, 112 in -> 34 out).
#   _AUTH_BARE_VALUE the authorization/bearer value: tokens joined by INLINE
#                    whitespace only, so it still carries one scheme word
#                    ("Bearer <secret>", "token <secret>") but can no longer
#                    swallow a multi-line diagnostic block either.
# Declared residual: a bare secret containing whitespace is redacted only up to
# its first token ("password: iron steel" -> "password: <redacted> steel");
# quote the value ("password: 'iron steel'") for full coverage.
_QUOTED_VALUE = r"\"[^\"\r\n]*\"|'[^'\r\n]*'"
_BARE_VALUE = r"[^\s,;&\"'|]+"
_VALUE = r"(?P<value>" + _QUOTED_VALUE + r"|" + _BARE_VALUE + r")"
_AUTH_BARE_VALUE = r"[^\s,;&\"'|]+(?:[ \t]+[^\s,;&\"'|]+)*"

# A value may still cross line breaks, but only behind one PRE-BREAK TOKEN.  That
# token has been widened four times, each time because a measured family leaked:
#   r2  a nine-word enumeration of scheme words (F-REV-R2-01: coverage was exactly
#       as wide as the list);
#   r3  one RFC 7235 scheme token, `[A-Za-z]...` (F-REV-R3-01: the after-break
#       quoted alternatives carried an optional-CR form inside a character class,
#       where `?` is a literal member of the negated set);
#   r4  the full RFC 7230 tchar class (F-REV-R3-04: a non-letter-initial scheme
#       leaked where the base tree redacted);
#   r5  the VALUE-TOKEN class (F-REV-R4-05: a token containing a non-tchar character,
#       e.g. `Bo?t`, leaked too) -- but that was a SWAP, not a widening: it closed `?`
#       and re-opened `&`, `'` and `|`, which r4 had redacted (F-REV-R5-01);
#   r6  ANY NON-WHITESPACE RUN, `[^\s]+`.
# Every widening before r6 was judged by "does the character that was pointed at now
# pass", which is only one of the two differences that matter.  The criterion is BOTH:
# what the new class closes that the old one did not, AND what it re-opens that the old
# one caught.  Swept over every printable ASCII at this position, `[^\s]+` closes every
# character r4 or r5 closed and every character either of them leaked, EXCEPT the space --
# and a space here means the value is a multi-token run, which is the registered OPEN
# shape below, not a token-class question at all.
# A wrapped header (`Authorization: Bearer` then the secret on the next line) or an
# RFC-7230 obs-fold puts the secret on a line that carries no `key=` prefix, so once
# the pre-break token alone is consumed neither this pattern nor the assignment
# scanner can see it.  Fail CLOSED: after that token and one or more line breaks (a
# blank line included), the next token - or a quoted string reached through the same
# break run - is redacted.  Measured as F-REV-D-01 / F-REV-R2-01 / F-REV-R3-01:
# without this branch the full credential is persisted in the append-only event log.
# Deliberate, registered cost (F-REV-R2-02): it cannot tell a wrapped credential from
# a diagnostic key, so `Authorization: Bearer` + newline DELETES `doc=17`.  The
# breaks are consumed by the match; the indentation and the keys on the lines AFTER
# the redacted one are not.
# One shape stays OPEN and is registered rather than hidden: a TWO-token value that
# then wraps (`Authorization: Bearer abc` + newline + secret) -- the space is exactly
# what a non-whitespace run stops at.  Closing it needs the whole first line consumed
# as a run of tokens (spaces included), which deletes `doc=17` from
# `Authorization: Bearer <marker>` + newline + `doc=17` + newline + `stage=` -
# reproduced in `_r3_design_reprobe_20260922/`.  The companion that reproduction
# names, `r3_fix_record.md`, was never written and is deliberately NOT substituted
# for; the reproduction is where the substance lives.
_AUTH_PREBREAK_TOKEN = r"[^\s]+"
_AUTH_SCHEME_SPLIT = (r"(?:" + _AUTH_PREBREAK_TOKEN + r")[ \t]*"
                      r"(?:(?:\r?\n)[ \t]*)+"
                      r"(?:" + _AUTH_BARE_VALUE + r"+|\"[^\"\r\n]*\"|'[^'\r\n]*')")
_AUTH_PATTERN = re.compile(
    r"(?i)(?P<key>" + _LEFT_ANCHOR + r"authorization\s*[:=]\s*|"
    + _LEFT_ANCHOR + r"bearer\s+)(?P<value>" + _QUOTED_VALUE + r"|" + _AUTH_SCHEME_SPLIT + r"|" + _AUTH_BARE_VALUE + r")"
)

# key=value / key: value forms are handled by `_redact_assignments` (single-pass
# scanner), NOT by a regex: see the F-I14C-07 note at the top of this block.

MAX_REDACTED_MESSAGE_CHARS = 200


def redact_text(text: Any) -> Any:
    """Replace credential-shaped values in free-form *text* with ``REDACT``.

    Content-aware counterpart of ``_PATH_PATTERN`` for text that is not a path:
    exception messages, CLI error envelopes and any future free-form field.
    Never raises; non-strings pass through unchanged.  Redaction happens
    *before* any truncation, so a length cut can never be the only protection.

    Cost is O(len(text)): one regex pass with fixed literals for
    ``authorization``/``bearer``, then one scanner pass over the assignment
    separators.  No nesting-dependent quantifier sees the message.
    """
    if not isinstance(text, str) or not text:
        return text
    redacted = _AUTH_PATTERN.sub(lambda m: m.group("key") + REDACT, text)
    return _redact_assignments(redacted)


# Complexity ratchet (FC-1204, owner §四十二 裁定一, 2026-09-27): split only;
# behaviour unchanged.  `_redact_assignments` was 27 (frozen 6): the key walk,
# the value walk and the quote handling are separate top-level functions now,
# and the dispatcher keeps every redaction branch — no redaction rule dropped.
def _redact_assignments(text: str) -> str:
    """Single pass over ``key = value`` / ``key: value`` forms.

    For every ``:``/``=`` the scanner walks back over whitespace and key characters,
    validates the key against the atom tables and, on a match, replaces the value.
    A rejected key does NOT consume the rest of the assignment, so a later genuine
    credential pair in the same text is still redacted (e.g. a `url=...?token=...`
    or `cmd: --token=...` shape, which the previous regex skipped).
    """
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char not in _ASSIGNMENT_CHARS:
            out.append(char)
            index += 1
            continue

        if not _credential_key_before_separator(text, index):
            out.append(char)
            index += 1
            continue

        # the value: a quoted string, or a run of non-delimiter tokens
        value_start = _assignment_value_start(text, index + 1)
        value_end = _assignment_value_end(text, value_start)
        if value_end <= value_start:
            out.append(char)
            index += 1
            continue

        # Everything before `index` is already in `out`: the loop emitted the key and
        # any whitespace between the key and the separator one character at a time.
        # Only the separator, the whitespace after it and the value remain to be written.
        # (F-I14C-08: re-appending the key here duplicated it, e.g. `tokentoken=<redacted>`.)
        out.append(char)                           # the separator
        out.append(text[index + 1:value_start])    # whitespace after the separator
        out.append(REDACT)
        index = value_end
    return "".join(out)


def _credential_key_before_separator(text: str, separator_at: int) -> bool:
    key_end = _scan_left_over(text, separator_at, _INLINE_SPACE)
    key_start = _scan_left_over(text, key_end, _KEY_CHARS)
    return _is_credential_key(text, key_start, key_end)


def _scan_left_over(text: str, cursor: int, allowed: frozenset[str]) -> int:
    while cursor > 0 and text[cursor - 1] in allowed:
        cursor -= 1
    return cursor


def _is_credential_key(text: str, key_start: int, key_end: int) -> bool:
    if key_start > 0 and text[key_start - 1] in _KEY_CHARS:
        return False
    key = text[key_start:key_end]
    return bool(key and key_is_credential(key))


def _assignment_value_start(text: str, cursor: int) -> int:
    while cursor < len(text) and text[cursor] in _INLINE_SPACE:
        cursor += 1
    return cursor


def _assignment_value_end(text: str, value_start: int) -> int:
    if value_start < len(text) and text[value_start] in _QUOTES:
        closing = _find_closing_quote(text, value_start)
        if closing == -1:  # unterminated quote: redact the tail
            return len(text)
        return closing + 1
    return _unquoted_assignment_end(text, value_start)


def _unquoted_assignment_end(text: str, value_start: int) -> int:
    # I-14-D (C13): consume one token, preserving the next diagnostic line.
    cursor = value_start
    while (cursor < len(text)
           and text[cursor] not in _VALUE_STOP_CHARS
           and not text[cursor].isspace()):
        cursor += 1
    return cursor


def _find_closing_quote(text: str, quote_at: int) -> int:
    quote = text[quote_at]
    cursor = quote_at + 1
    while cursor < len(text) and text[cursor] != quote:
        if text[cursor] in "\r\n":
            return -1
        cursor += 1
    return cursor if cursor < len(text) else -1


def redact_and_truncate(text: Any, limit: int = MAX_REDACTED_MESSAGE_CHARS) -> Any:
    """``redact_text`` first, then truncate to *limit* characters."""
    redacted = redact_text(text)
    if not isinstance(redacted, str):
        return redacted
    return redacted[:limit]


def exception_cause_types(exc: BaseException) -> list[str]:
    """Exception class names along the ``__cause__``/``__context__`` chain.

    Only the *type names* are reported as diagnostics; no cause message is
    returned, so a credential inside a nested cause cannot be persisted by
    accident (the nested message itself is still redacted by callers that
    choose to render it).
    """
    names: list[str] = []
    seen: set[int] = set()
    current = exc
    while (nxt := _next_unseen_cause(current, seen)) is not None:
        seen.add(id(nxt))
        names.append(type(nxt).__name__)
        current = nxt
    return names


def _next_unseen_cause(
    current: BaseException, seen: set[int]
) -> BaseException | None:
    nxt = current.__cause__ or current.__context__
    if nxt is None or id(nxt) in seen:
        return None
    return nxt


def validate_reason(code: str) -> bool:
    """Fail closed: only registered codes may be recorded."""
    return code in REASONS


# ---------------------------------------------------------------------------
# ZR-101: cross-repo stage taxonomy 2.0 (additive over the flat v1.1 codes).
# Every v1.1 reason code is attributed to >=1 of the eight canonical stages;
# nothing in REASONS is renamed or removed, so an N-1 consumer that only
# knows reason-taxonomy-1.1 keeps working and rejects 2.0 events gracefully.
# ---------------------------------------------------------------------------
STAGE_TAXONOMY_VERSION = "2.0"
STAGE_TAXONOMY_SCHEMA = "stage-taxonomy-2.0"


class CrossRepoStage(str, Enum):
    """The eight cross-repo pipeline stages, in canonical order.

    Members are named by their canonical snake_case stage name and carry
    that same snake_case string as their value (str, Enum) — e.g.
    ``CrossRepoStage.identity.value == "identity"``.
    """

    identity = "identity"
    resolution = "resolution"
    freshness = "freshness"
    acquisition = "acquisition"
    safety = "safety"
    artifact = "artifact"
    semantic = "semantic"
    consumer = "consumer"


_REGISTERED_STAGES = frozenset(stage.value for stage in CrossRepoStage)

# Attribution rules (documented for cross-repo consistency — revenue-forecast
# and filing-fetch consume this map in later cards):
#   identity    — entity/security identity + admission profile gates
#   resolution  — matching/disambiguation of issuer/handle/source
#   freshness   — as-of date, period, gap analysis, timeliness
#   acquisition — download/fetch/staging/canonical copy of bytes
#   safety      — prompt-safety vocabulary (none registered yet; reserved)
#   artifact    — artifact schema/hash/binding/status + path-policy checks
#   semantic    — content/meaning-level decisions
#   consumer    — downstream consumption: recompute, migration, legacy bridge
STAGES_BY_REASON: dict[str, tuple[str, ...]] = {
    # identity
    "admitted": ("identity",),
    "identity_missing": ("identity",),
    "kind_missing": ("identity",),
    "entity_gate_rejected": ("identity",),
    "identity_conflict_no_download": ("identity",),
    "explicit_security_id_conflicts_with_verified_identity": ("identity",),
    # resolution
    "exact_hit": ("resolution",),
    "latest_selected": ("resolution",),
    "latest_as_of": ("resolution", "freshness"),
    "no_local_match": ("resolution",),
    "multiple_local_matches": ("resolution",),
    "one_local_match": ("resolution",),
    "ambiguous_issuer": ("resolution",),
    "existing_catalog_source_reused_before_adapter": ("resolution",),
    "existing_catalog_source_reused_after_discovery": ("resolution",),
    "reused_after_discovery": ("resolution",),
    # freshness
    "period_missing": ("freshness",),
    "gap_not_required": ("freshness",),
    "gap_authorization_expired": ("freshness",),
    "only_sources_published_after_as_of_date": ("freshness",),
    "no_existing_source_satisfies_request": ("freshness",),
    "gap_already_closed": ("freshness",),
    "gap_closed_by_concurrent": ("freshness",),
    "fiscal_year": ("freshness",),
    "publication_date_unknown": ("freshness",),
    # acquisition
    "download_suppressed": ("acquisition",),
    "download_authorized": ("acquisition",),
    "downloaded": ("acquisition",),
    "adapter_discovery_returned_multiple_candidates": ("acquisition",),
    "adapter_discovery_returned_no_candidate": ("acquisition",),
    "adapter_or_staging_failed": ("acquisition",),
    "missing_source_downloaded_to_staging_pending_canonical_import": ("acquisition",),
    "canonical_copy": ("acquisition",),
    "canonical_import_failed": ("acquisition",),
    "download_required_but_not_allowed": ("acquisition",),
    "no_original_location": ("acquisition",),
    "acquisition_budget_required": ("acquisition",),
    "candidate_selected": ("resolution", "acquisition"),
    "request_scope_allows_no_items_or_bytes": ("acquisition",),
    # safety — no registered codes yet (stage reserved for prompt-safety)
    # artifact
    "hash_missing": ("artifact",),
    "content_hash_mismatch": ("artifact",),
    "focus_policy_invalid_relative_path": ("artifact",),
    "artifact_selected": ("artifact",),
    "artifact_rejected": ("artifact",),
    "stale_bundle": ("artifact",),
    "artifact_schema_unsupported": ("artifact",),
    "artifact_status_not_completed": ("artifact",),
    "artifact_source_binding_mismatch": ("artifact",),
    "artifact_hash_malformed": ("artifact",),
    "artifact_hash_mismatch": ("artifact",),
    "artifact_file_missing": ("artifact",),
    "artifact_generator_unregistered": ("artifact",),
    "artifact_created_at_malformed": ("artifact",),
    "artifact_created_at_future": ("artifact",),
    "artifact_path_outside_allowed_root": ("artifact",),
    "artifact_role_unknown": ("artifact",),
    "artifact_source_sha_missing": ("artifact",),
    "artifact_source_sha_mismatch": ("artifact",),
    "artifact_source_as_of_future": ("artifact",),
    "artifact_superseded_by_newer": ("artifact",),
    "unexpected_path_pattern": ("artifact",),
    "focus_policy_orphan_sidecar": ("artifact",),
    "maintenance_retired": ("resolution", "artifact"),
    # STAGE PLACEMENT CORRECTED 2026-09-16 (B-VR1301-03): the first registration put the
    # 13 focus_policy_* decision codes under "artifact", contradicting this map's own
    # rules - their sibling focus_policy_no_allowed_category_evidence is "semantic"
    # (they decide the document KIND from title/path/form evidence), v2_profile_admitted
    # mirrors "admitted" (identity), and stale_gap_hash mirrors gap_not_required /
    # gap_authorization_expired / gap_already_closed (freshness).  A wrong stage is not
    # cosmetic: record_stage_event drops mismatched events fail-closed.
    "focus_policy_explicit_document_kind": ("semantic",),
    "focus_policy_explicit_kind_not_allowed": ("semantic",),
    "focus_policy_announcement_or_notice": ("semantic",),
    "focus_policy_prospectus_keyword": ("semantic",),
    "focus_policy_call_transcript_keyword": ("semantic",),
    "focus_policy_strict_broker_evidence": ("semantic",),
    "focus_policy_commentary_without_broker_evidence": ("semantic",),
    "focus_policy_regulatory_form": ("semantic",),
    "focus_policy_semi_annual_keyword": ("semantic",),
    "focus_policy_quarterly_keyword": ("semantic",),
    "focus_policy_annual_keyword": ("semantic",),
    "focus_policy_financial_report_keyword": ("semantic",),
    "focus_policy_investor_relations_keyword": ("semantic",),
    "v2_profile_admitted": ("identity",),
    "stale_gap_hash": ("freshness",),
    # the 16 codes B-VR1301-01 found still invisible (same placement rules: identity
    # resolution -> identity, reuse decisions -> resolution, policy binding -> freshness)
    "one_verified_exact_identity": ("identity",),
    "multiple_verified_exact_identities": ("identity",),
    "exact_identity_conflicts_with_market_or_exchange_hint": ("identity",),
    "no_verified_identity_candidate": ("identity",),
    "one_unique_strong_fuzzy_identity": ("identity",),
    "fuzzy_candidates_require_user_selection": ("identity",),
    "identity_mismatch_market_or_security_id": ("identity",),
    "one_existing_source_matches_provider_identity": ("resolution",),
    "latest_existing_source_matches_provider_identity": ("resolution",),
    "multiple_existing_sources_match_provider_identity": ("resolution",),
    "one_existing_source_satisfies_semantic_request": ("resolution",),
    "latest_existing_source_satisfies_semantic_request": ("resolution",),
    "multiple_existing_sources_match_semantic_request": ("resolution",),
    "matching_sources_have_unknown_published_date": ("freshness",),
    "no_runtime_policy": ("freshness",),
    "stale_policy_hash": ("freshness",),
    # semantic
    "non_filing_kind": ("semantic",),
    "focus_policy_no_allowed_category_evidence": ("semantic",),
    "semantic_review_only": ("semantic",),
    "empty_text": ("semantic",),
    "unsupported_document": ("semantic",),
    "cannot_parse_yaml": ("semantic",),
    "llm_deferred": ("semantic",),
    "llm_global_failure": ("semantic",),
    "intra_group_repeat": ("semantic",),
    "same_unit_repeat": ("semantic",),
    # ZR-502 homepage identity — content-level verdict evidence
    "no_first_page_text": ("semantic",),
    "no_declared_identity_on_cover": ("semantic",),
    "no_strong_cover_framing": ("semantic",),
    # ZR-503 multi-entity attribution guard — content-level verdict evidence
    "no_company_name_phrases": ("semantic",),
    # consumer
    "status_not_active": ("consumer",),
    "policy_denied": ("consumer",),
    "recomputed": ("consumer",),
    "legacy_bridge_hit": ("consumer",),
    "shadow_diff": ("consumer",),
    "migration_remaining": ("consumer",),
    "verified_v2_assertion": ("consumer",),
    "unhandled_exception": ("consumer",),
    "cycle_failed": ("consumer",),
    "productive_cycle": ("consumer",),
    "already_running": ("consumer",),
    "control_request": ("consumer",),
    "persistent_pause": ("consumer",),
    "clean_exit": ("consumer",),
    "no_output": ("consumer",),
    "document_not_in_catalog": ("consumer",),
    "source_not_in_catalog": ("consumer",),
    "narrative_reader_unavailable": ("artifact", "consumer"),
    # Provider-use policy / transcript acquisition and source-export stages.
    "action_not_permitted": ("safety",),
    "allocated_staging_root_unavailable": ("acquisition", "safety"),
    "authorization_request_mismatch": ("acquisition", "safety"),
    "candidate_identity_mismatch": ("identity",),
    "candidate_security_identity_missing": ("identity",),
    "download_authorization_rejected": ("acquisition", "safety"),
    "download_not_authorized": ("acquisition", "safety"),
    "download_receipt_from_future": ("freshness",),
    "download_receipt_http_status_not_successful": ("acquisition",),
    "download_receipt_identity_mismatch": ("identity", "acquisition"),
    "downloaded_bytes_exceed_authorized_cap": ("acquisition", "safety"),
    "export_scope_mismatch": ("consumer",),
    "export_unavailable": ("artifact", "consumer"),
    "invalid_date": ("freshness",),
    "invalid_download_receipt": ("acquisition",),
    "invalid_fetch_timestamp": ("freshness", "acquisition"),
    "invalid_now": ("freshness",),
    "invalid_request": ("consumer",),
    "invalid_request_or_candidate": ("identity", "acquisition"),
    "invalid_source_url": ("acquisition", "safety"),
    "invalid_staging_root": ("acquisition", "safety"),
    "missing_download_authorization": ("acquisition", "safety"),
    "staged_file_not_regular": ("safety", "artifact"),
    "staged_file_outside_allocated_root": ("safety", "artifact"),
    "staged_file_sha256_mismatch": ("artifact",),
    "staged_file_size_mismatch": ("artifact",),
    "staged_file_unavailable": ("artifact",),
    "unsupported_transcript_mime_type": ("safety", "artifact"),
}


def stage_sequence() -> tuple[CrossRepoStage, ...]:
    """Canonical cross-repo stage order (taxonomy 2.0)."""
    return tuple(CrossRepoStage)


def is_registered_stage(stage: str) -> bool:
    """True when *stage* is one of the eight canonical stage names."""
    return stage in _REGISTERED_STAGES


def stages_for_reason(code: str) -> tuple[str, ...]:
    """Attributed stages for a registered reason code (canonical order).

    Fail closed: unknown codes raise ValueError instead of being silently
    attributed.
    """
    if code not in REASONS:
        raise ValueError(f"unknown reason code: {code!r}")
    return STAGES_BY_REASON[code]


def _utc_now_iso() -> str:
    """Current UTC instant as ISO-8601 with a trailing ``Z``."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class StageEvent:
    """One stage-attributed cross-repo event (stage-taxonomy-2.0).

    ``detail`` is sanitized on validation: path-like patterns are redacted
    to ``REDACT`` (never rejected).  ``emitted_at_utc`` defaults to the
    current UTC instant.
    """

    schema_version: str = STAGE_TAXONOMY_SCHEMA
    stage: str = ""
    reason: str = ""
    detail: str | None = None
    emitted_at_utc: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "reason": self.reason,
            "detail": self.detail,
            "emitted_at_utc": self.emitted_at_utc,
        }


def _redact_detail(detail: Any) -> Any:
    """Replace path-like patterns in *detail* with REDACT (never raises)."""
    if not isinstance(detail, str):
        return detail
    return _PATH_PATTERN.sub(REDACT, detail)


def _is_iso8601_utc(value: Any) -> bool:
    """True for ISO-8601 timestamps carrying an explicit UTC offset."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _schema_problems(schema_version: Any) -> list[str]:
    if schema_version == STAGE_TAXONOMY_SCHEMA:
        return []
    return [f"schema_version must be {STAGE_TAXONOMY_SCHEMA!r}, got {schema_version!r}"]


def _stage_problems(stage: Any) -> list[str]:
    if is_registered_stage(stage):
        return []
    return [f"unknown stage: {stage!r}"]


def _reason_stage_problems(reason: Any, stage: Any) -> list[str]:
    if reason not in REASONS:
        return [f"unknown reason: {reason!r}"]
    if is_registered_stage(stage) and stage not in STAGES_BY_REASON[reason]:
        return [f"reason {reason!r} not attributed to stage {stage!r}"]
    return []


def _emitted_at_problems(value: Any) -> list[str]:
    if _is_iso8601_utc(value):
        return []
    return [f"emitted_at_utc is not ISO-8601: {value!r}"]


def validate_stage_event(event: dict | StageEvent) -> list[str]:
    """Validate a stage event; returns problems (empty list == valid).

    Fail closed: wrong/missing schema_version, unknown stage, unknown
    reason, a reason not attributed to the declared stage, and non-ISO-8601
    emitted_at_utc are reported as problems.  Path-like ``detail`` is
    redacted in place (stored as ``REDACT``) instead of rejected.  Never
    raises on invalid input.
    """
    problems: list[str] = []
    if isinstance(event, StageEvent):
        schema_version = event.schema_version
        stage = event.stage
        reason = event.reason
        detail = event.detail
        emitted_at_utc = event.emitted_at_utc
        event.detail = _redact_detail(detail)
    elif isinstance(event, dict):
        schema_version = event.get("schema_version")
        stage = event.get("stage")
        reason = event.get("reason")
        detail = event.get("detail")
        emitted_at_utc = event.get("emitted_at_utc")
        event["detail"] = _redact_detail(detail)
    else:
        return ["event must be a dict or StageEvent"]
    problems.extend(_schema_problems(schema_version))
    problems.extend(_stage_problems(stage))
    problems.extend(_reason_stage_problems(reason, stage))
    problems.extend(_emitted_at_problems(emitted_at_utc))
    return problems


@dataclass
class Metric:
    """One observable event.  Free-form fields are redacted on export."""

    dimension: str  # root_id | route | adapter_id | role | reason
    key: str  # e.g. a root_id | an adapter_id
    count: int = 1


@dataclass
class ObservabilityReport:
    schema_version: str = f"reason-taxonomy-{REASON_TAXONOMY_VERSION}"
    metrics: list[Metric] = field(default_factory=list)
    latency_p50: float | None = None
    latency_p95: float | None = None
    latency_p99: float | None = None
    db_busy: int = 0
    db_timeout: int = 0
    subprocess_failures: int = 0
    legacy_bridge_hits: int = 0
    shadow_diffs: int = 0
    migration_remaining: int = 0
    raw: list[dict] = field(default_factory=list)

    def aggregate(self, dimension: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for metric in self.metrics:
            if metric.dimension == dimension:
                out[metric.key] = out.get(metric.key, 0) + metric.count
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "metrics": [m.__dict__ for m in self.metrics],
            "aggregated": {
                dim: self.aggregate(dim)
                for dim in ("root_id", "route", "adapter_id", "role", "reason")
            },
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "latency_p99": self.latency_p99,
            "db_busy": self.db_busy,
            "db_timeout": self.db_timeout,
            "subprocess_failures": self.subprocess_failures,
            "legacy_bridge_hits": self.legacy_bridge_hits,
            "shadow_diffs": self.shadow_diffs,
            "migration_remaining": self.migration_remaining,
        }


class MetricsCollector:
    """Thread-safe append-only collector.  Never raises; exporter optional."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._report = ObservabilityReport()

    def record(self, dimension: str, key: str, *, redact: bool = True) -> None:
        if redact:
            key = _PATH_PATTERN.sub(REDACT, str(key))
        with self._lock:
            self._report.metrics.append(Metric(dimension=dimension, key=key))

    def record_reason(self, code: str) -> bool:
        """Record a reason code; unknown codes are refused (fail closed)."""
        if not validate_reason(code):
            return False
        with self._lock:
            self._report.metrics.append(Metric(dimension="reason", key=code))
            if code == "legacy_bridge_hit":
                self._report.legacy_bridge_hits += 1
            elif code == "shadow_diff":
                self._report.shadow_diffs += 1
            elif code == "migration_remaining":
                self._report.migration_remaining += 1
        return True

    def record_stage_event(self, event: StageEvent) -> bool:
        """Record a stage-attributed event; refused when validation fails.

        Fail closed: an invalid event (see ``validate_stage_event``) is
        refused (False) and never stored.  Valid events append their dict
        form — with path-like detail already redacted — to the report's raw
        log.  The v1.1 ``record_reason`` contract is unaffected.
        """
        if validate_stage_event(event):
            return False
        with self._lock:
            self._report.raw.append(event.to_dict())
        return True

    def record_latency(self, samples: list[float]) -> None:
        if not samples:
            return
        ordered = sorted(samples)
        n = len(ordered)

        # nearest-rank percentiles: index = ceil(q * n) - 1
        def pct(q: float) -> float:
            return ordered[math.ceil(q * n) - 1]

        with self._lock:
            self._report.latency_p50 = pct(0.50)
            self._report.latency_p95 = pct(0.95)
            self._report.latency_p99 = pct(0.99)

    def record_db(self, *, busy: int = 0, timeout: int = 0) -> None:
        with self._lock:
            self._report.db_busy += busy
            self._report.db_timeout += timeout

    def record_subprocess_failure(self) -> None:
        with self._lock:
            self._report.subprocess_failures += 1

    def snapshot(self) -> ObservabilityReport:
        with self._lock:
            return self._report

    def reset(self) -> None:
        with self._lock:
            self._report = ObservabilityReport()
