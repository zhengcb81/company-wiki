"""ZR-510: multi-entity chunk attribution — attribute every chunk of a
multi-entity document to the entity its text actually names, with
zero cross-entity misattribution (BR-06/07).

  attribute_document(text, chunks, declared_entities) -> list of
      {"chunk_index", "start", "end", "entities", "attribution"}

attribution in {entity full name, "mixed", "unattributed"}:
  - one entity phrase in the chunk   -> that entity's name (matched via
    normalized containment against the declared entities)
  - several different entities       -> "mixed"
  - no entity phrase                 -> "unattributed" (honest, never
    guessed)

Hermetic (regex only; zero hardcoded names); reuses the ZR-503
suffix-anchored phrase pattern.
"""

from __future__ import annotations

import re
import unicodedata

ATTRIBUTION_SCHEMA_VERSION = "1.0"

_PHRASE = re.compile(
    r"[\u4e00-\u9fff]{2,12}"
    r"(?:股份有限公司|有限责任公司|有限公司|集团公司|集团)"
)


def _phrases(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in _PHRASE.finditer(text or ""):
        phrase = match.group(0)
        if phrase not in seen:
            seen[phrase] = None
    return list(seen)


def _related(phrase: str, declared: list[str]) -> str | None:
    phrase_norm = unicodedata.normalize("NFC", phrase).casefold()
    for entity in declared:
        entity_norm = unicodedata.normalize("NFC", entity).casefold()
        if phrase_norm in entity_norm or entity_norm in phrase_norm:
            return entity
    return None


def attribute_document(
    text: str | None,
    chunks: list[list[int]],
    declared_entities: list[str],
) -> list[dict[str, object]]:
    """Attribute every chunk by the entity phrases its own text names.

    Chunk offsets are CONTENT-line offsets (the ZR-506 convention: blank
    lines and page/locator headers excluded), so the same filtering is
    applied here before slicing."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    attributed: list[dict[str, object]] = []
    for chunk_index, (start, end) in enumerate(chunks):
        segment = "\n".join(lines[start:end])
        found = _phrases(segment)
        related = [item for item in ( _related(phrase, declared_entities) for phrase in found) if item]
        unique = list(dict.fromkeys(related))
        if len(unique) == 1:
            attribution = unique[0]
        elif len(unique) > 1:
            attribution = "mixed"
        else:
            attribution = "unattributed"
        attributed.append(
            {
                "chunk_index": chunk_index,
                "start": start,
                "end": end,
                "entities": found,
                "attribution": attribution,
            }
        )
    return attributed


__all__ = [
    "ATTRIBUTION_SCHEMA_VERSION",
    "attribute_document",
]
