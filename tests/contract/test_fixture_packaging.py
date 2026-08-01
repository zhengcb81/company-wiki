"""Hermetic fixtures must be present in a clean candidate/clone."""

import subprocess
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RAW_FIXTURES = [
    "tests/fixtures/mini_wiki/raw/北方华创/北方华创_2025年报.md",
    "tests/fixtures/mini_wiki/raw/中微公司/中微公司_歧义新闻.md",
    "tests/fixtures/mini_wiki/raw/中微公司/中微公司_恶意指令.md",
]


def test_required_raw_fixtures_are_not_gitignored():
    inside_git = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0
    candidate_manifest = ROOT / "candidate-manifest.json"
    candidate_files = None
    if not inside_git:
        assert candidate_manifest.is_file(), "clean candidate must include its materialization manifest"
        candidate_files = json.loads(candidate_manifest.read_text(encoding="utf-8"))["files"]

    for relative in REQUIRED_RAW_FIXTURES:
        assert (ROOT / relative).is_file(), f"missing fixture: {relative}"
        if inside_git:
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", "--", relative],
                cwd=ROOT,
                check=False,
            )
            assert result.returncode == 1, f"fixture is excluded from clean clone: {relative}"
        else:
            assert relative in candidate_files, f"fixture absent from candidate manifest: {relative}"
