# -*- coding: utf-8 -*-
"""Runner boundary tests on neutral fixtures (H11).

All fixtures are tiny synthetic TXT/HTML/PDF files. Two different absolute
test roots (one containing Chinese characters and spaces) run the same small
chain from an external cwd with a polluted PYTHONPATH to prove where the
executed code came from. Success, failure, timeout and existing-result paths
never overwrite sentinels or older evidence; cleanup touches only owned dirs.
"""
from __future__ import annotations

import json
import subprocess

from pathlib import Path

import pytest

from tools.holdout_replay.manifest import sha256_file
from tools.holdout_replay.producer import ProducerError, verify_producer
from tools.holdout_replay.runner import ReplayError, run_replay

REPO = Path(__file__).resolve().parents[3]

TXT_FIXTURE = """Acme Corp Q3 earnings call transcript
Operator: Welcome to the Acme third quarter call.
Speaker 1 (CFO): Revenue grew 12 percent year over year to 340 million dollars,
driven by enterprise subscriptions; hardware revenue declined 3 percent.
Speaker 1 (CFO): We plan to launch the Acme Vision product family in the first
quarter of next year, subject to certification.
Analyst: Is the decline in hardware permanent?
Speaker 1 (CFO): We have not decided on exiting hardware; no final decision has been made.
Operator: That concludes today's call.
"""

