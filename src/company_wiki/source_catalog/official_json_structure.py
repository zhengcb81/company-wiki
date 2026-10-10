"""Generic bounded JSON structure parser with exact raw byte identity.

This module owns grammar admission and byte-precise locators only.  It never
decides business meaning: no company, ticker, page number or provider field
name appears here.  Layout semantics live in the declarative adapter registry.

Every value is reachable by RFC 6901 pointer together with:

* ``token_range`` — half-open raw byte range including JSON delimiters
  (quotes for strings, digits for numbers, braces/brackets for containers);
* ``encoded_body_range`` — for strings, the raw byte range of the encoded
  body between (excluding) the quotes;
* ``decoded`` — the exact decoded string; offsets inside it are character
  offsets and are never raw byte offsets.

Duplicate keys are rejected on decoded key equality at any depth, numbers
must be finite, and lone surrogates / invalid escapes / control characters
are refused.  Depth, node, single-string, source-size and deadline budgets
are enforced while parsing, before any large object graph exists.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import time
from typing import Any
from urllib.parse import quote

CWP_JSON_STRUCTURE_PARSER_VERSION = "1.0.1"
LOCATOR_SCHEMA = "cwp-json-pointer/1"
LOCATOR_TRANSFORM_VERSION = "json-string-decode/1"

_BOM = b"\xef\xbb\xbf"
_WHITESPACE = b" \t\n\r"
_DIGITS = b"0123456789"
_NUMBER_RE = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_ESCAPE_MAP = {b'"': '"', b"\\": "\\", b"/": "/", b"b": "\b", b"f": "\f",
               b"n": "\n", b"r": "\r", b"t": "\t"}
_INDEX_RE = re.compile(r"0|[1-9][0-9]*")


class JsonStructureError(ValueError):
    """A named structural refusal; the raw page itself stays untouched."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class JsonStructureLimits:
    """Positive budgets applied while scanning, not after json.loads."""

    max_source_bytes: int = 16 * 1024 * 1024
    max_json_depth: int = 64
    max_json_nodes: int = 200_000
    max_json_string_bytes: int = 4 * 1024 * 1024
    deadline: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_source_bytes", "max_json_depth", "max_json_nodes",
                     "max_json_string_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.deadline is not None and not isinstance(self.deadline, (int, float)):
            raise ValueError("deadline must be a monotonic timestamp or null")


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _unescape_pointer_token(token: str) -> str | None:
    """Decode one RFC 6901 reference token, or None on a bad escape."""
    out: list[str] = []
    index = 0
    while index < len(token):
        char = token[index]
        if char == "~":
            if index + 1 >= len(token) or token[index + 1] not in "01":
                return None
            out.append("~" if token[index + 1] == "0" else "/")
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


