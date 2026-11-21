"""Offline end-to-end: real CLI process, frozen real responses, all three tables.

FF-style entry (``python -m company_wiki.source_catalog.financial_statements.cli``)
runs against the fixture replay root: 12 data pages plus one protocol-null
terminating page per statement. Assertions pin the frozen counts (income 36 /
balance 33 / cash 36 periods, 9,729 source rows including group/null rows),
exact anchor values with resolvable JSON Pointers, zero-HTTP reuse, narrative
exclusion, and corrupt-original rejection.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

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
    with closing(SourceCatalog(config)) as catalog:
        catalog.scan()
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


def _run(
    wiki_root: Path, fixture_root: Path | None, *, request: dict | None = None,
    capture: Path | None = None,
) -> subprocess.CompletedProcess:
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
    if capture is not None:
        command += ["--import-capture", str(capture)]
    return subprocess.run(
        command,
        input=json.dumps(REQUEST if request is None else request, ensure_ascii=False).encode("utf-8"),
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
    with closing(sqlite3.connect(db)) as conn:
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


def test_observed_capture_import_and_exact_period_reuse(tmp_path):
    wiki_root = _wiki_root(tmp_path)
    capture = fixtures.CAPTURE_DIR / "observations.json"
    request = {
        **REQUEST, "intent": "reuse_only", "knowledge_mode": "point_in_time",
        "as_of_date": "2026-10-26", "period_end_from": "2025-12-31",
        "period_end_to": "2025-12-31",
    }
    del request["acquisition_limits"]
    first = _run(wiki_root, None, request=request, capture=capture)
    assert first.returncode == 0, first.stderr.decode("utf-8", "replace")
    receipt = json.loads(first.stdout)
    counts = _db_counts(wiki_root)
    assert counts[0] > 0 and counts[2] == 0
    assert receipt["usage"]["http_requests"] == 0
    again = _run(wiki_root, None, request=request, capture=capture)
    assert again.returncode == 0
    assert _db_counts(wiki_root) == counts
    assert len(_lake(wiki_root)) == len({hashlib.sha256(f.read_bytes()).digest() for f in _lake(wiki_root)})

    reused = json.loads(_run(wiki_root, None, request=request).stdout)
    assert reused["status"] == "complete"
    assert len(reused["statements"]) == 3
    for block in reused["statements"]:
        assert block["coverage"]["terminal_reason"] is None
        report, = block["reports"]
        assert report["observed_at"].startswith("2026-10-25T")
        assert report["pit_verified"] is True

    prior = json.loads(_run(wiki_root, None, request={**request, "as_of_date": "2026-10-24"}).stdout)
    assert prior["status"] == "not_found"
    history = json.loads(_run(wiki_root, None, request={**request, "period_end_from": "2016-01-01"}).stdout)
    assert history["status"] == "partial"


def test_observed_capture_cannot_replace_page_bytes(tmp_path):
    wiki_root = _wiki_root(tmp_path)
    location = tmp_path / "captured"
    location.mkdir()
    records = json.loads((fixtures.CAPTURE_DIR / "observations.json").read_text(encoding="utf-8"))
    record = next(row for row in records if (row.get("fixture") or "").startswith("sh688012-lrb-type0-page1"))
    # Replacing the retained compressed file cannot retain the original receipt.
    (location / record["fixture"]).write_bytes(fixtures.fixture_path("sh688012-lrb-type0-page2-num10.json.gz").read_bytes())
    observation = location / "observations.json"
    observation.write_text(json.dumps([record]), encoding="utf-8")
    before = _db_counts(wiki_root)
    run = _run(wiki_root, None, capture=observation)
    assert run.returncode == 2
    assert "capture" in json.loads(run.stdout)["error"].lower()
    assert _db_counts(wiki_root) == before
    assert not _lake(wiki_root)


def _frozen_observation(directory, source, body, at):
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{source}.json"
    (directory / filename).write_bytes(body)
    return {
        "url": ("https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
                f"?paperCode=sh688012&source={source}&type=0&page=1&num=10"),
        "fixture": filename,
        "http_status": 200,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "retrieved_at": at,
    }


def test_capture_returns_the_unambiguous_observed_security(tmp_path):
    from company_wiki.source_catalog.financial_statements.sina_captures import read_captured_pages

    row = _frozen_observation(tmp_path, "lrb", b"{}", "2026-10-25T08:00:00Z")
    observed_url = row["url"].replace("sh688012", "sz000001")
    urls = [observed_url.replace("sz000001", "sh000001"),
            observed_url + "&paperCode=", observed_url]
    manifest = tmp_path / "observations.json"
    manifest.write_text(json.dumps([{**row, "url": url} for url in urls]), encoding="utf-8")

    page, = read_captured_pages(manifest, exchange="SZSE", code="000001",
                                statements=("income_statement",))
    assert (page.url, page.paper_code) == (observed_url, "sz000001")


def test_historical_source_attribution_uses_the_retained_provider_or_exact_capture(tmp_path):
    from company_wiki.source_catalog.financial_statements.sina_captures import matches_replay_source

    url = _frozen_observation(tmp_path, "lrb", b"{}", "2026-10-25T08:00:00Z")["url"]
    scope = {"exchange": "SSE", "code": "688012", "source_key": "lrb"}
    assert matches_replay_source(None, url, **scope)
    assert matches_replay_source("sina_finance", None, **scope)
    assert not matches_replay_source("other_vendor", url, **scope)
    assert not matches_replay_source(None, None, **scope)
    assert not matches_replay_source(None, url.replace("sh688012", "sz688012"), **scope)
    assert not matches_replay_source("sina_finance", url.replace("lrb", "fzb"), **scope)


def _exact_income_request(**changes):
    request = {
        **REQUEST, "statements": ["income_statement"], "intent": "reuse_only",
        "knowledge_mode": "point_in_time", "as_of_date": "2026-10-25",
        "period_end_from": "2025-12-31", "period_end_to": "2025-12-31",
        **changes,
    }
    del request["acquisition_limits"]
    return request


@pytest.mark.parametrize("same_source", [True, False])
def test_older_capture_reuses_business_version_with_its_own_original(tmp_path, same_source):
    import gzip
    import sqlite3

    wiki_root = _wiki_root(tmp_path)
    database = wiki_root / ".source_catalog" / "catalog.sqlite3"
    # Simulate an existing 1.4 catalog from before observation-to-source links.
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("DROP TABLE IF EXISTS financial_statement_observation_sources")
    request = _exact_income_request()
    original = gzip.decompress(fixtures.fixture_path("sh688012-lrb-type0-page1-num10.json.gz").read_bytes())
    late_raw = original if same_source else original + b"\n"
    captures = [
        ("late", late_raw, "2026-10-26T08:00:00.550721+00:00"),
        ("early", original, "2026-10-25T08:00:00.440000+00:00"),
    ]
    manifests = {}
    for label, body, at in captures:
        directory = tmp_path / label
        row = _frozen_observation(directory, "lrb", body, at)
        manifests[label] = directory / "observations.json"
        manifests[label].write_text(json.dumps([row]), encoding="utf-8")
    baseline = _run(wiki_root, None, request=request)
    assert json.loads(baseline.stdout)["status"] == "not_found"
    late = _run(wiki_root, None, request=request, capture=manifests["late"])
    assert late.returncode == 0, late.stdout.decode()
    assert json.loads(_run(wiki_root, None, request=request).stdout)["status"] == "not_found"
    early = _run(wiki_root, None, request=request, capture=manifests["early"])
    assert early.returncode == 0, early.stdout.decode()
    early_result = json.loads(_run(wiki_root, None, request=request).stdout)
    assert early_result["status"] == "complete", early_result
    prior, = early_result["statements"][0]["reports"]
    assert prior["pit_verified"] is True
    assert prior["observed_at"] == "2026-10-25T08:00:00.440000Z"
    assert prior["source_ref"]["content_sha256"] == hashlib.sha256(original).hexdigest()
    present, = json.loads(_run(wiki_root, None, request={**request, "as_of_date": "2026-10-26"}).stdout)["statements"][0]["reports"]
    assert present["statement_version_id"] == prior["statement_version_id"]
    assert present["source_ref"]["content_sha256"] == hashlib.sha256(late_raw).hexdigest()
    assert present["observed_at"] == "2026-10-26T08:00:00.550721Z"

    again = _run(wiki_root, None, request=request, capture=manifests["early"])
    assert again.returncode == 0
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM financial_statement_observations").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM financial_statement_observation_sources").fetchone()[0] == 2
    assert len(_lake(wiki_root)) == (1 if same_source else 2)


def test_malformed_later_capture_does_not_publish_earlier_page(tmp_path):
    import gzip

    wiki_root = _wiki_root(tmp_path)
    directory = tmp_path / "archive"
    original = gzip.decompress(fixtures.fixture_path("sh688012-lrb-type0-page1-num10.json.gz").read_bytes())
    rows = [
        _frozen_observation(directory, "lrb", original, "2026-10-25T08:00:00Z"),
        _frozen_observation(directory, "fzb", b"{bad json", "2026-10-25T08:00:01Z"),
    ]
    manifest = directory / "observations.json"
    manifest.write_text(json.dumps(rows), encoding="utf-8")
    before = _db_counts(wiki_root)
    request = _exact_income_request(statements=["income_statement", "balance_sheet"])
    failed = _run(wiki_root, None, request=request, capture=manifest)
    assert failed.returncode == 2
    assert _db_counts(wiki_root) == before
    assert not _lake(wiki_root)


@pytest.mark.parametrize("same_instant", [False, True])
def test_capture_clock_orders_versions_independent_of_ingestion(tmp_path, same_instant):
    import gzip

    wiki_root = _wiki_root(tmp_path)
    request = _exact_income_request()
    raw = gzip.decompress(fixtures.fixture_path("sh688012-lrb-type0-page1-num10.json.gz").read_bytes())
    changed = json.loads(raw)
    rows = changed["result"]["data"]["report_list"]["20251231"]["data"]
    next(item for item in rows if item.get("item_field") == "BIZTOTINCO")["item_value"] = "42.000000"
    updated = json.dumps(changed).encode()
    latest = "2026-10-25T08:00:00.000001Z"
    earlier = latest if same_instant else "2026-10-25T08:00:00Z"
    # Import newest first. SQLite insertion order says the opposite.
    for i, (body, at) in enumerate(((updated, latest), (raw, earlier))):
        directory = tmp_path / str(i)
        entry = _frozen_observation(directory, "lrb", body, at)
        manifest = directory / "observations.json"
        manifest.write_text(json.dumps([entry]), encoding="utf-8")
        response = _run(wiki_root, None, request=request, capture=manifest)
        assert response.returncode == 0, response.stdout.decode()
    result = json.loads(_run(wiki_root, None, request=request).stdout)
    report, = result["statements"][0]["reports"]
    assert report["pit_verified"] is (not same_instant)
    if same_instant:
        assert result["status"] == "partial"
    else:
        assert result["status"] == "complete"
        assert report["observed_at"] == latest
        assert report["source_ref"]["content_sha256"] == hashlib.sha256(updated).hexdigest()


@pytest.mark.skipif(
    not os.environ.get("MB_RF_ROOT") or not os.environ.get("MB_FF_ROOT"),
    reason="ROOT E07 uses explicitly selected RF and FF runtimes",
)
def test_rf_reads_three_statement_histories_through_ff(tmp_path):
    wiki_root = _wiki_root(tmp_path)
    fixture_root = _fixture_root(tmp_path)
    initial = _run(wiki_root, fixture_root)
    assert initial.returncode == 0, initial.stderr.decode("utf-8", errors="replace")
    captured = json.loads(initial.stdout)
    assert captured["status"] == "complete"
    reports = [report for table in captured["statements"] for report in table["reports"]]
    as_of = max(report["observed_at"][:10] for report in reports)
    # A further provider read would fail because the fixture manifest is gone.
    (fixture_root / "manifest.json").unlink()
    original_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in _lake(wiki_root)}
    counts = _db_counts(wiki_root)
    assert counts == (105, TOTAL_SOURCE_ROWS, 0)

    empty = tmp_path / "unrelated-cwd"
    empty.mkdir()
    config = tmp_path / "ff-connection.json"
    config.write_text(json.dumps({
        "schema_version": "1.0",
        "connection": {"cwd": str(empty), "commands": {"financial_statements": [
            sys.executable, "-B", "-m", "company_wiki.source_catalog.financial_statements.cli",
            "--wiki-root", str(wiki_root), "--fixture-root", str(fixture_root),
        ]}},
    }), encoding="utf-8")
    rf = Path(os.environ["MB_RF_ROOT"]).resolve(strict=True)
    ff = Path(os.environ["MB_FF_ROOT"]).resolve(strict=True)
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONUTF8": "1",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHON_DOTENV_DISABLED": "1"}
    command = [
        sys.executable, "-B", str(rf / "scripts/financial_statement_source.py"),
        "--filing-fetch-root", str(ff), "--company-wiki-config", str(config),
    ]
    # RF defaults to reuse. Query the same history twice as of a proven
    # observation date, with the table's own currency and period semantics.
    request = {**REQUEST, "as_of_date": as_of, "knowledge_mode": "point_in_time"}
    del request["intent"], request["acquisition_limits"]
    responses = []
    for _ in range(2):
        result = subprocess.run(
            command, input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
            capture_output=True, cwd=empty, env=env, check=False, timeout=60,
        )
        assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
        received = json.loads(result.stdout)
        assert received["status"] == "complete", received.get("reason")
        assert received["usage"]["http_requests"] == 0
        assert received["request"]["knowledge_mode"] == "point_in_time"
        responses.append(received["statements"])
    assert responses[0] == responses[1]

    by_type = {table["statement_type"]: table for table in responses[0]}
    assert set(by_type) == set(ANCHORS)
    by_hash = {sha: path for path, sha in original_hashes.items()}
    for table, (period, field, expected) in ANCHORS.items():
        assert len(by_type[table]["reports"]) == PAGE_COUNTS[table]
        report = next(r for r in by_type[table]["reports"] if r["period_end"] == period)
        assert report["currency"] == "CNY" and report["pit_verified"] is True
        assert report["period_semantics"] == ("instant" if table == "balance_sheet" else "duration")
        assert report["observed_at"][:10] <= as_of
        row = next(r for r in report["rows"] if r["provider_field"] == field)
        assert row["value_decimal"] == expected
        # Display precision is not the reporting scale. These amount rows
        # have no proven unit; per-share rows below do have one.
        assert row["scale"] is None and row["unit"] is None
        original = by_hash[report["source_ref"]["content_sha256"]]
        value = json.loads(original.read_bytes())
        for key in row["json_pointer"].split("/")[1:]:
            value = value[int(key)] if isinstance(value, list) else value[key]
        assert value == expected

    income = next(r for r in by_type["income_statement"]["reports"]
                  if r["period_end"] == ANCHORS["income_statement"][0])
    eps = next(row for row in income["rows"] if row["provider_field"] == "BASICEPS")
    assert eps["unit"] == "CNY/share" and eps["scale"] == 1

    assert _db_counts(wiki_root) == counts
    assert {path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in _lake(wiki_root)} == original_hashes
    assert not tuple(empty.iterdir())


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
