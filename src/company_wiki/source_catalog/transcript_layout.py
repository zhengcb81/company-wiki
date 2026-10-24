"""Bounded natural call headings, speaker labels and end controls.

Content evidence is required in addition to a heading. Names are structural,
never an issuer allowlist. Raw line strings/indices are not rewritten.
"""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata

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

# A printed diarization label and valid clock are structural evidence only.
# No issuer vocabulary, inferred names, institutional roles or ASR repair.
_TIMESTAMPED_SPEAKER = re.compile(
    r"^\s*(?P<speaker>(?:说话人|說話人|发言人|發言人)\s*\d{1,3}|Speaker\s+\d{1,3})"
    r"[ \t]+(?P<timestamp>(?:\d{1,3}:[0-5]\d:[0-5]\d|\d{1,4}:[0-5]\d))(?![\d:])",
    re.I,
)
_LEGACY_SPEAKER_LINE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9.'’ -]{1,78}?)(?:\s*--\s*(?P<title>[^:]{1,80}))?:\s*(?P<body>.*)$"
)
_LEGACY_SPEAKER_LABEL = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9.'’ -]{1,78})\s*--\s*(?P<title>[^:]{1,80})\s*$"
)
_NATIVE_CALL_HEADING = re.compile(
    r"^.{0,80}(?:财报|財報|业绩|業績)(?:交流会|交流會|电话会|電話會)[^。!?]{0,80}$"
)


def legacy_speaker_fields(stripped: str) -> tuple[str | None, str | None, str | None]:
    """One owner of the unchanged saved TXT label grammar."""
    label = _LEGACY_SPEAKER_LABEL.match(stripped)
    if label:
        return label['name'].strip(), label['title'].strip(), ''
    inline = _LEGACY_SPEAKER_LINE.match(stripped)
    if inline:
        return inline['name'].strip(), (inline['title'] or '').strip(), inline['body'].strip()
    return None, None, None


@dataclass
class AnonymousTurnObserver:
    """Observe a native prefix once; adapters own their document boundaries.

    Continuation records retain the actual label and original turn identity.
    None of these observations establishes who represents the company.
    """

    active: dict[str, str] | None = None
    closed: bool = False

    def clear(self) -> None:
        """Clear a physical turn boundary without reopening a closed source."""
        self.active = None

    def observe(self, text: str, *, source_id: str, locator: str) -> dict[str, str] | None:
        if self.closed:
            return None
        if END.fullmatch(text.strip()):
            self.active = None
            self.closed = True
            return None
        match = _TIMESTAMPED_SPEAKER.match(text[:128])
        if match:
            identity = '\0'.join((source_id, locator, match['speaker'], match['timestamp']))
            self.active = {
                'speaker': match['speaker'], 'timestamp': match['timestamp'],
                'turn_id': 'native-speaker:' + sha256(identity.encode()).hexdigest(),
            }
        elif speaker_fields([text], 0, legacy_speaker_fields, allow_affiliation=True)[0]:
            self.active = None
        result = dict(self.active) if self.active is not None else None
        if result is not None and END.search(text.strip()):
            self.active = None
            self.closed = True
        return result


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


def speaker_fields(lines, index, legacy_fields, *, allow_affiliation=False, allow_native=False):
    """Return name/title/inline body and source label line count."""
    value = lines[index].strip()
    if allow_native:
        native = _TIMESTAMPED_SPEAKER.match(value[:128])
        if native:
            return native['speaker'], '', lines[index], 1
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


def _substantive_speaker_body(body: str, *, allow_native: bool) -> bool:
    """The printed label itself is never evidence of spoken content."""
    native = _TIMESTAMPED_SPEAKER.match(body) if allow_native else None
    content = body[native.end():].strip() if native else body
    if native and sum('\u3400' <= char <= '\u9fff' for char in content[:64]) >= 4:
        return True
    return len(content) >= 24


def body_start(lines, explicit_start, legacy_fields, *, allow_affiliation=False,
               prefer_explicit=False, allow_native=False):
    """A nearby speaker with actual body is necessary; navigation is insufficient."""
    headings = list(enumerate(lines))
    if prefer_explicit:
        explicit_headings = [(index, line) for index, line in headings
                             if explicit_start.fullmatch(line.strip())]
        # An actual transcript marker wins over a wrapper title and roster.
        # If that explicit body cannot be verified, do not relabel the roster.
        if explicit_headings:
            headings = explicit_headings
    recognized_heading = False
    for heading, line in headings:
        explicit = bool(explicit_start.fullmatch(line.strip()))
        if not explicit and not NATURAL_START.fullmatch(line.strip()) and not (
            allow_native and _NATIVE_CALL_HEADING.fullmatch(line.strip())
        ):
            continue
        recognized_heading = True
        first = None
        turns = 0
        native_actors = set()
        substantive = False
        for index in range(heading + 1, min(len(lines), heading + 80)):
            name, _title, body, count = speaker_fields(
                lines, index, legacy_fields, allow_affiliation=allow_affiliation, allow_native=allow_native)
            if name:
                if first is None:
                    if index - heading > 16:
                        break
                    first = index
                turns += 1
                native_actors.add(''.join(unicodedata.normalize('NFKC', name).casefold().split()))
                if _substantive_speaker_body(body or "", allow_native=allow_native):
                    substantive = True
            elif (
                first is not None
                and len(line_body := lines[index].strip()) >= 32
                and not QA_HEADING.fullmatch(line_body)
            ):
                substantive = True
            enough_turns = len(native_actors) >= 2 if allow_native else turns >= 2
            if first is not None and substantive and (explicit or enough_turns):
                return first, explicit
    if allow_native and not recognized_heading:
        # Some raw diarized files have no wrapper. A small actual two-actor
        # prefix can prove the body; a roster before a recognized heading cannot.
        first = None
        actors = set()
        substantive = False
        for index in range(min(len(lines), 80)):
            if END.fullmatch(lines[index].strip()):
                break
            name, _title, body, _count = speaker_fields(
                lines, index, legacy_fields, allow_affiliation=allow_affiliation, allow_native=True
            )
            if name and body:
                first = index if first is None else first
                actors.add(''.join(unicodedata.normalize('NFKC', name).casefold().split()))
                substantive |= _substantive_speaker_body(body, allow_native=True)
                if len(actors) >= 2 and substantive:
                    return first, False
    return None