class JsonStructureNode:
    """One parsed value with its exact raw byte identity."""

    __slots__ = ("kind", "pointer", "token_range", "encoded_body_range",
                 "encoded_token_sha256", "decoded", "decoded_sha256",
                 "decoded_character_count", "_value", "_members", "_items", "_raw")

    def __init__(self, *, kind: str, pointer: str, token_range: tuple[int, int],
                 raw: bytes, value: Any = None,
                 encoded_body_range: tuple[int, int] | None = None,
                 decoded: str | None = None):
        self.kind = kind
        self.pointer = pointer
        self.token_range = token_range
        self.encoded_body_range = encoded_body_range or (0, 0)
        self._raw = raw
        start, end = token_range
        self.encoded_token_sha256 = hashlib.sha256(raw[start:end]).hexdigest()
        self.decoded = decoded
        if decoded is None:
            self.decoded_sha256 = ""
            self.decoded_character_count = 0
        else:
            self.decoded_sha256 = hashlib.sha256(decoded.encode("utf-8")).hexdigest()
            self.decoded_character_count = len(decoded)
        self._value = value
        self._members: dict[str, "JsonStructureNode"] | None = None
        self._items: list["JsonStructureNode"] | None = None

    # -- navigation ----------------------------------------------------------

    def at(self, token: str) -> "JsonStructureNode":
        """Resolve one unescaped reference token against this container."""
        if self.kind == "object":
            child = (self._members or {}).get(token)
            if child is None:
                raise JsonStructureError("pointer_not_found")
            return child
        if self.kind == "array":
            if not _INDEX_RE.fullmatch(token):
                raise JsonStructureError("pointer_not_found")
            items = self._items or []
            index = int(token)
            if index >= len(items):
                raise JsonStructureError("pointer_not_found")
            return items[index]
        raise JsonStructureError("pointer_not_found")

    @property
    def value(self) -> Any:
        if self.kind == "object":
            return {key: node.value for key, node in (self._members or {}).items()}
        if self.kind == "array":
            return [node.value for node in (self._items or [])]
        return self._value

    @property
    def member_names(self) -> tuple[str, ...]:
        return tuple((self._members or {}))

    def members(self) -> dict[str, "JsonStructureNode"]:
        return dict(self._members or {})

    def items(self) -> tuple["JsonStructureNode", ...]:
        return tuple(self._items or ())

    # -- locators ------------------------------------------------------------

    def locator(self) -> str:
        """Field-level locator binding pointer, token bytes and decoded text."""
        return "|".join((
            LOCATOR_SCHEMA,
            "p=" + quote(self.pointer, safe=""),
            "b={}:{}".format(*self.token_range),
            "d=0:{}".format(self.decoded_character_count),
            "x=" + LOCATOR_TRANSFORM_VERSION,
        ))

    def decoded_slice(self, char_start: int, char_end: int) -> str:
        """Cut the fully decoded value on character boundaries only."""
        if self.kind != "string" or self.decoded is None:
            raise JsonStructureError("invalid_decoded_range")
        if not 0 <= char_start < char_end <= self.decoded_character_count:
            raise JsonStructureError("invalid_decoded_range")
        return self.decoded[char_start:char_end]


class JsonStructureDocument:
    """A bounded, verified page plus its pointer-addressable node tree."""

    def __init__(self, *, raw: bytes, root: JsonStructureNode, node_count: int,
                 max_depth_reached: int, has_bom: bool):
        self.raw = raw
        self.root = root
        self.byte_size = len(raw)
        self.parser_version = CWP_JSON_STRUCTURE_PARSER_VERSION
        self.node_count = node_count
        self.max_depth_reached = max_depth_reached
        self.has_bom = has_bom

    def at_pointer(self, pointer: str) -> JsonStructureNode:
        if not isinstance(pointer, str):
            raise JsonStructureError("invalid_json_pointer")
        if pointer == "":
            return self.root
        if not pointer.startswith("/"):
            raise JsonStructureError("invalid_json_pointer")
        node = self.root
        for raw_token in pointer.split("/")[1:]:
            token = _unescape_pointer_token(raw_token)
            if token is None:
                raise JsonStructureError("invalid_json_pointer")
            node = node.at(token)
        return node


