"""Real-original check: the summary request on actual documents.

Confirms the profile-driven request is buildable from real parsed originals, that it keeps
replayable provenance, and that the Q&A shadow decision shows up in what would be read.

Run: python -X utf8 .planning/du-root/_summary_input_real_probe.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.document_understanding import build_summary_input, understand_units  # noqa: E402
from company_wiki.source_catalog.narrative_evidence import parse_pdf  # noqa: E402

BINDINGS = ROOT / ".planning" / "du-root" / "bindings.local.json"
LABELS = {
    "cn-equity": "恒锋 增发募集说明书",
    "cn-ir": "万润 投资者关系活动记录表",
    "hk-annual": "名创 港股年报",
    "cn-q-business": "中微 2026Q1 季报",
}


def main() -> int:
    bindings = json.loads(BINDINGS.read_text(encoding="utf-8"))
    print(
        f"{'sample':14} {'route':14} {'used':>5} {'pkgs':>5} {'chars':>7} "
        f"{'prov':>5} {'defer':>6} {'shdw':>5}"
    )
    print("-" * 78)
    for sample_id, label in LABELS.items():
        entry = bindings.get(sample_id)
        if not isinstance(entry, dict) or not pathlib.Path(entry["path"]).is_file():
            print(f"{sample_id:14} UNAVAILABLE ({label})")
            continue
        path = pathlib.Path(entry["path"])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            print(f"{sample_id:14} SHA MISMATCH ({label})")
            continue

        parsed = parse_pdf(path, source_id=f"probe:{sample_id}", source_sha256=digest)
        result = understand_units(
            list(parsed.units),
            source_id=f"probe:{sample_id}",
            source_sha256=digest,
            title=label,
            declared_kind="unknown",
            language=None,
        )
        request = build_summary_input(result)

        # Provenance must be complete on real data, not just fixtures.
        known = {u["unit_id"] for u in result["observation"]["units"]}
        cited = {
            m["unit_id"] for p in request["evidence_packages"] for m in p["members"]
        }
        provenance_ok = cited <= known and all(
            m["locator"] for p in request["evidence_packages"] for m in p["members"]
        )
        print(
            f"{sample_id:14} {request['profile_id']:14} "
            f"{request['budget']['packages_used']:>5} "
            f"{len(request['evidence_packages']):>5} "
            f"{request['budget']['chars_used']:>7} "
            f"{'OK' if provenance_ok else 'FAIL':>5} "
            f"{len(request['deferred']):>6} "
            f"{request['excluded']['not_selectable']:>5}"
        )

        # The decision under audit: no non-selectable (text-layer) unit may be sent as
        # evidence, while the same content must still reach the model through its
        # structured counterpart.
        sent_roles = {
            m["role"] for p in request["evidence_packages"] for m in p["members"]
        }
        if "qa_text_shadow" in sent_roles:
            print("   *** VIOLATION: a shadow unit was sent as evidence ***")

        # Show the focus actually selected for this document type.
        print(f"   focus: {request['focus'][:96]}")
        if request["evidence_packages"]:
            top = request["evidence_packages"][0]
            print(
                f"   first package: kind={top['kind']} role={top['section_role']} "
                f"completeness={top['completeness']} members={len(top['members'])}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
