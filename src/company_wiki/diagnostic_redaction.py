"""Shared, lossless redaction for text in local diagnostics."""
from __future__ import annotations

import re
from traceback import TracebackException
from typing import Any

__all__ = [
    "REDACT", "redact_text", "redact_and_truncate", "format_diagnostic_exception",
    "key_is_credential", "MAX_REDACTED_MESSAGE_CHARS",
]

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
_BACKSLASH = frozenset("\\")


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
_QUOTED_VALUE = r""""(?:\\[^\r\n]|[^"\\\r\n])*"|'(?:\\[^\r\n]|[^'\\\r\n])*'"""
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

    Cost is O(len(text)): one scanner pass over assignment separators and
    one regex pass with fixed literals for ``authorization``/``bearer``.
    """
    if not isinstance(text, str) or not text:
        return text
    return _AUTH_PATTERN.sub(lambda m: m.group("key") + REDACT, _redact_assignments(text))


def format_diagnostic_exception(error: BaseException) -> str:
    """Format the original stack and cause chain without locals or raw credentials."""
    try:
        trace = "".join(TracebackException.from_exception(error).format())
    except Exception:
        return type(error).__name__
    return str(redact_text(trace.rstrip()))


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
    if key_end and text[key_end - 1] in _QUOTES:
        quote_at = key_end - 1
        end = _scan_left_over(text, quote_at, _BACKSLASH)
        start = _scan_left_over(text, end, _KEY_CHARS)
        opening = start - 1
        if opening < 0 or text[opening] != text[quote_at]:
            return False
        if opening - _scan_left_over(text, opening, _BACKSLASH) != quote_at - end:
            return False
        key = text[start:end]
        return key.lower() in ("authorization", "proxy-authorization") or key_is_credential(key)
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
    opening = _scan_right_backslashes(text, value_start)
    if opening < len(text) and text[opening] in _QUOTES:
        closing = _find_closing_quote(text, opening, opening - value_start)
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


def _scan_right_backslashes(text: str, cursor: int) -> int:
    while cursor < len(text) and text[cursor] == "\\":
        cursor += 1
    return cursor


def _find_closing_quote(text: str, quote_at: int, opening_slashes: int) -> int:
    quote = text[quote_at]
    cursor = quote_at + 1
    # One JSON escaping layer doubles a backslash and adds one before
    # quotes. Match the opening layer while ignoring quotes inside the value.
    stride = 2 * (opening_slashes + 1)
    while cursor < len(text):
        end = _scan_right_backslashes(text, cursor)
        if end == len(text) or text[end] in "\r\n":
            break
        if text[end] == quote and (end - cursor - opening_slashes) % stride == 0:
            return end
        cursor = end + 1
    return -1


def redact_and_truncate(text: Any, limit: int = MAX_REDACTED_MESSAGE_CHARS) -> Any:
    """``redact_text`` first, then truncate to *limit* characters."""
    redacted = redact_text(text)
    if not isinstance(redacted, str):
        return redacted
    return redacted[:limit]
