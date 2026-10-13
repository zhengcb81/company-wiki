"""Behavioral regressions for the shared local file commit boundary."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from threading import Barrier, Lock

import pytest

from company_wiki.source_catalog.service import SourceCatalog


def test_catalog_export_same_process_writers_own_distinct_staging(tmp_path, monkeypatch):
    destination = tmp_path / "index.md"
    destination.write_text("old", encoding="utf-8")
    foreign = tmp_path / (destination.name + f".{os.getpid()}.tmp")
    foreign.write_text("another operation owns this", encoding="utf-8")
    barrier, lock = Barrier(2), Lock()
    staged = []
    real_replace = os.replace

    def coordinated_replace(source, target):
        if Path(target) == destination:
            with lock:
                first_attempt = Path(source) not in staged
                if first_attempt:
                    staged.append(Path(source))
            # Synchronise first submissions, not a retry after its peer exits.
            if first_attempt:
                barrier.wait(timeout=5)
        return real_replace(source, target)

    monkeypatch.setattr(os, "replace", coordinated_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(SourceCatalog._atomic_write, destination, text)
                   for text in ("complete A", "complete B")]
        outcomes = [future.exception() for future in futures]
    assert outcomes == [None, None]
    assert len(set(staged)) == 2
    assert destination.read_text(encoding="utf-8") in {"complete A", "complete B"}
    assert foreign.read_text(encoding="utf-8") == "another operation owns this"
    assert set(tmp_path.iterdir()) == {destination, foreign}


def test_failed_export_preserves_destination_and_foreign_staging(tmp_path, monkeypatch):
    destination = tmp_path / "index.md"
    destination.write_bytes(b"existing original")
    foreign = tmp_path / (destination.name + f".{os.getpid()}.tmp")
    foreign.write_bytes(b"foreign staging")

    def refused_replace(source, target):
        raise PermissionError("destination busy")

    monkeypatch.setattr(os, "replace", refused_replace)
    with pytest.raises(PermissionError, match="destination busy"):
        SourceCatalog._atomic_write(destination, "replacement")
    assert destination.read_bytes() == b"existing original"
    assert foreign.read_bytes() == b"foreign staging"
    assert set(tmp_path.iterdir()) == {destination, foreign}


def test_csv_serialization_failure_leaves_existing_export(tmp_path):
    destination = tmp_path / "catalog.csv"
    destination.write_bytes(b"prior complete csv")
    with pytest.raises(ValueError):
        SourceCatalog._write_csv(destination, [{"unexpected": "value"}], fields=["field"])
    assert destination.read_bytes() == b"prior complete csv"
    assert set(tmp_path.iterdir()) == {destination}


def test_atomic_body_failure_cleans_only_its_staging(tmp_path):
    from company_wiki._atomic_file import atomic_output

    destination = tmp_path / "metadata.json"
    destination.write_bytes(b"prior")
    foreign = tmp_path / "metadata.json.foreign.tmp"
    foreign.write_bytes(b"foreign")
    with pytest.raises(RuntimeError, match="serialization failed"):
        with atomic_output(destination) as stream:
            stream.write(b"partial")
            raise RuntimeError("serialization failed")
    assert destination.read_bytes() == b"prior"
    assert foreign.read_bytes() == b"foreign"
    assert set(tmp_path.iterdir()) == {destination, foreign}


def test_catalog_csv_bytes_preserve_utf8_bom_and_crlf(tmp_path):
    destination = tmp_path / "catalog.csv"
    SourceCatalog._write_csv(destination, [{"title": "年报", "text": "a,b"}])
    assert destination.read_bytes() == b"\xef\xbb\xbftitle,text\r\n" + "年报".encode() + b',"a,b"\r\n'
    assert set(tmp_path.iterdir()) == {destination}


def test_atomic_sync_is_caller_owned_opt_in(tmp_path, monkeypatch):
    from company_wiki._atomic_file import atomic_output

    sync_calls = []
    monkeypatch.setattr(os, "fsync", lambda descriptor: sync_calls.append(descriptor))
    for sync in (False, True):
        with atomic_output(tmp_path / "output", sync=sync) as stream:
            stream.write(b"complete")
    assert len(sync_calls) == 1
    assert (tmp_path / "output").read_bytes() == b"complete"
