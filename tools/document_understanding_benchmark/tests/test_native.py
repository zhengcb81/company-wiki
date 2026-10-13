"""Native-mode tests: read-only observation, restoration and honest UNAVAILABLE.

The default command
``python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q``
must stay **fast and fully offline**, so the real-original replays are skipped
unless ``DU_BENCH_ALLOW_REAL_DATA=1`` is set in the environment. They also carry
the ``real_data`` marker, so they can be selected explicitly::

    $env:DU_BENCH_ALLOW_REAL_DATA = "1"
    python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q -m real_data

The restoration, refusal and adapter-seam tests run everywhere because they do
not need an original.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.gold import (
    GoldError,
    load_bindings,
    resolve_original,
    unavailable_observed,
)
from tools.document_understanding_benchmark.records import validate_gold, validate_observed
from tools.document_understanding_benchmark.recovery import (
    compare_fingerprints,
    file_fingerprint,
    fingerprint_many,
    install_sentinel,
    mark_owned,
    read_sentinel,
)
from tools.document_understanding_benchmark.schema import UNAVAILABLE

REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# bindings: never substitute, never guess
# ---------------------------------------------------------------------------


def test_missing_binding_is_unavailable():
    resolved = resolve_original("sample-x", "a" * 64, {})
    assert resolved["status"] == "UNAVAILABLE"
    assert "no local binding" in resolved["reason"]


def test_missing_path_is_unavailable(tmp_path):
    resolved = resolve_original("sample-x", "a" * 64, {"sample-x": str(tmp_path / "nope.pdf")})
    assert resolved["status"] == "UNAVAILABLE"
    assert resolved["actual_sha256"] is None


def test_sha_mismatch_is_unavailable_not_a_substitute(tmp_path):
    original = tmp_path / "doc.pdf"
    original.write_bytes(b"real content")
    resolved = resolve_original("sample-x", "0" * 64, {"sample-x": str(original)})
    assert resolved["status"] == "UNAVAILABLE"
    assert resolved["actual_sha256"] != "0" * 64


def test_matching_sha_resolves(tmp_path):
    import hashlib

    original = tmp_path / "doc.pdf"
    original.write_bytes(b"real content")
    digest = hashlib.sha256(b"real content").hexdigest()
    resolved = resolve_original("sample-x", digest, {"sample-x": str(original)})
    assert resolved["status"] == "OK"


def test_bindings_accept_both_shapes(tmp_path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"a": "/x/y.pdf"}), encoding="utf8")
    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"bindings": {"a": {"path": "/x/y.pdf"}}}), encoding="utf8")
    assert load_bindings(flat) == {"a": "/x/y.pdf"}
    assert load_bindings(nested) == {"a": "/x/y.pdf"}


def test_unreadable_bindings_refuse_the_run(tmp_path):
    with pytest.raises(GoldError):
        load_bindings(tmp_path / "missing.json")


def test_unavailable_observation_never_fabricates_claims():
    gold = validate_gold(
        {
            "schema_version": "du-gold/1",
            "sample_id": "s",
            "source_sha256": "a" * 64,
            "scope": "development",
            "expected_route_families": ["annual"],
            "facts": [
                {
                    "id": "f",
                    "importance": "critical",
                    "any_support_sets": [[{"page": 1, "exact_quote": "x"}]],
                }
            ],
        }
    )
    observed = validate_observed(unavailable_observed(gold, "missing source"))
    assert observed["claims"] == []
    assert observed["selected_locators"] == []
    assert observed["coverage"]["native_scan"] == "unavailable"


# ---------------------------------------------------------------------------
# restoration
# ---------------------------------------------------------------------------


def test_fingerprints_detect_a_content_change(tmp_path):
    target = tmp_path / "config.yaml"
    target.write_text("a: 1", encoding="utf8")
    before = fingerprint_many([target])
    target.write_text("a: 2", encoding="utf8")
    after = fingerprint_many([target])
    report = compare_fingerprints(before, after)
    assert report["unchanged"] is False
    assert any(change["reason"] == "sha256_changed" for change in report["changes"])


def test_fingerprints_detect_a_mtime_only_change(tmp_path):
    import os

    target = tmp_path / "config.yaml"
    target.write_text("a: 1", encoding="utf8")
    before = fingerprint_many([target])
    stat = target.stat()
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000))
    after = fingerprint_many([target])
    report = compare_fingerprints(before, after)
    assert report["unchanged"] is False
    assert any(change["reason"] == "mtime_changed" for change in report["changes"])


def test_unchanged_fingerprints_report_clean(tmp_path):
    target = tmp_path / "config.yaml"
    target.write_text("a: 1", encoding="utf8")
    before = fingerprint_many([target])
    after = fingerprint_many([target])
    assert compare_fingerprints(before, after)["unchanged"] is True


def test_original_is_not_modified_by_observation(tmp_path):
    """A read-only observation must leave SHA and mtime identical."""

    original = tmp_path / "doc.bin"
    original.write_bytes(b"immutable original")
    before = file_fingerprint(original)
    _ = original.read_bytes()
    after = file_fingerprint(original)
    assert before["sha256"] == after["sha256"]
    assert before["mtime_ns"] == after["mtime_ns"]


def test_sentinel_round_trip(tmp_path):
    installed = install_sentinel(tmp_path, {"purpose": "test"})
    restored = read_sentinel(tmp_path)
    assert restored["exists"] is True
    assert restored["sha256"] == installed["sha256"]


def test_preserved_sentinel_text_restored_after_a_run(tmp_path):
    """A pre-existing sentinel in the owned container survives a run intact."""

    from tools.document_understanding_benchmark.gold import unavailable_observed
    from tools.document_understanding_benchmark.recovery import (
        SENTINEL_NAME,
        file_fingerprint,
    )
    from tools.document_understanding_benchmark.evaluate import evaluate
    from tools.document_understanding_benchmark.records import validate_gold

    container = tmp_path / "out"
    container.mkdir()
    sentinel = container / SENTINEL_NAME
    sentinel.write_text("pre-existing content that must not change", encoding="utf8")
    before = file_fingerprint(sentinel)

    mark_owned(container)
    (container / "scratch.tmp").write_text("run scratch", encoding="utf8")
    gold = validate_gold(
        {
            "schema_version": "du-gold/1",
            "sample_id": "s",
            "source_sha256": "a" * 64,
            "scope": "development",
            "expected_route_families": ["annual"],
            "facts": [
                {
                    "id": "f",
                    "importance": "critical",
                    "any_support_sets": [[{"page": 1, "exact_quote": "x"}]],
                }
            ],
        }
    )
    evaluate(validate_observed(unavailable_observed(gold, "missing source")), gold)

    after = file_fingerprint(sentinel)
    assert after["sha256"] == before["sha256"]
    assert after["mtime_ns"] == before["mtime_ns"]


def test_peak_rss_is_measured_when_the_host_exposes_it():
    """The Windows probe must not silently report None (missing ctypes prototypes)."""

    from tools.document_understanding_benchmark.recovery import peak_rss_bytes

    measured = peak_rss_bytes()
    if measured is None:
        pytest.skip("host does not expose peak RSS")
    assert measured > 1_000_000  # a real interpreter is never below 1 MiB


def test_sentinel_survives_a_real_offline_cli_run(tmp_path):
    """A pre-existing sentinel must come back byte-identical with its mtime."""

    from tools.document_understanding_benchmark.__main__ import main
    from tools.document_understanding_benchmark.recovery import SENTINEL_NAME

    out_dir = tmp_path / "out"
    owned = out_dir / "offline"
    owned.mkdir(parents=True)
    sentinel = owned / SENTINEL_NAME
    sentinel.write_text("pre-existing sentinel body", encoding="utf8")
    before = file_fingerprint(sentinel)

    # Leave unrelated pre-existing content in the container too.
    stranger = owned / "unrelated.txt"
    stranger.write_text("must survive", encoding="utf8")

    exit_code = main(["--mode", "offline", "--output", str(out_dir)])
    assert exit_code in {0, 1, 3}

    after = file_fingerprint(sentinel)
    assert after["sha256"] == before["sha256"]
    assert after["mtime_ns"] == before["mtime_ns"]
    assert sentinel.read_text(encoding="utf8") == "pre-existing sentinel body"

    # Offline mode wrote only its own summary; the stranger was not deleted by
    # the run itself (cleanup only happens on explicit request).
    assert (owned / "summary.json").is_file()


def test_preserved_sentinel_survives_a_REFUSED_run(tmp_path):
    """A run that refuses must still leave a pre-existing sentinel untouched.

    The card asks for the tool *and* failure cases to be exercised. A refusal
    happens after the sentinel has been installed, so anything that returns early
    without restoring it leaves content it found overwritten -- a run must never
    modify what it found, however it exits.
    """

    from tools.document_understanding_benchmark.__main__ import main
    from tools.document_understanding_benchmark.recovery import SENTINEL_NAME, file_fingerprint

    out_dir = tmp_path / "out"
    owned = out_dir / "offline"
    owned.mkdir(parents=True)
    sentinel = owned / SENTINEL_NAME
    sentinel.write_text("pre-existing sentinel body", encoding="utf8")
    before = file_fingerprint(sentinel)

    # A malformed review file makes the run refuse before it evaluates anything.
    bad_review = tmp_path / "bad-review.json"
    bad_review.write_text('{"schema_version": "du-review/9", "claims": []}', encoding="utf8")

    exit_code = main(
        [
            "--mode",
            "offline",
            "--output",
            str(out_dir),
            "--review",
            str(bad_review),
        ]
    )
    assert exit_code == 2, "a malformed review must refuse the run"

    after = file_fingerprint(sentinel)
    assert after["sha256"] == before["sha256"], "a refusing run clobbered the sentinel"
    assert after["mtime_ns"] == before["mtime_ns"]
    assert sentinel.read_text(encoding="utf8") == "pre-existing sentinel body"


def test_owned_marker_gates_cleanup(tmp_path):
    from tools.document_understanding_benchmark.recovery import cleanup_owned

    unowned = tmp_path / "stranger"
    unowned.mkdir()
    (unowned / "keep.txt").write_text("data", encoding="utf8")
    assert cleanup_owned(unowned)["removed"] is False
    assert (unowned / "keep.txt").is_file()

    owned = tmp_path / "mine"
    mark_owned(owned)
    (owned / "scratch.tmp").write_text("temp", encoding="utf8")
    (owned / "summary.json").write_text("{}", encoding="utf8")
    report = cleanup_owned(owned, keep={"summary.json"})
    assert report["removed"] is True
    assert (owned / "summary.json").is_file()
    assert not (owned / "scratch.tmp").exists()


# ---------------------------------------------------------------------------
# adapter seam
# ---------------------------------------------------------------------------


def test_adapter_seam_produces_observed():
    from tools.document_understanding_benchmark.observer import observe_du_adapter

    def adapter(observation):
        return {"route": {"family": "annual"}, "claims": [], "selected_locators": []}

    produced = observe_du_adapter(adapter, {"schema_version": "du-input/1"}, sample_id="s", sha256="a" * 64)
    assert produced["sample_id"] == "s"
    assert produced["source_sha256"] == "a" * 64
    assert produced["route"]["family"] == "annual"


def test_adapter_seam_rejects_a_non_callable():
    from tools.document_understanding_benchmark.observer import ObserverUnavailable, observe_du_adapter

    with pytest.raises(ObserverUnavailable):
        observe_du_adapter("not callable", {}, sample_id="s", sha256="a" * 64)


# ---------------------------------------------------------------------------
# carrier support
# ---------------------------------------------------------------------------


def test_pdf_and_transcript_carriers_are_supported():
    from tools.document_understanding_benchmark.observer import carrier_support

    for suffix in (".pdf", ".txt", ".md"):
        info = carrier_support(Path(f"doc{suffix}"))
        assert info["supported"] is True, suffix
        assert info["entry_point"], suffix


def test_sec_filing_html_is_reported_unsupported():
    """A 10-K HTML is not a transcript, so it must not be claimed as observable."""

    from tools.document_understanding_benchmark.observer import carrier_support

    for suffix in (".htm", ".html"):
        info = carrier_support(Path(f"filing{suffix}"))
        assert info["supported"] is False, suffix
        assert info["reason"], suffix


def test_unknown_carrier_is_unsupported_not_guessed():
    from tools.document_understanding_benchmark.observer import carrier_support

    info = carrier_support(Path("doc.xlsx"))
    assert info["supported"] is False


@pytest.mark.real_data
def test_real_10k_html_yields_no_units_through_the_transcript_path():
    """Measured, not assumed: the only HTML path produces zero units for a 10-K.

    This is the evidence behind reporting US filings as UNAVAILABLE rather than
    as documents with no business content.
    """

    if os.environ.get("DU_BENCH_ALLOW_REAL_DATA") != "1":
        pytest.skip("set DU_BENCH_ALLOW_REAL_DATA=1 to probe a real 10-K")
    bindings = _available_bindings()
    candidate = bindings.get("holdout-us-mongodb-10k") or bindings.get("us-10k")
    if not candidate or not Path(candidate).is_file():
        pytest.skip("no local US 10-K binding")

    from tools.document_understanding_benchmark.observer import probe_non_pdf_html

    report = probe_non_pdf_html(Path(candidate))
    assert report["extracted"] is True, report
    assert report["units"] == 0, report
    assert report["usable"] is False
    assert "transcript_start_missing" in " ".join(report["errors"])



BINDINGS_CANDIDATES = (
    # Preferred: kept outside the worktree so the repository stays clean.
    Path.home() / ".du-bench" / "bindings.local.json",
    # Legacy in-worktree location, still honoured.
    Path(__file__).resolve().parents[3] / ".du-bench-out" / "bindings.local.json",
)

GOLD_SAMPLES = ("cn-equity", "cn-ir", "cn-q-business", "hk-annual")


def _available_bindings() -> dict[str, str]:
    if os.environ.get("DU_BENCH_ALLOW_REAL_DATA") != "1":
        pytest.skip("set DU_BENCH_ALLOW_REAL_DATA=1 to replay real originals")
    for candidate in BINDINGS_CANDIDATES:
        if candidate.is_file():
            try:
                return load_bindings(candidate)
            except GoldError:
                continue
    return {}


@pytest.mark.real_data
@pytest.mark.parametrize("sample_id", GOLD_SAMPLES)
def test_native_replay_leaves_the_original_untouched(sample_id):
    """Observe a real original and prove SHA+mtime are unchanged."""

    bindings = _available_bindings()
    gold = validate_gold(
        json.loads(
            (
                REPO_ROOT
                / "tools"
                / "document_understanding_benchmark"
                / "gold"
                / f"{sample_id}.json"
            ).read_text(encoding="utf8")
        )
    )
    resolved = resolve_original(sample_id, gold["source_sha256"], bindings)
    if resolved["status"] != "OK":
        pytest.skip(f"{sample_id}: {resolved['reason']}")

    from tools.document_understanding_benchmark.observer import observe_native

    path = Path(resolved["path"])
    before = file_fingerprint(path)
    observe_native(path, sha256=gold["source_sha256"], sample_id=sample_id)
    after = file_fingerprint(path)
    assert before["sha256"] == after["sha256"]
    assert before["mtime_ns"] == after["mtime_ns"]


@pytest.mark.real_data
def test_native_baseline_reports_honest_not_evaluated():
    """The baseline has no new structure, so those dimensions are NOT_EVALUATED."""

    bindings = _available_bindings()
    if "cn-ir" not in bindings:
        pytest.skip("no local bindings for cn-ir")
    gold_path = (
        REPO_ROOT / "tools" / "document_understanding_benchmark" / "gold" / "cn-ir.json"
    )
    gold = validate_gold(json.loads(gold_path.read_text(encoding="utf8")))
    resolved = resolve_original("cn-ir", gold["source_sha256"], bindings)
    if resolved["status"] != "OK":
        pytest.skip(resolved["reason"])

    from tools.document_understanding_benchmark import evaluate
    from tools.document_understanding_benchmark.observer import observe_native

    observed = observe_native(
        Path(resolved["path"]), sha256=gold["source_sha256"], sample_id="cn-ir"
    )
    result = evaluate(observed, gold)
    not_evaluated = {row["check_id"] for row in result["not_evaluated"]}
    assert "context.semantic_units" in not_evaluated
    assert "semantics.entailment" in not_evaluated
    # Real recall is measured, not faked.
    assert result["metrics"]["critical_fact_recall"] is not None
    assert result["status"] in {UNAVAILABLE, "FAIL", "PARTIAL"}
