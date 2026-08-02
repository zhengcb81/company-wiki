"""WR-10.13 parser-process liveness and bounded-failure contracts."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from company_wiki.source_catalog.normalizer import (
    NormalizationCancelledError,
    NormalizationTimeoutError,
    ParserProcessError,
    ParserResultProtocolError,
    ParserResultTooLargeError,
    _Normalized,
    _normalized_from_payload,
    _normalized_to_payload,
    _parser_result,
    _run_parser_isolated,
)
from company_wiki.source_contract import SourceManifest, SourceType


PROJECT = Path(__file__).resolve().parents[2]


def _normalized(manifest: SourceManifest, body: str = "parsed text") -> _Normalized:
    return _Normalized(
        body=body,
        parser_results=(
            _parser_result(
                source_id=manifest.source_id,
                raw_text=body,
                parser_name="liveness_fixture",
                parser_version="1.0.0",
                paragraph_index=0,
            ),
        ),
        parser_name="liveness_fixture",
        parser_version="1.0.0",
        status="completed",
        quality_flags=(),
    )


def _fast_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, docling_path
    return _normalized(manifest)


def _slow_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, docling_path
    time.sleep(0.35)
    return _normalized(manifest)


def _hung_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, manifest, docling_path
    while True:
        time.sleep(1)


def _parser_with_descendant(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del manifest, docling_path
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    descendant = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    path.with_suffix(path.suffix + ".descendant.pid").write_text(
        str(descendant.pid), encoding="ascii"
    )
    while True:
        time.sleep(1)


def _raising_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, manifest, docling_path
    raise ValueError("fixture parser failed")


def _oversized_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, docling_path
    return _normalized(manifest, "x" * 16_384)


def _invalid_parser(path: Path, manifest: SourceManifest, docling_path: Path | None):
    del path, manifest, docling_path
    return {"not": "a normalized parser result"}


def _manifest(path: Path) -> SourceManifest:
    return SourceManifest.from_file(
        root=path.parent,
        file_path=path,
        entity_ids=("entity:test",),
        source_type=SourceType.OTHER,
        published_date=None,
        retrieved_at="2026-08-01T00:00:00Z",
        collector_name="parser-liveness-test",
        collector_version="1.0.0",
        mime_type="text/plain",
    )


def _run(
    path: Path,
    *,
    parser=_fast_parser,
    timeout_seconds: float = 5.0,
    heartbeat_interval_seconds: float = 0.05,
    result_max_bytes: int = 1_000_000,
    progress=None,
    should_stop=None,
) -> _Normalized:
    return _run_parser_isolated(
        path,
        _manifest(path),
        None,
        parser=parser,
        timeout_seconds=timeout_seconds,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        result_max_bytes=result_max_bytes,
        temp_dir=path.parent,
        progress=progress,
        should_stop=should_stop,
    )


def test_fast_parser_returns_validated_result_without_temp_leak(tmp_path):
    source = tmp_path / "fast.txt"
    source.write_text("source", encoding="utf-8")

    result = _run(source)

    assert result.status == "completed"
    assert result.body == "parsed text"
    assert result.parser_results[0].source_id == _manifest(source).source_id
    assert not list(tmp_path.glob(".parser-result-*.json"))


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("body", None),
        ("parser_name", None),
        ("quality_flags", "not-an-array"),
        ("error", 123),
    ),
)
def test_parser_payload_rejects_values_that_need_type_coercion(
    tmp_path, field, invalid_value
):
    source = tmp_path / "strict-payload.txt"
    source.write_text("source", encoding="utf-8")
    manifest = _manifest(source)
    payload = _normalized_to_payload(
        _normalized(manifest), expected_source_id=manifest.source_id
    )
    payload[field] = invalid_value

    with pytest.raises(ParserResultProtocolError):
        _normalized_from_payload(payload, expected_source_id=manifest.source_id)


def test_slow_parser_keeps_parent_progress_live(tmp_path):
    source = tmp_path / "slow.txt"
    source.write_text("source", encoding="utf-8")
    heartbeats: list[dict[str, object]] = []

    result = _run(source, parser=_slow_parser, progress=heartbeats.append)

    assert result.status == "completed"
    assert len(heartbeats) >= 3
    assert all(item["detail"] == "parser_alive" for item in heartbeats)
    assert len({item["parser_pid"] for item in heartbeats}) == 1
    assert heartbeats[-1]["parser_elapsed_seconds"] >= 0.25


def test_hung_parser_times_out_and_is_reaped(tmp_path):
    source = tmp_path / "hung.txt"
    source.write_text("source", encoding="utf-8")
    heartbeats: list[dict[str, object]] = []

    with pytest.raises(NormalizationTimeoutError):
        _run(
            source,
            parser=_hung_parser,
            timeout_seconds=0.25,
            progress=heartbeats.append,
        )

    parser_pid = int(heartbeats[-1]["parser_pid"])
    assert all(child.pid != parser_pid for child in multiprocessing.active_children())
    assert not list(tmp_path.glob(".parser-result-*.json"))


def _kill_pid_tree_for_test(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
        return
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass


def test_hung_parser_timeout_reaps_its_descendants(tmp_path):
    source = tmp_path / "hung-tree.txt"
    source.write_text("source", encoding="utf-8")
    descendant_pid_file = source.with_suffix(source.suffix + ".descendant.pid")
    descendant_pid = None

    try:
        with pytest.raises(NormalizationTimeoutError):
            _run(
                source,
                parser=_parser_with_descendant,
                timeout_seconds=5,
            )
        descendant_pid = int(descendant_pid_file.read_text(encoding="ascii"))
        deadline = time.monotonic() + 5
        while _pid_is_active(descendant_pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not _pid_is_active(descendant_pid)
    finally:
        if descendant_pid is not None and _pid_is_active(descendant_pid):
            _kill_pid_tree_for_test(descendant_pid)


def test_stop_cancels_parser_and_reaps_it(tmp_path):
    source = tmp_path / "cancel.txt"
    source.write_text("source", encoding="utf-8")
    heartbeats: list[dict[str, object]] = []

    with pytest.raises(NormalizationCancelledError):
        _run(
            source,
            parser=_hung_parser,
            timeout_seconds=2,
            progress=heartbeats.append,
            should_stop=lambda: len(heartbeats) >= 2,
        )

    parser_pid = int(heartbeats[-1]["parser_pid"])
    assert all(child.pid != parser_pid for child in multiprocessing.active_children())


def test_parser_exception_is_source_traceable(tmp_path):
    source = tmp_path / "raising.txt"
    source.write_text("source", encoding="utf-8")

    with pytest.raises(ParserProcessError, match="ValueError: fixture parser failed"):
        _run(source, parser=_raising_parser)


def test_oversized_parser_result_is_rejected(tmp_path):
    source = tmp_path / "large.txt"
    source.write_text("source", encoding="utf-8")

    with pytest.raises(ParserResultTooLargeError):
        _run(source, parser=_oversized_parser, result_max_bytes=512)


def test_invalid_parser_result_is_rejected(tmp_path):
    source = tmp_path / "invalid.txt"
    source.write_text("source", encoding="utf-8")

    with pytest.raises(ParserProcessError, match="ParserResultProtocolError"):
        _run(source, parser=_invalid_parser)


def test_spawn_parser_supports_non_ascii_paths(tmp_path):
    source = tmp_path / "公司资料.txt"
    source.write_text("source", encoding="utf-8")

    result = _run(source)

    assert result.body == "parsed text"


def _catalog_with_sources(tmp_path: Path, *names: str):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    sources = tmp_path / "sources"
    sources.mkdir()
    for name in names:
        (sources / name).write_text(f"content for {name}", encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("sources", sources, "directory"),),
        )
    )
    catalog.scan()
    return catalog


def test_normalize_timeout_retries_once_then_becomes_terminal(tmp_path, monkeypatch):
    import company_wiki.source_catalog.normalizer as normalizer
    from company_wiki.source_catalog.store import read_pipeline_status

    catalog = _catalog_with_sources(tmp_path, "timeout.txt", "healthy.txt")
    attempts = 0

    def fake_isolated(path, manifest, docling_path, **kwargs):
        nonlocal attempts
        del kwargs
        if path.name == "timeout.txt":
            attempts += 1
            raise NormalizationTimeoutError("fixture timeout")
        return normalizer._normalize_source(path, manifest, docling_path)

    monkeypatch.setattr(normalizer, "_run_parser_isolated", fake_isolated)

    first = catalog.normalize(limit=2, retry_limit=2, retry_backoff_seconds=0)
    first_status = read_pipeline_status(catalog.config.database_path)["markdown"]
    second = catalog.normalize(limit=2, retry_limit=2, retry_backoff_seconds=0)
    second_status = read_pipeline_status(catalog.config.database_path)["markdown"]
    third = catalog.normalize(limit=2, retry_limit=2, retry_backoff_seconds=0)

    assert (first.completed, first.failed) == (1, 1)
    assert first_status["retryable_failed"] == 1
    assert first_status["terminal_failed"] == 0
    assert first_status["pending"] == 1
    assert (second.completed, second.failed) == (0, 1)
    assert second_status["retryable_failed"] == 0
    assert second_status["terminal_failed"] == 1
    assert second_status["pending"] == 0
    assert (third.completed, third.failed) == (0, 0)
    assert attempts == 2


def test_normalize_stop_does_not_write_failure_or_consume_retry(tmp_path, monkeypatch):
    import company_wiki.source_catalog.normalizer as normalizer
    from company_wiki.source_catalog.store import read_pipeline_status

    catalog = _catalog_with_sources(tmp_path, "cancel.txt")

    def fake_isolated(path, manifest, docling_path, **kwargs):
        del path, manifest, docling_path, kwargs
        raise NormalizationCancelledError("fixture stop")

    monkeypatch.setattr(normalizer, "_run_parser_isolated", fake_isolated)

    report = catalog.normalize(limit=1)
    markdown = read_pipeline_status(catalog.config.database_path)["markdown"]

    assert (report.partial, report.failed) == (1, 0)
    assert markdown["pending"] == 1
    assert markdown["failed"] == 0
    assert markdown["retryable_failed"] == 0
    assert markdown["terminal_failed"] == 0


def test_fingerprint_timeout_uses_existing_retry_state_machine(tmp_path, monkeypatch):
    import company_wiki.source_catalog.normalizer as normalizer

    catalog = _catalog_with_sources(tmp_path, "fingerprint-timeout.txt")
    attempts = 0

    def fake_isolated(path, manifest, docling_path, **kwargs):
        nonlocal attempts
        del path, manifest, docling_path, kwargs
        attempts += 1
        raise NormalizationTimeoutError("fixture fingerprint timeout")

    monkeypatch.setattr(normalizer, "_run_parser_isolated", fake_isolated)

    first = catalog.backfill_text_fingerprints(
        limit=1,
        retry_limit=2,
        retry_backoff_seconds=0,
    )
    first_state = catalog.store.fetchone(
        "SELECT status,attempt_count,last_error_code FROM document_fingerprint_state"
    )
    second = catalog.backfill_text_fingerprints(
        limit=1,
        retry_limit=2,
        retry_backoff_seconds=0,
    )
    second_state = catalog.store.fetchone(
        "SELECT status,attempt_count,terminal_reason FROM document_fingerprint_state"
    )
    third = catalog.backfill_text_fingerprints(
        limit=1,
        retry_limit=2,
        retry_backoff_seconds=0,
    )

    assert first.failed == 1
    assert dict(first_state) == {
        "status": "retryable_failed",
        "attempt_count": 1,
        "last_error_code": "document_parse_timeout",
    }
    assert second.failed == 1
    assert dict(second_state) == {
        "status": "failed_terminal",
        "attempt_count": 2,
        "terminal_reason": "retry_exhausted:document_parse_timeout",
    }
    assert third.failed == 0
    assert attempts == 2


def test_corrupt_xls_is_terminal_unsupported_instead_of_retryable(tmp_path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.store import read_pipeline_status

    project = tmp_path / "project"
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "corrupt.xls").write_bytes(b"not an xls workbook")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("sources", sources, "directory"),),
        )
    )
    catalog.scan()

    first = catalog.normalize(limit=1, retry_limit=3, retry_backoff_seconds=0)
    second = catalog.normalize(limit=1, retry_limit=3, retry_backoff_seconds=0)
    markdown = read_pipeline_status(catalog.config.database_path)["markdown"]

    assert (first.unsupported, first.failed) == (1, 0)
    assert (second.unsupported, second.failed) == (0, 0)
    assert markdown["unsupported"] == 1
    assert markdown["failed"] == 0
    assert markdown["retryable_failed"] == 0
    assert markdown["terminal_failed"] == 0

    fingerprint = catalog.backfill_text_fingerprints(
        limit=1, retry_limit=3, retry_backoff_seconds=0
    )
    fingerprint_again = catalog.backfill_text_fingerprints(
        limit=1, retry_limit=3, retry_backoff_seconds=0
    )
    fingerprint_state = catalog.store.fetchone(
        "SELECT status,attempt_count,terminal_reason,last_error_code "
        "FROM document_fingerprint_state"
    )
    assert (fingerprint.unsupported, fingerprint.failed) == (1, 0)
    assert (fingerprint_again.unsupported, fingerprint_again.failed) == (0, 0)
    assert dict(fingerprint_state) == {
        "status": "unsupported_terminal",
        "attempt_count": 1,
        "terminal_reason": "unsupported_document",
        "last_error_code": "unsupported_document",
    }


def _pid_is_active(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == 259
    finally:
        kernel32.CloseHandle(handle)


def test_parser_tree_exits_when_its_parent_crashes(tmp_path):
    source = tmp_path / "parent-crash.txt"
    source.write_text("source", encoding="utf-8")
    pid_file = tmp_path / "parser.pid"
    descendant_pid_file = source.with_suffix(source.suffix + ".descendant.pid")
    code = """
