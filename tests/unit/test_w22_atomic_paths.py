"""W22: the shared atomic writer must not let its staging name amplify depth.

Two path-length failure owners are separated on purpose:

* the destination is inside the native limit while the legacy
  ``<basename>.<rand>.tmp`` staging name alone crossed it, and
* the parent directory itself only exists through extended-length creation.

Windows hosts that enforce the native limit run the strict boundary asserts;
hosts with long-path support natively just run the functional ones. Real
PermissionError contention must keep its own identity, never be re-read as a
path problem.
"""
import os
from pathlib import Path

import pytest

from company_wiki._atomic_file import atomic_output

NATIVE_LIMIT = 259  # usable path characters without an extended-length prefix
LEGACY_STAGE_OVERHEAD = 1 + 8 + 4  # "." + 8 random characters + ".tmp"


def _observed_stages(monkeypatch):
    """Record every os.replace stage while keeping the real behaviour."""
    stages = []
    real_replace = os.replace

    def spy(source, destination):
        stages.append((source, destination))
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", spy)
    return stages


def _extended(path: str) -> str:
    """Test-local extended-length form, used only to reach deep directories."""
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\"):
        return "\\\\?\\UNC\\" + absolute.lstrip("\\")
    return "\\\\?\\" + absolute.replace("/", "\\")


def test_staging_name_is_short_same_directory_and_independent_of_target(
        tmp_path, monkeypatch):
    stages = _observed_stages(monkeypatch)
    target = tmp_path / ("quarterly-report-" * 4 + ".json")
    with atomic_output(target) as stream:
        stream.write(b"body")
    source, destination = stages[0]
    assert Path(source).parent == target.parent
    assert Path(destination) == target
    assert not str(destination).startswith("\\\\?\\")
    assert len(Path(source).name) <= 32
    assert Path(source).suffix == ".tmp"
    assert target.read_bytes() == b"body"
    assert list(tmp_path.iterdir()) == [target]


def test_target_inside_native_limit_survives_legacy_staging_boundary(tmp_path):
    # The destination stays creatable natively; the legacy staging shape for
    # this exact destination would cross the native limit.
    parent = tmp_path / "legacy-boundary"
    parent.mkdir()
    room = NATIVE_LIMIT - (len(str(parent)) + 1)
    target = parent / ("n" * (room - LEGACY_STAGE_OVERHEAD + 1) + ".json")
    assert len(str(target)) <= NATIVE_LIMIT
    assert len(str(target)) + LEGACY_STAGE_OVERHEAD > NATIVE_LIMIT
    with atomic_output(target) as stream:
        stream.write(b"complete")
    assert target.read_bytes() == b"complete"
    assert list(parent.iterdir()) == [target]


def _deep_directory(root: Path) -> Path:
    deep = root
    while len(str(deep)) <= NATIVE_LIMIT + 40:
        deep = deep / ("d" * 120)
    if os.name == "nt":
        os.makedirs(_extended(str(deep)), exist_ok=True)
    else:
        deep.mkdir(parents=True, exist_ok=True)
    return deep


def test_deep_directory_beyond_native_limit_writes_atomically(tmp_path):
    deep = _deep_directory(tmp_path)
    target = deep / "destination.json"
    with atomic_output(target) as stream:
        stream.write(b"deep body")
    # A native plain read of this path may be impossible on Windows; the
    # extended-length form is the same file and proves the write landed.
    assert Path(_extended(str(target))).read_bytes() == b"deep body"


def test_relative_target_keeps_plain_representation(tmp_path, monkeypatch):
    stages = _observed_stages(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "rel").mkdir()
    target = Path("rel") / "leaf.json"
    with atomic_output(target) as stream:
        stream.write(b"relative")
    source, destination = stages[0]
    assert Path(destination) == target
    assert not str(source).startswith("\\\\?\\")
    assert not str(destination).startswith("\\\\?\\")
    assert target.read_bytes() == b"relative"


def test_fsync_failure_cleans_stage_and_preserves_target(tmp_path, monkeypatch):
    target = tmp_path / "out.bin"
    target.write_bytes(b"original")

    def broken_fsync(descriptor):
        raise OSError("fsync failed")

    monkeypatch.setattr(os, "fsync", broken_fsync)
    with pytest.raises(OSError, match="fsync failed"):
        with atomic_output(target, sync=True) as stream:
            stream.write(b"body")
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]


def test_text_modes_encoding_and_newline_are_preserved(tmp_path):
    # newline="\n" means "no output translation": LF must survive even on
    # Windows, where newline=None would rewrite it to CRLF.
    translated = tmp_path / "text.txt"
    with atomic_output(translated, mode="w", encoding="utf-8", newline="\n") as stream:
        stream.write("第一行\n第二行\n")
    assert translated.read_bytes() == "第一行\n第二行\n".encode("utf-8")
    verbatim = tmp_path / "catalog.csv"
    with atomic_output(verbatim, mode="w", encoding="utf-8-sig", newline="") as stream:
        stream.write("title,text\r\n年报,a,b\r\n")
    assert verbatim.read_bytes() == b"\xef\xbb\xbf" + "title,text\r\n年报,a,b\r\n".encode("utf-8")
    binary = tmp_path / "blob.bin"
    with atomic_output(binary) as stream:
        stream.write(b"\x00\x01\xff")
    assert binary.read_bytes() == b"\x00\x01\xff"


