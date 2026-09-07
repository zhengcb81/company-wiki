"""Pre-push gate: CI-equivalent fast checks BEFORE pushing (root-cause fix).

Mirrors the CI workflow's fast surface so failures are caught locally:

  1. ruff check src tests/unit tests/contract scripts   (CI WU-1.2)
  2. compileall src scripts tests                        (CI WU-7.1)
  3. config_doctor                                       (CI WU-7.1)
  4. FC-1204 complexity ratchet                          (CI meta-gate)
  5. Section-extractor + binding + observation contract tests
     (the surfaces most often broken by cross-repo changes)

Exit non-zero on the first red check.  Full pytest + coverage ratchet
stay in CI (too slow for a pre-push gate on Windows).

Push protocol (see revenue-forecast ci_root_fix.md):
    python tools/pre_push_gate.py   # ~2-3 min
    git push ...
    # self-monitor GitHub Actions until green; on red fix the ROOT CAUSE.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], label: str, timeout: int = 600, env_extra: dict | None = None) -> int:
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    if env_extra:
        env.update(env_extra)
    print(f"\n=== {label} ===")
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=env,
    )
    tail = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-1000:]
    if proc.returncode != 0:
        print(tail)
        print(f"FAILED: {label}")
    else:
        print("ok")
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-contract", action="store_true",
                        help="skip the contract-test step (fast lint-only)")
    args = parser.parse_args(argv)

    gates: list[tuple[list[str], str, dict | None]] = [
        (["ruff", "check", "src", "tests/unit", "tests/contract", "scripts"],
         "ruff (CI WU-1.2 full scope)", None),
        ([sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
         "compileall", None),
        ([sys.executable, "scripts/config_doctor.py"],
         "config_doctor (CI WU-7.1)", None),
        ([sys.executable, "-m", "pytest",
          "tests/contract/test_fc1204_complexity_ratchet.py", "-q"],
         "FC-1204 complexity ratchet (CI meta-gate)", None),
    ]
    if not args.skip_contract:
        gates.append((
            [sys.executable, "-m", "pytest", "-q", "--timeout=180",
             "tests/contract/test_source_catalog_section_extractor.py",
             "tests/contract/test_fc906a_producer_binding_metadata.py",
             "tests/contract/test_legacy_observation.py",
             "tests/contract/test_zr506_section_chunk_fact.py"],
            "contract tests (extractor + binding + observation + chunk)",
            None,
        ))

    for cmd, label, env_extra in gates:
        rc = _run(cmd, label, env_extra=env_extra)
        if rc != 0:
            print(f"\nGATE RED at: {label}\nFix the root cause (see "
                  f"revenue-forecast ci_root_fix.md), do not bypass.")
            return rc
    print("\npre-push gate GREEN — safe to push (then self-monitor CI).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

raise SystemExit(7)  # negative-test marker

raise SystemExit(7)  # negative-test marker
