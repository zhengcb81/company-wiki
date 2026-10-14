"""Observe the *final* summary material, independently of gold or generated claims.

``du_observer.observe_pipeline`` measures the shared DU pipeline's own
``summary`` mapping. That is the right seam while the pipeline owns assembly, but
it is not the material the model actually receives once a real producer builds a
``NarrativeModelRequest``: that envelope addresses evidence by *alias* rows and
groups by *group alias*, and none of those aliases are original locators.

This module measures the final envelope — the decode of
``NarrativeModelRequest.data_json``, or a frozen-equivalent fixture with the same
shape — and resolves every alias back to an already-verified original unit. The
invariants are:

1. **Text comes from the original, never from the envelope.** A material whose
   row text differs from its bound original unit is a fabrication attempt and
   the observation is refused, not silently corrected.
2. **Aliases are the material's own.** A row alias or group alias that the
   envelope does not declare is a broken reference, reported as such.
3. **Roles, locators and pages come from the original.** The envelope may omit a
   role (it does, via ``default_source_role``); it may never assert one that
   contradicts the original.
4. **Unread stays unread.** Opaque/deferred pages and units are carried into
   coverage, and the observation records explicitly that "not read" is not the
   same as "nothing there".
5. **Nothing is invented to make a shape look complete.** No semantic unit is
   minted from wording, and no scope is inferred from a group's name.

Nothing here parses, selects, calls a model, reads the network or writes a file.
Byte and identity verification belong to the source layer; this module only
checks that a member is an unchanged unit of the observation it claims to be.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .records import validate_observed

FINAL_ORIGINALS_SCHEMA_VERSION = "du-final-originals/1"
FINAL_OBSERVED_ENTRY_POINT = (
    "company_wiki.automation.narrative_model.NarrativeModelRequest.from_selection"
)

#: Default resource bounds for one observation. These are *assembly* bounds: a
#: caller may lower them, and reaching one refuses the observation rather than
#: truncating it, because a truncated observation silently shrinks the recall
#: denominator it is later compared on.
DEFAULT_LIMITS: dict[str, int] = {
    "max_evidence_rows": 512,
    "max_evidence_groups": 512,
    "max_units": 4096,
    "max_text_bytes": 4 * 1024 * 1024,
    "max_work_units": 200_000,
}

#: Group kinds the observer may report. A material group is by construction a
#: caller-declared closure over the evidence rows, so that is the only kind.
FINAL_GROUP_KIND = "final_evidence_group"


class FinalMaterialError(ValueError):
    """The final material or its originals violate the frozen contract."""


def _require_mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FinalMaterialError(f"{what} must be a mapping")
    return value


def _require_sequence(value: Any, what: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise FinalMaterialError(f"{what} must be an array")
    return value


def _require_text(value: Any, what: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise FinalMaterialError(f"{what} must be a string")
    if not allow_empty and not value:
        raise FinalMaterialError(f"{what} must be non-empty")
    return value


def _optional_text(value: Any, what: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value:
        return None
    return _require_text(value, what)


def _effective_limits(limits: Mapping[str, Any] | None) -> dict[str, int]:
    effective = dict(DEFAULT_LIMITS)
    if limits is None:
        return effective
    if not isinstance(limits, Mapping):
        raise FinalMaterialError("limits must be a mapping")
    for key, value in limits.items():
        if key not in DEFAULT_LIMITS:
            raise FinalMaterialError(f"unknown limit {key!r}")
        if type(value) is not int or value <= 0:
            raise FinalMaterialError(f"limit {key!r} must be a positive integer")
        # A caller may lower a bound, never raise it: these are technical hard
        # limits, and raising them from a call site would defeat the point.
        effective[key] = min(effective[key], value)
    return effective


# ---------------------------------------------------------------------------
# originals
# ---------------------------------------------------------------------------


class _Originals:
    """The already-verified source side, indexed by the material's own aliases."""

    def __init__(self, raw: Mapping[str, Any]) -> None:
        originals = _require_mapping(raw, "originals")
        version = originals.get("schema_version")
        if version != FINAL_ORIGINALS_SCHEMA_VERSION:
            raise FinalMaterialError(
                f"originals schema_version must be {FINAL_ORIGINALS_SCHEMA_VERSION}"
            )
        self.source_id = _require_text(originals.get("source_id"), "originals.source_id")
        self.source_sha256 = _require_text(
            originals.get("source_sha256"), "originals.source_sha256"
        )
        units = _require_mapping(originals.get("units"), "originals.units")
        self.units: dict[str, dict[str, Any]] = {}
        for alias, raw_unit in units.items():
            where = f"originals.units[{alias!r}]"
            unit = _require_mapping(raw_unit, where)
            locator = _require_text(unit.get("locator"), f"{where}.locator")
            text = unit.get("text")
            if not isinstance(text, str):
                raise FinalMaterialError(f"{where}.text must be a string")
            unit_source = _require_text(
                unit.get("source_sha256", self.source_sha256), f"{where}.source_sha256"
            )
            if unit_source != self.source_sha256:
                raise FinalMaterialError(
                    f"{where} claims source {unit_source}, which is not this observation's source"
                )
            unit_source_id = _require_text(
                unit.get("source_id", self.source_id), f"{where}.source_id"
            )
            if unit_source_id != self.source_id:
                raise FinalMaterialError(
                    f"{where} claims a different source_id than the observation"
                )
            page = unit.get("page")
            if page is not None and (type(page) is not int or page < 1):
                raise FinalMaterialError(f"{where}.page must be a positive integer or null")
            self.units[str(alias)] = {
                "unit_id": _optional_text(unit.get("unit_id"), f"{where}.unit_id"),
                "locator": locator,
                "text": text,
                "page": page,
                "source_role": _optional_text(unit.get("source_role"), f"{where}.source_role"),
                "language": _optional_text(unit.get("language"), f"{where}.language"),
                "scope_id": _optional_text(unit.get("scope_id"), f"{where}.scope_id"),
                "period": _optional_text(unit.get("period"), f"{where}.period"),
            }
        groups = originals.get("groups") or {}
        if not isinstance(groups, Mapping):
            raise FinalMaterialError("originals.groups must be a mapping")
        self.groups: dict[str, tuple[str, ...]] = {}
        for name, members in groups.items():
            seq = _require_sequence(members, f"originals.groups[{name!r}]")
            self.groups[str(name)] = tuple(
                _require_text(member, f"originals.groups[{name!r}]") for member in seq
            )

    def locator_owners(self) -> dict[str, list[str]]:
        owners: dict[str, list[str]] = {}
        for alias, unit in self.units.items():
            owners.setdefault(unit["locator"], []).append(alias)
        return owners

    def body_duplicates(self) -> list[list[str]]:
        by_body: dict[str, list[str]] = {}
        for alias, unit in self.units.items():
            by_body.setdefault(unit["text"], []).append(alias)
        return [sorted(aliases) for aliases in by_body.values() if len(aliases) > 1]


