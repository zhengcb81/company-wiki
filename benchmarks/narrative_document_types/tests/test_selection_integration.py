"""Integration checks: the benchmark runs the repository's real parser/selector.

These tests read the registered originals read-only, run the shipped
``parse_*`` / ``select_narrative_evidence`` / ``verify_*_evidence_spans``
functions through ``run_benchmark.run`` on a small subset, and then validate the
emitted report with the same validator that guards the committed one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import run_benchmark
from evaluator import SCHEMA_VERSION, validate_report


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CARD_BASELINE = run_benchmark.CARD_BASELINE
INVESTMENT_KEYS = {
    "target_price",
    "rating",
    "position",
    "valuation",
    "sotp",
    "buy",
    "sell",
    "overweight",
    "underweight",
    "price_target",
    "investment_conclusion",
}

# Quarter + valuable IR + English transcript: fast, and together they exercise
# PDF text, PDF table/QA fragments and speaker-turn transcript parsing.
SUBSET = ("S03", "S07", "S09")


@pytest.fixture(scope="module")
def manifests() -> dict:
    return {
        "samples": json.loads(
            (PACKAGE_ROOT / "samples.json").read_text(encoding="utf-8")
        ),
        "golden": json.loads(
            (PACKAGE_ROOT / "golden.json").read_text(encoding="utf-8")
        ),
        "local": json.loads((PACKAGE_ROOT / "local.json").read_text(encoding="utf-8")),
    }


def _roots(manifests: dict) -> dict[str, Path]:
    return {key: Path(value) for key, value in manifests["local"]["roots"].items()}


def _sample_path(sample: dict, roots: dict[str, Path]) -> Path:
    return roots[sample["root_key"]] / sample["relative_path"]


def _fingerprint(path: Path) -> tuple[int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return stat.st_size, stat.st_mtime_ns, digest


def test_committed_report_validates_against_manifest_and_golden(manifests):
    report = json.loads((PACKAGE_ROOT / "report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == SCHEMA_VERSION
    validate_report(
        report,
        samples=manifests["samples"]["samples"],
        golden=manifests["golden"],
        baseline=CARD_BASELINE,
        parser=report["parser"],
        selector=report["selector"],
    )
    assert report["totals"]["documents"] == len(manifests["samples"]["samples"])
    assert report["output_scope"] == "source-only"


def _json_keys(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{prefix}/{key}"
            yield from _json_keys(value, f"{prefix}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _json_keys(value, f"{prefix}[{index}]")


def test_report_is_source_only(manifests):
    report = json.loads((PACKAGE_ROOT / "report.json").read_text(encoding="utf-8"))
    keys = {key.casefold() for key in _json_keys(report)}
    offenders = sorted(
        key for key in keys
        if any(term in key for term in INVESTMENT_KEYS)
    )
    assert offenders == [], f"report must not carry investment evaluation keys: {offenders}"
    assert report["output_scope"] == "source-only"
    assert report["real_vs_fixture"]["synthetic_samples"] == 0


def test_sample_manifest_covers_required_document_types(manifests):
    samples = manifests["samples"]["samples"]
    kinds = {sample["doc_type"] for sample in samples}
    required = {
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "prospectus",
        "equity_offering_prospectus",
        "convertible_bond_prospectus",
        "investor_relations_valuable",
        "investor_relations_procedural",
        "investor_call_transcript",
    }
    assert required <= kinds, sorted(required - kinds)
    assert len(samples) >= 8
    assert len({sample["sample_id"] for sample in samples}) == len(samples)


def test_every_original_matches_its_registered_hash_and_golden_is_read(manifests):
    roots = _roots(manifests)
    golden_samples = manifests["golden"]["samples"]
    for sample in manifests["samples"]["samples"]:
        path = _sample_path(sample, roots)
        if not path.exists():
            pytest.skip(f"original not present on this machine: {sample['sample_id']}")
        size, _mtime, digest = _fingerprint(path)
        assert digest == sample["sha256"], sample["sample_id"]
        assert size == int(sample["byte_size"]), sample["sample_id"]
        entry = golden_samples[sample["sample_id"]]
        assert len(entry["points"]) >= 6, sample["sample_id"]
        assert entry["read_scope"], sample["sample_id"]
        scope = entry["read_scope"]
        if scope["unit"] == "pdf_page":
            assert scope["pages_read"], sample["sample_id"]
            assert len(scope["pages_read"]) <= scope["pages_total"]
        else:
            assert scope["lines_read"], sample["sample_id"]
        for point in entry["points"]:
            assert point["quote_sha256"], point["golden_id"]
            assert point["locator"], point["golden_id"]
            assert point.get("reason"), point["golden_id"]


def test_runner_reproduces_a_valid_report_for_the_subset(manifests, tmp_path):
    roots = _roots(manifests)
    before = {}
    for sample in manifests["samples"]["samples"]:
        if sample["sample_id"] in SUBSET:
            before[sample["sample_id"]] = _fingerprint(_sample_path(sample, roots))

    output = tmp_path / "subset-report.json"
    temp_root = tmp_path / "scratch"
    report = run_benchmark.run(
        package_root=PACKAGE_ROOT,
        output=output,
        temp_root=temp_root,
        sample_ids=SUBSET,
        overwrite=True,
    )

    validate_report(
        report,
        samples=[
            s for s in manifests["samples"]["samples"] if s["sample_id"] in SUBSET
        ],
        golden=manifests["golden"],
        baseline=CARD_BASELINE,
        parser=report["parser"],
        selector=report["selector"],
    )
    assert output.exists()
    assert report["totals"]["documents"] == len(SUBSET)
    assert report["totals"]["locator_roundtrip_failed"] == 0
    assert report["temp_peak_bytes"] > 0
    assert report["elapsed_seconds"] > 0
    for row in report["samples"]:
        assert row["selection"]["status"] in {
            "selected",
            "partial",
            "skipped_no_narrative",
            "needs_review",
            "blocked",
        }
        assert row["required_coverage"]["denominator"] >= 1
        assert len(row["golden_results"]) >= 6
        assert row["annotation_scope"]
        # every golden result must be traceable to a verified quote hash
        for golden_row in row["golden_results"]:
            assert golden_row["quote_sha256"]
    for sample_id, state in before.items():
        sample = next(
            s for s in manifests["samples"]["samples"] if s["sample_id"] == sample_id
        )
        assert _fingerprint(_sample_path(sample, roots)) == state, sample_id
    # scratch is left empty: the runner unlinks its measurement files
    if temp_root.exists():
        assert list(temp_root.glob("*.json")) == []


def test_runner_refuses_a_changed_original(manifests, tmp_path, monkeypatch):
    sample = next(s for s in manifests["samples"]["samples"] if s["sample_id"] == "S03")
    roots = _roots(manifests)
    path = _sample_path(sample, roots)
    if not path.exists():
        pytest.skip("original not present")
    tampered = dict(sample)
    tampered["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source sha changed"):
        run_benchmark._run_sample(
            tampered,
            path,
            temp_root=tmp_path / "scratch",
            locator_check=lambda _sample, _point: True,
        )
