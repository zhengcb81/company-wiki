"""One diagnostic-only budget profile; preserve all product work semantics."""
from __future__ import annotations

from collections import Counter
from functools import wraps
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.document_understanding import pipeline
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded, new_document_work_budget
from company_wiki.source_catalog import narrative_evidence as engine
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

BASE_CHARGE_CODE = WorkBudget.charge.__code__


class ProfileBudget(WorkBudget):
    """Only the root counts. Base scoped children forward to it exactly once."""

    def __post_init__(self):
        super().__post_init__()
        self.accepted = Counter()
        self.rejected = Counter()
        self.accepted_calls = Counter()
        self.rejected_calls = Counter()
        self.forwarding_frames_skipped = 0
        self.unresolved_forwarding_calls = 0

    def charge(self, n=1):
        # One fixed starting frame and at most four base forwarding frames;
        # no inspect.stack, whole-stack traversal or interception of children.
        frame = sys._getframe(1)
        try:
            for _ in range(4):
                if frame.f_code is not BASE_CHARGE_CODE:
                    break
                self.forwarding_frames_skipped += 1
                frame = frame.f_back
            if frame.f_code is BASE_CHARGE_CODE:
                self.unresolved_forwarding_calls += 1
            key = (frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno)
        finally:
            del frame
        before = self.used
        rejected = False
        try:
            return super().charge(n)
        except WorkBudgetExceeded:
            rejected = True
            raise
        finally:
            delta = self.used - before
            if delta:
                self.accepted[key] += delta
                self.accepted_calls[key] += 1
            if rejected:
                self.rejected[key] += n
                self.rejected_calls[key] += 1


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = sorted((ROOT / "src/company_wiki").rglob("*.py"))
    paths.append(ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json")
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def main():
    output = HERE / "ipo-profile.json"
    if output.exists():
        raise FileExistsError(output)
    baseline = load(HERE / "cn-ipo.json")
    frozen = load(HERE / "start-bindings.json")
    source_before = snapshot()
    if any(sha(ROOT / p) != row["actual_sha256"] for p, row in frozen["source_owner17"].items()):
        raise ValueError("Source owner changed; profile is not the frozen product")
    if reading.understand_units is not pipeline.understand_units:
        raise ValueError("Unexpected function alias; do not instrument unknown graph")
    cfg_path = ROOT / "config/source_catalog.yaml"
    cfg = load_catalog_config(cfg_path, project_root=ROOT)
    protected = [cfg_path, cfg.database_path, ROOT / "config/resource_budget.yaml"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    # The normal factory supplies configuration only. The sole charged root
    # ledger is the subclass below, shared unchanged by parse and select.
    configured = new_document_work_budget()
    if configured.used or configured.exhausted or configured.max_work_units != 16_000_000:
        raise ValueError("Unexpected configured budget")
    budget = ProfileBudget(configured.max_work_units, phase=configured.phase)
    stages = []
    restores = []

    def instrument(owner, name, label, wrapper=None):
        original = getattr(owner, name)
        if wrapper is None:
            @wraps(original)
            def wrapper(*args, **kwargs):
                entry, started = budget.used, time.perf_counter()
                error = None
                try:
                    return original(*args, **kwargs)
                except BaseException as exc:
                    error = type(exc).__name__
                    raise
                finally:
                    stages.append({"stage": label, "entry_used": entry, "exit_used": budget.used,
                        "inclusive_accepted_delta": budget.used - entry, "exhausted_on_exit": budget.exhausted,
                        "exception": error, "wall_seconds": round(time.perf_counter() - started, 6)})
        restores.append((owner, name, original))
        setattr(owner, name, wrapper)
        return wrapper

    instrument(reading, "_understand", "reading._understand")
    shared_wrapper = instrument(reading, "understand_units", "pipeline.understand_units")
    instrument(pipeline, "understand_units", "pipeline.understand_units", wrapper=shared_wrapper)
    instrument(reading, "_candidates", "reading._candidates")
    catalog = SourceCatalog(cfg)
    started = time.perf_counter()
    parse_work = None
    parsed = package = None
    error = None
    try:
        ref = SourceRef(**baseline["source_ref"])
        verified = SourceVersionReader(catalog).open_version(ref, purpose="preview")
        if hashlib.sha256(verified.data).hexdigest() != ref.content_sha256:
            raise ValueError("Source changed")
        parsed = engine.parse_pdf_bytes(verified.data, source_id=ref.source_id, source_sha256=ref.content_sha256,
            language=baseline["language"], selector_version="0.9.0",
            reading_context=PdfReadingContext(baseline["title"], baseline["declared_kind"], baseline["language"]),
            work_budget=budget)
        parse_work = budget.used
        if not budget.exhausted:
            package = engine.select_narrative_evidence(parsed, title=baseline["title"],
                existing_kind=baseline["declared_kind"], max_selected=112, selector_version="0.9.0", work_budget=budget)
    except WorkBudgetExceeded as exc:
        error = {k: getattr(exc, k, None) for k in ("phase", "used", "requested", "limit")}
    finally:
        for owner, name, original in reversed(restores):
            setattr(owner, name, original)
        store_constructed = catalog._store is not None
        catalog.close()
    elapsed = time.perf_counter() - started
    protected_unchanged = before == {str(p.relative_to(ROOT)): sha(p) for p in protected}
    if not protected_unchanged or source_before != snapshot() or store_constructed:
        raise ValueError("Protected/source/Store boundary changed")
    accepted = sum(budget.accepted.values())
    if accepted != budget.used or budget.unresolved_forwarding_calls:
        raise ValueError("Profiler cannot explain charged work without double counting")
    keys = set(budget.accepted) | set(budget.rejected)
    hot = []
    for file, function, line in sorted(keys, key=lambda k: (-budget.accepted[k], -budget.rejected[k], k)):
        path = Path(file)
        name = str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else path.name
        key = file, function, line
        hot.append({"file": name, "function": function, "line": line,
            "accepted_delta": budget.accepted[key], "accepted_calls": budget.accepted_calls[key],
            "rejected_requested": budget.rejected[key], "rejected_calls": budget.rejected_calls[key]})
    outcome = {"parsed_units": len(parsed.units) if parsed else None, "parsed_pages": parsed.page_count if parsed else None,
        "parse_work": parse_work, "work_used": budget.used, "work_limit": budget.max_work_units,
        "exhausted": budget.exhausted, "status": package.status if package else None,
        "candidate_count": package.candidate_count if package else None,
        "selected_count": len(package.evidence_spans) if package else None}
    expected = {"parsed_units": baseline["parsed_unit_count"], "parsed_pages": baseline["parsed_page_count"],
        "parse_work": baseline["parse_work"], "work_used": baseline["work_budget"]["used"],
        "work_limit": baseline["work_budget"]["limit"], "exhausted": baseline["work_budget"]["exhausted"],
        "status": baseline["selection"]["status"], "candidate_count": baseline["selection"]["candidate_count"],
        "selected_count": baseline["selection"]["selected_count"]}
    result = {"schema_version": "independent-single-account-ipo-work-profile/1",
        "scope": "Diagnostic-only subclass and function boundary wrappers; no model compiler, source projection or repeated baseline replay",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_ref": baseline["source_ref"], "source_original_sha_verified": True,
        "source_tree_sha256": hashlib.sha256(json.dumps(source_before, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "source_owner17_matches_frozen_run": True, "source_stable": True,
        "profile_code_sha256": sha(Path(__file__)), "baseline_result_sha256": sha(HERE / "cn-ipo.json"),
        "protected_sha256": before, "protected_unchanged": True, "write_store_constructed": False,
        "outcome": outcome, "same_outcome_as_uninstrumented_run": outcome == expected,
        "comparison": {k: {"profile": outcome[k], "baseline": expected[k], "equal": outcome[k] == expected[k]} for k in outcome},
        "wall_seconds_diagnostic_not_benchmark": round(elapsed, 6), "budget_exception": error,
        "accounting": {"accepted_total": accepted, "root_used": budget.used, "accepted_equals_root_used": accepted == budget.used,
            "rejected_requested_total": sum(budget.rejected.values()), "root_only_no_double_count": True,
            "forwarding_frames_skipped": budget.forwarding_frames_skipped, "unresolved_forwarding_calls": budget.unresolved_forwarding_calls,
            "interpretation": "Rejected requested units are tail attempts, never actual accepted work; inclusive nested stage deltas must not be summed."},
        "stage_boundaries": stages, "caller_hotspots": hot,
        "hooks_restored": all(getattr(owner, name) is original for owner, name, original in restores),
        "no_additional_source_or_model_work_after_exhaustion": True,
        "calls": {"model": 0, "api": 0, "download": 0, "raw_copy": 0}, "temporary_directories_created": 0,
        "limits": ["Constant-depth frame observation changes timing; this is diagnostic work accounting, not a timing benchmark.",
            "If outcome differs, do not assume it represents the uninstrumented run. Frozen three-case report remains unchanged."]}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outcome": outcome, "same_as_baseline": outcome == expected,
        "stages": stages, "top_accepted_hotspots": hot[:12], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