# ---------------------------------------------------------------------------
# material
# ---------------------------------------------------------------------------


def _columns(envelope: Mapping[str, Any], key: str, default: Sequence[str]) -> list[str]:
    raw = envelope.get(key, default)
    columns = [
        _require_text(item, f"material.{key}[{index}]")
        for index, item in enumerate(_require_sequence(raw, f"material.{key}"))
    ]
    if not columns:
        raise FinalMaterialError(f"material.{key} must not be empty")
    if len(set(columns)) != len(columns):
        raise FinalMaterialError(f"material.{key} has duplicate column names")
    return columns


def _read_rows(
    envelope: Mapping[str, Any],
    *,
    row_key: str,
    column_key: str,
    default_columns: Sequence[str],
) -> list[dict[str, Any]]:
    """Decode ``[value, ...]`` rows against the envelope's own column names.

    The real builder sometimes omits trailing columns whose value equals the
    declared default (a role equal to ``default_source_role``). That is legal and
    is decoded here as "not stated", which the caller distinguishes from an
    explicit ``unknown``.
    """

    columns = _columns(envelope, column_key, default_columns)
    raw_rows = _require_sequence(envelope.get(row_key, ()), f"material.{row_key}")
    rows: list[dict[str, Any]] = []
    for index, raw_row in enumerate(raw_rows):
        where = f"material.{row_key}[{index}]"
        cells = _require_sequence(raw_row, where)
        if not cells:
            raise FinalMaterialError(f"{where} must not be empty")
        if len(cells) > len(columns):
            raise FinalMaterialError(
                f"{where} has {len(cells)} cells for {len(columns)} declared columns"
            )
        rows.append(dict(zip(columns, cells, strict=False)))
    return rows


