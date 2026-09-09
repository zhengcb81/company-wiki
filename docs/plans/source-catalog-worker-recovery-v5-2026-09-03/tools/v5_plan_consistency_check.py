"""V5 pre-freeze / post-freeze consistency checker (read-only).

Reuses the imported baseline checker (`baseline/plan/plan_consistency_check.py`)
for the schema / gate-DAG / test-registry / validator-vector / prose suite, then
adds the v5 version-contract checks: frozen-set composition, boundary protocol
B1-B6, evidence reproduction, the v5 manifest schema, and the negative cases
N1-N17 of `v5-version-contract.md` §7 as machine checks with stable codes.

Modes:
  (default)          pre-freeze: baseline suite + frozen set + boundary +
                     evidence reproduction; stdout is the capturable artifact
  --verify-manifest  additionally validate plan_manifest.v5.json (N1-N17)
  --self-test        mutate a temporary copy of the frozen tree once per
                     negative case and assert the corresponding code rejects

Read-only: performs no writes, opens no production database/registry/process,
makes no network request. Loading the baseline module sets
`sys.dont_write_bytecode` so no `__pycache__` can appear inside the frozen set.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Loading the baseline module must not write baseline/plan/__pycache__ into the
# frozen directory (that would mutate the frozen set during verification).
sys.dont_write_bytecode = True
try:  # deterministic LF stdout: the captured artifact must contain no CR
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
except (AttributeError, ValueError):  # pragma: no cover
    pass

V5 = Path(__file__).resolve().parents[1]
GOVERNING = ("plan_manifest.schema.v5.json", "tools/v5_plan_consistency_check.py", ".gitattributes")
EVIDENCE_TOOLS = ("tools/v5_version_reference_scan.py", "tools/v5_equivalence_check.py")
ATTRS = ("text", "eol", "filter", "working-tree-encoding")
EXPECTED_IMPORTED = 48
EXPECTED_GOVERNING = 3
EXPECTED_TOTAL = 51


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Ctx:
    """All paths a check may touch, so the self-test can point them at a copy."""

    root: Path
    baseline: Path
    manifest: Path
    schema: Path
    freeze_output: Path
    import_manifest: Path
    boundary_record: Path
    old_dir: Path
    governing: tuple[str, ...]
    evidence_tools: tuple[str, ...]
    external: bool = True


REAL = Ctx(
    root=V5,
    baseline=V5 / "baseline" / "plan",
    manifest=V5 / "plan_manifest.v5.json",
    schema=V5 / "plan_manifest.schema.v5.json",
    freeze_output=V5 / "plan_freeze_check.v5.txt",
    import_manifest=V5 / "import_manifest.v5.json",
    boundary_record=V5 / "v5-freeze-boundary.md",
    old_dir=V5.parent / "source-catalog-worker-recovery-2026-08-22",
    governing=GOVERNING,
    evidence_tools=EVIDENCE_TOOLS,
)


def load_baseline():
    spec = importlib.util.spec_from_file_location(
        "v4_plan_check", REAL.baseline / "plan_consistency_check.py")
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError("cannot load the baseline checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_entries(ctx: Ctx) -> list[tuple[str, Path]]:
    imported = sorted(p for p in ctx.baseline.glob("*") if p.is_file())
    entries = [("baseline/plan/" + p.name, p) for p in imported]
    entries += [(rel, ctx.root / rel) for rel in ctx.governing]
    return entries


def snapshot(entries) -> dict[str, tuple[str, int]]:
    return {rel: (sha(p.read_bytes()), p.stat().st_size) for rel, p in entries}


def report(base) -> int:
    if base.ERRORS:
        print(f"FAIL: {len(base.ERRORS)} error(s) after {base.CHECKS} checks")
        for error in base.ERRORS[:80]:
            print(f"- {error}")
        return 1
    counts = {
        "fixed_nodes": len(base.load_json("gate_dag.v4.json")["nodes"]),
        "tests": len(base.load_json("test_id_registry.v4.json")["tests"]),
        "vectors": len(base.load_json("gate_ledger_validator_vectors.v4.json")["vectors"]),
        "schemas": len(base.SCHEMA_FILES),
    }
    print(f"PASS: {base.CHECKS} checks; {json.dumps(counts, sort_keys=True)}")
    print("READ_ONLY: no production database, registry, process, source, config, or network access")
    return 0


def baseline_suite(base, ctx: Ctx) -> None:
    base.schema_checks()
    nodes, fixed_ids = base.dag_checks()
    base.operation_checks(nodes)
    base.registry_checks(fixed_ids)
    base.vector_checks()
    base.catalog_pointer_checks()
    base.active_prose_semantic_checks()
    base.pre_freeze_output_checks()
    # The baseline keeps plan_manifest.v3.json at its own ROOT; the v5 import
    # stores history under baseline/history/, so the same hash pin is applied
    # with layout-aware resolution (byte-identical expectation, v3 sha verified).
    history = ctx.root / "baseline" / "history"
    for name, expected in base.IMMUTABLE_HISTORY_SHA256.items():
        found = next((c for c in (ctx.baseline / name, history / name) if c.is_file()), None)
        base.check(found is not None and sha(found.read_bytes()) == expected,
                   "IMMUTABLE-HISTORY",
                   f"{name}: expected {expected}, got "
                   f"{sha(found.read_bytes()) if found else 'MISSING'}")


def v5_checks(base, ctx: Ctx, entries, before) -> None:
    """Frozen-set composition, boundary protocol and evidence reproduction."""
    imported_count = sum(1 for rel, _ in entries if rel.startswith("baseline/plan/"))
    base.check(imported_count == EXPECTED_IMPORTED, "V5-SET-IMPORTED",
               f"expected {EXPECTED_IMPORTED} imported plan inputs, found {imported_count}")
    base.check(len(ctx.governing) == EXPECTED_GOVERNING, "V5-SET-GOVERNING",
               f"expected {EXPECTED_GOVERNING} v5-own governing artifacts")
    base.check(len(entries) == EXPECTED_TOTAL, "V5-SET-TOTAL",
               f"expected {EXPECTED_TOTAL} frozen entries, found {len(entries)}")
    for rel, path in entries:
        base.check(path.is_file(), "V5-SET-PRESENT", f"missing frozen file: {rel}")

    # N9 (boundary arm): a revived retired directory needs an explicit disposition.
    if ctx.old_dir.is_dir():
        base.check(ctx.boundary_record.is_file(), "N9-DISPOSITION",
                   "retired directory exists but v5-freeze-boundary.md is missing")
        for rel, path in entries:
            base.check(ctx.old_dir not in path.parents, "N9-PARALLEL",
                       f"frozen entry resolves inside the retired directory: {rel}")

    # N14 (boundary arm): .gitattributes in the set and attribute-free on disk.
    base.check((ctx.root / ".gitattributes").is_file(), "V5-ATTRS-PRESENT",
               ".gitattributes missing from the v5 directory")
    if ctx.external:
        proc = subprocess.run(
            ["git", "check-attr", *ATTRS, "--", *[str(p) for _, p in entries]],
            cwd=str(ctx.root), capture_output=True, text=True, encoding="utf-8",
            errors="replace",
        )
        lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
        base.check(len(lines) == len(ATTRS) * len(entries)
                   and all(line.endswith(": unset") for line in lines), "V5-ATTRS-UNSET",
                   f"git check-attr returned {len(lines)} lines; expected "
                   f"{len(ATTRS) * len(entries)} 'unset' lines")

        for rel in ctx.evidence_tools:
            tool = ctx.root / rel
            base.check(tool.is_file(), "V5-EVIDENCE", f"missing evidence tool: {rel}")
            if tool.is_file():
                run = subprocess.run([sys.executable, str(tool), "--check"],
                                     capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=600)
                base.check(run.returncode == 0, "V5-EVIDENCE-CHECK",
                           f"{rel} --check failed: {(run.stdout or run.stderr)[-200:]}")

    # B3: no byte drift while the suite ran.
    after = snapshot(entries)
    for rel in before:
        base.check(before.get(rel) == after.get(rel), "B3-BOUNDARY-DRIFT",
                   f"frozen file changed during the run: {rel}")
    base.check(not (ctx.baseline / "__pycache__").exists(), "B3-BOUNDARY-DRIFT",
               "verification left baseline/plan/__pycache__ behind")


def verify_manifest(base, ctx: Ctx, entries) -> None:
    """N1-N17 of v5-version-contract.md §7, one stable code per negative case."""
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:  # pragma: no cover
        base.check(False, "N4", f"jsonschema unavailable: {exc}")
        return

    # N1: the superseded v4 manifest must not be active in this directory.
    base.check(not (ctx.root / "plan_manifest.v4.json").exists(), "N1",
               "plan_manifest.v4.json must not exist as an active manifest")
    if not ctx.manifest.is_file():
        base.check(False, "N4", "plan_manifest.v5.json missing")
        return
    manifest = json.loads(ctx.manifest.read_text(encoding="utf-8"))
    schema = json.loads(ctx.schema.read_text(encoding="utf-8"))
    declared = {entry["path"]: entry for entry in manifest.get("normative_files", [])}
    expected = {rel for rel, _ in entries}

    # N2: no axis may point at the retired directory.
    base.check(manifest.get("plan_directory") !=
               "docs/plans/source-catalog-worker-recovery-2026-08-22"
               and "2026-08-22" not in str(manifest.get("pre_freeze_check", {}).get("command", "")),
               "N2", "plan_directory/pre_freeze_check.command must not point at the retired directory")

    # N3: the two axes must not be mixed.
    base.check(manifest.get("protocol_revision") == "v4"
               and manifest.get("freeze_generation") == "v5", "N3",
               "axis mixing: protocol_revision must stay v4 while freeze_generation is v5")

    # N4: schema conformance (unknown fields, missing fields, wrong const).
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest))
    base.check(not errors, "N4", "; ".join(error.message for error in errors[:5]))

    # N5 / N7 / N13: membership, per-entry hashes, imported-artifact integrity.
    base.check(set(declared) == expected, "N13",
               f"missing={sorted(expected - set(declared))} extra={sorted(set(declared) - expected)}")
    base.check(len(declared) == len(manifest.get("normative_files", [])), "N13",
               "duplicate path in normative_files")
    folded = [rel.casefold() for rel in declared]
    base.check(len(set(folded)) == len(folded), "N13", "casefold collision in normative_files")
    base.check(manifest.get("normative_file_count") == len(declared)
               == manifest.get("frozen_set_composition", {}).get("total"), "N13",
               "normative_file_count / len(normative_files) / composition.total disagree")
    coverage = manifest.get("coverage_counts", {})
    base.check(coverage == base.current_coverage_counts(base.dag_checks()[1]), "N13",
               f"coverage_counts do not match the frozen corpus: {coverage}")
    capture = json.loads(ctx.import_manifest.read_text(encoding="utf-8"))
    captured = {entry["target"]: entry for entry in capture.get("files", [])
                if entry.get("role") == "prior_plan_current_content"}
    frozen_imported = {rel for rel, _ in entries if rel.startswith("baseline/plan/")}
    base.check(set(captured) == frozen_imported, "N7",
               f"imported set != capture record: missing="
               f"{sorted(frozen_imported - set(captured))} extra={sorted(set(captured) - frozen_imported)}")
    counted = {"v4_exact": 0, "crlf_only": 0, "unproven_new_baseline": 0, "v5_own": 0}
    for rel, path in entries:
        entry = declared.get(rel)
        if entry is None:
            continue
        raw = path.read_bytes()
        base.check(entry.get("sha256") == sha(raw) and entry.get("size_bytes") == len(raw),
                   "N5", f"hash/size mismatch: {rel}")
        label = entry.get("equivalence")
        counted[label] = counted.get(label, 0) + 1
        if label in {"v4_exact", "crlf_only", "unproven_new_baseline"}:
            base.check(rel.startswith("baseline/plan/") and ".v5." not in Path(rel).name,
                       "N7", f"imported artifact renamed or relocated: {rel}")
            original = captured.get(rel)
            base.check(original is not None and original.get("sha256") == sha(raw),
                       "N7", f"imported artifact bytes differ from the capture record: {rel}")
    summary = manifest.get("equivalence_summary", {})
    base.check(all(summary.get(key) == counted[key]
                   for key in ("v4_exact", "crlf_only", "unproven_new_baseline")), "N6",
               f"equivalence_summary {summary} != recomputed {counted}")

    # N8: the recorded pre-freeze output must be this checker's own output.
    pre = manifest.get("pre_freeze_check", {})
    command = str(pre.get("command", ""))
    base.check("v5_plan_consistency_check.py" in command and "2026-08-22" not in command, "N8",
               f"pre_freeze_check.command must invoke the v5 checker: {command!r}")
    if ctx.freeze_output.is_file():
        payload = ctx.freeze_output.read_bytes()
        text = payload.decode("utf-8", errors="replace")
        match = re.match(r"PASS: ([0-9]+) checks; ", text)
        base.check(pre.get("stdout_sha256") == sha(payload)
                   and match is not None
                   and pre.get("reported_check_count") == int(match.group(1)), "N8",
                   "pre_freeze_check does not bind plan_freeze_check.v5.txt bytes and count")
    else:
        base.check(False, "N8", "plan_freeze_check.v5.txt missing")

    # N9: the retired directory must not act as a parallel authority.
    if ctx.old_dir.is_dir():
        base.check(ctx.boundary_record.is_file(), "N9",
                   "retired directory exists without an explicit disposition record")
        for rel, path in entries:
            base.check(ctx.old_dir not in path.parents, "N9",
                       f"frozen entry resolves inside the retired directory: {rel}")

    # N10: self-exclusion and no post-freeze rewrite of a tracked manifest.
    base.check(manifest.get("self_exclusion") == "plan_manifest.v5.json"
               and "plan_manifest.v5.json" not in declared, "N10",
               "the manifest must exclude itself from normative_files")
    if ctx.external:
        repo = subprocess.run(["git", "-C", str(ctx.root), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if repo.returncode == 0 and repo.stdout.strip():
            repo_root = Path(repo.stdout.strip())
            try:
                rel = ctx.manifest.relative_to(repo_root).as_posix()
            except ValueError:
                rel = ""
            if rel:
                tracked = subprocess.run(["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel],
                                         capture_output=True, text=True, encoding="utf-8",
                                         errors="replace")
                if tracked.returncode == 0:
                    head = subprocess.run(["git", "-C", str(repo_root), "rev-parse", f"HEAD:{rel}"],
                                          capture_output=True, text=True, encoding="utf-8",
                                          errors="replace").stdout.strip()
                    blob = subprocess.run(["git", "-C", str(repo_root), "hash-object", rel],
                                          capture_output=True, text=True, encoding="utf-8",
                                          errors="replace").stdout.strip()
                    base.check(bool(head) and head == blob, "N10",
                               f"tracked manifest was rewritten after freeze: {head} != {blob}")

    # N11: supersession chain must name the v4 and v3 manifests with matching bytes.
    superseded = {entry.get("path"): entry.get("sha256")
                  for entry in manifest.get("supersedes", [])}
    for name in ("plan_manifest.v4.json", "plan_manifest.v3.json"):
        matches = [key for key in superseded if str(key).endswith(name)]
        base.check(bool(matches), "N11", f"supersedes must name {name}")
        for key in matches:
            path = ctx.root / str(key)
            if not path.is_file():
                path = ctx.root / "baseline" / "history" / name
            base.check(path.is_file() and superseded[key] == sha(path.read_bytes()), "N11",
                       f"supersedes hash mismatch for {key}")

    # N12: the investigation source lives inside the v5 directory.
    investigation = manifest.get("investigation_source", {})
    path = ctx.root / str(investigation.get("path", ""))
    base.check(investigation.get("path") == "baseline/investigation/worker-investigation-2026-08-20.md"
               and path.is_file() and sha(path.read_bytes()) == investigation.get("sha256"), "N12",
               "investigation_source path/hash mismatch")

    # N14: .gitattributes is frozen.
    base.check(".gitattributes" in declared, "N14", ".gitattributes not in the frozen set")

    # N15: the generation axes must match the capture manifest.
    base.check(manifest.get("freeze_generation") == capture.get("capture_generation")
               and manifest.get("protocol_revision") == capture.get("source_protocol_revision"), "N15",
               "freeze_generation/protocol_revision mismatch with the capture manifest")
    base.check(manifest.get("capture_manifest", {}).get("sha256") == sha(ctx.import_manifest.read_bytes()),
               "N15", "capture_manifest.sha256 != import_manifest.v5.json bytes")

    # N16: the schema and the checker are hash-bound v5_own entries.
    for rel in ctx.governing:
        entry = declared.get(rel)
        base.check(entry is not None and entry.get("equivalence") == "v5_own", "N16",
                   f"governing artifact not bound as v5_own: {rel}")

    # N17: evidence tools are present and hash-bound.
    tools = {entry.get("path"): entry for entry in manifest.get("evidence_tools", [])}
    for rel in ctx.evidence_tools:
        entry = tools.get(rel)
        path = ctx.root / rel
        base.check(entry is not None and path.is_file()
                   and entry.get("sha256") == sha(path.read_bytes()), "N17",
                   f"evidence tool not hash-bound: {rel}")


# --- self-test: one mutation per negative case ------------------------------

def _n1(ctx: Ctx, manifest: dict) -> None:
    (ctx.root / "plan_manifest.v4.json").write_text("{}\n", encoding="utf-8")


def _n2(ctx: Ctx, manifest: dict) -> None:
    manifest["plan_directory"] = "docs/plans/source-catalog-worker-recovery-2026-08-22"


def _n3(ctx: Ctx, manifest: dict) -> None:
    manifest["freeze_generation"] = "v6"


def _n4(ctx: Ctx, manifest: dict) -> None:
    manifest["unknown_field"] = 1


def _n5(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"][0]["sha256"] = "0" * 64


def _n6(ctx: Ctx, manifest: dict) -> None:
    target = next(entry for entry in manifest["normative_files"]
                  if entry["equivalence"] == "v4_exact")
    target["equivalence"] = "crlf_only"


def _n7(ctx: Ctx, manifest: dict) -> None:
    target = next(entry for entry in manifest["normative_files"]
                  if entry["path"].startswith("baseline/plan/"))
    (ctx.baseline / Path(target["path"]).name).write_bytes(b"tampered\n")


def _n8(ctx: Ctx, manifest: dict) -> None:
    ctx.freeze_output.write_text("PASS: 1 checks; {}\n", encoding="utf-8", newline="\n")


def _n9(ctx: Ctx, manifest: dict) -> None:
    ctx.old_dir.mkdir(parents=True, exist_ok=True)
    (ctx.old_dir / "task_plan.md").write_text("revived\n", encoding="utf-8")
    ctx.boundary_record.unlink()


def _n10(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"].append({"path": "plan_manifest.v5.json", "sha256": "0" * 64,
                                        "size_bytes": 1, "equivalence": "v5_own"})


def _n11(ctx: Ctx, manifest: dict) -> None:
    manifest["supersedes"] = [{"path": "baseline/history/plan_manifest.v2.json", "sha256": "0" * 64}]


def _n12(ctx: Ctx, manifest: dict) -> None:
    manifest["investigation_source"] = {
        "path": "docs/plans/source-catalog-worker-recovery-2026-08-22/task_plan.md",
        "sha256": "0" * 64}


def _n13(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"] = manifest["normative_files"][:-1]
    manifest["normative_file_count"] = len(manifest["normative_files"])


def _n14(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"] = [entry for entry in manifest["normative_files"]
                                   if entry["path"] != ".gitattributes"]


def _n15(ctx: Ctx, manifest: dict) -> None:
    capture = json.loads(ctx.import_manifest.read_text(encoding="utf-8"))
    capture["capture_generation"] = "v6"
    ctx.import_manifest.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")


def _n16(ctx: Ctx, manifest: dict) -> None:
    for entry in manifest["normative_files"]:
        if entry["path"] == "plan_manifest.schema.v5.json":
            entry["equivalence"] = "v4_exact"


def _n17(ctx: Ctx, manifest: dict) -> None:
    manifest["evidence_tools"][0]["sha256"] = "0" * 64


N_CASES = (
    ("N1", "把 plan_manifest.v4.json 当作当前活动 manifest", _n1),
    ("N2", "plan_directory/pre_freeze_check.command 指向已退役旧目录", _n2),
    ("N3", "版本轴混用", _n3),
    ("N4", "schema_version/未知字段/缺必填字段", _n4),
    ("N5", "normative sha256/size 与冻结记录不符", _n5),
    ("N6", "equivalence 类别与复算不符", _n6),
    ("N7", "导入 artifact 被改名/改字节/改 $id", _n7),
    ("N8", "用旧 checker 输出冒充 v5 预冻结检查", _n8),
    ("N9", "旧目录复活且无显式处置", _n9),
    ("N10", "manifest 自身进入 normative 集", _n10),
    ("N11", "取代链不指向 v4/v3 manifest", _n11),
    ("N12", "investigation_source 不在 v5 目录内", _n12),
    ("N13", "normative 集缺项/计数不符", _n13),
    ("N14", ".gitattributes 不在冻结集内", _n14),
    ("N15", "generation 与 capture manifest 不符", _n15),
    ("N16", "v5 治理件未绑定为 v5_own", _n16),
    ("N17", "evidence_tools 哈希不符", _n17),
)


def self_test(base) -> int:
    if not REAL.manifest.is_file():
        print("SELF-TEST SKIP: plan_manifest.v5.json missing (freeze first)")
        return 1
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for code, label, mutate in N_CASES:
            root = Path(tmp) / "v5"
            if root.exists():
                shutil.rmtree(root)
            shutil.copytree(REAL.root / "baseline", root / "baseline")
            shutil.copytree(REAL.root / "tools", root / "tools")
            for name in (".gitattributes", "plan_manifest.v5.json", "plan_manifest.schema.v5.json",
                         "plan_freeze_check.v5.txt", "import_manifest.v5.json",
                         "v5-freeze-boundary.md"):
                source = REAL.root / name
                if source.is_file():
                    (root / name).write_bytes(source.read_bytes())
            ctx = Ctx(
                root=root, baseline=root / "baseline" / "plan",
                manifest=root / "plan_manifest.v5.json",
                schema=root / "plan_manifest.schema.v5.json",
                freeze_output=root / "plan_freeze_check.v5.txt",
                import_manifest=root / "import_manifest.v5.json",
                boundary_record=root / "v5-freeze-boundary.md",
                old_dir=Path(tmp) / "source-catalog-worker-recovery-2026-08-22",
                governing=GOVERNING, evidence_tools=EVIDENCE_TOOLS, external=False,
            )
            manifest = json.loads(ctx.manifest.read_text(encoding="utf-8"))
            mutate(ctx, manifest)
            ctx.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
            saved = (base.ERRORS, base.CHECKS)
            base.ERRORS, base.CHECKS = [], 0
            try:
                verify_manifest(base, ctx, frozen_entries(ctx))
                codes = {error.split(":", 1)[0] for error in base.ERRORS}
            finally:
                base.ERRORS, base.CHECKS = saved
            if code in codes:
                print(f"SELF-TEST {code} PASS: rejected - {label}")
            else:
                failures.append(code)
                print(f"SELF-TEST {code} FAIL: not rejected - {label}; codes={sorted(codes)}")
    print(f"SELF-TEST: {len(N_CASES) - len(failures)}/{len(N_CASES)} negative cases rejected")
    return 1 if failures else 0


def main() -> int:
    base = load_baseline()
    if "--self-test" in sys.argv:
        return self_test(base)

    ctx = REAL
    entries = frozen_entries(ctx)
    before = snapshot(entries)
    baseline_suite(base, ctx)
    v5_checks(base, ctx, entries, before)
    if "--verify-manifest" in sys.argv:
        verify_manifest(base, ctx, entries)
    return report(base)


if __name__ == "__main__":
    raise SystemExit(main())
