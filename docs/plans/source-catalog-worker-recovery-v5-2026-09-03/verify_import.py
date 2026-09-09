"""Read-only verification of the v5 import, NOT the future v5 plan validator."""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path

ROOT = Path(__file__).absolute().parent
MANIFEST_SHA256 = "da7d116e8c692d6311411c7390bec4278b59666a771823672f53e9b0f6567e4a"
HEX = re.compile(r"[0-9a-f]{64}\Z")
SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
RECORD_KEYS = {
    "source", "target", "role", "source_sha256_before", "source_sha256_after",
    "sha256", "size_bytes", "historical_v4_sha256",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def safe_target(value: object) -> str:
    require(isinstance(value, str), "target must be a string")
    require(value.startswith("baseline/"), "target outside baseline/")
    parts = value.split("/")
    require(all(SEGMENT.fullmatch(part) for part in parts), "unsafe target segment")
    return value


def no_reparse(path: Path) -> None:
    current = path
    while True:
        info = current.lstat()
        require(not stat.S_ISLNK(info.st_mode), f"symlink refused: {current}")
        require(
            not (getattr(info, "st_file_attributes", 0)
                 & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),
            f"reparse refused: {current}",
        )
        if current.parent == current:
            break
        current = current.parent


def raw_hash(path: Path) -> str:
    no_reparse(path)
    require(path.is_file(), f"not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory() -> set[str]:
    result = set()
    pending = [ROOT / "baseline"]
    while pending:
        directory = pending.pop()
        no_reparse(directory)
        for path in directory.iterdir():
            no_reparse(path)
            if path.is_dir():
                pending.append(path)
            else:
                require(path.is_file(), f"unsupported object: {path}")
                result.add(path.relative_to(ROOT).as_posix())
    return result


def main() -> None:
    # Verify parent chain too; this is a read-only import check, not a file lock.
    no_reparse(ROOT)
    for bad in (
        "../escape", "/baseline/a", "C:/baseline/a", "baseline//a",
        "baseline/./a", "baseline/../a", "baseline\\a", "baseline/a:ads",
    ):
        try:
            safe_target(bad)
        except ValueError:
            pass
        else:
            raise ValueError(f"path negative self-test survived: {bad}")

    manifest_path = ROOT / "import_manifest.v5.json"
    require(raw_hash(manifest_path) == MANIFEST_SHA256, "import manifest bytes changed")
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates
    )
    require(manifest["kind"] == "MIGRATION_INPUT_SNAPSHOT", "not an import manifest")
    require(manifest["capture_generation"] == "v5", "wrong capture generation")
    require(manifest["source_protocol_revision"] == "v4", "wrong source protocol")
    require(
        manifest["authorized_baseline"] == "CURRENT_CONTENT_NEW_BASELINE_NOT_V4_RESTORATION",
        "baseline meaning changed",
    )
    records = manifest["files"]
    require(type(manifest["file_count"]) is int and manifest["file_count"] == 54, "wrong count")
    require(len(records) == 54, "expected exactly 54 records")
    targets = []
    plan_records = []
    for record in records:
        require(set(record) == RECORD_KEYS, "unexpected record keys")
        target = safe_target(record["target"])
        targets.append(target)
        require(
            type(record["size_bytes"]) is int and record["size_bytes"] >= 0,
            f"invalid size: {target}",
        )
        for key in ("sha256", "source_sha256_before", "source_sha256_after"):
            require(
                isinstance(record[key], str) and HEX.fullmatch(record[key]),
                f"invalid digest {key}: {target}",
            )
        require(
            record["sha256"] == record["source_sha256_before"]
            == record["source_sha256_after"],
            f"capture source/destination mismatch: {target}",
        )
        path = ROOT / target
        require(raw_hash(path) == record["sha256"], f"snapshot bytes changed: {target}")
        require(path.stat().st_size == record["size_bytes"], f"size changed: {target}")
        if record["role"] == "prior_plan_current_content":
            plan_records.append(record)
            require(target.startswith("baseline/plan/"), "wrong plan destination")
            require(
                isinstance(record["historical_v4_sha256"], str)
                and HEX.fullmatch(record["historical_v4_sha256"]),
                "missing historical digest",
            )
        else:
            require(record["historical_v4_sha256"] is None, "unexpected historical digest")
    require(len({value.casefold() for value in targets}) == 54, "duplicate/casefold target")
    require(inventory() == set(targets), "unlisted or missing baseline file")
    require(len(plan_records) == 48, "expected 48 plan inputs")
    exact = sum(r["sha256"] == r["historical_v4_sha256"] for r in plan_records)
    require(exact == 21 and len(plan_records) - exact == 27, "historical drift count changed")

    attr_path = ROOT / ".gitattributes"
    no_reparse(attr_path)
    rules = [
        line.strip() for line in attr_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        rules == ["* -text -eol -filter -working-tree-encoding"],
        "local byte-preservation rule changed",
    )
    print("PASS: v5 import; 54/54 exact files; 48 plan inputs (21 v4-exact, 27 acknowledged drift)")
    print("READ_ONLY: local import files only; no source mutation, database, registry, process or network access")
    print("IMPORT_ONLY: not a formal v5 freeze, independent plan verdict, or worker execution authorization")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