def _resolve_text(
    row: Mapping[str, Any],
    original: Mapping[str, Any],
    *,
    alias: str,
) -> str:
    """The envelope's text must equal the original's, byte for byte."""

    stated = row.get("raw_text")
    if stated is None:
        stated = row.get("text")
    if not isinstance(stated, str):
        raise FinalMaterialError(f"material row {alias!r} carries no raw_text")
    if stated != original["text"]:
        raise FinalMaterialError(
            f"material row {alias!r} text differs from its original unit: the envelope "
            "cannot substitute its own wording for source evidence"
        )
    return original["text"]


def _resolve_role(
    row: Mapping[str, Any],
    original: Mapping[str, Any],
    *,
    alias: str,
    default_role: str | None,
) -> str | None:
    """A stated role must not contradict the original's role.

    ``default_source_role`` is the envelope's *most common* role, used to omit a
    repeated trailing cell. It is a majority summary of the rows, not an
    assertion about any single one, so it only conflicts when it names a
    concrete role that the original contradicts. ``unknown`` and an unstated
    default are both "no claim made", and the original's own role is used.
    """

    stated = _optional_text(row.get("source_role"), f"material row {alias!r}.source_role")
    if stated is None:
        concrete_default = default_role not in (None, "", "unknown")
        if concrete_default and original["source_role"] is not None:
            if default_role != original["source_role"]:
                raise FinalMaterialError(
                    f"material default_source_role {default_role!r} contradicts the original "
                    f"role {original['source_role']!r} for {alias!r}"
                )
        # An omitted cell means "same as the default", so a row whose original
        # differs from a concrete default would be mis-attributed.
        if concrete_default and original["source_role"] is None:
            raise FinalMaterialError(
                f"material row {alias!r} omits its role and inherits the default "
                f"{default_role!r}, but its original unit declares no role"
            )
        return original["source_role"]
    if original["source_role"] is not None and stated != original["source_role"]:
        raise FinalMaterialError(
            f"material row {alias!r} declares role {stated!r}, but its original unit is "
            f"{original['source_role']!r}"
        )
    return stated