import os
from pathlib import Path
from test_source_catalog_parser_liveness import _manifest, _parser_with_descendant
from company_wiki.source_catalog.normalizer import _run_parser_isolated

source = Path(os.environ['PARSER_SOURCE'])
pid_file = Path(os.environ['PARSER_PID_FILE'])
descendant_pid_file = Path(os.environ['DESCENDANT_PID_FILE'])

def crash_parent(details):
    if not descendant_pid_file.is_file():
        return
    pid_file.write_text(str(details['parser_pid']), encoding='ascii')
    os._exit(71)

_run_parser_isolated(
    source,
    _manifest(source),
    None,
    parser=_parser_with_descendant,
    timeout_seconds=60,
    heartbeat_interval_seconds=0.05,
    result_max_bytes=1_000_000,
    temp_dir=source.parent,
    progress=crash_parent,
)
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT / "tests" / "contract"), str(PROJECT / "src"), env.get("PYTHONPATH", "")]
    )
    env["PARSER_SOURCE"] = str(source)
    env["PARSER_PID_FILE"] = str(pid_file)
    env["DESCENDANT_PID_FILE"] = str(descendant_pid_file)

    parser_pid = descendant_pid = None
    try:
        parent = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        assert parent.returncode == 71, (parent.stdout, parent.stderr)
        parser_pid = int(pid_file.read_text(encoding="ascii"))
        descendant_pid = int(descendant_pid_file.read_text(encoding="ascii"))
        deadline = time.monotonic() + 10
        while (
            _pid_is_active(parser_pid) or _pid_is_active(descendant_pid)
        ) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not _pid_is_active(parser_pid)
        assert not _pid_is_active(descendant_pid)
        assert not list(tmp_path.glob(".parser-result-*.json"))
    finally:
        for pid in (parser_pid, descendant_pid):
            if pid is not None and _pid_is_active(pid):
                _kill_pid_tree_for_test(pid)


