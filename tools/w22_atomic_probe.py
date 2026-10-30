"""W22 evidence probe: separate the two path-length failure owners on real NTFS.

Read-only over production files; owns a scratch tree under the system temp and
removes it. Produces one JSON record per section on stdout:

1. target_valid_old_stage_breaks: the destination path itself is inside the
   native limit, but the legacy ``<basename>.<rand>.tmp`` staging name used by
   ``atomic_output`` pushes the stage path past it. Records the exact OSError.
2. deep_directory_beyond_native: the parent directory itself exceeds the
   native limit and only exists through extended-length creation. Records
   whether plain and extended-length access work there.
3. real_contention_error_shape: a genuine Windows sharing violation, so
   path-length handling can never be confused with a PermissionError.

Usage: python tools/w22_atomic_probe.py [--keep-scratch]
Exit code 0 means every section ran to a recorded verdict, not that paths are
supported; verdicts carry the evidence.
"""
from __future__ import annotations

import argparse
import errno as errno_module
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

NATIVE_LIMIT = 259  # usable characters without an extended-length prefix
STAGE_OVERHEAD = 1 + 8 + 4  # "." + random + ".tmp" copied from the legacy name


def _exc_record(exc: BaseException) -> dict:
    return {
        "type": type(exc).__name__,
        "str": str(exc),
        "errno": getattr(exc, "errno", None),
        "winerror": getattr(exc, "winerror", None),
    }


