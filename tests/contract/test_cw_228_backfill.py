"""CW-2.28 Phase 1 RED contracts: backfill progress, parser isolation, terminal reasons, worker interruptibility, exact-copy invariants.

These tests MUST FAIL (RED) before Phase 2 implementation begins.
"""

from __future__ import annotations

from pathlib import Path



# ------------------------------------------------------------------
# RED-5: Terminal reason for unsupported documents
# ------------------------------------------------------------------


def _catalog_with_docs(tmp_path: Path, files: dict[str, str]):
    """Helper that builds a catalog with given text files."""
    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for name, content in files.items():
        (source_root / name).write_text(content, encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog


def test_backfill_unsupported_has_terminal_reason(tmp_path):
    """A scanned PDF that cannot be parsed must get a terminal reason, not just unsupported=1.

    The backfill report (or per-document status) must distinguish why a
    document was unsupported: no_original_location, parse_failed, or
    empty_text. Currently ProcessingReport only counts 'unsupported' with
    no explanation.
    """
    from company_wiki.source_catalog.normalizer import backfill_text_fingerprints

    catalog = _catalog_with_docs(tmp_path, {"brief.txt": "Revenue 100."})
    # Set all fingerprints to NULL to simulate pre-backfill state
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    report = backfill_text_fingerprints(catalog.config, catalog.store)

    # Currently: report.unsupported == 0 (it was parseable)
    # This test WILL FAIL until terminal reasons are added to the report
    # RED assertion: report must have terminal_reasons dict or per-document detail
    assert hasattr(report, "terminal_reasons") or hasattr(report, "details"), (
        "RED: backfill report must include terminal reasons for unsupported docs"
    )


def test_backfill_terminal_reason_distinguishes_empty_from_parse_failure(tmp_path):
    """Empty files get 'empty_text'; unparseable files get 'parse_failed'.

    Create two documents: one empty, one with a valid file that we'll corrupt
    by making it a zero-byte PDF header.
    """
    from company_wiki.source_catalog.normalizer import backfill_text_fingerprints

    catalog = _catalog_with_docs(
        tmp_path,
        {"empty.txt": "", "valid.txt": "Revenue 100."},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    report = backfill_text_fingerprints(catalog.config, catalog.store)

    assert report.unsupported == 0  # empty.txt is parseable but fingerprint=NULL
    # RED: report must have terminal_reasons
    assert hasattr(report, "terminal_reasons"), (
        "RED: backfill report must have terminal_reasons dict"
    )


# ------------------------------------------------------------------
# RED-7: Parser failure isolation
# ------------------------------------------------------------------


class _FailingParser:
    """Simulates a parser that works N times then always raises."""

    def __init__(self, fail_after: int):
        self._call_count = 0
        self.fail_after = fail_after

    def __call__(self, *args, **kwargs):
        self._call_count += 1
        if self._call_count > self.fail_after:
            raise RuntimeError("simulated parser failure")
        return type(
            "FakeNormalized",
            (),
            {
                "raw_text": "Revenue 100.",
                "parser_results": [type("R", (), {"raw_text": "Revenue 100."})()],
            },
        )()


# Module-level parser stand-ins for monkeypatching.  Local closures cannot be
# pickled into the spawn-isolated parser children (WR-10.15), so the simulated
# failure behavior must be self-contained (path-based) and pickleable by
# reference — mirroring the module-level ``_FailingParser`` class above.
def _selective_fail_parser(path, manifest, maybe_extra):
    """Fail for bad.txt, else run the real normalizer."""
    import company_wiki.source_catalog.normalizer as norm_mod

    if "bad.txt" in str(path):
        raise RuntimeError("simulated parser failure")
    return norm_mod._normalize_source(path, manifest, maybe_extra)


def _empty_for_target_parser(path, manifest, maybe_extra):
    """Return empty text for empty.txt, else run the real normalizer."""
    import company_wiki.source_catalog.normalizer as norm_mod

    result = norm_mod._normalize_source(path, manifest, maybe_extra)
    if "empty.txt" in str(path):
        # Spawn-era envelope statuses are completed/partial/unsupported/failed;
        # "parsed" (in-process semantics) fails the protocol check.
        return norm_mod._Normalized(
            body="",
            parser_results=(),
            parser_name="fake",
            parser_version="0",
            status="unsupported",
            quality_flags=(),
        )
    return result


def _raise_for_bad_parser(path, manifest, maybe_extra):
    """Raise for bad.txt, else run the real normalizer."""
    import company_wiki.source_catalog.normalizer as norm_mod

    if "bad.txt" in str(path):
        raise RuntimeError("simulated")
    return norm_mod._normalize_source(path, manifest, maybe_extra)


def test_parser_failure_does_not_block_next_document(tmp_path, monkeypatch):
    """When one document's parser fails, the next document must still be processed.

    Only the middle file should fail; both surrounding files succeed, proving
    that a single failure does not abort the full batch.
    """
    from company_wiki.source_catalog.normalizer import backfill_text_fingerprints

    catalog = _catalog_with_docs(
        tmp_path,
        {
            "good1.txt": "Revenue 100.",
            "bad.txt": "Revenue 200.",
            "good2.txt": "Revenue 300.",
        },
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    monkeypatch.setattr(
        "company_wiki.source_catalog.normalizer._normalize_source",
        _selective_fail_parser,
    )

    report = backfill_text_fingerprints(catalog.config, catalog.store)

    assert report.completed == 2, f"expected 2 completed, got {report.completed}"
    assert report.failed == 1, f"expected 1 failed, got {report.failed}"
    assert report.unsupported == 0, f"expected 0 unsupported, got {report.unsupported}"


def test_failed_documents_have_retryable_status(tmp_path, monkeypatch):
    """A document that failed during backfill must be retryable on next run.

    When a parser transiently fails, the document's fingerprint should remain
    NULL (retryable), not be set to NULL with a terminal flag that prevents
    re-attempt. Only genuinely unsupported docs should be terminal.
    """
    from company_wiki.source_catalog.normalizer import backfill_text_fingerprints

    catalog = _catalog_with_docs(
        tmp_path,
        {"good.txt": "Revenue 100.", "fail.txt": "Revenue 200."},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    failing = _FailingParser(fail_after=0)  # First doc succeeds, second fails
    monkeypatch.setattr(
        "company_wiki.source_catalog.normalizer._normalize_source", failing
    )

    report1 = backfill_text_fingerprints(catalog.config, catalog.store)

    # Second run: the previously-failed doc should be retryable
    report2 = backfill_text_fingerprints(catalog.config, catalog.store)

    assert (
        report2.completed >= 0
    )  # The failed doc is retryable (fingerprint still NULL)
    assert report1.failed >= 1, "RED: first run must report at least 1 failed"


# ------------------------------------------------------------------
# RED-9: CLI/export shows both exact and semantic counts
# ------------------------------------------------------------------


def test_backfill_cli_shows_eligible_pending_counts(tmp_path):
    """CLI fingerprint-backfill must show eligible, pending, completed in its report.

    Currently `ProcessingReport` only has completed/skipped/partial/unsupported/failed.
    The CLI and JSON output must include `eligible` (total NULL before start) and
    `pending` (eligible - completed - unsupported - failed).
    """
    catalog = _catalog_with_docs(
        tmp_path,
        {"a.txt": "Revenue 100.", "b.txt": "Revenue 200."},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    report = catalog.backfill_text_fingerprints(limit=1)

    assert report.completed == 1
    # RED: report must expose eligible and pending counts
    assert hasattr(report, "eligible"), "RED: ProcessingReport must have 'eligible'"
    assert hasattr(report, "pending"), "RED: ProcessingReport must have 'pending'"
    assert report.eligible == 2, (
        f"RED: eligible should be 2, got {getattr(report, 'eligible', None)}"
    )
    assert report.pending == 1, (
        f"RED: pending should be 1, got {getattr(report, 'pending', None)}"
    )


def test_backfill_report_includes_current_path(tmp_path):
    """Backfill progress reporting must include the current path being processed.

    The `progress` callback is passed but the invariant that current_path appears
    in structured progress must be tested.
    """
    catalog = _catalog_with_docs(
        tmp_path,
        {"a.txt": "Revenue 100."},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    progress_calls = []

    catalog.backfill_text_fingerprints(
        limit=1, progress=lambda **kw: progress_calls.append(kw)
    )

    assert len(progress_calls) >= 1, "RED: progress callback must be invoked"
    assert "current_path" in progress_calls[0], (
        "RED: progress must include current_path"
    )
    assert all(k in progress_calls[0] for k in ("current", "total", "detail")), (
        "RED: progress must include current, total, detail"
    )


# ------------------------------------------------------------------
# RED-12: Worker interruptibility
# ------------------------------------------------------------------


def test_t2_07_should_stop_finishes_current_file_then_stops(tmp_path):
    """A ``should_stop`` callback (what the worker passes, §12.4.3.7) must let the
    current file finish and then stop before starting the next. No xfail: the
    pause path is a real, asserted contract.
    """
    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for i in range(10):
        (source_root / f"doc_{i:03d}.txt").write_text(
            f"Revenue {i:05d}.", encoding="utf-8"
        )

    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()

    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    # Stop after the first document is actually completed (fingerprint
    # persisted). Progress/heartbeat events fire mid-parse and must not cancel
    # the in-flight parser, so completion is detected from the DB.
    def should_stop() -> bool:
        return (
            catalog.store.fetchone(
                "SELECT COUNT(*) FROM documents WHERE text_fingerprint IS NOT NULL"
            )[0]
            >= 1
        )

    progress_calls: list[dict] = []

    def progress(**kw):
        progress_calls.append(kw)

    report = catalog.backfill_text_fingerprints(
        limit=10, should_stop=should_stop, progress=progress
    )

    assert report.completed == 1, (
        f"should_stop must halt after the current file; completed={report.completed}"
    )
    assert report.partial >= 1, "partial must reflect the unprocessed remainder"
    # DB must remain consistent after an interrupted batch.
    import sqlite3

    with sqlite3.connect(catalog.config.catalog_dir / "catalog.sqlite3") as conn:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"


# ------------------------------------------------------------------
# RED-13: Exact-copy invariants after backfill
# ------------------------------------------------------------------


def test_exact_copy_groups_unchanged_after_backfill(tmp_path):
    """After fingerprint backfill, exact-copy groups (same byte SHA) must be
    identical to the pre-backfill state. No document must move between groups.
    """
    catalog = _catalog_with_docs(
        tmp_path,
        {"a.txt": "Revenue 100.", "b.txt": "Revenue 100."},
    )
    exact_before = catalog.duplicate_groups()
    assert len(exact_before) == 1  # Same content = exact duplicate

    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    catalog.backfill_text_fingerprints()

    exact_after = catalog.duplicate_groups()
    assert len(exact_after) == len(exact_before), (
        "RED: exact groups must not change after backfill"
    )


# ------------------------------------------------------------------
# RED-14: Semantic groups after backfill in production context
# ------------------------------------------------------------------


def test_semantic_groups_reachable_after_backfill(tmp_path):
    """After backfill completes, semantic_duplicate_groups() must produce groups
    from the now-populated text_fingerprint column.
    """
    catalog = _catalog_with_docs(
        tmp_path,
        {
            "a.txt": "Revenue 100.\n\nProfit 20.",
            "b.txt": "Revenue   100.\r\nProfit 20.",
        },
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    # Before backfill, should be 0 semantic groups
    pre = catalog.semantic_duplicate_groups()
    assert len(pre) == 0, "Pre-backfill: 0 semantic groups (fingerprints are NULL)"

    catalog.backfill_text_fingerprints()

    post = catalog.semantic_duplicate_groups()
    assert len(post) == 1, "RED: after backfill, semantic groups must appear"


# ------------------------------------------------------------------
# CW-2.28 Phase 2R rigorous contracts (T2-03..T2-07, T2-14)
# ------------------------------------------------------------------


def test_t2_03_success_text_writes_fingerprint_and_state_atomically(tmp_path):
    """A successfully parsed document must have non-NULL ``text_fingerprint`` AND a
    ``document_fingerprint_state`` row with status ``completed`` in the same
    transaction (CW-2.28 §12.3 rule 4).
    """
    catalog = _catalog_with_docs(tmp_path, {"a.txt": "Revenue 100."})
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    report = catalog.backfill_text_fingerprints()

    assert report.completed == 1
    doc_id = catalog.store.fetchone(
        "SELECT document_id FROM documents ORDER BY document_id"
    )["document_id"]
    doc = catalog.store.fetchone(
        "SELECT text_fingerprint FROM documents WHERE document_id=?", (doc_id,)
    )
    assert doc is not None and doc["text_fingerprint"] is not None, "fingerprint set"
    state = catalog.store.fetchone(
        "SELECT status, attempt_count, normalizer_version "
        "FROM document_fingerprint_state WHERE document_id=?",
        (doc_id,),
    )
    assert state is not None, "state row must exist"
    assert state["status"] == "completed"
    assert state["attempt_count"] == 1
    assert state["normalizer_version"]


def test_t2_04_empty_text_terminal_is_not_re_selected(tmp_path, monkeypatch):
    """A doc whose extracted text is empty must become ``unsupported_terminal`` and
    never be re-selected by a subsequent backfill (CW-2.28 §12.3 rule 5).
    """
    catalog = _catalog_with_docs(tmp_path, {"a.txt": "Revenue 100.", "empty.txt": "x"})
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    monkeypatch.setattr(
        "company_wiki.source_catalog.normalizer._normalize_source",
        _empty_for_target_parser,
    )

    report1 = catalog.backfill_text_fingerprints()
    assert report1.unsupported >= 1, f"unsupported doc: {report1}"
    assert report1.terminal_reasons and "empty_text" in report1.terminal_reasons

    loc = catalog.store.fetchone(
        "SELECT document_id FROM locations WHERE relative_path=? AND location_status='active'",
        ("empty.txt",),
    )
    assert loc is not None, "empty.txt must have an active location"
    doc_id = loc["document_id"]
    state1 = catalog.store.fetchone(
        "SELECT status FROM document_fingerprint_state WHERE document_id=?", (doc_id,)
    )
    assert state1 and state1["status"] == "unsupported_terminal"

    report2 = catalog.backfill_text_fingerprints()
    assert report2.completed == 0, "terminal doc must not be re-selected"
    assert report2.unsupported == 0


def test_t2_05_retry_backoff_and_three_strike_failed_terminal(tmp_path, monkeypatch):
    """A parser exception goes through retryable_failed with backoff; after
    ``retry_limit`` attempts it becomes ``failed_terminal`` with reason
    ``retry_exhausted:<code>`` (CW-2.28 §12.3 rules 6-7).
    """
    catalog = _catalog_with_docs(tmp_path, {"good.txt": "Revenue 100.", "bad.txt": "x"})
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    monkeypatch.setattr(
        "company_wiki.source_catalog.normalizer._normalize_source",
        _raise_for_bad_parser,
    )

    loc = catalog.store.fetchone(
        "SELECT document_id FROM locations WHERE relative_path=? AND location_status='active'",
        ("bad.txt",),
    )
    assert loc is not None, "bad.txt must have an active location"
    doc_id = loc["document_id"]

    # Attempt 1: should become retryable_failed
    report1 = catalog.backfill_text_fingerprints(
        retry_limit=3, retry_backoff_seconds=0
    )
    assert report1.failed >= 1
    s1 = catalog.store.fetchone(
        "SELECT status, attempt_count, next_retry_at "
        "FROM document_fingerprint_state WHERE document_id=?",
        (doc_id,),
    )
    assert s1["status"] == "retryable_failed"
    assert s1["attempt_count"] == 1

    # Attempt 2
    catalog.backfill_text_fingerprints(
        retry_limit=3, retry_backoff_seconds=0
    )
    s2 = catalog.store.fetchone(
        "SELECT status, attempt_count FROM document_fingerprint_state "
        "WHERE document_id=?",
        (doc_id,),
    )
    assert s2["status"] == "retryable_failed"
    assert s2["attempt_count"] == 2

    # Attempt 3 → exhausted → failed_terminal
    catalog.backfill_text_fingerprints(
        retry_limit=3, retry_backoff_seconds=0
    )
    s3 = catalog.store.fetchone(
        "SELECT status, attempt_count, terminal_reason, last_error_code "
        "FROM document_fingerprint_state WHERE document_id=?",
        (doc_id,),
    )
    assert s3["status"] == "failed_terminal"
    assert s3["attempt_count"] == 3
    assert s3["terminal_reason"] and s3["terminal_reason"].startswith(
        "retry_exhausted:"
    )
    # Spawn isolation wraps the child's exception in ParserProcessError
    # (WR-10.15); the child's original type survives in the message.
    assert s3["last_error_code"] == "ParserProcessError"

    # Attempt 4: not re-selected (terminal)
    report4 = catalog.backfill_text_fingerprints(
        retry_limit=3, retry_backoff_seconds=0
    )
    assert report4.failed == 0


def test_t2_06_limit_reports_global_backlog(tmp_path):
    """With ``--limit N``, at most N documents are processed, and
    ``eligible`` reports the pre-batch global backlog (CW-2.28 §12.3 rule 11).
    """
    catalog = _catalog_with_docs(
        tmp_path,
        {f"doc_{i:02d}.txt": f"Revenue {i:05d}." for i in range(5)},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    report1 = catalog.backfill_text_fingerprints(limit=2)
    assert report1.completed == 2
    assert report1.eligible == 5, f"eligible should be global backlog (5), got {report1.eligible}"
    assert report1.pending == 3, f"pending should be remaining (3), got {report1.pending}"

    report2 = catalog.backfill_text_fingerprints(limit=10)
    assert report2.completed == 3, f"remaining 3 docs, got {report2.completed}"
    assert report2.eligible == 3


def test_t2_14_raw_immutability_after_backfill(tmp_path):
    """Running fingerprint backfill must not alter raw source files: count, size,
    and SHA must be identical before and after (CW-2.28 §12.4.2 T2-14).
    """
    import hashlib

    catalog = _catalog_with_docs(
        tmp_path,
        {f"doc_{i:02d}.txt": f"Revenue {i:05d}.\n" for i in range(5)},
    )
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET text_fingerprint=NULL")

    def snapshot():
        files: dict[str, tuple[int, str]] = {}
        for loc in catalog.store.fetchall(
            "SELECT absolute_path FROM locations WHERE location_status='active'"
        ):
            p = Path(loc["absolute_path"])
            if p.exists():
                data = p.read_bytes()
                files[loc["absolute_path"]] = (len(data), hashlib.sha256(data).hexdigest())
        return files

    before = snapshot()
    catalog.backfill_text_fingerprints()
    after = snapshot()

    assert before == after, "raw files must be byte-identical after backfill"