def test_real_permission_error_is_never_treated_as_path_length(
        tmp_path, monkeypatch):
    target = tmp_path / "held.json"
    target.write_bytes(b"original")
    attempts = []

    def access_denied(source, destination):
        attempts.append(source)
        error = PermissionError("destination stays access denied")
        error.winerror = 5
        raise error

    monkeypatch.setattr(os, "replace", access_denied)
    with pytest.raises(PermissionError, match="access denied"):
        with atomic_output(target) as stream:
            stream.write(b"body")
    # The existing bounded Windows contention policy, unchanged: four
    # attempts on winerror 5, and the error surfaces as itself.
    assert len(attempts) == 4
    assert target.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.skipif(os.name != "nt", reason="extended-length forms are Windows-only")
def test_openable_wraps_only_paths_beyond_the_native_limit():
    from company_wiki import _atomic_path

    short = r"C:\short\leaf.json"
    assert _atomic_path.openable(short) == short
    edge = "C:\\" + "x" * (NATIVE_LIMIT - 3)
    assert len(edge) == NATIVE_LIMIT
    assert _atomic_path.openable(edge) == edge
    beyond = "C:\\" + "x" * (NATIVE_LIMIT - 2)
    wrapped = _atomic_path.openable(beyond)
    assert wrapped == "\\\\?\\" + beyond
    assert _atomic_path.openable(wrapped) == wrapped  # idempotent


@pytest.mark.skipif(os.name != "nt", reason="extended-length forms are Windows-only")
def test_openable_handles_unc_and_forward_slashes(tmp_path, monkeypatch):
    from company_wiki import _atomic_path

    monkeypatch.chdir(tmp_path)
    unc = "\\\\" + "server" + "\\" + "share" + "\\" + "d" * 300
    assert _atomic_path.openable(unc) == "\\\\?\\UNC\\" + "server" + "\\" + "share" + "\\" + "d" * 300
    slashed = "C:/" + "d" * 300
    assert _atomic_path.openable(slashed) == "\\\\?\\C:\\" + "d" * 300
    relative = "d" * 300
    assert _atomic_path.openable(relative).startswith("\\\\?\\")
    assert ".." not in _atomic_path.openable(relative)


@pytest.mark.skipif(os.name != "nt", reason="extended-length forms are Windows-only")
def test_stage_dir_wraps_only_when_a_stage_name_would_not_fit():
    from company_wiki import _atomic_path

    short = r"C:\short"
    assert _atomic_path.stage_dir(short) == short
    fits = "C:\\" + "x" * (_atomic_path.NATIVE_PATH_LIMIT
                          - _atomic_path.STAGE_NAME_RESERVE - 3)
    assert len(fits) == _atomic_path.NATIVE_PATH_LIMIT - _atomic_path.STAGE_NAME_RESERVE
    assert _atomic_path.stage_dir(fits) == fits
    one_over = "C:\\" + "x" * (_atomic_path.NATIVE_PATH_LIMIT
                               - _atomic_path.STAGE_NAME_RESERVE - 2)
    assert _atomic_path.stage_dir(one_over) == "\\\\?\\" + one_over


def test_short_basename_target_near_limit_still_writes(tmp_path):
    # A destination with a short basename inside the native limit, in a
    # parent deep enough that a 20-character stage name would not fit
    # natively: the writer reaches its stage through the extended-length
    # form while the plain destination keeps its representation.
    if len(str(tmp_path)) + 2 > 240:
        pytest.skip("host pytest temp too deep to place the probe parent")
    parent = tmp_path / ("c" * (240 - len(str(tmp_path)) - 1))
    parent.mkdir()
    assert len(str(parent)) == 240
    target = parent / "leaf.json"
    assert len(str(target)) <= NATIVE_LIMIT
    with atomic_output(target) as stream:
        stream.write(b"wrapped stage body")
    assert target.read_bytes() == b"wrapped stage body"
    assert list(parent.iterdir()) == [target]


@pytest.mark.skipif(os.name == "nt", reason="non-Windows keeps every path verbatim")
def test_openable_is_identity_off_windows():
    from company_wiki import _atomic_path

    assert _atomic_path.openable("d" * 400 + "/leaf.json") == "d" * 400 + "/leaf.json"
    assert _atomic_path.stage_dir("d" * 400) == "d" * 400
    assert isinstance(_atomic_path.openable(Path("/tmp/leaf.json")), str)


def test_stage_file_has_short_random_exclusive_name(tmp_path, monkeypatch):
    stages = _observed_stages(monkeypatch)
    target = tmp_path / "same-name.bin"
    for body in (b"first", b"second"):
        with atomic_output(target) as stream:
            stream.write(body)
    assert len(stages) == 2
    stage_names = {Path(source).name for source, _ in stages}
    assert len(stage_names) == 2
    assert all(len(name) <= 32 and name.endswith(".tmp") for name in stage_names)
    assert target.read_bytes() == b"second"
    assert list(tmp_path.iterdir()) == [target]
