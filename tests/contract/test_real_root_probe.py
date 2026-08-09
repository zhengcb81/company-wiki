"""WU-1301 RED/audit tests: real-root read-only probe."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "real_root_probe.py"


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "companies" / "Acme" / "raw").mkdir(parents=True)
    (tmp_path / "companies" / "Acme" / "raw" / "annual.pdf").write_bytes(
        b"%PDF-1.4 x" * 10
    )
    return tmp_path / "companies"


def test_fast_probe_deterministic(tmp_path):
    tree = _tree(tmp_path)
    first = json.loads(subprocess.run(
        [sys.executable, str(PROBE), "--root", str(tree), "--read-only"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    ).stdout)
    second = json.loads(subprocess.run(
        [sys.executable, str(PROBE), "--root", str(tree), "--read-only"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    ).stdout)
    assert first == second
    assert first["fast"]["file_count"] == 1


def test_full_probe_salted_no_raw_paths(tmp_path):
    tree = _tree(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(PROBE), "--root", str(tree), "--read-only",
         "--full"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    payload = json.loads(proc.stdout)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "Acme" not in serialized  # no raw path leaks
    assert "annual.pdf" not in serialized
    assert payload["entries"][0]["salted_path"]


def test_read_only_flag_mandatory(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(PROBE), "--root", str(_tree(tmp_path))],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert proc.returncode == 2


def test_probe_never_writes(tmp_path):
    tree = _tree(tmp_path)
    before = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    subprocess.run(
        [sys.executable, str(PROBE), "--root", str(tree), "--read-only",
         "--full"],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    after = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    assert before == after
