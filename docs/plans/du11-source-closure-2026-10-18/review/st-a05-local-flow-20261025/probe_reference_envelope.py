"""Observe the production reference-envelope decision, without changing it."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

from company_wiki.source_catalog import narrative_reading as reading

HERE = Path(__file__).resolve().parent
rows = []
original = reading.within_reference_envelope


def observe(targets, contexts, declarations, units, **kwargs):
    result = original(targets, contexts, declarations, units, **kwargs)
    expand = kwargs.get("expand", lambda uid: (uid,))
    all_ids = list(dict.fromkeys(uid for key in (*targets, *contexts, *declarations) for uid in expand(key)))
    if len(rows) < 30 and any(units[uid].coordinates.page_number == 14 for uid in targets if uid in units):
        rows.append({"accepted": result, "target_ids": list(targets), "context_ids": list(contexts),
            "declaration_ids": list(declarations), "original_count": len(all_ids),
            "block_count": len({(units[uid].coordinates.page_number, units[uid].metadata.get("pdf_block")) for uid in all_ids}),
            "character_count": sum(len(units[uid].raw_text) for uid in all_ids),
            "originals": [{"unit_id": uid, "page": units[uid].coordinates.page_number,
                "paragraph": units[uid].coordinates.paragraph_index, "block": units[uid].metadata.get("pdf_block"),
                "text": units[uid].raw_text} for uid in all_ids]})
    return result


def main():
    output = HERE / "reference-envelope-before.json"
    if output.exists():
        raise FileExistsError(output)
    path = HERE.parent / "st-a13-recognition-scope-20261025/replay.py"
    spec = spec_from_file_location("existing_source_observer", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE
    reading.within_reference_envelope = observe
    try:
        sys.argv = [str(path), "attempt02"]
        module.main()
    finally:
        reading.within_reference_envelope = original
        with output.open("x", encoding="utf-8") as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


if __name__ == "__main__":
    main()