HTML_FIXTURE = """<!doctype html><html><head><title>Acme IR update</title></head>
<body><h1>Acme Corp investor update</h1>
<p>Acme Corp announced that its overseas subsidiary signed a distribution
agreement covering eleven new countries in the EMEA region.</p>
<p>The company reiterated that the agreement is conditional on regulatory
clearance and does not create revenue guidance for the current year.</p>
</body></html>
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   text=True, encoding="utf-8")


def make_stub_producer(base: Path) -> Path:
    """A minimal committed git repo that satisfies verify_producer.

    company_wiki here is a one-line package; enough to prove import-origin
    checks without the full production tree.
    """
    repo = base / "stub-producer"
    (repo / "src" / "company_wiki").mkdir(parents=True)
    (repo / "src" / "company_wiki" / "__init__.py").write_text(
        '"""stub producer package for boundary tests"""\n', encoding="utf-8")
    _git_init(repo)
    return repo


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=w18", "-c", "user.email=w18@test", "commit", "-qm", "stub")


def stub_producer_commit(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


def make_snapshot_producer(base: Path) -> Path:
    """Snapshot the committed production trees into a clean temp git repo.

    ``git archive`` exports exactly HEAD, so a dirty development tree cannot
    leak into the replayed deploy. The orchestrator package itself is removed
    from the snapshot so the live (dev/committed) copy under test provides it.
    """
    repo = base / "snapshot-producer"
    repo.mkdir(parents=True)
    for tree in ("src", "scripts", "tools", "config"):
        archive = subprocess.run(
            ["git", "-C", str(REPO), "archive", "--format=tar", "HEAD", tree],
            check=True, capture_output=True)
        subprocess.run(["tar", "-x", "-f", "-", "-C", str(repo)],
                       input=archive.stdout, check=True, capture_output=True)
    holder = repo / "tools" / "holdout_replay"
    if holder.exists():
        import shutil
        shutil.rmtree(holder)
    _git_init(repo)
    return repo


def make_mini_manifest(base: Path, fixtures: dict[str, Path]) -> tuple[Path, dict[str, Path]]:
    root = base / "pkg"
    gold_dir = root / "gold"
    gold_dir.mkdir(parents=True)
    samples = []
    bindings = {}
    quotes = {
        "neutral-txt-call": "Revenue grew 12 percent year over year to 340 million dollars",
        "neutral-html-ir": "distribution\nagreement covering eleven new countries",
    }
    kinds = {"neutral-txt-call": "investor_call_transcript",
             "neutral-html-ir": "investor_relations"}
    for sample_id, path in fixtures.items():
        sha = sha256_file(path)
        gold = {
            "schema_version": "du-gold/1", "sample_id": sample_id, "scope": "holdout",
            "market": "US", "company": "Acme", "language": "en",
            "source_sha256": sha, "support_set_frozen_before_output": True,
            "expected_route_families": ["earnings_call"],
            "notes": "neutral fixture",
            "facts": [{
                "id": "f1", "importance": "critical", "target_kind": "required_business",
                "quantity_basis": "period_flow", "modality": "actual",
                "role": "company_statement", "fact_scope": "narrative",
                "any_support_sets": [[{"location_kind": "document",
                                       "exact_quote": quotes[sample_id]}]],
                "must_preserve": ["fixture fact"], "must_not_assert": ["anything else"],
                "reason": "neutral",
            }],
        }
        gold_path = gold_dir / f"{sample_id}.json"
        gold_path.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
        samples.append({
            "sample_id": sample_id, "gold_file": f"gold/{sample_id}.json",
            "gold_sha256": sha256_file(gold_path), "document_kind": kinds[sample_id],
            "market": "US", "language": "en", "carrier": path.suffix,
            "source_ref": {"document_id": f"urn:company-wiki:document:sha256:{sha}",
                           "source_id": f"urn:company-wiki:source:sha256:{sha}",
                           "content_sha256": sha, "byte_size": path.stat().st_size,
                           "mime_type": "text/plain", "schema_version": "2.0"},
            "identity_evidence": {"method": "fixture", "security_id": "ACME",
                                  "entity": "Acme", "evidence": "neutral fixture"},
            "prior_use": {"status": "fresh", "known_prior_sightings": "none"},
            "reading_scope": {"fully_read": "all"}, "designated_trap": "none",
        })
        bindings[sample_id] = str(path)
    manifest = {
        "schema_version": "w18-holdout-manifest/1", "card": "W18-CWP-HOLDOUT",
        "plan_id": "w18-cwp-holdout-2026-10-25", "created": "2026-10-25",
        "base_code_commit": "0" * 40, "frozen_before_candidate_output": True,
        "sample_count": len(samples), "samples": samples,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    bindings_path = root / "bindings.json"
    bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
    return manifest_path, bindings


def test_producer_verification_refuses_wrong_commit_and_dirty_tree(tmp_path):
    repo = make_stub_producer(tmp_path)
    commit = stub_producer_commit(repo)
    ok = verify_producer(repo, commit)
    assert ok["producer_commit"] == commit
    with pytest.raises(ProducerError):
        verify_producer(repo, "0" * 40)
    (repo / "src" / "company_wiki" / "extra.py").write_text("x = 1", encoding="utf-8")
    with pytest.raises(ProducerError):
        verify_producer(repo, commit)


def test_run_refuses_without_bindings_or_source_root(tmp_path):
    repo = make_stub_producer(tmp_path)
    commit = stub_producer_commit(repo)
    with pytest.raises(ReplayError):
        run_replay(producer_root=repo, producer_commit=commit,
                   manifest_path=tmp_path / "m.json", out_dir=tmp_path / "out")


def test_run_reports_unavailable_without_substitution(tmp_path):
    repo = make_stub_producer(tmp_path)
    commit = stub_producer_commit(repo)
    fixture = tmp_path / "call.txt"
    fixture.write_text(TXT_FIXTURE, encoding="utf-8")
    manifest_path, bindings = make_mini_manifest(tmp_path, {"neutral-txt-call": fixture})
    # drop the binding entirely: the sample must be unavailable, never swapped
    broken = tmp_path / "pkg" / "bindings-empty.json"
    broken.write_text("{}", encoding="utf-8")
    receipt = run_replay(producer_root=repo, producer_commit=commit,
                         manifest_path=manifest_path, out_dir=tmp_path / "out",
                         bindings_path=broken)
    row = receipt["samples"][0]
    assert row["status"] == "unavailable"
    assert row["reason"].startswith("RESOLVE")
    assert receipt["overall"] == "has_failures"


def test_run_fails_on_sha_mismatched_original(tmp_path):
    repo = make_stub_producer(tmp_path)
    commit = stub_producer_commit(repo)
    fixture = tmp_path / "call.txt"
    fixture.write_text(TXT_FIXTURE, encoding="utf-8")
    manifest_path, bindings = make_mini_manifest(tmp_path, {"neutral-txt-call": fixture})
    fixture.write_text(TXT_FIXTURE + "tampered\n", encoding="utf-8")
    receipt = run_replay(producer_root=repo, producer_commit=commit,
                         manifest_path=manifest_path, out_dir=tmp_path / "out",
                         bindings_path=tmp_path / "pkg" / "bindings.json")
    row = receipt["samples"][0]
    assert row["status"] == "unavailable"
    assert "sha" in row["reason"]


@pytest.fixture(scope="module")
def real_chain_env(tmp_path_factory):
    """Snapshot producer + neutral fixtures + manifest shared by chain tests."""
    base = tmp_path_factory.mktemp("w18chain")
    producer = make_snapshot_producer(base)
    commit = stub_producer_commit(producer)
    fixtures = {}
    txt = base / "acme-call.txt"
    txt.write_text(TXT_FIXTURE, encoding="utf-8")
    fixtures["neutral-txt-call"] = txt
    html = base / "acme-ir.html"
    html.write_text(HTML_FIXTURE, encoding="utf-8")
    fixtures["neutral-html-ir"] = html
    pdf = base / "acme-note.pdf"
    _write_tiny_pdf(pdf)
    manifest_path, bindings = make_mini_manifest(base, fixtures)
    bindings_dir = tmp_path_factory.mktemp("bindings")
    bindings_path = bindings_dir / "bindings.json"
    bindings_path.write_text(json.dumps(bindings, ensure_ascii=False), encoding="utf-8")
    return {"base": base, "producer": producer, "commit": commit,
            "manifest": manifest_path, "bindings": bindings_path}


def _write_tiny_pdf(path: Path) -> None:
    try:
        import fitz
    except ImportError:  # pragma: no cover
        pytest.skip("pymupdf unavailable")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 96), "Acme Corp interim note: overseas revenue grew 9 percent.")
    doc.save(str(path))
    doc.close()


def test_real_chain_runs_and_proves_import_origin(real_chain_env):
    env = real_chain_env
    out = env["base"] / "out-a"
    receipt = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                         manifest_path=env["manifest"], out_dir=out,
                         bindings_path=env["bindings"],
                         external_cwd=env["base"], per_sample_timeout=180)
    assert [row["status"] for row in receipt["samples"]] == ["ok", "ok"]
    for row in receipt["samples"]:
        payload = row["result_path"]
        roots = payload["import_roots"]
        producer_root = str(env["producer"].resolve())
        for module, path in roots.items():
            assert path.replace("\\", "/").startswith(
                producer_root.replace("\\", "/") + "/"), module
        assert payload["original_unchanged"] is True
        assert payload["model_view"]["status"] == "not_attempted"
        # D1: both selector generations are stamped so the two visibility
        # layers (observe default vs compile-pinned) are never conflated
        versions = payload["selector_versions"]
        assert versions["observe_path_default"] and versions["compile_path_pinned"]
        assert payload["targets"], "per-target rows must exist"
        assert payload["evaluation"] is not None


def test_real_chain_portable_to_unicode_space_root(real_chain_env):
    env = dict(real_chain_env)
    second_root = env["base"].parent / "根 目录 W18"
    second_root.mkdir(parents=True, exist_ok=True)
    out = second_root / "out"
    receipt = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                         manifest_path=env["manifest"], out_dir=out,
                         bindings_path=env["bindings"],
                         external_cwd=second_root,
                         sample_ids=["neutral-txt-call"], per_sample_timeout=180)
    assert receipt["samples"][0]["status"] == "ok"
    assert receipt["samples"][0]["result_path"]["original_unchanged"] is True


def test_real_chain_rejects_polluted_pythonpath(real_chain_env):
    env = real_chain_env
    decoy = env["base"] / "decoy"
    (decoy / "company_wiki").mkdir(parents=True)
    (decoy / "company_wiki" / "__init__.py").write_text(
        "# decoy package planted ahead of the producer on PYTHONPATH\n", encoding="utf-8")
    out = env["base"] / "out-polluted"
    receipt = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                         manifest_path=env["manifest"], out_dir=out,
                         bindings_path=env["bindings"],
                         sample_ids=["neutral-txt-call"], per_sample_timeout=180,
                         extra_pythonpath=[decoy])
    row = receipt["samples"][0]
    assert row["status"] == "failed"
    assert not (Path(receipt["attempt_dir"]) / "neutral-txt-call.result.json").exists()


def test_timeout_records_failure_without_overwriting(real_chain_env):
    env = real_chain_env
    out = env["base"] / "out-timeout"
    receipt = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                         manifest_path=env["manifest"], out_dir=out,
                         bindings_path=env["bindings"],
                         sample_ids=["neutral-txt-call"], per_sample_timeout=0.15)
    row = receipt["samples"][0]
    assert row["status"] == "timeout"
    assert not (Path(receipt["attempt_dir"]) / "neutral-txt-call.result.json").exists()


def test_existing_result_refuses_and_preserves_bytes(real_chain_env, monkeypatch):
    env = real_chain_env
    out = env["base"] / "out-nooverwrite"
    first = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                       manifest_path=env["manifest"], out_dir=out,
                       bindings_path=env["bindings"],
                       sample_ids=["neutral-txt-call"], per_sample_timeout=180)
    attempt_dir = Path(first["attempt_dir"])
    result_file = attempt_dir / "neutral-txt-call.result.json"
    result_before = result_file.read_bytes()
    sentinel_before = (attempt_dir / ".du-bench-sentinel.json").read_bytes()

    from tools.holdout_replay import runner as runner_mod
    monkeypatch.setattr(runner_mod, "_next_attempt_dir",
                        lambda out_dir, commit: attempt_dir)
    second = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                        manifest_path=env["manifest"], out_dir=out,
                        bindings_path=env["bindings"],
                        sample_ids=["neutral-txt-call"], per_sample_timeout=180)
    assert second["samples"][0]["status"] == "refused"
    assert second["samples"][0]["reason"] == "RESULT_EXISTS_NOT_OVERWRITING"
    assert result_file.read_bytes() == result_before
    assert (attempt_dir / ".du-bench-sentinel.json").read_bytes() == sentinel_before


def test_cleanup_removes_only_owned_attempt_dir(real_chain_env):
    from tools.document_understanding_benchmark import recovery

    env = real_chain_env
    out = env["base"] / "out-cleanup"
    receipt = run_replay(producer_root=env["producer"], producer_commit=env["commit"],
                         manifest_path=env["manifest"], out_dir=out,
                         bindings_path=env["bindings"],
                         sample_ids=["neutral-txt-call"], per_sample_timeout=180)
    attempt_dir = Path(receipt["attempt_dir"])
    foreign = attempt_dir.parent / "foreign-dir"
    foreign.mkdir(exist_ok=True)
    report = recovery.cleanup_owned(attempt_dir)
    assert report["removed"] is True
    assert report["children_removed"]  # sentinel/result/job removed
    # cleanup clears children; removing the now-empty owned dir itself is ours too
    if attempt_dir.exists():
        attempt_dir.rmdir()
    assert not attempt_dir.exists()
    assert foreign.exists()  # never touched
    foreign.rmdir()
