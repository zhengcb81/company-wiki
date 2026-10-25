"""Observe actual counter metadata; do not replace layout or scope decisions."""
from __future__ import annotations
import json
from pathlib import Path
import sys

from company_wiki.document_understanding.structure import layout, sections
from replay_current import load

HERE = Path(__file__).resolve().parent


def main():
    label = sys.argv[1] if len(sys.argv) == 2 else "initial"
    if not label.isalnum():
        raise ValueError("invalid observation label")
    observer = load("actual_scope_observer", HERE / "probe_real_structure.py")
    observer.OUTPUT = HERE / f"real-counter-structure-{label}.json"
    original = sections._native_list_scopes
    observations = []
    context = {}

    def inspect(ordering, native_context=None):
        if native_context is not None:
            context.update(coverage_complete=native_context.coverage_complete,
                unique=native_context.unique, unproven_pages=sorted(native_context.unproven_pages))
        for unit in ordering.ordered:
            if len(unit.text) <= 30 and (" / 249" in unit.text or unit.page in (13, 14) and "/" in unit.text):
                observations.append({"page": unit.page, "text": unit.text,
                    "source_id": unit.source_id, "page_width": unit.page_width,
                    "page_height": unit.page_height, "bbox": unit.bbox,
                    "table_id": unit.table_id, "dom_path": unit.dom_path,
                    "is_table_furniture": unit.is_table_furniture,
                    "counter_match": layout._page_counter(unit), "edge": layout._counter_edge(unit),
                    "classified_furniture": unit.unit_id in ordering.running_header_ids})
        return original(ordering, native_context)

    sections._native_list_scopes = inspect
    try:
        observer.main()
    finally:
        sections._native_list_scopes = original
    output = HERE / f"real-counter-observation-{label}.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(observations, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with (HERE / f"real-native-context-{label}.json").open("x", encoding="utf-8") as stream:
        json.dump(context, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"counters": len(observations), "matched": sum(o["counter_match"] is not None for o in observations),
        "edges": sum(o["edge"] is not None for o in observations), "context": context,
        "actual_13_14": [o for o in observations if o["page"] in (13, 14)]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
