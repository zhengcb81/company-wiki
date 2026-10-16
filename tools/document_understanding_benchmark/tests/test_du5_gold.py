"""DU5-CORPUS: the frozen new set, the preserved old set, and du5-scoped controls.

Three jobs, in the card's own words:

* ``旧集合保持`` — the twenty pre-existing gold files are byte-locked here, so
  the new set can never be merged into, or silently rewrite, the old one;
* ``新集合校验`` — the nine ``du5-*`` records must be a real, frozen, honestly
  attributed corpus: ≥6 document shapes, ≥4 companies, A/H/US coverage, per
  sample SHA-bound originals, freeze digests and prior-use records;
* real behaviour positive controls on the frozen du5 gold — one readable
  support group survives an opaque alternative, and a correct quote on the
  wrong page can never be recalled (the ``错页行`` counterexample).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.contamination import (
    contamination_by_id,
    support_set_digest,
)
from tools.document_understanding_benchmark.gold import GOLD_DIR, load_gold_dir

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = REPO_ROOT / "tools" / "document_understanding_benchmark"
MANIFEST_PATH = PACKAGE / "du5_manifest.json"

#: The pre-DU5 gold set, byte-locked 2026-10-15. Hashes are over the
#: git-normalized content (LF), i.e. the blob identity a fresh checkout
#: materializes on every platform — ``core.autocrlf=true`` hosts smudge the
#: working copy to CRLF, so hashing raw working bytes would lock the host, not
#: the gold. A change here means old gold was edited — that needs its own
#: correction record and version, never a silent rewrite.
OLD_GOLD_SHA256 = {
    "cn-equity.json": "3a365abac9effe0a06c7ebf47239b2ec41e2e3f775e022f2456cb0efb19a7d39",
    "cn-h1.json": "10d1dc12e251e57354599c58abd55d5ee3d010259a8bf04415a73fb55cb2a335",
    "cn-ipo-confirmation.json": "0cd4b300ddad687c32ac9d9aa335f799fb9a355c6e49a4af360034e106ee5e7a",
    "cn-ir.json": "37e20bcae25648377457d69df05493011f845c287ee79fe19e1ce99e6e71e2a5",
    "cn-q-business.json": "0c5df70c402990e3fc1f16abf8add93956e9964678eef66ba2df24e98fb0f0ed",
    "cn-q-sparse.json": "ce16d824f6dbc775018224b12d2725cd31256e7b87f25cbc6837d0298f46f404",
    "fresh-cn-smic-fy2025.json": "d00ddbd8cb1bacd008416b1258cbc5aa6e199125fccfb620f932976fd0b1391c",
    "fresh-hk-anta-fy2025.json": "85dde8c05713dc06c459719e40d00eb45d40723e11148565b0161861f3187371",
    "fresh-us-apple-10k.json": "e6df1dec4dd3c56ab673df07ab7e8f48cae8551859595d14c4cf5a30d0d7a3f7",
    "hk-annual-mojibake.json": "d47cba87351c8387de8a4b4a79710de88de9ebc663a23f1b0dd9ffa93a703c35",
    "hk-annual.json": "ca0ff77cb0243e2d512da6b88b5e7d315e0dacaf8f7653993586dbf84ea1693e",
    "holdout-cn-glodon-q1.json": "d5731c52e924b31172fa09846ddb39ec37099502775135abde24f7b3fd2048fd",
    "holdout-cn-yake-q1.json": "0663bc5ff56bb980edb5001b345a8084c3d8f9bb618b295a2e457b3949d18d85",
    "holdout-hk-alibaba-fy2023.json": "7593f953805b38907f3827dde32919937d46080d0108c88280f8ec3e04a3f414",
    "holdout-hk-biren-fy2025.json": "6e3079ab763071ed572f70fc9ea00f93a7d5321abaa683d7c31ce2ebf4c099c0",
    "holdout-us-mongodb-10k.json": "1d5884b6f3c5ff480303581ff147a6e04354228fbbfd5f22a05d3aaf196ceca0",
    "holdout-us-nvidia-10k.json": "394aba0ad0c33afa751abfff184ea3a16290ec458f9cd320a9913e7ed18918b2",
    "us-10k.json": "d1a9d6c2cfa4a9518fdea9c018496b0eacf75ebb2cb8f7887536c17161d44b74",
    "us-20f.json": "d41b68f9206ac7b91870efa8ebaee2ef7917b0931eb4eb382fc2379dd32bc137",
    "us-txt.json": "e6d41f0c9eb97535a56ba3d0df9ceab380939729ab763ed93fae9ef684be67ce",
}


def _locked_sha(path: Path) -> str:
    """Hash the git-normalized (LF) content — the blob identity, not host EOL."""

    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

DU5_PREFIX = "du5-"
REQUIRED_BUSINESS_TARGET_KEYS = {
    "subject",
    "stage",
    "plan_negation_conditional",
    "overseas_new_business",
    "investment_vs_capacity_vs_revenue",
    "amounts_units_periods",
}


def _du5_records() -> list[dict]:
    return [r for r in load_gold_dir() if r["sample_id"].startswith(DU5_PREFIX)]


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf8"))


# ---------------------------------------------------------------------------
# 旧集合保持
# ---------------------------------------------------------------------------


def test_old_gold_set_is_byte_preserved():
    """The old gold files must not move; new work never rewrites them."""

    drifted = []
    for name, expected in OLD_GOLD_SHA256.items():
        path = GOLD_DIR / name
        assert path.is_file(), f"old gold file vanished: {name}"
        actual = _locked_sha(path)
        if actual != expected:
            drifted.append(f"{name}: {actual[:12]} != {expected[:12]}")
    assert not drifted, "old gold edited without a correction record: " + "; ".join(drifted)


def test_du5_gold_never_replaces_an_old_sample_id():
    """New samples carry the du5- prefix; old ids stay reserved for old gold."""

    old_ids = set(OLD_GOLD_SHA256)
    for record in load_gold_dir():
        if record["sample_id"] + ".json" in old_ids:
            assert not record["sample_id"].startswith(DU5_PREFIX)


# ---------------------------------------------------------------------------
# 新集合校验
# ---------------------------------------------------------------------------


def test_du5_set_meets_the_card_spread():
    """6–10 samples, ≥4 companies, A/H/US markets, ≥6 document shapes."""

    records = _du5_records()
    assert 6 <= len(records) <= 10, f"du5 set size {len(records)}"
    manifest = _manifest()
    shapes = {row["shape"] for row in manifest["samples"]}
    companies = {row["company"] for row in manifest["samples"]}
    markets = {row["market"] for row in manifest["samples"]}
    assert len(shapes) >= 6, f"shapes covered: {sorted(shapes)}"
    assert len(companies) >= 4, f"companies covered: {sorted(companies)}"
    assert {"CN", "HK", "US"} <= markets, f"markets covered: {markets}"


def test_du5_records_are_frozen_before_candidate_output():
    for record in _du5_records():
        raw = json.loads((GOLD_DIR / f"{record['sample_id']}.json").read_text(encoding="utf8"))
        assert record["scope"] == "holdout", record["sample_id"]
        assert raw.get("support_set_frozen_before_output") is True, record["sample_id"]
        assert support_set_digest(raw) == raw["support_set_digest"], record["sample_id"]
        assert record["gold_quote_chars"] <= 8 * 1024, record["sample_id"]


def test_du5_manifest_matches_the_packaged_gold():
    manifest = _manifest()
    assert manifest["schema_version"] == "du5-manifest/1"
    rows = manifest["samples"]
    gold_ids = {record["sample_id"] for record in _du5_records()}
    assert {row["sample_id"] for row in rows} == gold_ids
    for row in rows:
        gold_path = PACKAGE / row["gold_file"]
        actual = _locked_sha(gold_path)
        assert actual == row["gold_sha256"], f"{row['sample_id']} gold bytes drifted after freeze"
        raw = json.loads(gold_path.read_text(encoding="utf8"))
        assert row["support_set_digest"] == raw["support_set_digest"], row["sample_id"]
        assert row["frozen_before_candidate_output"] is True, row["sample_id"]
        assert row["source_sha256"] == raw["source_sha256"], row["sample_id"]


def test_du5_manifest_records_prior_use_and_reading_scope():
    for row in _manifest()["samples"]:
        prior = row["prior_use"]
        assert prior["status"] in {"fresh", "contaminated"}, row["sample_id"]
        assert prior["known_prior_sightings"], row["sample_id"]
        scope = row["reading_scope"]
        assert any(scope.get(key) for key in ("fully_read_pages", "skimmed_pages", "unread_pages")), (
            row["sample_id"]
        )
        targets = row["business_targets"]
        missing = REQUIRED_BUSINESS_TARGET_KEYS - set(targets)
        assert not missing, f"{row['sample_id']} business targets missing {missing}"


def test_du5_fresh_samples_claim_only_unseen_companies():
    """A du5 sample marked fresh must be a company the benchmark never used."""

    known = {
        row["company"]
        for row in contamination_by_id().values()
        if row["status"] == "contaminated" and row.get("company")
    }
    for row in _manifest()["samples"]:
        if row["prior_use"]["status"] != "fresh":
            continue
        assert row["company"] not in known, (
            f"{row['sample_id']} claims fresh for {row['company']}, already used"
        )


def test_du5_facts_cover_modality_role_and_target_kinds():
    """The card's named risk shapes must actually appear in the frozen facts."""

    modalities: set[str] = set()
    target_kinds: set[str] = set()
    for record in _du5_records():
        for fact in record["facts"]:
            modalities.add(fact["modality"])
            target_kinds.add(fact["target_kind"])
    assert {"actual", "plan", "negation"} <= modalities, modalities
    assert "question" in modalities or "conditional" in modalities, modalities
    assert {"required_business", "disposition_context", "correctness_if_emitted"} == target_kinds


