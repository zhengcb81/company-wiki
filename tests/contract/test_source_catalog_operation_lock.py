"""Contracts for PID-reuse-safe Source Catalog operation locks."""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading

import pytest


def _write_lock(catalog_dir: Path, payload: dict[str, object], *, mtime: float) -> Path:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / "operation.lock"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def _identity(*, creation_time: float | None) -> dict[str, object]:
    return {
        "live": True,
        "creation_time": creation_time,
        "executable": "C:/Python/python.exe",
        "verification": "verified" if creation_time is not None else "unavailable",
    }


def test_new_lock_records_creation_identity_and_rejects_the_matching_owner(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.lock as lock_module

    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=2_000.0),
        raising=False,
    )
    catalog_dir = tmp_path / ".source_catalog"

    with lock_module.CatalogOperationLock(catalog_dir, operation="normalize"):
        payload = json.loads((catalog_dir / "operation.lock").read_text("utf-8"))
        status = lock_module.operation_lock_status(catalog_dir)

        assert payload["process_creation_time"] == 2_000.0
        assert status["state"] == "live"
        assert status["identity_verification"] == "matched"
        assert status["process_creation_time"] == 2_000.0
        with pytest.raises(lock_module.CatalogOperationLockedError):
            with lock_module.CatalogOperationLock(catalog_dir, operation="export"):
                pass


def test_reused_pid_with_mismatched_creation_identity_is_stale_and_replaceable(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.lock as lock_module

    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=3_000.0),
        raising=False,
    )
    catalog_dir = tmp_path / ".source_catalog"
    _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "backfill_text_fingerprints",
            "token": "old-owner",
            "process_creation_time": 2_000.0,
        },
        mtime=2_100.0,
    )

    status = lock_module.operation_lock_status(catalog_dir)
    assert status["state"] == "stale"
    assert status["identity_verification"] == "mismatch"

    with lock_module.CatalogOperationLock(catalog_dir, operation="normalize"):
        replacement = json.loads(
            (catalog_dir / "operation.lock").read_text(encoding="utf-8")
        )
        assert replacement["token"] != "old-owner"
        assert replacement["process_creation_time"] == 3_000.0


def test_legacy_lock_is_stale_when_current_pid_started_after_lock_mtime(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.lock as lock_module

    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=3_000.0),
        raising=False,
    )
    catalog_dir = tmp_path / ".source_catalog"
    _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "normalize",
            "token": "legacy-owner",
        },
        mtime=2_000.0,
    )

    status = lock_module.operation_lock_status(catalog_dir)
    assert status["state"] == "stale"
    assert status["identity_verification"] == "legacy_pid_reused"

    with lock_module.CatalogOperationLock(catalog_dir, operation="export"):
        replacement = json.loads(
            (catalog_dir / "operation.lock").read_text(encoding="utf-8")
        )
        assert replacement["token"] != "legacy-owner"


def test_legacy_lock_fails_closed_when_creation_identity_is_unavailable(
    tmp_path, monkeypatch
):
    import company_wiki.source_catalog.lock as lock_module

    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=None),
        raising=False,
    )
    catalog_dir = tmp_path / ".source_catalog"
    _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "normalize",
            "token": "legacy-owner",
        },
        mtime=2_000.0,
    )

    status = lock_module.operation_lock_status(catalog_dir)
    assert status["state"] == "live"
    assert status["identity_verification"] == "legacy_unverified"
    with pytest.raises(lock_module.CatalogOperationLockedError):
        with lock_module.CatalogOperationLock(catalog_dir, operation="export"):
            pass


def test_legacy_lock_fails_closed_when_process_predates_lock(tmp_path, monkeypatch):
    import company_wiki.source_catalog.lock as lock_module

    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=1_000.0),
    )
    catalog_dir = tmp_path / ".source_catalog"
    _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "normalize",
            "token": "legacy-owner",
        },
        mtime=2_000.0,
    )

    status = lock_module.operation_lock_status(catalog_dir)
    assert status["state"] == "live"
    assert status["identity_verification"] == "legacy_consistent"
    with pytest.raises(lock_module.CatalogOperationLockedError):
        with lock_module.CatalogOperationLock(catalog_dir, operation="export"):
            pass


