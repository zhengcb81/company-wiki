"""Run the N5-DOCSET multi-document quality benchmark (no model, no network).

Parses each registered original with the repository's existing parser, runs the
existing selector, replays every selected locator, re-reads every golden quote
from its cited locator, evaluates, self-validates the report and writes
``report.json``.

Usage::

    python benchmarks/narrative_document_types/run_benchmark.py \
        --output benchmarks/narrative_document_types/report.json
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
for _entry in (REPO_ROOT / "src", PACKAGE_ROOT):
    entry = str(_entry)
    if entry not in sys.path:
        sys.path.insert(0, entry)

from company_wiki.source_catalog.narrative_evidence import (  # noqa: E402
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    parse_pdf,
    parse_transcript_text,
    select_narrative_evidence,
    verify_pdf_evidence_spans,
    verify_transcript_evidence_spans,
)
from company_wiki.source_contract import source_id_for_sha256  # noqa: E402

from evaluator import (  # noqa: E402
    SCHEMA_VERSION,
    evaluate,
    normalize_text,
    validate_report,
)

CARD_BASELINE = "e46108b4f30d5b7e47bfc712e360f173c00b702c"

SCOPE_DEFINITION = (
    "9 real originals across annual/semi/quarterly/prospectus/equity-offering/"
    "convertible/procedural-IR/valuable-IR/earnings-call types. Golden points were "
    "written after reading the cited pages or lines; the selector output was never "
    "used as the answer key. Coverage denominators only count golden points that are "
    "verified at their cited locator and that sit inside the sample's declared "
    "read_scope; noise and duplicate denominators are stated per row."
)

SCOPE_DENOMINATORS = {
    "required_coverage": "verified required positive golden points inside the declared read_scope of each sample",
    "selected_noise_rate": "in-scope selected spans that carry at least one golden point (positive or negative)",
    "duplicate_ratio": "all selected spans of the sample",
    "source_bytes": "byte_size of the registered original",
}

LIMITATIONS = [
    "A targeted read of the cited sections, not an exhaustive read of every page of every filing; uncovered ranges are recorded per sample.",
    "A golden miss means the selector did not reproduce the quoted passage inside its selected spans, not that the passage is unimportant.",
    "Noise rate is judged only over in-scope selected spans that a golden point can adjudicate; unjudged in-scope spans are reported separately.",
    "Locators use the 1-based PDF page index, which can differ from the printed folio on the page.",
    "No model call, no network, and no download is performed by this runner.",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(sample: Mapping[str, Any], roots: Mapping[str, Path]) -> Path:
    root = roots[sample["root_key"]]
    path = (root / sample["relative_path"]).resolve(strict=True)
    if not path.is_relative_to(root.resolve(strict=True)):
        raise ValueError(f"{sample['sample_id']}: path escapes its read-only root")
    return path


class _TempPeak:
    """Track the peak scratch usage: sampled tree size plus recorded artifacts."""

    def __init__(self, root: Path, interval: float = 0.2) -> None:
        self.root = root
        self.interval = interval
        self.peak = 0
        self._recorded = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def record(self, size: int) -> None:
        self._recorded = max(self._recorded, int(size))
        self.peak = max(self.peak, self._recorded + self._tree_bytes(self.root))

    @staticmethod
    def _tree_bytes(root: Path) -> int:
        total = 0
        if not root.exists():
            return 0
        for path in root.rglob("*"):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except OSError:
                continue
        return total

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.peak = max(self.peak, self._tree_bytes(self.root))
            self._stop.wait(self.interval)

    def __enter__(self) -> _TempPeak:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.peak = max(self.peak, self._tree_bytes(self.root))


def _locator_check_factory(sample: Mapping[str, Any], path: Path, cache: dict):
    """Re-read the original and prove each golden quote sits at its locator."""
    suffix = path.suffix.casefold()

    def check(_sample: Mapping[str, Any], point: Mapping[str, Any]) -> bool:
        quote = normalize_text(point["quote"])
        if not quote:
            return False
        if suffix == ".pdf":
            page_number = int(point["locator"]["page_number"])
            key = (sample["sample_id"], page_number)
            if key not in cache:
                import fitz

                with fitz.open(str(path)) as document:
                    cache[key] = document[page_number - 1].get_text("text")
            return quote in normalize_text(cache[key])
        key = (sample["sample_id"], "text")
        if key not in cache:
            cache[key] = path.read_bytes().decode("utf-8-sig").splitlines()
        lines = cache[key]
        locator = point["locator"]
        start = int(locator["line_start"])
        end = int(locator.get("line_end", start))
        segment = "\n".join(lines[start - 1 : end])
        return quote in normalize_text(segment)

    return check


def _run_sample(
    sample: Mapping[str, Any],
    path: Path,
    *,
    temp_root: Path,
    locator_check,
    peak: _TempPeak | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    before = _snapshot(path)
    source_sha = _sha256(path)
    if source_sha != sample["sha256"]:
        raise ValueError(f"{sample['sample_id']}: source sha changed")
    if path.stat().st_size != int(sample["byte_size"]):
        raise ValueError(f"{sample['sample_id']}: source byte size changed")
    source_id = source_id_for_sha256(source_sha)
    parser_options = dict(sample.get("parser_options") or {})
    text: str | None = None
    if sample["source_format"] == "pdf":
        parsed = parse_pdf(
            path,
            source_id=source_id,
            source_sha256=source_sha,
            language=sample["language"],
            **parser_options,
        )
    else:
        text = path.read_bytes().decode("utf-8-sig", errors="strict")
        parsed = parse_transcript_text(
            text,
            source_id=source_id,
            source_sha256=source_sha,
            language=sample["language"],
        )
    package = select_narrative_evidence(
        parsed,
        title=sample["title"],
        existing_kind=sample["existing_kind"],
    )
    if text is None:
        verified, failed = verify_pdf_evidence_spans(
            path,
            source_id=source_id,
            source_sha256=source_sha,
            evidence_spans=package.evidence_spans,
        )
    else:
        verified, failed = verify_transcript_evidence_spans(
            text,
            source_id=source_id,
            source_sha256=source_sha,
            evidence_spans=package.evidence_spans,
            language=sample["language"],
        )

    wire = package.summary_input()
    serialized = json.dumps(
        wire, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    temp_root.mkdir(parents=True, exist_ok=True)
    measure_path = temp_root / f"{sample['sample_id']}.summary-input.json"
    with measure_path.open("xb") as stream:
        stream.write(serialized)
        stream.flush()
    persisted = measure_path.stat().st_size
    if peak is not None:
        peak.record(persisted)
    measure_path.unlink()
    if persisted != len(serialized):
        raise OSError(f"{sample['sample_id']}: persisted package length mismatch")

    after = _snapshot(path)
    if after != before:
        raise OSError(
            f"{sample['sample_id']}: original file metadata changed during the run"
        )

    parse_record = {
        "page_count": parsed.page_count,
        "pages_read": parsed.pages_read,
        "opaque_pages": list(parsed.opaque_pages),
        "table_scan_page_count": len(parsed.table_scan_pages),
        "deferred_table_pages": list(parsed.deferred_table_pages),
        "line_count": parsed.line_count,
        "errors": list(parsed.errors),
        "coverage_complete": parsed.coverage_complete,
        "parser_name": NARRATIVE_PARSER_NAME,
        "parser_version": NARRATIVE_PARSER_VERSION,
        "selector_name": NARRATIVE_SELECTOR_NAME,
        "selector_version": NARRATIVE_SELECTOR_VERSION,
    }
    selection_record = {
        "source_sha256": source_sha,
        "spans": list(package.evidence_spans),
        "parse": parse_record,
        "status": package.status,
        "document_kind": package.document_kind,
        "selection_limit": package.selection_limit,
        "candidate_count": package.candidate_count,
        "source_units": package.source_units,
        "omitted_candidate_count": package.omitted_candidate_count,
        "dropped_financial_count": package.dropped_financial_count,
        "selected_span_count": len(package.evidence_spans),
        "locator_roundtrip_verified": len(verified),
        "locator_roundtrip_failed": len(failed),
        "locator_roundtrip_failed_span_ids": list(failed),
        "coverage_complete": package.coverage_complete,
        "summary_input_bytes": len(serialized),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    extra = {
        "summary_input_bytes": len(serialized),
        "pointer": None,
    }
    # locator verification for this sample happens before evaluation
    for point in _golden_points_for(sample):
        if not locator_check(sample, point):
            raise SystemExit(
                f"{sample['sample_id']}/{point['golden_id']}: quote is not readable at its "
                "cited locator; fix golden.json instead of shrinking the denominator"
            )
    return selection_record, extra


_GOLDEN_CACHE: dict[str, Any] = {}


def _golden_points_for(sample: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    return _GOLDEN_CACHE[sample["sample_id"]]["points"]


def run(
    *,
    package_root: Path,
    output: Path,
    temp_root: Path,
    sample_ids: Sequence[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    samples_doc = _load_json(package_root / "samples.json")
    golden_doc = _load_json(package_root / "golden.json")
    local_doc = _load_json(package_root / "local.json")
    roots = {key: Path(value) for key, value in local_doc["roots"].items()}
    samples = list(samples_doc["samples"])
    if sample_ids:
        wanted = set(sample_ids)
        samples = [sample for sample in samples if sample["sample_id"] in wanted]
        found = {sample["sample_id"] for sample in samples}
        if found != wanted:
            raise ValueError(f"unknown sample ids: {sorted(wanted - found)}")
    _GOLDEN_CACHE.clear()
    _GOLDEN_CACHE.update(golden_doc["samples"])
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} exists; pass --overwrite after reviewing it")

    started = time.perf_counter()
    selections: dict[str, dict[str, Any]] = {}
    original_state = {}
    locator_cache: dict = {}
    peak = _TempPeak(temp_root)
    with peak:
        for sample in samples:
            path = _resolve(sample, roots)
            original_state[sample["sample_id"]] = {
                "sha256": _sha256(path),
                "byte_size": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            selection, _extra = _run_sample(
                sample,
                path,
                temp_root=temp_root,
                locator_check=_locator_check_factory(sample, path, locator_cache),
                peak=peak,
            )
            selections[sample["sample_id"]] = selection
        report = evaluate(
            samples=samples,
            golden=golden_doc,
            selections=selections,
            locator_check=_locator_check_factory_multi(samples, roots, locator_cache),
        )
        report.update(
            {
                "baseline": CARD_BASELINE,
                "generated_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "runner": "benchmarks/narrative_document_types/run_benchmark.py",
                "parser": {
                    "name": NARRATIVE_PARSER_NAME,
                    "version": NARRATIVE_PARSER_VERSION,
                },
                "selector": {
                    "name": NARRATIVE_SELECTOR_NAME,
                    "version": NARRATIVE_SELECTOR_VERSION,
                },
                "scope": {
                    "definition": SCOPE_DEFINITION,
                    "denominators": SCOPE_DENOMINATORS,
                    "samples_declared": len(samples_doc["samples"]),
                    "samples_evaluated": len(samples),
                    "golden_points_declared": sum(
                        len(entry["points"]) for entry in golden_doc["samples"].values()
                    ),
                },
                "real_vs_fixture": {
                    "real_originals_read": len(samples),
                    "synthetic_samples": 0,
                    "metadata_is_fixture_samples": [
                        sample["sample_id"]
                        for sample in samples
                        if sample.get("metadata_is_fixture")
                    ],
                    "notes": [
                        "Every sample is a real on-disk original opened read-only from a root in local.json.",
                        "SHA-256 and byte size are checked before parsing and again after the run.",
                        "Golden quotes are re-read from the original at their cited locator on every run.",
                    ],
                },
                "original_fingerprints": original_state,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "temp_peak_bytes": peak.peak,
                "limitations": LIMITATIONS,
                "output_scope": "source-only",
            }
        )
    validate_report(
        report,
        samples=samples,
        golden=golden_doc,
        baseline=CARD_BASELINE,
        parser={"name": NARRATIVE_PARSER_NAME, "version": NARRATIVE_PARSER_VERSION},
        selector={
            "name": NARRATIVE_SELECTOR_NAME,
            "version": NARRATIVE_SELECTOR_VERSION,
        },
    )
    for sample in samples:
        path = _resolve(sample, roots)
        now = (path.stat().st_size, path.stat().st_mtime_ns)
        before = original_state[sample["sample_id"]]
        if (before["byte_size"], before["mtime_ns"]) != now:
            raise OSError(f"{sample['sample_id']}: original changed after the run")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _locator_check_factory_multi(samples, roots, cache: dict):
    checks = {}
    for sample in samples:
        path = _resolve(sample, roots)
        checks[sample["sample_id"]] = _locator_check_factory(sample, path, cache)

    def check(sample: Mapping[str, Any], point: Mapping[str, Any]) -> bool:
        return checks[sample["sample_id"]](sample, point)

    return check


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--output", type=Path, default=PACKAGE_ROOT / "report.json")
    parser.add_argument(
        "--temp-root", type=Path, default=REPO_ROOT / "tmp" / "n5-docset-run"
    )
    parser.add_argument("--sample-id", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    report = run(
        package_root=args.package_root.resolve(strict=True),
        output=args.output.resolve(),
        temp_root=args.temp_root,
        sample_ids=args.sample_id or None,
        overwrite=args.overwrite,
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "samples": report["totals"]["documents"],
        "required_coverage_rate": report["totals"]["required_coverage_rate"],
        "optional_coverage_rate": report["totals"]["optional_coverage_rate"],
        "selected_noise_rate": report["totals"]["selected_noise_rate"],
        "duplicate_ratio": report["totals"]["duplicate_ratio"],
        "role_confusion": report["totals"]["role_confusion"],
        "modality_confusion": report["totals"]["modality_confusion"],
        "locator_roundtrip_failed": report["totals"]["locator_roundtrip_failed"],
        "elapsed_seconds": report["elapsed_seconds"],
        "temp_peak_bytes": report["temp_peak_bytes"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
