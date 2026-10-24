"""Observe all frozen annual14 targets in one real, unmodified selector run.

Reuse the earlier bounded observer, replacing only its review-specific labels.
No model call, raw copy, score/limit override or content grading is performed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in HERE.parents if (parent / "pyproject.toml").exists())
INPUTS = HERE.parent
OLD_TRACE = INPUTS / "annual14-v2/trace_targets.py"
CHECKLIST = INPUTS / "annual14/review.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text)


def main():
    args = sys.argv[1:]
    output = Path(args[args.index("--output") + 1]).resolve()
    trace_output = Path(args[args.index("--trace-output") + 1]).resolve()
    assert output.parent == trace_output.parent == HERE
    assert not output.exists() and not trace_output.exists(), "Do not overwrite old observations"
    targets = json.loads(CHECKLIST.read_text(encoding="utf-8"))["rows"]
    assert len(targets) == 14
    source_files = sorted((ROOT / "src/company_wiki").rglob("*.py"))
    before = {str(path.relative_to(ROOT)): digest(path) for path in source_files}
    spec = importlib.util.spec_from_file_location("w08_existing_bounded_observer", OLD_TRACE)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)

    def labels(unit):
        page = getattr(getattr(unit, "coordinates", None), "page_number", None)
        text = compact(getattr(unit, "raw_text", "") or "")
        if len(text) < 16:
            return []
        return [row["target_id"] for row in targets if any(
            page == support.get("pdf_page") and len(quote := compact(support.get("quote", ""))) >= 16
            and (quote in text or text in quote)
            for support in row.get("fallback", {}).get("original_support", ())) ]

    observer.labels = labels
    observer.MAX_UNIT_TEXT_CHARS = 400
    # Preserve every observation while avoiding whitespace-only inflation of
    # the old indented trace. The existing 512KiB bound remains unchanged.
    observer.json = SimpleNamespace(loads=json.loads, dumps=lambda value, **kwargs:
        json.dumps(value, **{**kwargs, "indent": None, "separators": (",", ":")}))
    observer.main()
    after = {str(path.relative_to(ROOT)): digest(path) for path in source_files}
    assert before == after, "Production code changed during the real selection"
    selection = json.loads(output.read_text(encoding="utf-8"))
    trace = json.loads(trace_output.read_text(encoding="utf-8"))
    assert len(trace["targets"]) <= 256, "Observer target bound exceeded"
    receipt = {
        "schema_version": "w08-all-target-replay/1", "argv": args,
        "observer_sha256": digest(OLD_TRACE), "wrapper_sha256": digest(Path(__file__)),
        "checklist_sha256": digest(CHECKLIST), "selection_sha256": digest(output),
        "trace_sha256": digest(trace_output), "source_count": len(before),
        "source_digest": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        "source_stable": True, "head": __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "changed_source_sha256": {path: value for path, value in before.items()
            if Path(path).name in {"narrative_reporting_rules.py", "narrative_source_purpose.py",
                                  "narrative_business_meaning.py"}},
        "observed_target_units": len(trace["targets"]),
        "observed_target_labels": sorted({label for row in trace["targets"] for label in row["target"]}),
        "physical_pages": selection["physical_pages"], "selected_count": selection["selected_count"],
        "selected_chars": selection["selected_chars"], "work_budget": selection["work_budget"],
        "source_ref": selection["source_ref"], "protected_unchanged": selection["protected_unchanged"],
        "content_quality": "not_regraded", "external_model_calls": 0, "downloads": 0, "raw_copies": 0,
        "limits": "Original 96 spans / 48000 characters / 16M work; unchanged by observation",
    }
    (HERE / "replay-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
