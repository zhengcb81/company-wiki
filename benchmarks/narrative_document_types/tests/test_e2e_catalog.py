"""End-to-end: independent catalog + official read-only interface + locator replay.

The three originals are the ones the lane card names (semi-annual report,
quarterly report, refinancing prospectus). They are copied into this test's own
short tmp root, indexed by a private ``SourceCatalog`` whose SQLite lives under
that root, opened through ``SourceVersionReader.open_version`` with
``purpose="narrative_derivation"`` and the current read-policy pin, then parsed
and selected with the shipped parser/selector. Every selected locator is
replayed from the verified bytes. Nothing is written to a production catalog,
and the tmp root is restored in ``finally``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_VERSION,
    parse_pdf_bytes,
    select_narrative_evidence,
    verify_pdf_evidence_spans_bytes,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_contract import source_id_for_sha256


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
E2E_SAMPLE_IDS = ("S02", "S03", "S05")  # 半年报 / 季报 / 增发募集说明书
E2E_SIDECAR_KINDS = {
    "S02": "semi_annual_report",
    "S03": "quarterly_report",
    "S05": "prospectus",
}


@pytest.fixture(scope="module")
def manifests() -> dict:
    return {
        "samples": json.loads(
            (PACKAGE_ROOT / "samples.json").read_text(encoding="utf-8")
        ),
        "local": json.loads((PACKAGE_ROOT / "local.json").read_text(encoding="utf-8")),
    }


def _sample(manifests: dict, sample_id: str) -> dict:
    return next(
        s for s in manifests["samples"]["samples"] if s["sample_id"] == sample_id
    )


def _source_path(sample: dict, manifests: dict) -> Path:
    root = Path(manifests["local"]["roots"][sample["root_key"]])
    return root / sample["relative_path"]


def _fingerprint(path: Path) -> tuple[int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return stat.st_size, stat.st_mtime_ns, digest


def _sidecar(sample: dict, data: bytes) -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": f"ent-n5-{sample['sample_id'].lower()}",
        "display_name": sample["relative_path"].split("/")[1]
        if "/" in sample["relative_path"]
        else "sample",
        "market": "CN",
        "security_id": sample["sample_id"],
        "document_kind": E2E_SIDECAR_KINDS[sample["sample_id"]],
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-04-01",
        "provider": "n5_document_quality_fixture",
        "provider_document_id": sample["sample_id"],
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "source_url": f"https://fixtures.invalid/n5/{sample['sample_id']}",
        "source_title": Path(sample["relative_path"]).stem,
        "language": sample["language"],
        "retrieved_at": "2026-10-06T00:00:00Z",
        "collector_name": "n5_document_quality_e2e",
        "collector_version": "1.0.0",
    }


def _select_with_production_policy(
    data: bytes, *, source_id: str, sha256: str, title: str, kind: str
):
    """Mirror NarrativeSelectHandler: auto table scan, full scan only if empty."""
    parsed = parse_pdf_bytes(
        data, source_id=source_id, source_sha256=sha256, language="zh"
    )
    package = select_narrative_evidence(parsed, title=title, existing_kind=kind)
    used_full_scan = False
    if not package.evidence_spans and parsed.deferred_table_pages:
        parsed = parse_pdf_bytes(
            data,
            source_id=source_id,
            source_sha256=sha256,
            language="zh",
            full_table_scan=True,
        )
        package = select_narrative_evidence(parsed, title=title, existing_kind=kind)
        used_full_scan = True
    return parsed, package, used_full_scan


def test_independent_catalog_official_read_replay_and_restore(manifests, tmp_path):
    samples = [_sample(manifests, sample_id) for sample_id in E2E_SAMPLE_IDS]
    roots = {key: Path(value) for key, value in manifests["local"]["roots"].items()}
    sources = []
    before: dict[str, tuple[int, int, str]] = {}
    for sample in samples:
        original = roots[sample["root_key"]] / sample["relative_path"]
        if not original.exists():
            pytest.skip(f"original not present: {sample['sample_id']}")
        before[sample["sample_id"]] = _fingerprint(original)
        sources.append((sample, original))

    baseline_entries = set(tmp_path.iterdir())
    run_root = tmp_path / "n5-e2e-catalog"
    catalog: SourceCatalog | None = None
    try:
        for sample, original in sources:
            target = (
                run_root / "companies" / Path(*Path(sample["relative_path"]).parts[1:])
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            data = original.read_bytes()
            shutil.copyfile(original, target)
            target.with_name(target.name + ".source.json").write_text(
                json.dumps(_sidecar(sample, data), ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
                newline="\n",
            )

        config = CatalogConfig(
            project_root=run_root,
            catalog_dir=run_root / "catalog",
            roots=(
                RootSpec(
                    "company_raw",
                    run_root / "companies",
                    "company_raw",
                    priority=10,
                    adapter_id="company_raw_v1",
                    read_only=True,
                    reusable_for_filing=True,
                    canonical_write_target="companies",
                ),
            ),
            reusable_root_kinds=("company_raw",),
        )
        catalog = SourceCatalog(config)
        catalog.scan()
        reader = SourceVersionReader(catalog)
        read_policy_sha256 = reader.read_policy_sha256()

        receipts = []
        for sample, original in sources:
            data = original.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            assert digest == sample["sha256"]
            row = catalog.reader.fetchone(
                """SELECT d.document_id, d.primary_source_id AS source_id
                     FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
                    WHERE d.source_status='active' AND s.content_sha256=?""",
                (digest,),
            )
            assert row is not None, sample["sample_id"]
            ref = reader.query_ref(row["document_id"], row["source_id"], digest)
            content = reader.open_version(
                ref,
                purpose="narrative_derivation",
                expected_read_policy_sha256=read_policy_sha256,
            )
            assert content.content_sha256 == digest, sample["sample_id"]
            assert hashlib.sha256(content.data).hexdigest() == sample["sha256"]

            source_id = source_id_for_sha256(digest)
            parsed, package, used_full_scan = _select_with_production_policy(
                content.data,
                source_id=source_id,
                sha256=digest,
                title=Path(sample["relative_path"]).stem,
                kind=E2E_SIDECAR_KINDS[sample["sample_id"]],
            )
            verified, failed = verify_pdf_evidence_spans_bytes(
                content.data,
                source_id=source_id,
                source_sha256=digest,
                evidence_spans=package.evidence_spans,
            )
            assert list(failed) == [], (sample["sample_id"], list(failed))
            assert len(verified) == len(package.evidence_spans)
            receipts.append(
                {
                    "sample_id": sample["sample_id"],
                    "sha256_prefix": digest[:12],
                    "document_kind": package.document_kind,
                    "status": package.status,
                    "page_count": parsed.page_count,
                    "pages_read": parsed.pages_read,
                    "coverage_complete": parsed.coverage_complete,
                    "selected_span_count": len(package.evidence_spans),
                    "replayed": len(verified),
                    "used_full_scan_retry": used_full_scan,
                    "parser_version": NARRATIVE_PARSER_VERSION,
                    "selector_version": NARRATIVE_SELECTOR_VERSION,
                }
            )

        assert {row["sample_id"] for row in receipts} == set(E2E_SAMPLE_IDS)
        kinds = {row["document_kind"] for row in receipts}
        assert "semi_annual_report" in kinds
        assert "quarterly_report" in kinds
        assert "equity_offering_prospectus" in kinds
        for row in receipts:
            assert row["parser_version"] == NARRATIVE_PARSER_VERSION
            assert row["selector_version"] == NARRATIVE_SELECTOR_VERSION
            print(
                "N5_E2E_RECEIPT " + json.dumps(row, ensure_ascii=False, sort_keys=True)
            )
    finally:
        if catalog is not None:
            catalog.close()
        if run_root.exists():
            shutil.rmtree(run_root, ignore_errors=True)
        for sample, original in sources:
            assert _fingerprint(original) == before[sample["sample_id"]], sample[
                "sample_id"
            ]
        assert set(tmp_path.iterdir()) == baseline_entries