# ---------------------------------------------------------------------------
# real behaviour positive controls on the frozen du5 gold
# ---------------------------------------------------------------------------


def _observed_for(gold: dict, anchors: list[dict], *, page_override: int | None = None) -> dict:
    rows = []
    locators = []
    for index, anchor in enumerate(anchors):
        locator = f"loc:test/{index}"
        locators.append(locator)
        rows.append(
            {
                "locator": locator,
                "text": anchor["exact_quote"],
                "page": page_override if page_override is not None else anchor.get("page"),
            }
        )
    return {
        "schema_version": "du-observed/1",
        "sample_id": gold["sample_id"],
        "source_sha256": gold["source_sha256"],
        "route": None,
        "selected_locators": locators,
        "selected_evidence": rows,
        "selected_text": "",
        "semantic_units": [],
        "claims": [],
        "coverage": {
            "native_scan": "partial",
            "complete": False,
            "opaque_pages": [1],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {},
        "execution": {"mode": "offline_fixture", "calls": 0},
    }


def _fangbang_copperfoil() -> tuple[dict, dict]:
    record = next(r for r in _du5_records() if r["sample_id"] == "du5-cn-fangbang-q1")
    fact = next(f for f in record["facts"] if f["id"] == "copperfoil-project-recognition")
    assert len(fact["any_support_sets"]) >= 2, "control needs two alternative support groups"
    return record, fact


def test_one_readable_support_group_survives_an_opaque_alternative():
    """Positive control on real du5 gold: OR across groups, AND within a group.

    Only the second (page-5) group is present in the observation and page 1 is
    declared opaque; the fact must still be recalled — one opaque alternative
    cannot invalidate another readable complete group.
    """

    from tools.document_understanding_benchmark import evaluate

    gold, fact = _fangbang_copperfoil()
    readable_group = fact["any_support_sets"][1]
    observed = _observed_for(gold, readable_group)
    single_gold = {**gold, "facts": [fact]}
    result = evaluate(observed, single_gold)
    metrics = result["metrics"]
    assert metrics["fact_recall_denominator"] == 1
    assert metrics["fact_recall"] == 1.0, f"readable alternative was dragged down: {result['checks']}"


def test_a_correct_quote_on_the_wrong_page_is_never_recalled():
    """Positive control on real du5 gold: the 错页行 counterexample.

    The exact quote text is present, but at page 999 instead of the page the
    anchor claims — recall must miss, or a wrong-page gold would silently pass.
    """

    from tools.document_understanding_benchmark import evaluate

    gold, fact = _fangbang_copperfoil()
    wrong_group = fact["any_support_sets"][1]
    observed = _observed_for(gold, wrong_group, page_override=999)
    single_gold = {**gold, "facts": [fact]}
    result = evaluate(observed, single_gold)
    metrics = result["metrics"]
    assert metrics["fact_recall_denominator"] == 1
    assert metrics["fact_recall"] == 0.0, "wrong-page evidence was accepted"


def test_duplicate_gold_sample_ids_are_refused(tmp_path):
    """Positive control: a duplicate sample_id must refuse to load, not merge."""

    from tools.document_understanding_benchmark.gold import GoldError, load_gold_dir as load_dir
    from tools.document_understanding_benchmark.schema import BenchmarkSchemaError

    first = (GOLD_DIR / "du5-cn-proya-q1.json").read_text(encoding="utf8")
    (tmp_path / "a.json").write_text(first, encoding="utf8")
    (tmp_path / "b.json").write_text(first, encoding="utf8")
    with pytest.raises((GoldError, BenchmarkSchemaError)):
        load_dir(tmp_path)