def _make_parent(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def probe_target_valid_old_stage_breaks(scratch: Path) -> dict:
    """Destination inside the limit; legacy staging name alone crosses it."""
    parent = _make_parent(scratch / "sec1")
    room = NATIVE_LIMIT - (len(str(parent)) + 1)
    target_name_length = room - STAGE_OVERHEAD + 1
    # Sanity: the destination stays creatable while the legacy stage is not.
    assert len(str(parent)) + 1 + target_name_length <= NATIVE_LIMIT
    assert len(str(parent)) + 1 + target_name_length + STAGE_OVERHEAD > NATIVE_LIMIT
    target = parent / ("t" * target_name_length + ".json")

    record: dict = {
        "section": "target_valid_old_stage_breaks",
        "parent_chars": len(str(parent)),
        "target_name_chars": len(target.name),
        "target_path_chars": len(str(target)),
        "legacy_stage_path_chars": len(str(target)) + STAGE_OVERHEAD,
        "long_paths_enabled_registry_note":
            "not read here; capability is measured behaviorally below",
    }
    try:
        with target.open("wb") as stream:
            stream.write(b"target itself is creatable")
        record["target_plain_create"] = "OK"
    except OSError as exc:
        record["target_plain_create"] = _exc_record(exc)
        return record

    # One real stage candidate with the legacy naming shape, no retry loop.
    legacy_stage = str(target) + "." + "12345678" + ".tmp"
    try:
        handle = os.open(legacy_stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(handle)
        record["legacy_stage_create"] = "OK"
        os.unlink(legacy_stage)
    except OSError as exc:
        record["legacy_stage_create"] = _exc_record(exc)

    # The real shared primitive as it exists on this checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from company_wiki._atomic_file import atomic_output

    try:
        with atomic_output(target) as stream:
            stream.write(b"replacement body")
        record["atomic_output"] = "OK"
    except OSError as exc:
        record["atomic_output"] = _exc_record(exc)
    record["target_bytes_after"] = target.read_bytes().decode("ascii", "replace")
    return record


def _extended(path: str) -> str:
    if path.startswith("\\\\?\\"):
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute.replace("/", "\\")


def probe_deep_directory_beyond_native(scratch: Path) -> dict:
    """The directory itself only exists through extended-length creation."""
    parent = scratch / "sec2"
    filler = "d" * 200
    deep = parent
    while len(str(deep)) <= NATIVE_LIMIT + 60:
        deep = deep / filler
    record: dict = {
        "section": "deep_directory_beyond_native",
        "deep_path_chars": len(str(deep)),
    }
    try:
        os.makedirs(_extended(str(deep)), exist_ok=True)
        record["extended_mkdir"] = "OK"
    except OSError as exc:
        record["extended_mkdir"] = _exc_record(exc)
        return record

    plain = str(deep)
    try:
        os.stat(plain)
        record["plain_stat"] = "OK"
    except OSError as exc:
        record["plain_stat"] = _exc_record(exc)

    stage = _extended(plain) + "\\" + "stage.body.tmp"
    try:
        handle = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(handle)
        record["extended_stage_create"] = "OK"
    except OSError as exc:
        record["extended_stage_create"] = _exc_record(exc)
        return record

    destination = _extended(plain) + "\\" + "destination.json"
    try:
        os.replace(stage, destination)
        record["extended_replace"] = "OK"
    except OSError as exc:
        record["extended_replace"] = _exc_record(exc)
    try:
        os.unlink(destination)
        record["extended_unlink_destination"] = "OK"
    except OSError as exc:
        record["extended_unlink_destination"] = _exc_record(exc)
    return record


def probe_real_contention_error_shape(scratch: Path) -> dict:
    """A locked destination must stay a permission error, never path length."""
    parent = _make_parent(scratch / "sec3")
    destination = parent / "destination.json"
    moving = parent / "moving.json"
    destination.write_bytes(b"held by an open handle")
    moving.write_bytes(b"replacement")
    record: dict = {"section": "real_contention_error_shape"}
    held = os.open(destination, os.O_RDONLY)  # Windows: no FILE_SHARE_DELETE
    try:
        os.replace(moving, destination)
        record["replace_onto_open_file"] = "OK"
    except OSError as exc:
        record["replace_onto_open_file"] = _exc_record(exc)
    finally:
        os.close(held)
    record["errno_constants"] = {
        "ENOENT": errno_module.ENOENT, "EACCES": errno_module.EACCES,
    }
    return record


def probe_plain_boundaries(scratch: Path) -> dict:
    """Pin the native Win32 limits the extended-length wrapper encodes.

    Without the ``\\\\?\\`` prefix, file creation stops at 259 characters
    while directory creation stops lower; the mixed extended-to-plain
    replacement inside one directory must work for the writer's wrap choice.
    """
    parent = _make_parent(scratch / "sec4")
    record: dict = {"section": "plain_boundaries", "parent_chars": len(str(parent))}
    for total in (259, 260):
        stage = str(parent / ("f" * (total - len(str(parent)) - 1 - 5))) + ".json"
        try:
            handle = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(handle)
            os.unlink(stage)
            record[f"plain_file_create_{total}"] = "OK"
        except OSError as exc:
            record[f"plain_file_create_{total}"] = _exc_record(exc)
    for total in (247, 248):
        candidate = parent / ("d" * (total - len(str(parent)) - 1))
        try:
            candidate.mkdir()
            candidate.rmdir()
            record[f"plain_mkdir_{total}"] = "OK"
        except OSError as exc:
            record[f"plain_mkdir_{total}"] = _exc_record(exc)
    deep_parent = parent / ("e" * (240 - len(str(parent)) - 1))
    os.makedirs(_extended(str(deep_parent)), exist_ok=True)
    stage = _extended(str(deep_parent)) + "\\" + "stage.body.tmp"
    handle = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(handle)
    destination = deep_parent / "a.json"
    try:
        os.replace(stage, destination)
        record["mixed_extended_to_plain_replace"] = "OK"
        os.unlink(_extended(str(destination)))
    except OSError as exc:
        record["mixed_extended_to_plain_replace"] = _exc_record(exc)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-scratch", action="store_true",
                        help="print the scratch path and leave it for inspection")
    args = parser.parse_args(argv)
    scratch = Path(tempfile.mkdtemp(prefix="w22-probe-"))
    try:
        sections = [
            probe_target_valid_old_stage_breaks(scratch),
            probe_deep_directory_beyond_native(scratch),
            probe_real_contention_error_shape(scratch),
            probe_plain_boundaries(scratch),
        ]
    finally:
        if args.keep_scratch:
            print(f"SCRATCH_KEPT={scratch}", file=sys.stderr)
        else:
            shutil.rmtree(scratch, ignore_errors=True)
    json.dump(sections, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
