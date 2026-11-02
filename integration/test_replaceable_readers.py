"""Real public reader substitution from an unrelated cwd in a new process."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_real_public_raw_and_narrative_commands_are_replaceable(tmp_path):
    unrelated = tmp_path / "unrelated working directory"
    unrelated.mkdir()
    probe = Path(__file__).with_name("public_reading_probe.py")
    result = subprocess.run([sys.executable, "-B", str(probe)], cwd=unrelated,
        env=dict(os.environ), capture_output=True, timeout=50)
    assert result.returncode == 0, (result.stdout + result.stderr).decode("utf-8", errors="replace")
    observed = json.loads(result.stdout)
    assert observed["same_semantics"]
    assert observed["producer_database_unchanged"]
    assert observed["changed_cwd_and_command_location"]
    assert observed["fixture_restored"]
    assert list(unrelated.iterdir()) == []
