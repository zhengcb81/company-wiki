from pathlib import Path

from recovery_baseline import RecoveryBaselineVerifier


def make_verifier(tmp_path: Path, source: Path, destination: Path) -> RecoveryBaselineVerifier:
    return RecoveryBaselineVerifier(
        source,
        destination,
        tmp_path / "state" / "verify.db",
        tmp_path / "state" / "manifest.json",
    )


def test_matching_copy_is_fully_verified(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "a.txt").write_text("alpha", encoding="utf-8")
    (destination / "a.txt").write_text("alpha", encoding="utf-8")

    verifier = make_verifier(tmp_path, source, destination)
    try:
        verifier.scan()
        summary = verifier.verify()
        verifier.write_manifest()
        assert summary["verified"] == 1
        assert verifier.is_complete_and_valid()
    finally:
        verifier.close()


def test_scan_detects_missing_extra_and_size_mismatch(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "missing.txt").write_text("missing", encoding="utf-8")
    (source / "different.txt").write_text("short", encoding="utf-8")
    (destination / "different.txt").write_text("much longer", encoding="utf-8")
    (destination / "extra.txt").write_text("extra", encoding="utf-8")

    verifier = make_verifier(tmp_path, source, destination)
    try:
        summary = verifier.scan()
        assert summary["missing"] == 1
        assert summary["extra"] == 1
        assert summary["size_mismatch"] == 1
        assert not verifier.is_complete_and_valid()
    finally:
        verifier.close()


def test_equal_size_content_mismatch_is_rejected(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "same-size.bin").write_bytes(b"AAAA")
    (destination / "same-size.bin").write_bytes(b"BBBB")

    verifier = make_verifier(tmp_path, source, destination)
    try:
        verifier.scan()
        summary = verifier.verify()
        assert summary["hash_mismatch"] == 1
        assert not verifier.is_complete_and_valid()
    finally:
        verifier.close()


def test_verification_resumes_from_checkpoint(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    for index in range(3):
        (source / f"{index}.txt").write_text(str(index), encoding="utf-8")
        (destination / f"{index}.txt").write_text(str(index), encoding="utf-8")

    verifier = make_verifier(tmp_path, source, destination)
    try:
        verifier.scan()
        partial = verifier.verify(max_files=1)
        assert partial["verified"] == 1
        assert partial["pending"] == 2
    finally:
        verifier.close()

    resumed = make_verifier(tmp_path, source, destination)
    try:
        resumed.scan()
        final = resumed.verify()
        assert final["verified"] == 3
        assert resumed.is_complete_and_valid()
    finally:
        resumed.close()
