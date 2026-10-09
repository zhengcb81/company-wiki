"""Bounded natural call headings, speaker labels and end controls.

Content evidence is required in addition to a heading. Names are structural,
never an issuer allowlist. Raw line strings/indices are not rewritten.
"""

from __future__ import annotations
import re

NATURAL_START = re.compile(
    r"^(?:transcript|(?:.{0,100}\b)?(?:earnings|results|conference)\s+call(?:\s+transcript)?|(?:.{0,100}\b)?earnings\s+conference\s+call(?:\s+transcript)?)\s*:?[ \t]*$",
    re.I,
)
QA_HEADING = re.compile(
    r"^(?:questions?\s*(?:&|and)\s*answers?(?:\s+session)?|Q\s*&\s*A(?:\s+session)?)\s*:?[ \t]*$",
    re.I,
)
END = re.compile(
    r"^(?:end(?:\s+of\s+(?:the\s+)?(?:call|transcript))?|\[?end\s+of\s+transcript\]?)\s*[.!]?$|(?:this\s+concludes|concludes?\s+today[’\']?s).{0,100}(?:conference|earnings)?\s*call|you\s+may\s+(?:now\s+)?disconnect",
    re.I,
)
_NON_SPEAKER = frozenset(
    {
        "revenue",
        "download",
        "contact",
        "date",
        "time",
        "copyright",
        "transcript",
        "earnings",
        "metrics",
        "operator direction",
        "presentation",
        "financial results",
    }
)
_NAME = re.compile(r"^[A-Z][A-Za-z.\'’ -]{1,75}$")
_ROLE = re.compile(
    r"chief|CEO|CFO|president|executive|officer|analyst|investor relations|operator",
    re.I,
)
_DASH_LABEL = re.compile(
    r"^(?P<name>[A-Z][A-Za-z.\'’ -]{1,75}?)\s*(?:—|–)\s*(?P<title>[^:]{1,80})\s*$"
)

_AFFILIATION_LABEL = re.compile(
    r"^(?P<name>[A-Z][A-Za-z.\'’ -]{1,75}?)\s*,\s*"
    r"(?P<title>[^:\r\n]{1,80}):\s*(?P<body>.*)$"
)


def valid_speaker(name):
    if not name or name.casefold() in _NON_SPEAKER:
        return False
    if name.casefold() in {
        "ceo",
        "cfo",
        "operator",
        "analyst",
        "management",
        "president",
    }:
        return True
    words = name.split()
    return 2 <= len(words) <= 5 and all(
        word[:1].isupper() or word.casefold() in {"de", "van", "von", "der"}
        for word in words
    )


def speaker_fields(lines, index, legacy_fields, *, allow_affiliation=False):
    """Return name/title/inline body and source label line count."""
    value = lines[index].strip()
    name, title, body = legacy_fields(value)
    if valid_speaker(name):
        return name, title or "", body or "", 1
    if allow_affiliation:
        affiliation = _AFFILIATION_LABEL.fullmatch(value)
        if affiliation and valid_speaker(affiliation["name"].strip()):
            return (affiliation["name"].strip(), affiliation["title"].strip(),
                    affiliation["body"].strip(), 1)
    match = _DASH_LABEL.fullmatch(value)
    if match and valid_speaker(match["name"].strip()) and _ROLE.search(match["title"]):
        return match["name"].strip(), match["title"].strip(), "", 1
    if _NAME.fullmatch(value) and valid_speaker(value) and index + 1 < len(lines):
        title = lines[index + 1].strip().lstrip("-—– ")
        if len(title) <= 100 and _ROLE.search(title):
            return value, title, "", 2
    return None, None, None, 0


def body_start(lines, explicit_start, legacy_fields, *, allow_affiliation=False):
    """A nearby speaker with actual body is necessary; navigation is insufficient."""
    for heading, line in enumerate(lines):
        explicit = bool(explicit_start.fullmatch(line.strip()))
        if not explicit and not NATURAL_START.fullmatch(line.strip()):
            continue
        first = None
        turns = 0
        substantive = False
        for index in range(heading + 1, min(len(lines), heading + 80)):
            name, _title, body, count = speaker_fields(
                lines, index, legacy_fields, allow_affiliation=allow_affiliation)
            if name:
                if first is None:
                    if index - heading > 16:
                        break
                    first = index
                turns += 1
                if len(body or "") >= 24:
                    substantive = True
            elif (
                first is not None
                and len(line_body := lines[index].strip()) >= 32
                and not QA_HEADING.fullmatch(line_body)
            ):
                substantive = True
            if first is not None and substantive and (explicit or turns >= 2):
                return first, explicit
    return None
