"""V5 evidence tool: classify imported plan inputs against their v4 frozen hash.

Reproduces v5-baseline-equivalence.json. Enum matches the version contract:
  v4_exact               current bytes == v4 freeze
  crlf_only              LF-normalized current bytes == v4 freeze
  unproven_new_baseline  neither (new baseline; review from zero)

Modes:
  (default)  write the evidence file
  --check    read-only: exit 1 if the on-disk evidence file differs
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

V5 = Path(__file__).resolve().parents[1]
MANIFEST = V5 / "import_manifest.v5.json"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def resolve(target: str) -> Path | None:
    cand = Path(target)
    for p in (V5 / cand, V5 / "baseline" / "plan" / cand.name, V5 / "baseline" / cand):
        if p.is_file():
            return p
    return None


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups: dict[str, list[str]] = {
        "v4_exact": [], "crlf_only": [], "unproven_new_baseline": [], "unresolved": [],
    }
    for f in man["files"]:
        if f.get("role") != "prior_plan_current_content":
            continue
        p = resolve(f["target"])
        if p is None:
            groups["unresolved"].append(f["target"])
            continue
        raw = p.read_bytes()
        hist = (f.get("historical_v4_sha256") or "").lower()
        if not hist:
            groups["unproven_new_baseline"].append(f["target"])
        elif sha(raw) == hist:
            groups["v4_exact"].append(f["target"])
        elif sha(raw.replace(b"\r\n", b"\n")) == hist:
            groups["crlf_only"].append(f["target"])
        else:
            groups["unproven_new_baseline"].append(f["target"])
    out = {
        "generated_at_utc": "2026-09-09",
        "method": "compare imported baseline bytes against import_manifest.v5.json "
                  "historical_v4_sha256; crlf_only means sha256(LF-normalized bytes) "
                  "equals the v4 frozen hash",
        "counts": {k: len(v) for k, v in groups.items()},
        "groups": {k: sorted(v) for k, v in groups.items()},
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = V5 / "v5-baseline-equivalence.json"
    if "--check" in sys.argv:
        # Byte-strict comparison: a CRLF/LF drift must fail (the v4 incident
        # was exactly an EOL-drift class), so never use text-mode reads here.
        actual = target.read_bytes() if target.is_file() else b""
        if actual != payload.encode("utf-8"):
            print(f"CHECK FAIL: {target.name} differs from the recomputation", file=sys.stderr)
            return 1
        print(f"CHECK OK: {target.name} reproduces byte-for-byte")
        return 0
    target.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps(out["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
