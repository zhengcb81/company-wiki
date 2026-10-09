"""Bounded format-neutral image_pixels context, retaining every source line."""

from __future__ import annotations
from collections.abc import Sequence
import hashlib
import re
from .n6_candidate_completion import (
    BUSINESS_CHARACTER_WINDOW,
    MAX_COMPLETION_UNITS,
    ends_sentence,
)
from .narrative_document import NarrativeUnit
from .narrative_pdf_groups import PdfContextGroup, PdfGroupRules
from .narrative_visual_units import join_unit_text, ocr_continues, ocr_identity

_NEW_BULLET = re.compile(r"^\s*(?:[•●▪◦]|[-–—]\s|�{2,}|\d+[.)]\s)")


def _heading(unit: NarrativeUnit, rules: PdfGroupRules) -> bool:
    return any(
        p.search(unit.raw_text)
        for p in (rules.project_heading, rules.business_heading, rules.heading_only)
    )


def build_ocr_context_groups(
    units: Sequence[NarrativeUnit], rules: PdfGroupRules
) -> tuple[PdfContextGroup, ...]:
    """One image/shape is one coordinate domain; gaps and sentence barriers split."""
    by_identity = {}
    for unit in units:
        identity = ocr_identity(unit)
        if identity is not None and unit.source_role != "qa_text_shadow":
            by_identity.setdefault(identity, []).append(unit)
    groups = []
    for lines in by_identity.values():
        clusters = []
        for line in sorted(lines, key=lambda u: u.metadata["ocr_line_index"]):
            prior = clusters[-1][-1] if clusters else None
            continues = prior is not None and ocr_continues(prior, line)
            if continues:
                continues = (
                    not ends_sentence(prior.raw_text)
                    and not _heading(prior, rules)
                    and not _heading(line, rules)
                    and not _NEW_BULLET.match(line.raw_text)
                    and len(clusters[-1]) < MAX_COMPLETION_UNITS
                    and len(join_unit_text((*clusters[-1], line)))
                    <= BUSINESS_CHARACTER_WINDOW
                )
            if continues:
                clusters[-1].append(line)
            else:
                clusters.append([line])
        for cluster in clusters:
            members = tuple(cluster)
            digest = hashlib.sha256(
                ("image_pixels:" + "|".join(u.unit_id for u in members)).encode()
            ).hexdigest()
            groups.append(
                (
                    f"urn:company-wiki:context-group:sha256:{digest}",
                    members,
                    join_unit_text(members),
                )
            )
    return tuple(groups)
