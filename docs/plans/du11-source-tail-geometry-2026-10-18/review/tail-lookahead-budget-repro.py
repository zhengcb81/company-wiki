"""Pure budget monotonicity control; no originals, clients or environment reads."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from unit.du11_tail_integration.test_tail_source_wiring import rows
from unit.document_understanding_selection.test_reading_native_continuity import native, run


def make_case():
    pair = rows()
    for wire, _metadata, _profile in pair:
        wire["layout"].pop("column", None)
    anchor = native("公司持续开展新产品研发，并推进客户验证。", 2,
                    box=[89.88, 140.8, 530.76, 172])
    anchor[0]["hints"]["font_runs"][0]["font_size"] = 10.45
    return [*pair, anchor]


def exercise(cap):
    values = make_case()
    result = run(values, max_work_units=cap)
    pair_ids = {v[0]["unit_id"] for v in values[:2]}
    deferred = set(result["deferred_unit_ids"])
    return {"cap": cap, "complete": result["complete"],
            "window_count": len(result["windows"]),
            "both_pair_members_deferred": pair_ids <= deferred,
            "deferred_unit_ids": result["deferred_unit_ids"],
            "unexamined_from_index": result["unexamined_from_index"],
            "standalone_unit_count": result["standalone_unit_count"]}


if __name__ == "__main__":
    results = [exercise(cap) for cap in (4, 5, 6)]
    print(json.dumps(results))
    raise SystemExit(0 if all(r["both_pair_members_deferred"] for r in results) else 1)
