"""GP-003 acceptance: LLM selection requires source-bound review receipts.

All configured roots may feed the LLM regardless of historical privacy labels.
The receipt must still bind to the current source SHA-256 before text leaves.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.prompt_injection import (
    record_prompt_injection_review,
)

# ---------------------------------------------------------------------------
# fixture: two directory roots (one private_user), one document each
# ---------------------------------------------------------------------------


def _seed(root_dir: Path, name: str, body: str) -> None:
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / name).write_text(body, encoding="utf-8")


def _catalog(
    tmp_path: Path, *, private_root: bool = False, public_root: bool = True
):
    project = tmp_path / "project"
    sources = tmp_path / "sources"
    _seed(sources, "public.txt", "2025年公开公司收入增长20%，产能达到100万台。")
    roots = (
        [RootSpec("public_root", sources, "directory", priority=10)]
        if public_root else []
    )
    if private_root:
        private = tmp_path / "private"
        _seed(private, "private.txt", "用户私有研究笔记：某公司尚未公开的产能计划。")
        roots.append(
            RootSpec(
                "private_root",
                private,
                "directory",
                priority=20,
                privacy_class="private_user",
            )
        )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=tuple(roots),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog


class _Response:
    def __init__(self, content: str):
        self.content = content
        self.success = True
        self.error = ""
        self.model = "MiniMax-M3"
        self.usage = {"total_tokens": 321}


class _FakeLLM:
    provider = "minimax"
    model = "MiniMax-M3"

    def __init__(self):
        self.prompts: list[str] = []

    def generate(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        return _Response(
            json.dumps(
                {
                    "overview": "经营进展。",
                    "key_facts": ["收入增长"],
                    "topics": ["收入"],
                    "limitations": [],
                },
                ensure_ascii=False,
            )
        )


def _document_ids(catalog) -> list[str]:
    return [
        str(row["document_id"])
        for row in catalog.store.fetchall(
            "SELECT document_id FROM documents ORDER BY document_id"
        )
    ]


def _source_sha256(catalog, document_id: str) -> str:
    row = catalog.store.fetchone(
        "SELECT s.content_sha256 FROM documents d JOIN sources s "
        "ON s.source_id = d.primary_source_id WHERE d.document_id=?",
        (document_id,),
    )
    assert row is not None
    return str(row["content_sha256"])


def _review(catalog, document_id: str, *, source_sha256: str | None = None) -> None:
    """Write a prompt-injection review receipt bound to the document's
    current source bytes (the same shape ZR-302 review flows produce)."""
    binding = _source_sha256(catalog, document_id) if source_sha256 is None else source_sha256
    with catalog.store.transaction() as connection:
        record_prompt_injection_review(
            connection,
            document_id,
            status="not_detected",
            reviewer="gp003-test",
            evidence_sha256=hashlib.sha256(binding.encode()).hexdigest(),
            evidence_payload=binding,
            now="2026-09-02T12:00:00Z",
            source_sha256=binding,
            policy_hash="c" * 64,
        )


def _summarize(catalog, client: _FakeLLM):
    return catalog.summarize_with_llm(
        limit=10,
        llm_client_factory=lambda: client,
        max_input_chars=120000,
        max_output_tokens=1200,
    )


# ---------------------------------------------------------------------------
# Historical root labels do not bypass the review and SHA checks.
# ---------------------------------------------------------------------------


def test_gp3_01_configured_roots_without_receipts_not_selected(tmp_path) -> None:
    catalog = _catalog(tmp_path, private_root=True)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0, (
        "documents without source-bound review receipts must not reach the LLM "
        f"(completed={report.completed}, prompts={len(client.prompts)})"
    )
    assert client.prompts == []


def test_gp3_02_public_doc_without_receipt_not_selected(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0, (
        "a public document WITHOUT a review receipt must not be sent to "
        f"the LLM (completed={report.completed})"
    )
    assert client.prompts == []


def test_gp3_03_public_doc_with_bound_receipt_is_selected(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    for document_id in _document_ids(catalog):
        _review(catalog, document_id)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 1, (
        f"reviewed public document must be selectable (completed={report.completed})"
    )
    assert len(client.prompts) == 1


def test_gp3_04_receipt_source_mismatch_blocks(tmp_path) -> None:
    """A receipt bound to different source bytes (stale/tampered) must
    fail closed — the gate checks the byte binding, not just presence."""
    catalog = _catalog(tmp_path)
    for document_id in _document_ids(catalog):
        _review(catalog, document_id, source_sha256="f" * 64)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0, (
        "a source-mismatched receipt must block selection "
        f"(completed={report.completed})"
    )
    assert client.prompts == []


def test_gp3_05_all_configured_roots_with_bound_receipts_are_selected(tmp_path) -> None:
    """A historical private_user label does not veto reviewed content."""
    catalog = _catalog(tmp_path, private_root=True)
    for document_id in _document_ids(catalog):
        _review(catalog, document_id)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 2, (
        "both reviewed configured-root documents must be selectable "
        f"(completed={report.completed}, prompts={len(client.prompts)})"
    )
    assert len(client.prompts) == 2
    assert any("私有研究笔记" in prompt for prompt in client.prompts)


def test_gp3_06_private_labeled_root_alone_with_bound_receipt_is_selected(
    tmp_path,
) -> None:
    catalog = _catalog(tmp_path, private_root=True, public_root=False)
    for document_id in _document_ids(catalog):
        _review(catalog, document_id)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 1
    assert len(client.prompts) == 1
    assert "私有研究笔记" in client.prompts[0]


def test_gp3_07_changed_normalized_bytes_never_leave_for_llm(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    document_id = _document_ids(catalog)[0]
    _review(catalog, document_id)
    artifact = catalog.store.fetchone(
        "SELECT path FROM artifacts WHERE document_id=? AND artifact_role='normalized'",
        (document_id,),
    )
    assert artifact is not None
    Path(artifact["path"]).write_text("未审查的替换内容", encoding="utf-8")

    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0
    assert report.failed == 1
    assert client.prompts == []
    assert "normalized" in str(report.error).lower()


def test_gp3_08_old_root_location_does_not_hide_current_copy(tmp_path) -> None:
    catalog = _catalog(tmp_path, private_root=True)
    current = catalog.store.fetchone(
        "SELECT * FROM locations WHERE root_id='public_root'"
    )
    assert current is not None
    _review(catalog, str(current["document_id"]))
    old_copy = tmp_path / "private" / "old-copy.txt"
    old_copy.write_bytes(Path(current["absolute_path"]).read_bytes())
    location = dict(current)
    location["location_id"] = str(location["location_id"]) + ":old-copy"
    location["root_id"] = "private_root"
    location["relative_path"] = "old-copy.txt"
    location["absolute_path"] = str(old_copy)
    with catalog.store.transaction() as connection:
        connection.execute(
            f"INSERT INTO locations ({','.join(location)}) "
            f"VALUES ({','.join('?' for _ in location)})",
            tuple(location.values()),
        )
    catalog.config = replace(
        catalog.config, roots=(catalog.config.roots[0],)
    )

    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 1
    assert len(client.prompts) == 1
    assert "公开公司" in client.prompts[0]


def test_gp3_09_normalized_lineage_mismatch_never_leaves_for_llm(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    document_id = _document_ids(catalog)[0]
    _review(catalog, document_id)
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE artifacts SET source_sha256=? WHERE document_id=? "
            "AND artifact_role='normalized'",
            ("f" * 64, document_id),
        )

    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0
    assert report.failed == 1
    assert client.prompts == []
    assert "normalized" in str(report.error).lower()


def _add_legacy_normalized(catalog, document_id: str, *, path: Path | None = None) -> Path:
    modern = catalog.store.fetchone(
        "SELECT path FROM artifacts WHERE document_id=? "
        "AND artifact_role='normalized' AND generator_name='source_catalog_normalizer'",
        (document_id,),
    )
    assert modern is not None
    modern_path = Path(modern["path"])
    with catalog.store.transaction() as connection:
        connection.execute(
            """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,
                content_sha256,byte_size,mime_type,generator_name,generator_version,
                status,error,metadata_json,created_at,schema_version,source_sha256)
                SELECT artifact_id || ':legacy',document_id,source_id,artifact_role,?,
                content_sha256,byte_size,mime_type,'plain_text',generator_version,
                status,error,'{}','2099-01-01T00:00:00Z',NULL,NULL
                FROM artifacts WHERE document_id=? AND artifact_role='normalized'
                AND generator_name='source_catalog_normalizer'""",
            (str(path or modern_path), document_id),
        )
    return modern_path


def test_gp3_10_two_normalized_artifacts_send_one_llm_request(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    document_id = _document_ids(catalog)[0]
    _review(catalog, document_id)
    _add_legacy_normalized(catalog, document_id)

    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 1
    assert len(client.prompts) == 1
    assert catalog.store.fetchone(
        "SELECT COUNT(*) AS n FROM artifacts WHERE document_id=? "
        "AND artifact_role='summary'",
        (document_id,),
    )["n"] == 1


def test_gp3_11_bad_modern_artifact_does_not_send_legacy_copy(tmp_path) -> None:
    catalog = _catalog(tmp_path)
    document_id = _document_ids(catalog)[0]
    _review(catalog, document_id)
    modern = catalog.store.fetchone(
        "SELECT path FROM artifacts WHERE document_id=? "
        "AND artifact_role='normalized' AND generator_name='source_catalog_normalizer'",
        (document_id,),
    )
    assert modern is not None
    modern_path = Path(modern["path"])
    legacy_path = tmp_path / "legacy-normalized.md"
    legacy_path.write_bytes(modern_path.read_bytes())
    _add_legacy_normalized(catalog, document_id, path=legacy_path)
    modern_path.write_bytes(modern_path.read_bytes() + b"\nTampered modern bytes.\n")

    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0
    assert report.failed == 1
    assert client.prompts == []
    assert "normalized" in str(report.error).lower()
