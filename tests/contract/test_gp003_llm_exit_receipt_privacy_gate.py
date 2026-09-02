"""GP-003 RED/acceptance: LLM exit gate — receipt + privacy filters on the
summarize_catalog_with_llm selection (D-2 gap closure).

Review finding D-2: the selection SQL has no receipt/privacy/root filter,
so documents without a prompt-injection review receipt — and documents
from private_user roots — can still be sent to the external LLM.  The
production catalog confirms it: 122 current LLM candidates (all
dayu_portfolio) carry no receipt; only 15 documents in the whole catalog
have one.

Gate semantics (fail closed, consistent with ZR-302 / readiness safety):

  GP3-01  A private_user-root document is NEVER selected — the review
          receipt authorizes absence of injection, not exfiltration of
          private content (even with a valid receipt).
  GP3-02  A public-root document WITHOUT a valid bound receipt is never
          selected (no receipt = not_reviewed).
  GP3-03  A public-root document WITH a valid source-bound receipt IS
          selected.
  GP3-04  A receipt whose source_sha256 does not match the current source
          bytes (tampered/stale) blocks selection.
  GP3-05  private_user + valid receipt is still blocked (privacy gate
          dominates).
"""

from __future__ import annotations

import hashlib
import json
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


def _catalog(tmp_path: Path, *, private_root: bool = False):
    project = tmp_path / "project"
    sources = tmp_path / "sources"
    _seed(sources, "public.txt", "2025年公开公司收入增长20%，产能达到100万台。")
    roots = [
        RootSpec(
            "public_root",
            sources,
            "directory",
            priority=10,
        )
    ]
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
# GP3-01 / GP3-02 / GP3-04 / GP3-05: RED at HEAD (documents are selected
# today regardless of receipt or privacy); GP3-03 pins the allowed case.
# ---------------------------------------------------------------------------


def test_gp3_01_private_user_doc_never_selected(tmp_path) -> None:
    catalog = _catalog(tmp_path, private_root=True)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 0, (
        "a private_user-root document must never reach the LLM exit "
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


def test_gp3_05_private_user_with_valid_receipt_still_blocked(tmp_path) -> None:
    """The privacy gate dominates: a review receipt proves no injection
    but never authorizes sending private_user content to an external LLM.
    The public document in the same catalog stays selectable."""
    catalog = _catalog(tmp_path, private_root=True)
    for document_id in _document_ids(catalog):
        _review(catalog, document_id)
    client = _FakeLLM()
    report = _summarize(catalog, client)
    assert report.completed == 1, (
        "only the public document may be selected "
        f"(completed={report.completed}, prompts={len(client.prompts)})"
    )
    assert len(client.prompts) == 1
    assert "私有研究笔记" not in client.prompts[0], (
        "private_user content must never reach the LLM prompt"
    )
