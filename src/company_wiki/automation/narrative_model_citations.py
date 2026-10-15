"""Finite, source-bound citation units compiled from one pinned selection.

This is a transient model view, not another group registry. Existing native
groups own closure; only spans outside every group become standalone units.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path
from types import MappingProxyType

from company_wiki.source_contract import EvidenceSpan

from .models import canonical_json_hash


class CitationUnitError(ValueError):
    """A unit binding or model reference is absent, ambiguous or malformed."""


def _alias_for_members(members: tuple[str, ...], support: tuple[str, ...]) -> str:
    # Span IDs bind actual source bytes, locator, parser and original prose.
    # Sorting prevents source/group enumeration numbers becoming model aliases.
    return "u_" + canonical_json_hash({"members": sorted(members), "support": sorted(support)})[:20]


@dataclass(frozen=True)
class CitationUnits:
    units: tuple[tuple[str, tuple[str, ...]], ...]
    group_unit_ids: tuple[str, ...]
    evidence_order: tuple[str, ...]
    _members: Mapping[str, tuple[str, ...]]
    _support: Mapping[str, tuple[str, ...]]

    def resolve(self, references: object) -> tuple[str, ...]:
        """Expand exactly declared units once, without following overlap edges."""
        if (not isinstance(references, list) or not references
                or not all(isinstance(value, str) for value in references)):
            raise CitationUnitError("model citation units require a nonempty string array")
        if len(references) > len(self.units) or len(references) != len(set(references)):
            raise CitationUnitError("model citation units exceed the pinned unique set")
        if any(value not in self._members for value in references):
            raise CitationUnitError("model citation unit is not in the pinned selection")
        cited = {member for value in references for member in self._members[value]}
        return tuple(member for member in self.evidence_order if member in cited)

    def resolve_attribution(self, references: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
        members = self.resolve(references)
        # resolve validates shape, identity and duplicates before any lookup.
        assert isinstance(references, list)
        support = {member for value in references for member in self._support[value]}
        return (tuple(member for member in members if member in support),
                tuple(member for member in members if member not in support))

    def support_for(self, alias: str) -> tuple[str, ...]:
        return self._support[alias]


def compile_citation_units(
    evidence_spans: Sequence[EvidenceSpan], groups: Sequence[tuple[str, ...]],
    *, support_views: Sequence[Sequence[tuple[str, ...]]] | None = None,
) -> CitationUnits:
    """Compile native groups and true standalone spans; never invent neighbors."""
    order = tuple(span.span_id for span in evidence_spans)
    if len(order) != len(set(order)):
        raise CitationUnitError("duplicate canonical citation ids")
    sources = {span.span_id: span.source_id for span in evidence_spans}
    members_by_alias: dict[str, tuple[str, ...]] = {}
    support_by_alias: dict[str, tuple[str, ...]] = {}
    grouped: set[str] = set()
    group_aliases: list[str] = []

    def register(members: tuple[str, ...], support: tuple[str, ...]) -> str:
        member_set = set(members)
        if (not members or len(members) != len(member_set)
                or member_set - sources.keys()):
            raise CitationUnitError("citation unit requires unique pinned evidence")
        if len({sources[member] for member in members}) != 1:
            raise CitationUnitError("citation unit cannot cross original source parents")
        support_set = set(support)
        if not support or len(support) != len(support_set) or support_set - member_set:
            raise CitationUnitError("citation support must be a nonempty pinned subset")
        canonical = tuple(member for member in order if member in member_set)
        canonical_support = tuple(member for member in canonical if member in support_set)
        alias = _alias_for_members(canonical, canonical_support)
        previous = members_by_alias.get(alias)
        if previous is not None and (previous != canonical or support_by_alias[alias] != canonical_support):
            raise CitationUnitError("citation unit alias collision")
        members_by_alias[alias] = canonical
        support_by_alias[alias] = canonical_support
        return alias

    if support_views is not None and len(support_views) != len(groups):
        raise CitationUnitError("citation support views must match native groups")
    for index, members in enumerate(groups):
        views = support_views[index] if support_views is not None else (members,)
        if not 1 <= len(views) <= 2:
            raise CitationUnitError("citation group requires one or two native views")
        aliases = [register(members, support) for support in views]
        group_aliases.append(aliases[0])
        grouped.update(members)
    for member in order:
        if member not in grouped:
            register((member,), (member,))
    return CitationUnits(tuple(members_by_alias.items()), tuple(group_aliases), order,
                         MappingProxyType(members_by_alias), MappingProxyType(support_by_alias))


def citation_units_implementation_sha256() -> str:
    data = Path(__file__).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()
