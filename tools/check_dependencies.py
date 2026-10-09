"""Fast declaration parity, independent of the packages on the developer's host."""
from __future__ import annotations

import argparse
from pathlib import Path
try:
    import tomllib
except ImportError:  # Python 3.10, supported by the project/test install.
    import tomli as tomllib


def missing_dependencies(root: Path) -> list[str]:
    declared = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    required = {line.split("#", 1)[0].replace(" ", "").lower()
                for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")}
    return [item for item in declared["project"]["dependencies"]
            if item.replace(" ", "").lower() not in required]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    missing = missing_dependencies(parser.parse_args().root)
    if missing:
        print(f"CI requirements omit declared direct runtime dependencies: {missing}")
        return 1
    print("Runtime dependency declarations match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
