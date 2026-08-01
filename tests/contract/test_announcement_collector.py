"""Consumer contract for the create-once official announcement collector."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE_URL = (
    "https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/"
    "2026-03-25/688012_20260325_404H.pdf"
)
FINAL_URL = SOURCE_URL.replace("star.sse.com.cn", "static.sse.com.cn")
TITLE = "关于召开2025年度业绩说明会的公告"
PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _collector():
    return importlib.import_module(
        "company_wiki.source_contract.announcement_collector"
    )


def _cli():
    return importlib.import_module("company_wiki.source_contract.announcement_cli")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "companies" / "中微公司").mkdir(parents=True)
    return root


def _response(module, **overrides):
    values = {
        "body": PDF_BYTES,
        "final_url": FINAL_URL,
        "content_type": "application/pdf; charset=binary",
        "etag": '"official-etag"',
        "last_modified": "Wed, 25 Mar 2026 08:00:00 GMT",
    }
    values.update(overrides)
    return module.DownloadedAnnouncement(**values)


def _collect(module, root: Path, *, response=None, **overrides):
    response = response or _response(module)

    def fetcher(url: str, max_bytes: int):
        assert url == SOURCE_URL
        assert max_bytes > 0
        return response

    values = {
        "root": root,
        "company_name": "中微公司",
        "entity_ids": ("SSE:688012",),
        "source_url": SOURCE_URL,
        "title": TITLE,
        "published_date": "2026-03-25",
        "fetcher": fetcher,
        "now": lambda: datetime(2026, 7, 18, 12, 34, 56, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return module.collect_announcement(**values)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize(
    "url",
    (
        "http://star.sse.com.cn/announcement.pdf",
        "https://star.sse.com.cn.evil.example/announcement.pdf",
        "https://user@star.sse.com.cn/announcement.pdf",
        "https://star.sse.com.cn:8443/announcement.pdf",
        "https://star.sse.com.cn/announcement.pdf#fragment",
        "file:///tmp/announcement.pdf",
    ),
)
def test_url_policy_rejects_non_official_or_ambiguous_urls(url):
    module = _collector()
    with pytest.raises(module.AnnouncementURLPolicyError):
        module.validate_official_announcement_url(url)


@pytest.mark.parametrize(
    "url",
    (
        SOURCE_URL,
        "https://static.sse.com.cn/disclosure/item.pdf",
        "https://disc.static.szse.cn/download/item.pdf?name=1",
        "https://www.szse.cn/disclosure/item.pdf",
    ),
)
def test_url_policy_accepts_https_exchange_domains_and_normalizes_host(url):
    module = _collector()
    assert module.validate_official_announcement_url(url) == url


def test_redirect_handler_rejects_redirect_before_request_leaves_official_domains():
    module = _collector()
    handler = module._OfficialRedirectHandler()
    with pytest.raises(module.AnnouncementURLPolicyError):
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://attacker.example/announcement.pdf",
        )


@pytest.mark.parametrize(
    ("response_overrides", "error_text"),
    (
        ({"body": b""}, "empty"),
        ({"body": b"<html>blocked</html>"}, "PDF magic"),
        ({"body": b"%PDF-1.4\nmissing trailer"}, "EOF"),
        ({"content_type": "text/html"}, "content type"),
        ({"final_url": "https://attacker.example/item.pdf"}, "official"),
    ),
)
def test_collection_rejects_non_pdf_or_non_official_responses(
    tmp_path, response_overrides, error_text
):
    module = _collector()
    root = _root(tmp_path)
    with pytest.raises(module.AnnouncementCollectionError, match=error_text):
        _collect(module, root, response=_response(module, **response_overrides))
    assert not (root / "companies" / "中微公司" / "raw").exists()


def test_collection_rejects_response_above_explicit_size_limit(tmp_path):
    module = _collector()
    root = _root(tmp_path)
    with pytest.raises(module.AnnouncementContentError, match="maximum"):
        _collect(module, root, max_bytes=len(PDF_BYTES) - 1)
    assert not (root / "companies" / "中微公司" / "raw").exists()


@pytest.mark.parametrize(
    "company_name",
    ("../中微公司", "中微公司/其他", "中微公司\\其他", ".", " 中微公司"),
)
def test_collection_rejects_company_path_escape_before_fetch(tmp_path, company_name):
    module = _collector()
    root = _root(tmp_path)
    called = False

    def fetcher(url: str, max_bytes: int):
        nonlocal called
        called = True
        return _response(module)

    with pytest.raises(module.AnnouncementCollectionError):
        module.collect_announcement(
            root=root,
            company_name=company_name,
            entity_ids=("SSE:688012",),
            source_url=SOURCE_URL,
            title=TITLE,
            published_date="2026-03-25",
            fetcher=fetcher,
        )
    assert called is False


def test_success_creates_content_addressed_raw_manifest_and_provenance(tmp_path):
    module = _collector()
    root = _root(tmp_path)
    receipt = _collect(module, root)
    data = receipt.to_dict()
    content_hash = hashlib.sha256(PDF_BYTES).hexdigest()
    provenance_key = hashlib.sha256(
        (content_hash + "\0" + SOURCE_URL).encode("utf-8")
    ).hexdigest()
    expected_raw = (
        root
        / "companies"
        / "中微公司"
        / "raw"
        / "announcements"
        / f"{content_hash}.pdf"
    )
    expected_manifest = (
        root / "source_manifests" / "companies" / "中微公司" / f"{content_hash}.json"
    )
    expected_provenance = (
        root
        / "source_provenance"
        / "companies"
        / "中微公司"
        / "announcements"
        / f"{provenance_key}.json"
    )

    assert expected_raw.read_bytes() == PDF_BYTES
    assert json.loads(expected_manifest.read_text(encoding="utf-8")) == data["manifest"]
    assert json.loads(expected_provenance.read_text(encoding="utf-8")) == data
    assert data["schema_version"] == "1.0.0"
    assert data["source_url"] == SOURCE_URL
    assert data["final_url"] == FINAL_URL
    assert data["title"] == TITLE
    assert data["published_date"] == "2026-03-25"
    assert data["retrieved_at"] == "2026-07-18T12:34:56Z"
    assert data["manifest_path"] == (
        f"source_manifests/companies/中微公司/{content_hash}.json"
    )
    assert data["provenance_path"] == (
        "source_provenance/companies/中微公司/announcements/"
        f"{provenance_key}.json"
    )
    assert data["manifest"]["original_path"] == (
        f"companies/中微公司/raw/announcements/{content_hash}.pdf"
    )
    assert data["manifest"]["source_type"] == "company_announcement"
    assert data["manifest"]["immutable_status"] == "verified"
    assert data["manifest"]["collector_name"] == module.ANNOUNCEMENT_COLLECTOR_NAME
    assert data["manifest"]["collector_version"] == module.ANNOUNCEMENT_COLLECTOR_VERSION
    assert data["manifest"]["content_sha256"] == content_hash
    assert data["manifest"]["byte_size"] == len(PDF_BYTES)
    payload = dict(data)
    collection_id = payload.pop("collection_id")
    assert collection_id == module.ANNOUNCEMENT_COLLECTION_ID_PREFIX + _canonical_sha256(
        payload
    )


def test_repeat_collection_is_byte_stable_and_does_not_rewrite_files(tmp_path):
    module = _collector()
    root = _root(tmp_path)
    first = _collect(module, root)
    tracked = tuple(
        path
        for path in root.rglob("*")
        if path.is_file()
    )
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in tracked
    }
    second = _collect(
        module,
        root,
        response=_response(module, etag='"changed-but-same-content"'),
        now=lambda: datetime(2026, 7, 18, 13, 0, 0, tzinfo=timezone.utc),
    )
    assert second.canonical_json() == first.canonical_json()
    assert set(path for path in root.rglob("*") if path.is_file()) == set(tracked)
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in tracked
    } == before


def test_existing_raw_tamper_is_a_conflict_and_never_overwritten(tmp_path):
    module = _collector()
    root = _root(tmp_path)
    receipt = _collect(module, root)
    raw = root / receipt.manifest.original_path
    replacement = b"X" * len(PDF_BYTES)
    raw.write_bytes(replacement)
    with pytest.raises(module.AnnouncementConflictError, match="existing raw"):
        _collect(module, root)
    assert raw.read_bytes() == replacement


def test_existing_manifest_tamper_is_a_conflict_and_never_overwritten(tmp_path):
    module = _collector()
    root = _root(tmp_path)
    receipt = _collect(module, root)
    manifest = root / receipt.manifest_path
    replacement = b'{}\n'
    manifest.write_bytes(replacement)
    with pytest.raises(module.AnnouncementConflictError, match="manifest"):
        _collect(module, root)
    assert manifest.read_bytes() == replacement


def test_crash_after_raw_and_manifest_is_recoverable_without_raw_rewrite(
    tmp_path, monkeypatch
):
    module = _collector()
    root = _root(tmp_path)
    original = module._immutable_create_json

    def fail_provenance(path: Path, value: object, *, root: Path):
        if "source_provenance" in path.parts:
            raise OSError("injected provenance failure")
        return original(path, value, root=root)

    monkeypatch.setattr(module, "_immutable_create_json", fail_provenance)
    with pytest.raises(OSError, match="injected provenance failure"):
        _collect(module, root)
    raw_files = list((root / "companies" / "中微公司" / "raw").rglob("*.pdf"))
    manifest_files = list((root / "source_manifests").rglob("*.json"))
    assert len(raw_files) == len(manifest_files) == 1
    raw_before = (raw_files[0].read_bytes(), raw_files[0].stat().st_mtime_ns)

    monkeypatch.setattr(module, "_immutable_create_json", original)
    receipt = _collect(
        module,
        root,
        now=lambda: datetime(2026, 7, 18, 14, 0, 0, tzinfo=timezone.utc),
    )
    assert (raw_files[0].read_bytes(), raw_files[0].stat().st_mtime_ns) == raw_before
    assert receipt.retrieved_at == "2026-07-18T12:34:56Z"
    assert (root / receipt.provenance_path).is_file()


def test_download_reads_bounded_bytes_and_preserves_response_metadata():
    module = _collector()

    class Response:
        status = 200
        headers = {
            "Content-Type": "application/pdf",
            "ETag": '"etag"',
            "Last-Modified": "Wed, 25 Mar 2026 08:00:00 GMT",
            "Content-Length": str(len(PDF_BYTES)),
        }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def geturl(self):
            return FINAL_URL

        def read(self, size: int):
            assert size == len(PDF_BYTES) + 1
            return PDF_BYTES

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == SOURCE_URL
            assert timeout > 0
            return Response()

    result = module.download_announcement(
        SOURCE_URL,
        max_bytes=len(PDF_BYTES),
        opener=Opener(),
    )
    assert result == _response(module, final_url=FINAL_URL, content_type="application/pdf", etag='"etag"')


def test_collector_module_is_single_threaded_and_create_only():
    path = ROOT / "src" / "company_wiki" / "source_contract" / "announcement_collector.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imports & {
        "asyncio",
        "concurrent",
        "multiprocessing",
        "threading",
        "openai",
        "playwright",
    }
    assert "legacy_writer" not in text
    assert "source_policy" not in text
    assert "os.replace" not in text
    assert "os.link" in text


def test_cli_has_separate_collect_surface_and_canonical_stdout(
    tmp_path, monkeypatch, capsys
):
    module = _collector()
    cli = _cli()
    root = _root(tmp_path)
    monkeypatch.setattr(
        module,
        "download_announcement",
        lambda url, max_bytes: _response(module),
    )
    argv = [
        "--root",
        str(root),
        "--company",
        "中微公司",
        "--entity-id",
        "SSE:688012",
        "--url",
        SOURCE_URL,
        "--title",
        TITLE,
        "--published-date",
        "2026-03-25",
    ]
    assert cli.main(argv) == 0
    first = capsys.readouterr()
    assert first.err == ""
    assert first.out.endswith("\n") and first.out.count("\n") == 1
    assert json.loads(first.out)["manifest"]["source_type"] == "company_announcement"
    assert cli.main(argv) == 0
    second = capsys.readouterr()
    assert second.out == first.out
    assert second.err == ""


def test_cli_rejects_bad_url_without_stdout_or_files(tmp_path, capsys):
    cli = _cli()
    root = _root(tmp_path)
    result = cli.main(
        [
            "--root",
            str(root),
            "--company",
            "中微公司",
            "--entity-id",
            "SSE:688012",
            "--url",
            "https://attacker.example/a.pdf",
            "--title",
            TITLE,
            "--published-date",
            "2026-03-25",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "announcement collection failed" in captured.err
    assert not (root / "companies" / "中微公司" / "raw").exists()


def test_console_script_and_contract_documentation_are_published():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["company-wiki-collect-announcement"] == (
        "company_wiki.source_contract.announcement_cli:main"
    )
    text = (
        ROOT / "docs" / "contracts" / "announcement-collector-v1.md"
    ).read_text(encoding="utf-8")
    for term in (
        "explicit official URL",
        "HTTPS",
        "create-once",
        "SHA-256",
        "company_announcement",
        "source_manifests",
        "source_provenance",
        "single-threaded",
        "StockWiki",
        "no overwrite",
    ):
        assert term in text