def observe_final_material(
    material: Mapping[str, Any],
    originals: Mapping[str, Any],
    *,
    sample_id: str,
    execution: Mapping[str, Any],
    limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure one final ``ModelRequest`` against its verified originals.

    Returns a ``du-observed/1`` record so the existing oracle consumes it
    unchanged. Raises :class:`FinalMaterialError` for a material that fabricates,
    mis-references or mis-attributes source text; those are refused runs, not
    quality verdicts.
    """

    effective = _effective_limits(limits)
    checked_sample_id = _require_text(sample_id, "sample_id")
    checked_execution = _require_mapping(execution, "execution")
    envelope = _require_mapping(material, "material")
    source = _Originals(originals)

    source_block = _require_mapping(envelope.get("source") or envelope.get("subject") or {},
                                    "material.source")
    stated_sha = source_block.get("source_sha256", source_block.get("subject_sha256"))
    if stated_sha is not None and stated_sha != source.source_sha256:
        raise FinalMaterialError(
            "material and originals describe different sources; the observation cannot "
            "be tied to the gold source"
        )

    default_role = _optional_text(
        envelope.get("default_source_role"), "material.default_source_role"
    )

    rows = _read_rows(
        envelope,
        row_key="evidence",
        column_key="evidence_columns",
        default_columns=("id", "raw_text", "source_role", "quality_flags"),
    )
    if len(rows) > effective["max_evidence_rows"]:
        raise FinalMaterialError(
            f"material carries {len(rows)} evidence rows, over the limit of "
            f"{effective['max_evidence_rows']}"
        )

    work = 0
    selected_evidence: list[dict[str, Any]] = []
    seen_aliases: set[str] = set()
    duplicate_alias_ids: list[str] = []
    text_bytes = 0

    for row in rows:
        alias = _require_text(row.get("id"), "material evidence row id")
        if alias in seen_aliases:
            duplicate_alias_ids.append(alias)
            continue
        seen_aliases.add(alias)
        original = source.units.get(alias)
        if original is None:
            raise FinalMaterialError(
                f"material references alias {alias!r}, which has no verified original unit"
            )
        work += 1
        if work > effective["max_work_units"]:
            raise FinalMaterialError("observation exceeded its work limit")
        text = _resolve_text(row, original, alias=alias)
        text_bytes += len(text.encode("utf8"))
        if text_bytes > effective["max_text_bytes"]:
            raise FinalMaterialError(
                f"observation text exceeds the limit of {effective['max_text_bytes']} bytes"
            )
        role = _resolve_role(row, original, alias=alias, default_role=default_role)
        selected_evidence.append(
            {
                "locator": original["locator"],
                "text": text,
                "page": original["page"],
                "line": None,
                "line_end": None,
                "unit_id": original["unit_id"] or alias,
                "source_role": role,
                "language": original["language"],
                "scope_id": original["scope_id"],
                "period": original["period"],
            }
        )

    if duplicate_alias_ids:
        raise FinalMaterialError(
            f"material declares duplicate evidence aliases: {sorted(set(duplicate_alias_ids))}"
        )

    group_rows = _read_rows(
        envelope,
        row_key="evidence_groups",
        column_key="evidence_group_columns",
        default_columns=("id", "evidence_ids"),
    )
    if len(group_rows) > effective["max_evidence_groups"]:
        raise FinalMaterialError(
            f"material carries {len(group_rows)} groups, over the limit of "
            f"{effective['max_evidence_groups']}"
        )

    semantic_units: list[dict[str, Any]] = []
    shared_aliases: dict[str, int] = {}
    cross_scope_groups: dict[str, list[str]] = {}
    closure_repackaged: dict[str, dict[str, list[str]]] = {}
    for row in group_rows:
        group_alias = _require_text(row.get("id"), "material evidence group id")
        members = [
            _require_text(member, f"material group {group_alias!r} member")
            for member in _require_sequence(
                row.get("evidence_ids", ()), f"material group {group_alias!r}.evidence_ids"
            )
        ]
        work += len(members)
        if work > effective["max_work_units"]:
            raise FinalMaterialError("observation exceeded its work limit")
        locators: list[str] = []
        scopes: set[str] = set()
        for member in members:
            if member not in seen_aliases:
                raise FinalMaterialError(
                    f"group {group_alias!r} references alias {member!r}, which the material "
                    "does not declare"
                )
            original = source.units[member]
            shared_aliases[member] = shared_aliases.get(member, 0) + 1
            locators.append(original["locator"])
            if original["scope_id"]:
                scopes.add(original["scope_id"])
        # A material group must not merge members that the source declares as
        # distinct subjects or scopes: packaging a listed company's action
        # together with an affiliate's, or a parent filing together with its
        # exhibit, creates one false "scope" out of two different ones.
        if len(scopes) > 1:
            cross_scope_groups[group_alias] = sorted(scopes)
        # If the originals declare a source closure for this group, note when the
        # material re-packages it into a different member set. Reported as a
        # diagnostic (not a hard failure): the scope-span check above is the
        # authoritative cross-subject guard, and a caller may legitimately
        # re-slice a closure while staying inside one subject.
        if group_alias in source.groups:
            declared = set(source.groups[group_alias])
            actual = set(members)
            if declared != actual:
                closure_repackaged[group_alias] = {
                    "declared": sorted(declared),
                    "material": sorted(actual),
                }
        semantic_units.append(
            {
                "semantic_id": group_alias,
                "kind": FINAL_GROUP_KIND,
                "locators": list(dict.fromkeys(locators)),
                "completeness": "complete",
                "required_locators": list(dict.fromkeys(locators)),
                "dependencies_resolved": True,
                "diagnostics": [],
            }
        )
    if cross_scope_groups:
        raise FinalMaterialError(
            f"material groups merge distinct source scopes: {cross_scope_groups}; "
            "a cross-subject or parent-source package is not one scope"
        )

    locator_owners = source.locator_owners()
    ambiguous = sorted(
        locator for locator, owners in locator_owners.items()
        if len({source.units[alias]["text"] for alias in owners}) > 1
    )
    if ambiguous:
        raise FinalMaterialError(
            f"two different original units share one locator: {ambiguous}"
        )

    selected_text = "\n".join(row["text"] for row in selected_evidence)
    coverage = _coverage(envelope, originals, source, selected_evidence)
    coverage["unresolved_aliases"] = []
    coverage["shared_alias_ids"] = sorted(
        alias for alias, count in shared_aliases.items() if count > 1
    )
    coverage["duplicate_body_alias_ids"] = source.body_duplicates()
    coverage["duplicate_material_alias_ids"] = sorted(set(duplicate_alias_ids))
    coverage["closure_repackaged"] = closure_repackaged
    coverage["unread_is_not_absence"] = True

    observed = validate_observed(
        {
            "schema_version": "du-observed/1",
            "sample_id": checked_sample_id,
            "source_sha256": source.source_sha256,
            "route": _route(envelope),
            "selected_locators": list(dict.fromkeys(
                row["locator"] for row in selected_evidence
            )),
            "selected_evidence": selected_evidence,
            "selected_text": selected_text,
            "semantic_units": semantic_units,
            "claims": [],
            "coverage": coverage,
            "metrics": {
                "evidence_rows": len(selected_evidence),
                "evidence_groups": len(semantic_units),
                "source_units": len(source.units),
                "selected_spans": len(selected_evidence),
                "selected_text_bytes": text_bytes,
                "assembly_budget": dict(envelope.get("output_plan") or {}),
                "observed_entry_point": FINAL_OBSERVED_ENTRY_POINT,
                "evidence_columns": list(
                    envelope.get("evidence_columns") or ()
                ),
                "work_units": work,
            },
            "execution": {
                "entry_point": FINAL_OBSERVED_ENTRY_POINT,
                "selector_version": checked_execution.get("selector_version"),
                "parser_version": checked_execution.get("parser_version"),
                "prompt_version": checked_execution.get("prompt_version"),
                "mode": checked_execution.get("mode") or "final-material",
                "calls": int(checked_execution.get("calls") or 0),
                "elapsed_seconds": checked_execution.get("elapsed_seconds"),
                "assessment": checked_execution.get("assessment"),
                "limits": effective,
            },
        }
    )
    # ``du-observed/1`` coverage normalisation keeps only its fixed fields at the
    # top level and stashes the rest in ``coverage.raw``. The additive
    # final-material diagnostics (shared aliases, duplicate bodies, the explicit
    # unread-is-not-absence flag) are exactly what a reader must be able to see
    # without reaching into ``raw``, so they are lifted back up here. This is
    # additive: the schema fields keep their normalised values.
    raw_coverage = observed["coverage"].get("raw") or {}
    for key, value in raw_coverage.items():
        if key not in observed["coverage"]:
            observed["coverage"][key] = value
    return observed


def _route(envelope: Mapping[str, Any]) -> dict[str, Any] | None:
    """Route facts the envelope really carries, or nothing at all."""

    source = envelope.get("source") or envelope.get("subject") or {}
    if not isinstance(source, Mapping):
        return None
    document_kind = _optional_text(source.get("document_kind"), "material.source.document_kind")
    if not document_kind:
        return None
    return {
        "family": None,
        "subtype": None,
        "regime": None,
        "confidence": None,
        "document_kind": document_kind,
        "profile_id": None,
        "raw_source": "final_material_envelope",
    }


def _coverage(
    envelope: Mapping[str, Any],
    originals: Mapping[str, Any],
    source: _Originals,
    selected_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Coverage as the *source* states it, never as the material wishes it were."""

    unread = originals.get("unread") or {}
    if not isinstance(unread, Mapping):
        raise FinalMaterialError("originals.unread must be a mapping")
    opaque_pages = sorted({int(page) for page in (unread.get("opaque_pages") or ())})
    deferred_pages = sorted({int(page) for page in (unread.get("deferred_pages") or ())})
    deferred_unit_ids = sorted({
        str(unit) for unit in (unread.get("deferred_unit_ids") or ())
    })
    unassigned = sorted({str(unit) for unit in (unread.get("unassigned_unit_ids") or ())})
    native_scan = _optional_text(unread.get("native_scan"), "originals.unread.native_scan")
    structure_complete = unread.get("structure_complete")

    pages = {unit["page"] for unit in source.units.values() if unit["page"] is not None}
    unread_pages = set(opaque_pages) | set(deferred_pages)
    complete = bool(structure_complete) and not (
        unread_pages or deferred_unit_ids or unassigned or native_scan not in (None, "complete")
    )
    if not selected_evidence:
        complete = False

    return {
        "native_scan": native_scan,
        "complete": complete,
        "structured_unit_count": len(source.units),
        "opaque_pages": opaque_pages,
        "deferred_pages": deferred_pages,
        "read_pages": sorted(pages - unread_pages) if pages else None,
        "deferred_unit_ids": deferred_unit_ids,
        "unassigned_unit_ids": unassigned,
        "material_group_count": len(_require_sequence(
            envelope.get("evidence_groups", ()), "material.evidence_groups"
        )),
    }


__all__ = [
    "DEFAULT_LIMITS",
    "FINAL_GROUP_KIND",
    "FINAL_OBSERVED_ENTRY_POINT",
    "FINAL_ORIGINALS_SCHEMA_VERSION",
    "FinalMaterialError",
    "observe_final_material",
]
