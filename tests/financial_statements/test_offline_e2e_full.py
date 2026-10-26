"""Offline end-to-end: real CLI process, frozen real responses, all three tables.

FF-style entry (``python -m company_wiki.source_catalog.financial_statements.cli``)
runs against the fixture replay root: 12 data pages plus one protocol-null
terminating page per statement. Assertions pin the frozen counts (income 36 /
balance 33 / cash 36 periods, 9,729 source rows including group/null rows),
exact anchor values with resolvable JSON Pointers, zero-HTTP reuse, narrative
exclusion, and corrupt-original rejection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_routing import classify_document_kind
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)
from company_wiki.source_catalog.service import SourceCatalog

from . import fixtures

REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCES = {"income_statement": "lrb", "balance_sheet": "fzb", "cash_flow": "llb"}
PAGE_COUNTS = {"income_statement": 36, "balance_sheet": 33, "cash_flow": 36}
ROWS_PER_PERIOD = {"income_statement": 77, "balance_sheet": 141, "cash_flow": 64}
ANCHORS = {
    "income_statement": ("2026-06-30", "BIZTOTINCO", "6691287327.670000"),
    "balance_sheet": ("2026-06-30", "CURFDS", "9768212270.460000"),
    "cash_flow": ("2026-06-30", "LABORGETCASH", "5829401875.080000"),
}
NULL_PAGE_BYTES = b'{"result":{"status":{"code":0},"data":null}}'
TOTAL_SOURCE_ROWS = 36 * 77 + 33 * 141 + 36 * 64  # 9,729 incl. group/null rows

REQUEST = {
    "schema_version": "financial-statements-request/1",
    "company_query": "中微公司",
    "market": "CN",
    "statements": ["income_statement", "balance_sheet", "cash_flow"],
    "report_types": ["annual", "semi_annual", "q1", "q3"],
    "period_end_from": "2016-01-01",
    "period_end_to": "2026-06-30",
    "knowledge_mode": "current_snapshot",
    "as_of_date": "2026-10-25",
    "intent": "fetch_if_missing",
    "acquisition_limits": {
        "max_bytes": 8000000, "timeout_seconds": 120, "max_cost_usd": "0.00",
    },
}


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "fixtures"
    root.mkdir()
    entries = []
    for source in SOURCES.values():
        for page in range(1, 5):
            name = f"sh688012-{source}-type0-page{page}-num10.json.gz"
            entries.append(
                {
                    "url": (
                        "https://quotes.sina.cn/cn/api/openapi.php/"
                        "CompanyFinanceService.getFinanceReport2022"
                        f"?paperCode=sh688012&source={source}&type=0&page={page}&num=10"
                    ),
                    "file": name,
                }
            )
        # Terminating null page: byte-exact real observation (sh999999 probe),
        # stored gzipped like every other replay fixture.
        import gzip as _gzip

        terminator = f"null-{source}-page5.json.gz"
        (root / terminator).write_bytes(_gzip.compress(NULL_PAGE_BYTES, 9))
        entries.append(
            {
                "url": (
                    "https://quotes.sina.cn/cn/api/openapi.php/"
                    "CompanyFinanceService.getFinanceReport2022"
                    f"?paperCode=sh688012&source={source}&type=0&page=5&num=10"
                ),
                "file": terminator,
            }
        )
    for entry in entries:
        if entry["file"].startswith("sh688012"):
            (root / entry["file"]).write_bytes(
                fixtures.fixture_path(entry["file"]).read_bytes()
            )
    (root / "manifest.json").write_text(
        json.dumps({"fixtures": entries}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return root


def _wiki_root(tmp_path: Path) -> Path:
    project = tmp_path / "wiki"
    companies = project / "companies"
    companies.mkdir(parents=True)
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    )
    SourceCatalog(config).scan()
    SecurityMasterStore(config.catalog_dir / "security_master").write_market(
        "CN",
        (
            SecurityRecord(
                canonical_name="中微公司", market="CN", exchange="SSE",
                ticker="688012", security_id="688012", aliases=("中微",),
                active=True, source_name="cninfo",
                source_url="https://www.cninfo.com.cn/",
                source_record_id="9900033375", identifiers={},
            ),
        ),
        retrieved_at="2026-10-25T00:00:00Z",
        sources=("cninfo",),
    )
    (project / "config").mkdir(exist_ok=True)
    (project / "config" / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: '${PROJECT_ROOT}/.source_catalog'\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    kind: company_raw\n"
        "    path: companies\n",
        encoding="utf-8",
    )
    return project


def _run(wiki_root: Path, fixture_root: Path | None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    command = [
        sys.executable, "-m",
        "company_wiki.source_catalog.financial_statements.cli",
        "--wiki-root", str(wiki_root),
    ]
    if fixture_root is not None:
        command += ["--fixture-root", str(fixture_root)]
    return subprocess.run(
        command,
        input=json.dumps(REQUEST, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(REPO_ROOT), env=env, timeout=180,
    )


def _lake(wiki_root: Path) -> list[Path]:
    directory = wiki_root / "companies" / "中微公司" / "raw" / "financial_statements"
    return [
        item for item in sorted(directory.glob("*.json"))
        if not item.name.endswith(".source.json")
    ]


def _db_counts(wiki_root: Path):
    import sqlite3

    db = wiki_root / ".source_catalog" / "catalog.sqlite3"
    with sqlite3.connect(db) as conn:
        versions = conn.execute(
            "SELECT COUNT(*) FROM financial_statement_versions"
        ).fetchone()[0]
        values = conn.execute(
            "SELECT COUNT(*) FROM financial_statement_values"
        ).fetchone()[0]
        normalized = conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_role IN ('normalized','summary')"
        ).fetchone()[0]
    return versions, values, normalized


class TestFullHistoryOfflineEndToEnd:
    def test_three_statements_36_33_36_and_9729_rows(self, tmp_path):
        wiki_root = _wiki_root(tmp_path)
        fixture_root = _fixture_root(tmp_path)
        proc = _run(wiki_root, fixture_root)
        assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
        response = json.loads(proc.stdout.decode("utf-8"))
        assert response["status"] == "complete"
        by_type = {s["statement_type"]: s for s in response["statements"]}
        total_rows = 0
        for statement_type, expected_periods in PAGE_COUNTS.items():
            statement = by_type[statement_type]
            assert statement["status"] == "complete"
            assert statement["coverage"]["observed_periods"] == expected_periods
            assert statement["coverage"]["pages"] == 4
            assert statement["usage"]["http_requests"] == 5  # 4 data + 1 null
            assert len(statement["reports"]) == expected_periods
            row_counts = {len(r["rows"]) for r in statement["reports"]}
            assert row_counts == {ROWS_PER_PERIOD[statement_type]}
            total_rows += sum(len(r["rows"]) for r in statement["reports"])
        assert total_rows == TOTAL_SOURCE_ROWS == 9729
        assert response["usage"]["http_requests"] == 15

        # anchor values with pointers that resolve inside the exact committed
        # original each report references (content-addressed file name)
        for statement_type, (period, field, expected) in ANCHORS.items():
            report = next(
                r for r in by_type[statement_type]["reports"]
                if r["period_end"] == period
            )
            row = next(r for r in report["rows"] if r["provider_field"] == field)
            assert row["value_decimal"] == expected
            original_path = (
                _lake(wiki_root)[0].parent
                / f"{report['source_ref']['content_sha256']}.json"
            )
            original = json.loads(original_path.read_bytes().decode("utf-8"))
            candidate = original
            for segment in row["json_pointer"].lstrip("/").split("/"):
                segment = int(segment) if isinstance(candidate, list) else segment
                candidate = candidate[segment]
            assert candidate == expected

        versions, values, normalized = _db_counts(wiki_root)
        assert versions == sum(PAGE_COUNTS.values()) == 105
        assert values == TOTAL_SOURCE_ROWS
        assert normalized == 0  # nothing entered the narrative artifact chain
        # directed regression: the dataset kind is never routed into the
        # financial-report narrative lanes.
        route_kind = classify_document_kind(
            "Sina lrb sh688012 page 1", existing_kind="financial_statement_dataset"
        )
        assert route_kind == "financial_statement_dataset"

        # repeat identical request: zero HTTP, zero growth, same versions
        (fixture_root / "manifest.json").unlink()  # any HTTP attempt now fails
        before_files = [item.stat().st_size for item in _lake(wiki_root)]
        second_proc = _run(wiki_root, fixture_root)
        assert second_proc.returncode == 0
        second = json.loads(second_proc.stdout.decode("utf-8"))
        assert second["status"] == "complete"
        assert second["usage"]["http_requests"] == 0
        versions2, values2, _ = _db_counts(wiki_root)
        assert (versions2, values2) == (versions, values)
        assert [item.stat().st_size for item in _lake(wiki_root)] == before_files
        first_ids = {
            (s["statement_type"], r["statement_version_id"])
            for s in response["statements"] for r in s["reports"]
        }
        second_ids = {
            (s["statement_type"], r["statement_version_id"])
            for s in second["statements"] for r in s["reports"]
        }
        assert first_ids == second_ids

        # space: initial originals plus database stay within the 16MiB target
        originals_bytes = sum(item.stat().st_size for item in _lake(wiki_root))
        db_bytes = (wiki_root / ".source_catalog" / "catalog.sqlite3").stat().st_size
        assert originals_bytes + db_bytes <= 16 * 1024 * 1024

    def test_corrupted_original_is_rejected_by_reader(self, tmp_path):
        wiki_root = _wiki_root(tmp_path)
        fixture_root = _fixture_root(tmp_path)
        proc = _run(wiki_root, fixture_root)
        assert proc.returncode == 0
        response = json.loads(proc.stdout.decode("utf-8"))
        report = next(
            r for r in response["statements"][0]["reports"]
            if r["period_end"] == "2026-06-30"
        )
        reference = report["source_ref"]

        from company_wiki.source_catalog.source_reader import (
            SourceReadError,
            SourceVersionReader,
        )

        config = load_wiki_config(wiki_root)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(
            reference["document_id"], reference["source_id"],
            reference["content_sha256"],
        )
        # happy path first, then corrupt the committed bytes
        assert reader.open_version(ref).content_sha256 == reference["content_sha256"]
        target = _lake(wiki_root)[0]
        original_bytes = target.read_bytes()
        target.write_bytes(original_bytes[:-2] + b"xx")
        try:
            raised = False
            try:
                reader.open_version(ref)
            except SourceReadError:
                raised = True
            # the corrupted file is the one whose sha differs; find the ref
            # that breaks instead of assuming file order
            if not raised:
                for item in _lake(wiki_root):
                    data = item.read_bytes()
                    if data != original_bytes and item.name == target.name:
                        pass
                # corrupted bytes may belong to a different page; verify by
                # reading every ref until one refuses
                for statement in response["statements"]:
                    for rep in statement["reports"]:
                        candidate = reader.query_ref(
                            rep["source_ref"]["document_id"],
                            rep["source_ref"]["source_id"],
                            rep["source_ref"]["content_sha256"],
                        )
                        try:
                            reader.open_version(candidate)
                        except SourceReadError:
                            raised = True
                            break
                    if raised:
                        break
            assert raised
        finally:
            target.write_bytes(original_bytes)


def load_wiki_config(wiki_root: Path):
    from company_wiki.source_catalog.config import load_catalog_config

    return load_catalog_config(
        wiki_root / "config" / "source_catalog.yaml", project_root=wiki_root
    )