def test_stale_cleanup_never_removes_a_replaced_owner_token(tmp_path, monkeypatch):
    import company_wiki.source_catalog.lock as lock_module

    catalog_dir = tmp_path / ".source_catalog"
    path = _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "normalize",
            "token": "old-owner",
            "process_creation_time": 1_000.0,
        },
        mtime=1_100.0,
    )
    original_owner_status = lock_module._owner_status

    def replace_during_validation(lock_path, payload):
        if payload.get("token") == "old-owner":
            lock_path.write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "operation": "export",
                        "token": "new-owner",
                        "process_creation_time": 3_000.0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return {
                "state": "stale",
                "pid": os.getpid(),
                "identity_verification": "mismatch",
                "process_creation_time": 1_000.0,
                "observed_process_creation_time": 3_000.0,
            }
        return original_owner_status(lock_path, payload)

    monkeypatch.setattr(lock_module, "_owner_status", replace_during_validation)
    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=3_000.0),
    )

    with pytest.raises(lock_module.CatalogOperationLockedError):
        with lock_module.CatalogOperationLock(catalog_dir, operation="scan"):
            pass

    assert json.loads(path.read_text(encoding="utf-8"))["token"] == "new-owner"


def test_stale_takeover_is_serialized_across_the_final_unlink(tmp_path, monkeypatch):
    import company_wiki.source_catalog.lock as lock_module

    catalog_dir = tmp_path / ".source_catalog"
    lock_path = _write_lock(
        catalog_dir,
        {
            "pid": os.getpid(),
            "operation": "normalize",
            "token": "stale-owner",
            "process_creation_time": 1_000.0,
        },
        mtime=1_100.0,
    )
    monkeypatch.setattr(
        lock_module,
        "_process_identity",
        lambda _pid: _identity(creation_time=3_000.0),
    )

    owner_a_at_unlink = threading.Event()
    allow_owner_a_unlink = threading.Event()
    owner_a_owned = threading.Event()
    owner_b_owned = threading.Event()
    release_owners = threading.Event()
    owner_b_done = threading.Event()
    errors: list[BaseException] = []
    original_unlink = Path.unlink
    paused = False

    def controlled_unlink(path, *args, **kwargs):
        nonlocal paused
        if (
            path == lock_path
            and threading.current_thread().name == "owner-a"
            and not paused
        ):
            paused = True
            owner_a_at_unlink.set()
            assert allow_owner_a_unlink.wait(5)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", controlled_unlink)

    def acquire_a():
        try:
            with lock_module.CatalogOperationLock(catalog_dir, operation="scan"):
                owner_a_owned.set()
                release_owners.wait(5)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def acquire_b():
        try:
            with lock_module.CatalogOperationLock(catalog_dir, operation="export"):
                owner_b_owned.set()
                release_owners.wait(5)
        except lock_module.CatalogOperationLockedError:
            pass
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)
        finally:
            owner_b_done.set()

    owner_a = threading.Thread(target=acquire_a, name="owner-a")
    owner_b = threading.Thread(target=acquire_b, name="owner-b")
    owner_a.start()
    assert owner_a_at_unlink.wait(5)
    owner_b.start()

    owner_b_entered_during_takeover = owner_b_owned.wait(1)
    allow_owner_a_unlink.set()
    assert owner_a_owned.wait(5)
    release_owners.set()
    assert owner_b_done.wait(5)
    owner_a.join(5)
    owner_b.join(5)

    assert not owner_b_entered_during_takeover
    assert not owner_a.is_alive()
    assert not owner_b.is_alive()
    assert errors == []


@pytest.mark.skipif(os.name != "nt", reason="Windows CIM identity fallback")
def test_windows_cim_fallback_returns_a_real_process_creation_time():
    import company_wiki.source_catalog.lock as lock_module

    creation_time = lock_module._windows_creation_time_via_cim(os.getpid())

    assert isinstance(creation_time, float)
    assert creation_time > 0


@pytest.mark.skipif(os.name != "nt", reason="Windows lock payload identity")
def test_real_windows_lock_payload_matches_the_current_process(tmp_path):
    import company_wiki.source_catalog.lock as lock_module

    catalog_dir = tmp_path / ".source_catalog"
    with lock_module.CatalogOperationLock(catalog_dir, operation="normalize"):
        payload = json.loads((catalog_dir / "operation.lock").read_text("utf-8"))
        status = lock_module.operation_lock_status(catalog_dir)

        assert isinstance(payload["process_creation_time"], float)
        assert status["state"] == "live"
        assert status["identity_verification"] == "matched"