class _Scanner:
    """Single-pass recursive descent over the exact raw bytes."""

    def __init__(self, raw: bytes, limits: JsonStructureLimits):
        self.raw = raw
        self.limits = limits
        self.pos = 0
        self.node_count = 0
        self.max_depth = 0

    def _tick(self) -> None:
        if self.limits.deadline is not None and time.monotonic() > self.limits.deadline:
            raise JsonStructureError("json_time_limit_exceeded")

    def _count_node(self, depth: int) -> None:
        self.node_count += 1
        if self.node_count > self.limits.max_json_nodes:
            raise JsonStructureError("json_node_limit_exceeded")
        if depth > self.max_depth:
            self.max_depth = depth
        if depth > self.limits.max_json_depth:
            raise JsonStructureError("json_depth_limit_exceeded")

    def skip_ws(self) -> None:
        raw, pos = self.raw, self.pos
        length = len(raw)
        while pos < length and raw[pos:pos + 1] in (b" ", b"\t", b"\n", b"\r"):
            pos += 1
        self.pos = pos

    def parse(self) -> tuple[JsonStructureNode, bool]:
        if len(self.raw) > self.limits.max_source_bytes:
            raise JsonStructureError("json_source_limit_exceeded")
        has_bom = self.raw.startswith(_BOM)
        body = self.raw[3:] if has_bom else self.raw
        if not body:
            raise JsonStructureError("empty_original")
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            raise JsonStructureError("invalid_json_encoding") from None
        self.pos = 3 if has_bom else 0
        self.skip_ws()
        if self.pos >= len(self.raw):
            raise JsonStructureError("empty_original")
        root = self._value("", depth=0)
        self.skip_ws()
        if self.pos != len(self.raw):
            raise JsonStructureError("invalid_json_syntax")
        return root, has_bom

    def _value(self, pointer: str, *, depth: int) -> JsonStructureNode:
        self._tick()
        self._count_node(depth)
        raw = self.raw
        self.skip_ws()
        if self.pos >= len(raw):
            raise JsonStructureError("invalid_json_syntax")
        head = raw[self.pos:self.pos + 1]
        if head == b"{":
            return self._object(pointer, depth)
        if head == b"[":
            return self._array(pointer, depth)
        if head == b'"':
            return self._string(pointer, depth)
        match = _NUMBER_RE.match(raw, self.pos)
        if match is None:
            # RFC 8259 has no NaN/Infinity constants; name them explicitly
            # instead of reporting generic syntax damage.
            for constant in (b"NaN", b"Infinity", b"-Infinity"):
                if raw.startswith(constant, self.pos):
                    raise JsonStructureError("nonfinite_json_number")
        if match is not None:
            text = match.group()
            self.pos = match.end()
            value = self._number_value(text)
            return JsonStructureNode(kind="number", pointer=pointer,
                                     token_range=(match.start(), match.end()),
                                     raw=raw, value=value)
        for literal, literal_value in ((b"true", True), (b"false", False),
                                       (b"null", None)):
            if raw.startswith(literal, self.pos):
                start = self.pos
                self.pos += len(literal)
                return JsonStructureNode(kind="literal", pointer=pointer,
                                         token_range=(start, self.pos),
                                         raw=raw, value=literal_value)
        raise JsonStructureError("invalid_json_syntax")

    @staticmethod
    def _number_value(text: bytes) -> int | float:
        as_text = text.decode("ascii")
        if b"." in text or b"e" in text or b"E" in text:
            value = float(as_text)
        else:
            return int(as_text)
        if value in (float("inf"), float("-inf")):
            raise JsonStructureError("nonfinite_json_number")
        return value

    def _object(self, pointer: str, depth: int) -> JsonStructureNode:
        raw = self.raw
        start = self.pos
        self.pos += 1
        node = JsonStructureNode(kind="object", pointer=pointer,
                                 token_range=(start, 0), raw=raw)
        members: dict[str, JsonStructureNode] = {}
        node._members = members
        self.skip_ws()
        if raw[self.pos:self.pos + 1] == b"}":
            self.pos += 1
            node.token_range = (start, self.pos)
            node.encoded_token_sha256 = hashlib.sha256(raw[start:self.pos]).hexdigest()
            return node
        while True:
            self._tick()
            self.skip_ws()
            if raw[self.pos:self.pos + 1] != b'"':
                raise JsonStructureError("invalid_json_syntax")
            key_node = self._string(pointer, depth, count_node=False)
            self.skip_ws()
            if raw[self.pos:self.pos + 1] != b":":
                raise JsonStructureError("invalid_json_syntax")
            self.pos += 1
            key = key_node.decoded
            assert isinstance(key, str)  # _string always decodes a str body
            if key in members:
                raise JsonStructureError("duplicate_json_key")
            members[key] = self._value(
                pointer + "/" + _escape_pointer_token(key), depth=depth + 1)
            self.skip_ws()
            separator = raw[self.pos:self.pos + 1]
            if separator == b",":
                self.pos += 1
                continue
            if separator == b"}":
                self.pos += 1
                node.token_range = (start, self.pos)
                node.encoded_token_sha256 = hashlib.sha256(raw[start:self.pos]).hexdigest()
                return node
            raise JsonStructureError("invalid_json_syntax")

    def _array(self, pointer: str, depth: int) -> JsonStructureNode:
        raw = self.raw
        start = self.pos
        self.pos += 1
        node = JsonStructureNode(kind="array", pointer=pointer,
                                 token_range=(start, 0), raw=raw)
        items: list[JsonStructureNode] = []
        node._items = items
        self.skip_ws()
        if raw[self.pos:self.pos + 1] == b"]":
            self.pos += 1
            node.token_range = (start, self.pos)
            node.encoded_token_sha256 = hashlib.sha256(raw[start:self.pos]).hexdigest()
            return node
        index = 0
        while True:
            self._tick()
            items.append(self._value("{}/{}".format(pointer, index),
                                     depth=depth + 1))
            index += 1
            self.skip_ws()
            separator = raw[self.pos:self.pos + 1]
            if separator == b",":
                self.pos += 1
                continue
            if separator == b"]":
                self.pos += 1
                node.token_range = (start, self.pos)
                node.encoded_token_sha256 = hashlib.sha256(raw[start:self.pos]).hexdigest()
                return node
            raise JsonStructureError("invalid_json_syntax")

    def _string(self, pointer: str, depth: int, *, count_node: bool = True
                ) -> JsonStructureNode:
        if count_node:
            self._tick()
            self._count_node(depth)
        raw = self.raw
        start = self.pos
        pos = start + 1
        decoded_bytes = bytearray()
        limit = len(raw)
        while True:
            if pos >= limit:
                raise JsonStructureError("invalid_json_syntax")
            char = raw[pos]
            if char == 0x22:  # closing quote
                body_range = (start + 1, pos)
                if pos - (start + 1) > self.limits.max_json_string_bytes:
                    raise JsonStructureError("json_string_limit_exceeded")
                self.pos = pos + 1
                decoded = decoded_bytes.decode("utf-8")
                return JsonStructureNode(
                    kind="string", pointer=pointer, token_range=(start, pos + 1),
                    raw=raw, value=decoded, encoded_body_range=body_range,
                    decoded=decoded)
            if char == 0x5C:  # backslash
                escape = raw[pos + 1:pos + 2]
                if escape in _ESCAPE_MAP:
                    decoded_bytes += _ESCAPE_MAP[escape].encode("utf-8")
                    pos += 2
                    continue
                if escape == b"u":
                    code = self._hex4(raw, pos + 2)
                    if 0xD800 <= code <= 0xDBFF:
                        if raw[pos + 6:pos + 8] != b"\\u":
                            raise JsonStructureError("invalid_json_surrogate")
                        low = self._hex4(raw, pos + 8)
                        if not 0xDC00 <= low <= 0xDFFF:
                            raise JsonStructureError("invalid_json_surrogate")
                        combined = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                        decoded_bytes += chr(combined).encode("utf-8")
                        pos += 12
                    elif 0xDC00 <= code <= 0xDFFF:
                        raise JsonStructureError("invalid_json_surrogate")
                    else:
                        decoded_bytes += chr(code).encode("utf-8")
                        pos += 6
                    continue
                raise JsonStructureError("invalid_json_syntax")
            if char < 0x20:
                raise JsonStructureError("invalid_json_syntax")
            decoded_bytes.append(char)
            pos += 1

    @staticmethod
    def _hex4(raw: bytes, offset: int) -> int:
        chunk = raw[offset:offset + 4]
        if len(chunk) != 4:
            raise JsonStructureError("invalid_json_syntax")
        try:
            return int(chunk, 16)
        except ValueError:
            raise JsonStructureError("invalid_json_syntax") from None


def parse_json_structure(data: bytes, *, limits: JsonStructureLimits | None = None
                         ) -> JsonStructureDocument:
    """Parse one bounded JSON page into pointer-addressable raw identity."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be raw bytes")
    if isinstance(data, bytearray):
        data = bytes(data)
    if limits is None:
        limits = JsonStructureLimits()
    if not isinstance(limits, JsonStructureLimits):
        raise TypeError("limits must be JsonStructureLimits")
    if not data:
        raise JsonStructureError("empty_original")
    scanner = _Scanner(data, limits)
    root, has_bom = scanner.parse()
    return JsonStructureDocument(raw=data, root=root,
                                 node_count=scanner.node_count,
                                 max_depth_reached=scanner.max_depth,
                                 has_bom=has_bom)
