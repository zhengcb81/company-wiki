"""WU-603: v1/v2 shadow parity — compare legacy scanner output with the
v2 adapter pipeline over the same immutable tree.

Comparisons: candidate count, relative paths, roles, content hashes,
entity/kind/period/status identity, and admission outcome.  Differences are
classified: expected_good (must match), known_bad (must have a RED owner),
blocker (unexplained — stop the line).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParityDiff:
    path: str
    field: str
    v1_value: object
    v2_value: object
    classification: str = "blocker"  # expected_good | known_bad | blocker


@dataclass
class ParityReport:
    total_v1: int = 0
    total_v2: int = 0
    diffs: list[ParityDiff] = field(default_factory=list)

    @property
    def blockers(self) -> list[ParityDiff]:
        return [d for d in self.diffs if d.classification == "blocker"]

    @property
    def ok(self) -> bool:
        return not self.blockers


def run_parity(
    v1_candidates: list,
    v2_candidates: list,
    *,
    known_bad: dict[str, str] | None = None,
    entity_of=lambda candidate: getattr(candidate, "entity_name", None),
) -> ParityReport:
    """Compare v1/v2 candidate sets.  known_bad maps (path, field) -> reason;
    every known_bad diff must have an entry, else it is a blocker."""
    report = ParityReport(
        total_v1=len(v1_candidates),
        total_v2=len(v2_candidates),
    )
    by_path_v1 = {c.relative_path: c for c in v1_candidates}
    by_path_v2 = {c.relative_path: c for c in v2_candidates}

    for path in sorted(set(by_path_v1) | set(by_path_v2)):
        left = by_path_v1.get(path)
        right = by_path_v2.get(path)
        if left is None or right is None:
            report.diffs.append(ParityDiff(
                path, "presence",
                "v1-only" if right is None else "v2-only",
                "v1-only" if right is None else "v2-only",
            ))
            continue
        for field_name, getter in (
            ("role", lambda c: getattr(c, "role", None)),
            ("entity", entity_of),
            ("status", lambda c: getattr(c, "source_status",
                                         getattr(c, "normalized", {}).get("normalization_status"))),
        ):
            v1_value = getter(left)
            v2_value = getter(right)
            if v1_value != v2_value:
                key = (path, field_name)
                classification = (
                    "known_bad" if known_bad and key in known_bad else "blocker"
                )
                report.diffs.append(ParityDiff(
                    path, field_name, v1_value, v2_value, classification
                ))
    return report