# --- WR-10.13 controlled slow canary (shortened clock) ---
# Contract-equivalent of the production >900s slow document: a parser that
# runs for a duration that would have exceeded the OLD 900s watchdog. Under
# the new isolation model the document timeout is the parser timeout, so a
# slow-but-under-timeout document must complete with continuous heartbeats
# (no supervisor kill), and an over-timeout document must become terminal
# instead of looping. Clock is shortened (60s timeout / 45s slow work) so no
# real 900s sleep is needed.


def _canary_slow_parser(
    path: Path, manifest: SourceManifest, docling_path: Path | None
) -> _Normalized:
    del path, docling_path
    time.sleep(45)
    return _normalized(manifest)


def test_slow_canary_document_under_parser_timeout_completes_with_heartbeats(
    tmp_path: Path,
):
    # >900s-equivalent slow document, shortened clock: 45s slow work under a
    # 60s parser timeout (ratio 0.75, same as 900s under old watchdog).
    source = tmp_path / "slow-canary.txt"
    source.write_text("slow canary source", encoding="utf-8")
    heartbeats: list[dict[str, object]] = []

    result = _run(
        source,
        parser=_canary_slow_parser,
        timeout_seconds=60,
        heartbeat_interval_seconds=1,
        progress=heartbeats.append,
    )

    assert result.status == "completed"
    assert len(heartbeats) >= 3
    assert all(item["detail"] == "parser_alive" for item in heartbeats)
    # single stable parser PID, never reaped by a watchdog
    assert len({item["parser_pid"] for item in heartbeats}) == 1
    assert heartbeats[-1]["parser_elapsed_seconds"] >= 40
    assert not list(tmp_path.glob(".parser-result-*.json"))


def test_slow_canary_document_over_parser_timeout_becomes_terminal_not_loop(
    tmp_path: Path,
):
    # Over-timeout slow document must raise NormalizationTimeoutError exactly
    # once (retry policy handles terminal transition upstream); parser PID is
    # reaped and no temp results leak.
    source = tmp_path / "over-timeout-canary.txt"
    source.write_text("over timeout canary source", encoding="utf-8")
    heartbeats: list[dict[str, object]] = []

    with pytest.raises(NormalizationTimeoutError):
        _run(
            source,
            parser=_canary_slow_parser,
            timeout_seconds=10,
            heartbeat_interval_seconds=0.5,
            progress=heartbeats.append,
        )

    parser_pid = int(heartbeats[-1]["parser_pid"])
    assert all(child.pid != parser_pid for child in multiprocessing.active_children())
    assert not list(tmp_path.glob(".parser-result-*.json"))
