"""V5 evidence tool: scan every version reference in the v5 baseline.

Reproduces v5-version-reference-inventory.{json,md}. Scope = baseline/** (54
files) + the v5 root planning documents present at scan time; v5-owned metadata
(reviews/, tools/, import manifest, verify_import.py, this tool, the contract
and the review records) is excluded.

Modes:
  (default)  write the two evidence files
  --check    read-only: exit 1 if either on-disk evidence file differs
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

V5 = Path(__file__).resolve().parents[1]
OLD_DIR = "source-catalog-worker-recovery-2026-08-22"
FILENAME_VERSION = re.compile(r"\.v([345])\.")
DIR_REF = re.compile(re.escape(OLD_DIR))
CHECKER_REF = re.compile(r"plan_consistency_check\.py")
CLI_REF = re.compile(r"python\s+[^\s`\"']+\.py")
EXCLUDE = {
    "import_manifest.v5.json",
    "verify_import.py",
    "v5-version-reference-inventory.json",
    "v5-version-reference-inventory.md",
    "v5-baseline-equivalence.json",
    "v5-version-contract.md",
}
EXCLUDE_PREFIX = "v5-version-contract-review"  # review records grow per round


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def scan(path: Path) -> dict:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
    version_hits: dict[str, int] = {}
    for m in re.finditer(r"\bv([345])\b", text):
        version_hits[f"v{m.group(1)}"] = version_hits.get(f"v{m.group(1)}", 0) + 1
    return {
        "sha256": sha(raw),
        "size_bytes": len(raw),
        "version_tokens": version_hits,
        "id_values": sorted(set(re.findall(r'"\$id"\s*:\s*"([^"]+)"', text)))[:6],
        "plan_revision_values": sorted(set(re.findall(r'"plan_revision"\s*:\s*"([^"]+)"', text))),
        "schema_version_values": sorted(set(re.findall(r'"schema_version"\s*:\s*(\d+)', text))),
        "old_dir_refs": len(DIR_REF.findall(text)),
        "checker_refs": len(CHECKER_REF.findall(text)),
        "cli_commands": sorted(set(CLI_REF.findall(text)))[:4],
        "filename_version": (FILENAME_VERSION.search(path.name).group(1)
                             if FILENAME_VERSION.search(path.name) else None),
    }


def build() -> tuple[dict, dict[str, str]]:
    files: dict[str, dict] = {}
    for p in sorted(V5.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(V5).as_posix()
        if (rel.startswith(("reviews/", "tools/"))
                or rel in EXCLUDE
                or rel.startswith(EXCLUDE_PREFIX)):
            continue
        files[rel] = scan(p)

    baseline = [r for r in files if r.startswith("baseline/")]
    root = [r for r in files if not r.startswith("baseline/")]
    ids = sorted({i for v in files.values() for i in v["id_values"]})
    suffixes: dict[str, int] = {}
    for i in ids:
        suffix = i.rsplit(":", 1)[-1]
        suffixes[suffix] = suffixes.get(suffix, 0) + 1
    totals = {
        "files_scanned": len(files),
        "baseline_files": len(baseline),
        "v5_root_files": len(root),
        "files_with_v4": sum(1 for v in files.values() if "v4" in v["version_tokens"]),
        "files_with_v3": sum(1 for v in files.values() if "v3" in v["version_tokens"]),
        "files_referencing_old_dir": sum(1 for v in files.values() if v["old_dir_refs"]),
        "files_referencing_old_checker": sum(1 for v in files.values() if v["checker_refs"]),
        "distinct_ids": ids,
        "id_suffix_counts": dict(sorted(suffixes.items())),
        "plan_revision_values": sorted({p for v in files.values() for p in v["plan_revision_values"]}),
        "schema_version_values": sorted({s for v in files.values() for s in v["schema_version_values"]}),
    }
    json_payload = json.dumps(
        {"generated_at_utc": "2026-09-09",
         "scope": "baseline/** + v5 root planning docs "
                  "(excl. reviews/, tools/, import manifest, verify_import.py)",
         "totals": totals, "files": files},
        ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    lines = [
        "# V5 版本引用枚举（V5-1 第 2 项）",
        "",
        "日期：2026-09-09。状态：PLAN_ONLY。范围：`baseline/**`（54 份）＋ v5 根目录规划文档（5 份）＝ **59 份**；"
        "排除 `reviews/`、`tools/`、`import_manifest.v5.json`、`verify_import.py` 与 v5 自有元数据。",
        "机器明细见 [v5-version-reference-inventory.json](v5-version-reference-inventory.json)；"
        "可用 [tools/v5_version_reference_scan.py](tools/v5_version_reference_scan.py) 复现"
        "（`--check` 为只读校验）。",
        "",
        "## 汇总",
        "",
        f"- 扫描文件：**{totals['files_scanned']}**（baseline {totals['baseline_files']} + 根 {totals['v5_root_files']}）",
        f"- 含 `v4` token：**{totals['files_with_v4']}**；含 `v3`：**{totals['files_with_v3']}**",
        f"- 引用已退役旧目录 `{OLD_DIR}`：**{totals['files_referencing_old_dir']}**",
        f"- 引用旧 checker `plan_consistency_check.py`：**{totals['files_referencing_old_checker']}**",
        f"- `$id` 总数：**{len(totals['distinct_ids'])}**；后缀分布："
        + "、".join(f"`:{k}`={v}" for k, v in totals["id_suffix_counts"].items()),
        f"- `plan_revision`：{totals['plan_revision_values']}；`schema_version`：{totals['schema_version_values']}",
        "",
        "## 需要版本合同裁决的引用面",
        "",
        "| 类别 | 现状 | 影响 |",
        "|---|---|---|",
        "| 冻结 manifest 常量 | `plan_revision: \"v4\"`、`plan_directory: 旧目录`、`investigation_source.path` 旧路径、`pre_freeze_check.command` 旧目录 checker | 照抄会指向已退役目录；由合同 §5 的 v5 schema 定义新取值 |",
        "| schema `$id` | 29 个，后缀 `:v4`=14、`:v1`=12、`:v5`=2、`:v2`=1 | 新 manifest schema 必须自带 `:v5` 且不与既有 `:v5` 撞名 |",
        "| 文件名内嵌版本 | `gate_dag.v4.json`、`operation_contracts.v4.json`、`test_id_registry.v4.json`、`gate_ledger_validator_vectors.v4.json`、`plan_freeze_check.v4.txt` | 命名即版本声明；合同裁定**不改名**（协议线标识） |",
        "| 正文/命令引用旧目录 | 见上表计数 | 合同 §6 给出取代映射；旧引用只作历史 |",
        "| 机器实例内版本字段 | 4 个 `.v4.json` 实例的内部 `$id`/`schema_version` | 只改 manifest 不改实例即构成混合版本，由 N3/N7 拒绝 |",
        "",
        "## 明细（按旧目录引用数降序，前 20）",
        "",
        "| 文件 | v4 | v3 | 旧目录引用 | checker 引用 | plan_revision |",
        "|---|---|---|---|---|---|",
    ]
    for rel, v in sorted(files.items(), key=lambda kv: -kv[1]["old_dir_refs"])[:20]:
        lines.append(
            f"| `{rel}` | {v['version_tokens'].get('v4', 0)} | {v['version_tokens'].get('v3', 0)} | "
            f"{v['old_dir_refs']} | {v['checker_refs']} | {','.join(v['plan_revision_values']) or '-'} |")
    return totals, {
        "v5-version-reference-inventory.json": json_payload,
        "v5-version-reference-inventory.md": "\n".join(lines) + "\n",
    }


def main() -> int:
    totals, payloads = build()
    check = "--check" in sys.argv
    bad = []
    for name, payload in payloads.items():
        path = V5 / name
        if check:
            # Byte-strict: EOL drift must fail (v4 incident class), so compare
            # bytes rather than text-mode reads.
            actual = path.read_bytes() if path.is_file() else b""
            if actual != payload.encode("utf-8"):
                bad.append(name)
        else:
            path.write_text(payload, encoding="utf-8", newline="\n")
    if check:
        if bad:
            print(f"CHECK FAIL: {bad} differ from the recomputation", file=sys.stderr)
            return 1
        print("CHECK OK: inventory .json and .md reproduce byte-for-byte")
        return 0
    print(json.dumps(totals, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
