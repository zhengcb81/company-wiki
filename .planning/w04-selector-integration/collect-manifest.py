"""Read-only three-tree W04 receipt; writes only this task's planning directory."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

CANON = Path("C:/Users/郑曾波/Projects/company-wiki")
OLD = Path("C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
OUT = CANON / ".planning/w04-selector-integration"
BASE = "35a9a64591169bf217f05e87aba633dc4204033a"
MAIN = "d75f0d42e0fc11caa50d5030d16fa238c0e02d55"


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(root), *args])


def sha(raw: bytes | None) -> str | None:
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def normalized(raw: bytes | None) -> bytes | None:
    return raw.replace(b"\r\n", b"\n") if raw is not None else None


def tree(ref: str) -> dict[str, tuple[str, bytes]]:
    specs: dict[str, str] = {}
    for row in git(CANON, "ls-tree", "-r", "-z", ref).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            kind, oid = meta.split()[1:]
            if kind == b"blob":
                specs[path.decode("utf-8")] = oid.decode("ascii")
    return specs  # blobs read once below only for relevant paths


def read_blobs(oids: set[str]) -> dict[str, bytes]:
    ids = sorted(oids)
    raw = subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(CANON), "cat-file", "--batch"],
        input="".join(x + "\n" for x in ids).encode("ascii"),
    )
    result: dict[str, bytes] = {}
    offset = 0
    for oid in ids:
        stop = raw.index(b"\n", offset)
        parts = raw[offset:stop].split()
        assert parts[0].decode("ascii") == oid and parts[1] == b"blob"
        size = int(parts[2])
        offset = stop + 1
        result[oid] = raw[offset:offset + size]
        offset += size + 1
    return result


def working(root: Path, path: str) -> bytes | None:
    file = root / path
    return file.read_bytes() if file.is_file() else None


def integrity(root: Path) -> dict:
    raw_status = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    index = Path(git(root, "rev-parse", "--git-path", "index").decode().strip())
    if not index.is_absolute():
        index = root / index
    return {"head": head, "status_sha256": sha(raw_status),
            "status": raw_status.decode("utf-8").replace("\0", "\n"),
            "index_sha256": sha(index.read_bytes())}


initial = {"canonical": integrity(CANON), "old": integrity(OLD)}
assert initial["canonical"]["head"] == MAIN
assert initial["old"]["head"] == BASE
phase2 = json.loads((OLD / ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json").read_text("utf-8"))
semantic = json.loads((OLD / ".planning/w04-root-selector-recall/semantic-coverage-freeze.json").read_text("utf-8"))
paths = set(phase2["products"])
for key in ("files", "products", "sources", "tests", "product_files"):
    items = semantic.get(key, {})
    if isinstance(items, dict):
        paths.update(items)
    elif isinstance(items, list):
        paths.update(x if isinstance(x, str) else x["path"] for x in items)
old_status = git(OLD, "status", "--porcelain=v1", "-z", "--untracked-files=all")
for item in old_status.split(b"\0"):
    if not item:
        continue
    path = item[3:].decode("utf-8")
    if path.startswith(("src/", "tests/", "scripts/", "tools/", ".github/")):
        paths.add(path)
base = tree(BASE)
main = tree(MAIN)
blobs = read_blobs({d[p] for d in (base, main) for p in paths if p in d})
rows = []
for path in sorted(paths):
    b = blobs.get(base.get(path, ""))
    m = blobs.get(main.get(path, ""))
    t = working(OLD, path)
    c = working(CANON, path)
    bn, mn, tn = normalized(b), normalized(m), normalized(t)
    if mn == tn:
        route = "already_on_main_eol_equivalent"
    elif bn == tn:
        route = "keep_current_main_no_old_target_change"
    elif bn == mn:
        route = "accept_frozen_target_no_main_content_conflict"
    else:
        route = "both_sides_changed_requires_three_way_review"
    rows.append({
        "path": path,
        "old_base": {"git_blob": base.get(path), "sha256": sha(b), "bytes": len(b) if b is not None else None},
        "current_main": {"git_blob": main.get(path), "sha256": sha(m), "bytes": len(m) if m is not None else None},
        "pending_worktree": {"sha256": sha(t), "bytes": len(t) if t is not None else None},
        "canonical_working_sha256": sha(c),
        "canonical_working_eol_equivalent_to_main": normalized(c) == mn,
        "normalized_lf_sha256": {"old_base": sha(bn), "current_main": sha(mn), "pending": sha(tn)},
        "main_changed_from_base": bn != mn,
        "pending_changed_from_base": bn != tn,
        "receipt_recommendation": route,
        "phase2_frozen_product": path in phase2["products"],
        "phase2_freeze_matches": sha(t) == phase2["products"].get(path, {}).get("sha256") if path in phase2["products"] else None,
    })
final = {"canonical": integrity(CANON), "old": integrity(OLD)}
assert initial == final, "Git HEAD/index/status changed during read-only snapshot"
snapshot = {"schema_version": "w04-selector-three-tree-snapshot/1", "old_tree": str(OLD),
            "canonical_tree": str(CANON), "old_base": BASE, "current_main": MAIN,
            "scope": "read-only source/test blob inspection; no product tests or six originals",
            "semantic_freeze": semantic, "phase2_freeze_sha256": sha((OLD / ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json").read_bytes()),
            "rows": rows, "integrity_before": initial, "integrity_after": final,
            "git_products_config_raw_mutations": 0, "provider_network_llm_calls": 0}
(OUT / "three-tree-snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"rows": len(rows), "routes": {x: sum(r["receipt_recommendation"] == x for r in rows) for x in sorted({r["receipt_recommendation"] for r in rows})}, "phase2_freeze_matches": all(r["phase2_freeze_matches"] for r in rows if r["phase2_frozen_product"]), "integrity_unchanged": initial == final}, ensure_ascii=False))
