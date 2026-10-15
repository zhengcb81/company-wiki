"""collect_source_signals: du4-source-signal-observation/1 -> du4-source-signals/1.

A bounded pure collector over already-observed native carriers.  It never
opens a file, never parses a DOM, never scans the document text, never calls a
provider and never decides a document family or route.

Evidence semantics
------------------

* Only carriers the producer observed natively can produce evidence.  Visible
  ``dei:DocumentType`` values and own-form labels become scoped form evidence;
  native speaker turns become turn evidence.  Colon/caps shape never creates a
  turn, and there is no forbidden-word label blacklist: financial labels and
  captions are excluded structurally because no native carrier stands behind
  them, while real table-shaped attributed turns stay admissible.
* The printed literal is preserved verbatim (``value``); ``normalized_value``
  only strips a leading ``FORM`` label and upper-cases.  The limited literal
  vocabulary check is a known/unknown diagnostic, not a family classification,
  and no route, family or confidence is ever produced.
* Declarative metadata (``declared_form``, filename/title, provider
  ``form_type``) may only generate conflict diagnostics; it can never
  manufacture an observed fact.
* Each native unit is one DOM owner.  Spans of one unit may be concatenated
  (same-owner inline wrapping); tokens from different owners are never joined
  into an invented value.  A carrier whose units span parents is refused
  rather than paired across scopes.

Work accounting
---------------

``work_budget`` is the caller-owned existing ``WorkBudget`` instance; this
module neither resets nor creates one.  Building the unit index, inspecting
carriers and resolving references are metered operations.  On exhaustion the
determined results are kept and the call returns ``partial`` with honest
counts instead of claiming to have read what it did not.

Structural malformation (wrong schema, duplicate carrier unit ids, impossible
reference indices) raises ``ValueError``.  Insufficient source text is a
per-item diagnostic: a reference the source text cannot back is never clamped
and never borrowed onto another unit.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, cast

from ..layout_hints.contract import WorkBudget, WorkBudgetExceeded
from .contract import (
    CARRIER_KINDS,
    FORM_CARRIER_KINDS,
    KIND_DEI,
    KIND_TURN,
    NATIVE_ATTRIBUTE_KEYS,
    SCHEMA_IN,
    SCHEMA_OUT,
    declared_literal,
    is_known_form_literal,
    normalize_form_value,
    ref_text,
    require,
    validate_ref_shape,
    validate_unit_shape,
)

__all__ = ["collect_source_signals", "SCHEMA_IN", "SCHEMA_OUT"]

_CONFLICT_CODES = frozenset({"FORM_VALUE_CONFLICT", "DECLARED_FORM_CONFLICT"})


def collect_source_signals(
    observation: Mapping[str, Any], *, work_budget: WorkBudget
) -> dict:
    require(isinstance(observation, Mapping), "observation must be a mapping")
    require(
        observation.get("schema_version") == SCHEMA_IN,
        f"schema_version must be {SCHEMA_IN}",
    )
    units = cast(Mapping[str, Any], observation.get("units"))
    require(isinstance(units, Mapping), "units must be a mapping")
    carriers = cast(list, observation.get("carriers"))
    require(isinstance(carriers, list), "carriers must be a list")
    declared_form = cast("str | None", observation.get("declared_form"))
    require(
        declared_form is None or isinstance(declared_form, str),
        "declared_form must be a string or null",
    )
    collector = _Collector(units, carriers, declared_form, work_budget)
    try:
        collector.run()
    except WorkBudgetExceeded:
        collector.exhausted = True
    return collector.result()


class _Collector:
    def __init__(
        self,
        units: Mapping[str, Any],
        carriers: list,
        declared_form: str | None,
        budget: WorkBudget,
    ) -> None:
        self.units = units
        self.carriers = carriers
        self.declared_form = declared_form
        self.budget = budget
        self.start_used = budget.used
        self.diagnostics: list[dict] = []
        self.form_entries: list[dict] = []
        self.turn_entries: list[dict] = []
        self.reserved_unit_ids: list[str] = []
        self.seen_carrier_keys: set[str] = set()
        self.observed_form_values: set[str] = set()
        self.observed_form_unit_ids: list[str] = []
        self.form_values_by_parent: dict[str, set[str]] = {}
        self.form_unit_ids_by_parent: dict[str, list[str]] = {}
        self.conflict_parents: list[str] = []
        self.conflict_parents_seen: set[str] = set()
        self.indexed_units = 0
        self.started_carriers = 0
        self.completed_carriers = 0
        self.resolved_carriers = 0
        self.dropped_carriers = 0
        self.resolved_any = False
        self.dropped_any = False
        self.exhausted = False

    # -- pipeline -------------------------------------------------------

    def run(self) -> None:
        self._index_units()
        for position, raw in enumerate(self.carriers):
            self._process_carrier(position, raw)
            self.completed_carriers += 1

    def _index_units(self) -> None:
        for unit_id, unit in self.units.items():
            self.budget.charge(1)
            require(
                bool(isinstance(unit_id, str) and unit_id),
                "units keys must be non-empty strings",
            )
            validate_unit_shape(unit_id, unit)
            self.indexed_units += 1

    def _process_carrier(self, position: int, raw: Any) -> None:
        where = f"carriers[{position}]"
        require(isinstance(raw, Mapping), f"{where} must be a mapping")
        kind = raw.get("kind")
        require(kind in CARRIER_KINDS, f"{where}.kind must be one of {sorted(CARRIER_KINDS)}")
        unit_ids = raw.get("unit_ids")
        require(isinstance(unit_ids, list), f"{where}.unit_ids must be a list")
        seen: set[str] = set()
        for slot, unit_id in enumerate(unit_ids):
            require(
                bool(isinstance(unit_id, str) and unit_id),
                f"{where}.unit_ids[{slot}] must be a non-empty string",
            )
            require(unit_id not in seen, f"{where}.unit_ids contains duplicate {unit_id!r}")
            seen.add(unit_id)
        value_refs = raw.get("value_refs")
        require(isinstance(value_refs, list), f"{where}.value_refs must be a list")
        parent_id = raw.get("parent_id")
        require(
            bool(isinstance(parent_id, str) and parent_id),
            f"{where}.parent_id must be a non-empty string",
        )
        attributes = raw.get("attributes")
        require(
            attributes is None or isinstance(attributes, Mapping),
            f"{where}.attributes must be a mapping or null",
        )
        attributes = attributes or {}

        self.budget.charge(1)
        self.started_carriers += 1

        carrier_key = json.dumps(raw, sort_keys=True, default=str, ensure_ascii=False)
        if carrier_key in self.seen_carrier_keys:
            self._diag("DUPLICATE_CARRIER", unit_ids, "identical carrier already collected")
            self._resolve_carrier()
            return
        self.seen_carrier_keys.add(carrier_key)

        ignored = sorted(set(attributes) - NATIVE_ATTRIBUTE_KEYS)
        if ignored:
            self._diag(
                "DECLARED_ATTRIBUTE_IGNORED",
                unit_ids,
                f"non-native attribute keys {ignored} are declarative and ignored",
            )

        if not self._check_units(where, unit_ids, parent_id):
            return
        spans = self._resolve_value_refs(where, value_refs, set(unit_ids))
        if spans is None:
            return
        if kind in FORM_CARRIER_KINDS:
            self._collect_form(kind, raw, unit_ids, spans, attributes)
        else:
            self._collect_turn(raw, unit_ids, spans, attributes)

    # -- shared validation ---------------------------------------------

    def _check_units(self, where: str, unit_ids: list, parent_id: str) -> bool:
        for unit_id in unit_ids:
            self.budget.charge(1)
            unit = self.units.get(unit_id)
            if unit is None:
                self._drop(
                    "UNKNOWN_REF_UNIT",
                    [unit_id],
                    f"{where} references unit {unit_id!r} which is not in units",
                )
                return False
            if unit.get("parent_id") != parent_id:
                self._drop(
                    "CARRIER_PARENT_MISMATCH",
                    [unit_id],
                    f"{where} unit parent {unit.get('parent_id')!r} != carrier parent {parent_id!r}",
                )
                return False
        return True

    def _resolve_value_refs(
        self, where: str, value_refs: list, carrier_unit_ids: set[str]
    ) -> list[tuple[str, int, int, str]] | None:
        spans: list[tuple[str, int, int, str]] = []
        for slot, raw_ref in enumerate(value_refs):
            self.budget.charge(1)
            unit_id, start, end = validate_ref_shape(
                raw_ref, where=f"{where}.value_refs[{slot}]"
            )
            unit = self.units.get(unit_id)
            if unit is None:
                self._drop(
                    "UNKNOWN_REF_UNIT",
                    [unit_id],
                    f"{where}.value_refs[{slot}] references missing unit {unit_id!r}",
                )
                return None
            text = unit["text"]
            if end > len(text):
                self._drop(
                    "REF_EXCEEDS_TEXT",
                    [unit_id],
                    f"{where}.value_refs[{slot}] claims [{start}, {end}) "
                    f"but the source text is {len(text)} characters",
                )
                return None
            if unit_id not in carrier_unit_ids:
                self._drop(
                    "REF_OUTSIDE_CARRIER",
                    [unit_id],
                    f"{where}.value_refs[{slot}] points outside the carrier's own units",
                )
                return None
            if start == end:
                self._drop(
                    "EMPTY_VALUE_REF",
                    [unit_id],
                    f"{where}.value_refs[{slot}] is an empty span; an unknown value "
                    "is never an empty string",
                )
                return None
            spans.append((unit_id, start, end, ref_text(text, start, end)))
        return spans

    # -- form evidence -------------------------------------------------

    def _collect_form(
        self,
        kind: str,
        raw: Mapping[str, Any],
        unit_ids: list,
        spans: list[tuple[str, int, int, str]],
        attributes: Mapping[str, Any],
    ) -> None:
        visibility = attributes.get("visibility")
        if kind == KIND_DEI and isinstance(visibility, str) and visibility != "visible":
            self._drop(
                "NON_VISIBLE_DEI",
                unit_ids,
                f"DEI carrier visibility is {visibility!r}; hidden, excluded or "
                "externally linked facts are not visible observations",
            )
            return
        concept = attributes.get("concept")
        concept_str = concept if isinstance(concept, str) and concept else None
        if (
            kind == KIND_DEI
            and concept_str is not None
            and concept_str.strip().lower() != "dei:documenttype"
        ):
            self._drop(
                "DEI_CONCEPT_MISMATCH",
                unit_ids,
                f"concept {concept_str!r} is not dei:DocumentType and cannot be form evidence",
            )
            return

        owner_units = {span[0] for span in spans}
        if len(owner_units) > 1:
            self._drop(
                "SPLIT_OWNER_VALUE",
                sorted(owner_units),
                "value spans belong to different native owners and are never "
                "concatenated into one invented value",
            )
            return
        ordered = sorted(spans, key=lambda span: span[1])
        for previous, current in zip(ordered, ordered[1:]):
            if current[1] < previous[2]:
                self._drop(
                    "OVERLAPPING_VALUE_REFS",
                    [previous[0]],
                    "value spans overlap inside one owner unit",
                )
                return
        if not ordered:
            self._drop(
                "EMPTY_VALUE_REF",
                list(unit_ids),
                "carrier carries no value span; an unknown value is never an empty string",
            )
            return

        value = "".join(span[3] for span in ordered)
        normalized = normalize_form_value(value)
        if not is_known_form_literal(normalized):
            self._diag(
                "UNRECOGNIZED_FORM_LITERAL",
                list(unit_ids),
                f"observed literal {value!r} is outside the limited printed-form "
                "vocabulary; the fact itself is kept",
            )
        entry = {
            "parent_id": raw.get("parent_id"),
            "value": value,
            "origin": kind,
            "carrier_unit_ids": list(unit_ids),
            "value_refs": [
                {"unit_id": uid, "char_start": start, "char_end": end}
                for uid, start, end, _ in spans
            ],
            "normalized_value": normalized,
            "concept": concept_str,
        }
        self.form_entries.append(entry)
        self._note_form_value(entry)
        self._reserve(unit_ids)
        self._resolve_carrier()

    # -- turn evidence -------------------------------------------------

    def _collect_turn(
        self,
        raw: Mapping[str, Any],
        unit_ids: list,
        spans: list[tuple[str, int, int, str]],
        attributes: Mapping[str, Any],
    ) -> None:
        speaker = attributes.get("speaker")
        speaker_str = speaker if isinstance(speaker, str) and speaker else None
        turn_id = attributes.get("turn_id")
        turn_id_str = turn_id if isinstance(turn_id, str) and turn_id else None
        turn_role = attributes.get("turn_role")
        turn_role_str = turn_role if isinstance(turn_role, str) and turn_role else None

        speaker_units = {span[0] for span in spans}
        body_refs = [
            {"unit_id": unit_id, "char_start": 0, "char_end": len(self.units[unit_id]["text"])}
            for unit_id in unit_ids
            if unit_id not in speaker_units and self.units[unit_id]["text"]
        ]
        identity = bool(spans) or speaker_str is not None or turn_id_str is not None
        content = bool(body_refs) or turn_id_str is not None
        if not content:
            self._drop(
                "TURN_WITHOUT_BODY_OR_ASSOCIATION",
                list(unit_ids),
                "carrier has no speech body and no source-owned turn association",
            )
            return
        if not identity:
            self._drop(
                "TURN_WITHOUT_NATIVE_IDENTITY",
                list(unit_ids),
                "carrier carries no native speaker, speaker mention or turn id",
            )
            return

        entry = {
            "parent_id": raw.get("parent_id"),
            "speaker_refs": [
                {"unit_id": uid, "char_start": start, "char_end": end}
                for uid, start, end, _ in spans
            ],
            "body_refs": body_refs,
            "turn_id": turn_id_str,
            "turn_role": turn_role_str,
            "origin": KIND_TURN,
            "speaker": speaker_str,
        }
        self.turn_entries.append(entry)
        self._reserve(unit_ids)
        self._resolve_carrier()

    # -- declared metadata and scope conflicts -------------------------
    #
    # Both passes are O(1) per emitted entry or per call: value conflicts are
    # noted as entries arrive and the declared comparison reads precomputed
    # sets.  They therefore run even when the work budget is already spent,
    # so conflicts among determined evidence are never silently unreported.

    def _note_form_value(self, entry: dict) -> None:
        parent_id = entry["parent_id"]
        normalized = entry["normalized_value"]
        self.observed_form_values.add(normalized)
        self.observed_form_unit_ids.extend(entry["carrier_unit_ids"])
        self.form_unit_ids_by_parent.setdefault(parent_id, []).extend(
            entry["carrier_unit_ids"]
        )
        values = self.form_values_by_parent.setdefault(parent_id, set())
        values.add(normalized)
        if len(values) > 1 and parent_id not in self.conflict_parents_seen:
            self.conflict_parents_seen.add(parent_id)
            self.conflict_parents.append(parent_id)

    def _materialize_conflict_diagnostics(self) -> None:
        for parent_id in self.conflict_parents:
            self._diag(
                "FORM_VALUE_CONFLICT",
                self.form_unit_ids_by_parent[parent_id],
                f"parent {parent_id!r} carries conflicting form values "
                f"{sorted(self.form_values_by_parent[parent_id])}",
            )

    def _apply_declared_form(self) -> None:
        declared = self.declared_form
        if declared is None or not declared.strip():
            return
        if not self.form_entries:
            self._diag(
                "DECLARED_FORM_UNOBSERVED",
                [],
                f"declared_form={declared!r} has no observed carrier in the body; "
                "declared metadata never manufactures observed facts",
            )
            return
        literal = declared_literal(normalize_form_value(declared))
        if literal is None:
            return
        if literal not in self.observed_form_values:
            self._diag(
                "DECLARED_FORM_CONFLICT",
                list(self.observed_form_unit_ids),
                f"declared literal {literal!r} conflicts with observed "
                f"{sorted(self.observed_form_values)}",
            )

    # -- output --------------------------------------------------------

    def _reserve(self, unit_ids: list) -> None:
        for unit_id in unit_ids:
            if unit_id not in self.reserved_unit_ids:
                self.reserved_unit_ids.append(unit_id)

    def _diag(self, code: str, unit_ids: Any, detail: str) -> None:
        self.diagnostics.append(
            {"code": code, "unit_ids": sorted(set(unit_ids)), "detail": detail}
        )

    def _drop(self, code: str, unit_ids: Any, detail: str) -> None:
        self._diag(code, unit_ids, detail)
        self.dropped_any = True
        self.dropped_carriers += 1

    def _resolve_carrier(self) -> None:
        self.resolved_any = True
        self.resolved_carriers += 1

    def result(self) -> dict:
        # O(1) passes over precomputed sets: they must run even after budget
        # exhaustion so determined evidence is still fully reported.
        self._apply_declared_form()
        self._materialize_conflict_diagnostics()
        if self.exhausted:
            self._diag(
                "WORK_BUDGET_EXCEEDED",
                [],
                "collection interrupted at the caller work budget; "
                f"indexed {self.indexed_units}/{len(self.units)} units and "
                f"collected {self.completed_carriers}/{len(self.carriers)} carriers; "
                "determined results are kept and nothing unread is claimed",
            )
        return {
            "schema_version": SCHEMA_OUT,
            "source_form_evidence": self.form_entries,
            "turn_evidence": self.turn_entries,
            "reserved_unit_ids": list(self.reserved_unit_ids),
            "diagnostics": list(self.diagnostics),
            "status": self._status(),
            "work_used": self.budget.used - self.start_used,
            "observed_counts": {
                "units_indexed": self.indexed_units,
                "carriers_seen": self.started_carriers,
                "carriers_resolved": self.resolved_carriers,
                "carriers_dropped": self.dropped_carriers,
                "evidence_chars": self._evidence_chars(),
                "reserved_unit_chars": sum(
                    len(self.units[unit_id]["text"])
                    for unit_id in self.reserved_unit_ids
                ),
            },
        }

    def _evidence_chars(self) -> int:
        total = sum(len(entry["value"]) for entry in self.form_entries)
        for entry in self.turn_entries:
            for key in ("speaker_refs", "body_refs"):
                total += sum(
                    item["char_end"] - item["char_start"] for item in entry[key]
                )
        return total

    def _status(self) -> str:
        if self.exhausted:
            return "partial"
        if any(item["code"] in _CONFLICT_CODES for item in self.diagnostics):
            return "partial"
        if self.dropped_any:
            return "partial" if self.resolved_any else "unavailable"
        return "complete"
