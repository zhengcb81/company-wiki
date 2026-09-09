"""V5 pre-freeze / post-freeze consistency checker (read-only).

Reuses the imported baseline checker (`baseline/plan/plan_consistency_check.py`)
for the schema / gate-DAG / test-registry / validator-vector / prose suite, then
adds the v5 version-contract checks: frozen-set composition, boundary protocol
B1-B6, path safety, evidence reproduction, the v5 manifest schema, and the
negative cases N1-N17 of `v5-version-contract.md` §7 as machine checks with
stable codes.

Modes:
  (default)          pre-freeze: baseline suite + frozen set + path safety +
                     evidence reproduction; stdout is the capturable artifact
  --verify-manifest  additionally validate plan_manifest.v5.json (N1-N17)
  --self-test        mutate a temporary copy once per negative case and assert
                     the corresponding code rejects BOTH with all checks enabled
                     and with that single code enabled (isolation)

Read-only when executed as a script: performs no writes, opens no production
database/registry/process, makes no network request. Loading this module as a
library can still make CPython write `tools/__pycache__` for the checker itself
before this module's body runs, so import callers must set
`sys.dont_write_bytecode = True` first; the frozen set and the evidence scope
exclude `__pycache__` either way.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True
try:  # deterministic LF/UTF-8 stdout: the captured artifact must contain no CR
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
except (AttributeError, ValueError):  # pragma: no cover
    pass

V5 = Path(__file__).resolve().parents[1]
GOVERNING = ("plan_manifest.schema.v5.json", "tools/v5_plan_consistency_check.py", ".gitattributes")
EVIDENCE_TOOLS = ("tools/v5_version_reference_scan.py", "tools/v5_equivalence_check.py")
EVIDENCE_FILES = ("v5-version-reference-inventory.json", "v5-baseline-equivalence.json")
ATTRS = ("text", "eol", "filter", "working-tree-encoding")
EXPECTED_IMPORTED = 48
EXPECTED_GOVERNING = 3
EXPECTED_TOTAL = 51
CHECKER_REL = "tools/v5_plan_consistency_check.py"
EXPECTED_COMMAND = ("python docs/plans/source-catalog-worker-recovery-v5-2026-09-03/"
                    + CHECKER_REL)
EXPECTED_SUPERSEDES = ("baseline/history/plan_manifest.v4.json",
                       "baseline/history/plan_manifest.v3.json")
RETIRED_MARKERS = ("plan_consistency_check.py", "gate_dag.v4.json", "plan_manifest.v3.json")
MARKER_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

# Self-test isolation: when set, only these codes are recorded.
ONLY: set[str] | None = None


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def check(base, condition: bool, code: str, message: str) -> None:
    if ONLY is not None and code not in ONLY:
        return
    base.check(condition, code, message)


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
    v4_manifest: Path
    plans_root: Path
    old_dir: Path
    governing: tuple[str, ...]
    evidence_tools: tuple[str, ...]
    evidence_files: tuple[str, ...]
    external: bool = True


REAL = Ctx(
    root=V5,
    baseline=V5 / "baseline" / "plan",
    manifest=V5 / "plan_manifest.v5.json",
    schema=V5 / "plan_manifest.schema.v5.json",
    freeze_output=V5 / "plan_freeze_check.v5.txt",
    import_manifest=V5 / "import_manifest.v5.json",
    boundary_record=V5 / "v5-freeze-boundary.md",
    v4_manifest=V5 / "baseline" / "history" / "plan_manifest.v4.json",
    plans_root=V5.parent,
    old_dir=V5.parent / "source-catalog-worker-recovery-2026-08-22",
    governing=GOVERNING,
    evidence_tools=EVIDENCE_TOOLS,
    evidence_files=EVIDENCE_FILES,
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
    """Recursive enumeration of `baseline/plan/**` plus the 3 governing files."""
    files = sorted((p for p in ctx.baseline.rglob("*") if p.is_file()),
                   key=lambda p: p.relative_to(ctx.baseline).as_posix())
    entries = [("baseline/plan/" + p.relative_to(ctx.baseline).as_posix(), p) for p in files]
    entries += [(rel, ctx.root / rel) for rel in ctx.governing]
    return entries


def nested_plan_files(ctx: Ctx) -> list[str]:
    return sorted(p.relative_to(ctx.baseline).as_posix()
                  for p in ctx.baseline.rglob("*") if p.is_file() and p.parent != ctx.baseline)


def snapshot(entries) -> dict[str, tuple[str, int]]:
    return {rel: (sha(p.read_bytes()), p.stat().st_size) for rel, p in entries}


def reparse_chain(path: Path, stop: Path) -> list[str]:
    """Return every component from `path` up to `stop` that is a symlink/reparse."""
    bad: list[str] = []
    current = path
    while True:
        try:
            stat_result = current.lstat()
        except OSError:
            return bad + [f"{current} (missing)"]
        if current.is_symlink() or getattr(stat_result, "st_file_attributes", 0) & 0x400:
            bad.append(str(current))
        if current == stop or current.parent == current:
            return bad
        current = current.parent


def retired_candidates(ctx: Ctx) -> list[Path]:
    """Any sibling plan directory carrying worker-recovery plan markers."""
    found = []
    if not ctx.plans_root.is_dir():
        return found
    for candidate in sorted(p for p in ctx.plans_root.iterdir() if p.is_dir()):
        if candidate.resolve() == ctx.root.resolve():
            continue
        if any((candidate / marker).exists() or list(candidate.rglob(marker))
               for marker in RETIRED_MARKERS):
            found.append(candidate)
    return found


def inventory_digest(directory: Path) -> tuple[int, str]:
    files = sorted((p for p in directory.rglob("*") if p.is_file()),
                   key=lambda p: p.relative_to(directory).as_posix())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\x00")
        digest.update(sha(path.read_bytes()).encode("ascii"))
        digest.update(b"\n")
    return len(files), digest.hexdigest()


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
    """Frozen-set composition, path safety, boundary protocol, evidence."""
    nested = nested_plan_files(ctx)
    check(base, not nested, "V5-SET-NESTED",
          f"unexpected files below baseline/plan/**: {nested[:5]}")
    imported_count = sum(1 for rel, _ in entries if rel.startswith("baseline/plan/"))
    check(base, imported_count == EXPECTED_IMPORTED, "V5-SET-IMPORTED",
          f"expected {EXPECTED_IMPORTED} imported plan inputs, found {imported_count}")
    check(base, len(ctx.governing) == EXPECTED_GOVERNING, "V5-SET-GOVERNING",
          f"expected {EXPECTED_GOVERNING} v5-own governing artifacts")
    check(base, len(entries) == EXPECTED_TOTAL, "V5-SET-TOTAL",
          f"expected {EXPECTED_TOTAL} frozen entries, found {len(entries)}")
    for rel, path in entries:
        check(base, path.is_file(), "V5-SET-PRESENT", f"missing frozen file: {rel}")

    # Path safety (the v4 MANIFEST-PATH-SAFETY invariant): every frozen file
    # must resolve beneath the plan directory through a reparse-free chain.
    root_resolved = ctx.root.resolve()
    for rel, path in entries:
        resolved = path.resolve()
        check(base, root_resolved in resolved.parents or resolved.parent == root_resolved,
              "V5-PATH-SAFETY", f"frozen entry resolves outside the plan directory: {rel}")
        bad = reparse_chain(path, root_resolved)
        check(base, not bad, "V5-PATH-SAFETY",
              f"frozen entry traverses a symlink/reparse point: {rel} -> {bad[:2]}")

    # .gitattributes in the set and attribute-free on disk.
    check(base, (ctx.root / ".gitattributes").is_file(), "V5-ATTRS-PRESENT",
          ".gitattributes missing from the v5 directory")
    if ctx.external:
        proc = subprocess.run(
            ["git", "check-attr", *ATTRS, "--", *[str(p) for _, p in entries]],
            cwd=str(ctx.root), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120)
        lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
        check(base, len(lines) == len(ATTRS) * len(entries)
              and all(line.endswith(": unset") for line in lines), "V5-ATTRS-UNSET",
              f"git check-attr returned {len(lines)} lines; expected "
              f"{len(ATTRS) * len(entries)} 'unset' lines")

        for rel in ctx.evidence_tools:
            tool = ctx.root / rel
            check(base, tool.is_file(), "V5-EVIDENCE", f"missing evidence tool: {rel}")
            if tool.is_file():
                run = subprocess.run([sys.executable, str(tool), "--check"],
                                     capture_output=True, text=True, encoding="utf-8",
                                     errors="replace", timeout=600)
                check(base, run.returncode == 0, "V5-EVIDENCE-CHECK",
                      f"{rel} --check failed: {(run.stdout or run.stderr)[-200:]}")

    # B3: no byte drift while the suite ran.
    after = snapshot(entries)
    for rel in before:
        check(base, before.get(rel) == after.get(rel), "B3-BOUNDARY-DRIFT",
              f"frozen file changed during the run: {rel}")
    for cache in (ctx.baseline / "__pycache__", ctx.root / "tools" / "__pycache__"):
        check(base, not cache.exists(), "B3-BOUNDARY-DRIFT",
              f"verification left {cache.name} behind: {cache}")


def verify_manifest(base, ctx: Ctx, entries) -> None:
    """N1-N17 of v5-version-contract.md §7, one stable code per negative case."""
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:  # pragma: no cover
        check(base, False, "N4", f"jsonschema unavailable: {exc}")
        return

    # N1: the superseded v4 manifest must not be active in this directory.
    check(base, not (ctx.root / "plan_manifest.v4.json").exists(), "N1",
          "plan_manifest.v4.json must not exist as an active manifest")
    if not ctx.manifest.is_file():
        check(base, False, "N4", "plan_manifest.v5.json missing")
        return
    manifest = json.loads(ctx.manifest.read_text(encoding="utf-8"))
    schema = json.loads(ctx.schema.read_text(encoding="utf-8"))
    declared = {entry["path"]: entry for entry in manifest.get("normative_files", [])}
    expected = {rel for rel, _ in entries}

    # N2: no axis may point at the retired directory.
    retired_names = [d.name for d in retired_candidates(ctx)]
    blob = json.dumps(manifest, ensure_ascii=False)
    check(base, not any(name in blob for name in retired_names), "N2",
          f"manifest references a retired plan directory: {retired_names}")

    # N3: the two axes must not be mixed.
    check(base, manifest.get("protocol_revision") == "v4"
          and manifest.get("freeze_generation") == "v5", "N3",
          "axis mixing: protocol_revision must stay v4 while freeze_generation is v5")

    # N4: schema conformance (unknown fields, missing fields, wrong const).
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest))
    check(base, not errors, "N4", "; ".join(error.message for error in errors[:5]))

    # N5 / N13: membership, per-entry hashes, counts, duplicates, coverage.
    check(base, set(declared) == expected, "N13",
          f"missing={sorted(expected - set(declared))} extra={sorted(set(declared) - expected)}")
    check(base, len(declared) == len(manifest.get("normative_files", [])), "N13",
          "duplicate path in normative_files")
    folded = [rel.casefold() for rel in declared]
    check(base, len(set(folded)) == len(folded), "N13", "casefold collision in normative_files")
    check(base, not nested_plan_files(ctx), "N13",
          f"files below baseline/plan/** are not enumerated: {nested_plan_files(ctx)[:5]}")
    check(base, manifest.get("normative_file_count") == len(declared)
          == manifest.get("frozen_set_composition", {}).get("total"), "N13",
          "normative_file_count / len(normative_files) / composition.total disagree")
    coverage = manifest.get("coverage_counts", {})
    check(base, coverage == base.current_coverage_counts(base.dag_checks()[1]), "N13",
          f"coverage_counts do not match the frozen corpus: {coverage}")
    for rel, path in entries:
        entry = declared.get(rel)
        if entry is None:
            continue
        raw = path.read_bytes()
        check(base, entry.get("sha256") == sha(raw) and entry.get("size_bytes") == len(raw),
              "N5", f"hash/size mismatch: {rel}")

    # N6: recompute every equivalence class from bytes, never from labels.
    capture = json.loads(ctx.import_manifest.read_text(encoding="utf-8"))
    captured = {entry["target"]: entry for entry in capture.get("files", [])
                if entry.get("role") == "prior_plan_current_content"}
    v4_files = {entry["path"]: entry["sha256"]
                for entry in json.loads(ctx.v4_manifest.read_text(encoding="utf-8"))
                .get("normative_files", [])}
    equivalence = json.loads((ctx.root / "v5-baseline-equivalence.json")
                             .read_text(encoding="utf-8"))["groups"]
    counted = {"v4_exact": 0, "crlf_only": 0, "unproven_new_baseline": 0, "v5_own": 0}
    for rel, path in entries:
        entry = declared.get(rel)
        if entry is None:
            continue
        label = entry.get("equivalence")
        counted[label] = counted.get(label, 0) + 1
        if label not in {"v4_exact", "crlf_only", "unproven_new_baseline"}:
            continue
        raw = path.read_bytes()
        name = Path(rel).name
        historical = (captured.get(rel) or {}).get("historical_v4_sha256")
        recomputed = ("v4_exact" if historical == sha(raw)
                      else "crlf_only" if historical == sha(raw.replace(b"\r\n", b"\n"))
                      else "unproven_new_baseline")
        check(base, recomputed == label, "N6",
              f"{rel}: declared {label}, recomputed {recomputed} from bytes")
        if historical is not None:
            check(base, v4_files.get(name) == historical, "N6",
                  f"{rel}: capture historical hash != the v4 frozen manifest entry")
        check(base, rel in equivalence.get(label, []), "N6",
              f"{rel}: label {label} contradicts v5-baseline-equivalence.json")
    summary = manifest.get("equivalence_summary", {})
    check(base, all(summary.get(key) == counted[key]
                    for key in ("v4_exact", "crlf_only", "unproven_new_baseline")), "N6",
          f"equivalence_summary {summary} != recomputed {counted}")

    # N7: imported artifacts are anchored to the capture record AND to the v4
    # frozen manifest (an independent, non-regenerable source).
    frozen_imported = {rel for rel, _ in entries if rel.startswith("baseline/plan/")}
    check(base, set(captured) == frozen_imported, "N7",
          f"imported set != capture record: missing="
          f"{sorted(frozen_imported - set(captured))} extra={sorted(set(captured) - frozen_imported)}")
    for rel, path in entries:
        if rel not in frozen_imported:
            continue
        name = Path(rel).name
        raw = path.read_bytes()
        check(base, (captured.get(rel) or {}).get("sha256") == sha(raw), "N7",
              f"imported bytes differ from the capture record: {rel}")
        check(base, ".v5." not in name, "N7", f"imported artifact renamed: {rel}")
        historical = v4_files.get(name)
        label = (declared.get(rel) or {}).get("equivalence")
        if historical is None:
            check(base, label == "unproven_new_baseline", "N7",
                  f"artifact {rel} has no v4 record, so it cannot claim {label}")
        elif label == "v4_exact":
            check(base, sha(raw) == historical, "N7",
                  f"imported bytes differ from the v4 frozen manifest: {rel}")
        elif label == "crlf_only":
            check(base, sha(raw.replace(b"\r\n", b"\n")) == historical, "N7",
                  f"imported bytes differ from the v4 frozen manifest after LF normalization: {rel}")
        else:
            check(base, sha(raw) != historical
                  and sha(raw.replace(b"\r\n", b"\n")) != historical, "N7",
                  f"artifact {rel} is labelled unproven but matches the v4 frozen bytes")

    # N8: the recorded pre-freeze output must be THIS checker's own output.
    pre = manifest.get("pre_freeze_check", {})
    command = str(pre.get("command", ""))
    check(base, command == EXPECTED_COMMAND and "#" not in command, "N8",
          f"pre_freeze_check.command must equal {EXPECTED_COMMAND!r}, got {command!r}")
    scripts = [token for token in command.split() if token.endswith(".py")]
    check(base, len(scripts) == 1
          and PurePosixPath(scripts[0].replace("\\", "/")).as_posix().endswith(CHECKER_REL),
          "N8", f"command must invoke exactly the frozen checker entry: {scripts}")
    if ctx.freeze_output.is_file():
        payload = ctx.freeze_output.read_bytes()
        text = payload.decode("utf-8", errors="replace")
        match = re.match(r"PASS: ([0-9]+) checks; (\{.*\})\nREAD_ONLY: .*\n$", text)
        check(base, b"\r" not in payload and match is not None, "N8",
              "pre-freeze output is not the canonical PASS/READ_ONLY form")
        if match is not None:
            reported = int(match.group(1))
            try:
                recorded_counts = json.loads(match.group(2))
            except json.JSONDecodeError:
                recorded_counts = {}
            recomputed = {
                "fixed_nodes": len(base.load_json("gate_dag.v4.json")["nodes"]),
                "schemas": len(base.SCHEMA_FILES),
                "tests": len(base.load_json("test_id_registry.v4.json")["tests"]),
                "vectors": len(base.load_json("gate_ledger_validator_vectors.v4.json")["vectors"]),
            }
            check(base, recorded_counts == recomputed, "N8",
                  f"pre-freeze counts {recorded_counts} != recomputed {recomputed}")
            check(base, pre.get("stdout_sha256") == sha(payload)
                  and pre.get("reported_check_count") == reported, "N8",
                  "manifest does not bind the pre-freeze output bytes and count")
        if ctx.external:
            env = dict(os.environ, V5_PREFREEZE_CHILD="1")
            rerun = subprocess.run([sys.executable, str(ctx.root / CHECKER_REL)],
                                   capture_output=True, timeout=600, env=env)
            check(base, rerun.stdout == payload, "N8",
                  "a fresh default-mode run does not reproduce plan_freeze_check.v5.txt")
    else:
        check(base, False, "N8", "plan_freeze_check.v5.txt missing")

    # N9: every retired plan copy must be declared non-authoritative, with a
    # machine-verifiable inventory, and must not be a parallel authority.
    candidates = retired_candidates(ctx)
    declaration = {}
    if ctx.boundary_record.is_file():
        blocks = MARKER_BLOCK.findall(ctx.boundary_record.read_text(encoding="utf-8"))
        for block in blocks:
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "disposition" in parsed:
                declaration = parsed
    check(base, bool(declaration), "N9",
          "v5-freeze-boundary.md must carry a machine-readable disposition JSON block")
    check(base, declaration.get("disposition") == "NON_AUTHORITATIVE", "N9",
          f"disposition must be NON_AUTHORITATIVE, got {declaration.get('disposition')!r}")
    declared_dirs = {entry.get("path"): entry
                     for entry in declaration.get("retired_dirs", [])
                     if isinstance(entry, dict)}
    for candidate in candidates:
        rel = candidate.relative_to(ctx.plans_root.parent.parent).as_posix()
        entry = declared_dirs.get(rel) or declared_dirs.get(candidate.as_posix())
        check(base, entry is not None, "N9",
              f"retired plan copy not declared in the boundary record: {candidate}")
        if entry is not None:
            count, digest = inventory_digest(candidate)
            check(base, entry.get("file_count") == count
                  and entry.get("inventory_sha256") == digest, "N9",
                  f"declared inventory for {candidate} != measured ({count}, {digest})")
        for rel_path, path in entries:
            check(base, candidate.resolve() not in path.resolve().parents, "N9",
                  f"frozen entry resolves inside the retired copy: {rel_path}")
    check(base, len(declared_dirs) == len(candidates), "N9",
          f"declared {len(declared_dirs)} retired dirs but found {len(candidates)}")

    # N10: self-exclusion plus git-backed immutability of the manifest AND of
    # every frozen entry (fail-closed when the manifest is not tracked).
    check(base, manifest.get("self_exclusion") == "plan_manifest.v5.json"
          and "plan_manifest.v5.json" not in declared, "N10",
          "the manifest must exclude itself from normative_files")
    if ctx.external:
        repo = subprocess.run(["git", "-C", str(ctx.root), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        repo_root = Path(repo.stdout.strip()) if repo.returncode == 0 and repo.stdout.strip() else None
        if repo_root is None:
            check(base, False, "N10", "cannot resolve the git repository root")
        else:
            targets = [ctx.manifest] + [path for _, path in entries]
            for target in targets:
                try:
                    rel = target.relative_to(repo_root).as_posix()
                except ValueError:
                    check(base, False, "N10", f"frozen path outside the repository: {target}")
                    continue
                tracked = subprocess.run(
                    ["git", "-C", str(repo_root), "ls-files", "--error-unmatch", rel],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=60)
                if tracked.returncode != 0:
                    check(base, False, "N10",
                          f"not tracked at HEAD, so immutability is unverifiable: {rel}")
                    continue
                head = subprocess.run(["git", "-C", str(repo_root), "rev-parse", f"HEAD:{rel}"],
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60).stdout.strip()
                blob = subprocess.run(["git", "-C", str(repo_root), "hash-object", rel],
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=60).stdout.strip()
                check(base, bool(head) and head == blob, "N10",
                      f"tracked file was rewritten after freeze: {rel}")

    # N11: the supersession chain is exactly the two history manifests.
    superseded = manifest.get("supersedes", [])
    paths = [entry.get("path") for entry in superseded if isinstance(entry, dict)]
    check(base, sorted(paths) == sorted(EXPECTED_SUPERSEDES), "N11",
          f"supersedes must be exactly {list(EXPECTED_SUPERSEDES)}, got {paths}")
    for entry in superseded:
        if not isinstance(entry, dict):
            continue
        rel = str(entry.get("path"))
        check(base, not any(name in rel for name in retired_names)
              and rel.isascii() and rel == PurePosixPath(rel).as_posix(), "N11",
              f"supersedes path is not a canonical in-tree path: {rel!r}")
        path = ctx.root / rel
        check(base, path.is_file() and entry.get("sha256") == sha(path.read_bytes()), "N11",
              f"supersedes hash mismatch for {rel}")

    # N12: the investigation source lives inside the v5 directory.
    investigation = manifest.get("investigation_source", {})
    path = ctx.root / str(investigation.get("path", ""))
    check(base, investigation.get("path") == "baseline/investigation/worker-investigation-2026-08-20.md"
          and path.is_file() and sha(path.read_bytes()) == investigation.get("sha256"), "N12",
          "investigation_source path/hash mismatch")

    # N14: .gitattributes is frozen.
    check(base, ".gitattributes" in declared, "N14", ".gitattributes not in the frozen set")

    # N15: the generation axes must match the capture manifest.
    check(base, manifest.get("freeze_generation") == capture.get("capture_generation")
          and manifest.get("protocol_revision") == capture.get("source_protocol_revision"), "N15",
          "freeze_generation/protocol_revision mismatch with the capture manifest")
    check(base, manifest.get("capture_manifest", {}).get("sha256") == sha(ctx.import_manifest.read_bytes()),
          "N15", "capture_manifest.sha256 != import_manifest.v5.json bytes")

    # N16: the schema and the checker are hash-bound v5_own entries.
    for rel in ctx.governing:
        entry = declared.get(rel)
        check(base, entry is not None and entry.get("equivalence") == "v5_own", "N16",
              f"governing artifact not bound as v5_own: {rel}")

    # N17: evidence tools and evidence outputs are hash-bound.
    tools = {entry.get("path"): entry for entry in manifest.get("evidence_tools", [])}
    for rel in ctx.evidence_tools:
        entry = tools.get(rel)
        path = ctx.root / rel
        check(base, entry is not None and path.is_file()
              and entry.get("sha256") == sha(path.read_bytes()), "N17",
              f"evidence tool not hash-bound: {rel}")
    bound = manifest.get("evidence", {})
    for rel in ctx.evidence_files:
        entry = bound.get(rel)
        path = ctx.root / rel
        check(base, entry is not None and path.is_file()
              and entry.get("sha256") == sha(path.read_bytes()), "N17",
              f"evidence output not hash-bound in the manifest: {rel}")


# --- self-test: mutations per negative case, with isolation ------------------

def _mutate_manifest(ctx: Ctx, manifest: dict) -> None:
    ctx.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")


def _sync_capture(ctx: Ctx, manifest: dict, rel: str, raw: bytes) -> None:
    """Attack helper: keep every writable record consistent with new bytes."""
    capture = json.loads(ctx.import_manifest.read_text(encoding="utf-8"))
    for item in capture["files"]:
        if item["target"] == rel:
            item["sha256"] = sha(raw)
            item["size_bytes"] = len(raw)
            item["source_sha256_after"] = sha(raw)
            item["historical_v4_sha256"] = sha(raw.replace(b"\r\n", b"\n"))
    ctx.import_manifest.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
    for item in manifest["normative_files"]:
        if item["path"] == rel:
            item["sha256"] = sha(raw)
            item["size_bytes"] = len(raw)
    manifest["capture_manifest"]["sha256"] = sha(ctx.import_manifest.read_bytes())


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


def _n6_swap(ctx: Ctx, manifest: dict) -> None:
    first = next(e for e in manifest["normative_files"] if e["equivalence"] == "crlf_only")
    second = next(e for e in manifest["normative_files"]
                  if e["equivalence"] == "unproven_new_baseline")
    first["equivalence"], second["equivalence"] = second["equivalence"], first["equivalence"]


def _n6_single(ctx: Ctx, manifest: dict) -> None:
    next(e for e in manifest["normative_files"] if e["equivalence"] == "v4_exact")["equivalence"] = "crlf_only"


def _n7_tamper(ctx: Ctx, manifest: dict) -> None:
    target = next(e for e in manifest["normative_files"] if e["path"].startswith("baseline/plan/"))
    (ctx.baseline / Path(target["path"]).name).write_bytes(b"tampered\n")


def _n7_v4_rewrite(ctx: Ctx, manifest: dict) -> None:
    """Rewrite a v4-anchored file and sync every writable record."""
    rel = "baseline/plan/gate_state_machine.md"
    path = ctx.baseline / Path(rel).name
    raw = path.read_bytes().replace(b"# ", b"#  ", 1)
    path.write_bytes(raw)
    _sync_capture(ctx, manifest, rel, raw)


def _n7_rename(ctx: Ctx, manifest: dict) -> None:
    entry = next(e for e in manifest["normative_files"] if e["path"].startswith("baseline/plan/"))
    old = ctx.baseline / Path(entry["path"]).name
    new = ctx.baseline / "renamed.v5.md"
    old.rename(new)
    entry["path"] = "baseline/plan/renamed.v5.md"


def _n8_fake(ctx: Ctx, manifest: dict) -> None:
    """Fabricated output with a self-consistent hash but wrong corpus counts."""
    payload = (b'PASS: 12345 checks; {"fixed_nodes": 999, "schemas": 29, '
               b'"tests": 315, "vectors": 18}\n'
               b'READ_ONLY: no production database, registry, process, source, config, '
               b'or network access\n')
    ctx.freeze_output.write_bytes(payload)
    manifest["pre_freeze_check"]["stdout_sha256"] = sha(payload)
    manifest["pre_freeze_check"]["reported_check_count"] = 12345


def _n8_consistent(ctx: Ctx, manifest: dict) -> None:
    """Correct counts and synced hash: only a fresh re-run can expose it."""
    payload = (b'PASS: 12345 checks; {"fixed_nodes": 115, "schemas": 29, '
               b'"tests": 315, "vectors": 18}\n'
               b'READ_ONLY: no production database, registry, process, source, config, '
               b'or network access\n')
    ctx.freeze_output.write_bytes(payload)
    manifest["pre_freeze_check"]["stdout_sha256"] = sha(payload)
    manifest["pre_freeze_check"]["reported_check_count"] = 12345


def _n8_comment(ctx: Ctx, manifest: dict) -> None:
    manifest["pre_freeze_check"]["command"] = ("python baseline/plan/plan_consistency_check.py "
                                               "# v5_plan_consistency_check.py")


def _n9_undeclared(ctx: Ctx, manifest: dict) -> None:
    fake = ctx.plans_root / "source-catalog-worker-recovery-2027-01-01"
    fake.mkdir(parents=True, exist_ok=True)
    (fake / "gate_dag.v4.json").write_text("{}\n", encoding="utf-8")


def _n9_flip(ctx: Ctx, manifest: dict) -> None:
    text = ctx.boundary_record.read_text(encoding="utf-8")
    ctx.boundary_record.write_text(text.replace("NON_AUTHORITATIVE", "AUTHORITATIVE"),
                                   encoding="utf-8", newline="\n")


def _n9_missing(ctx: Ctx, manifest: dict) -> None:
    ctx.boundary_record.unlink()


def _n10(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"].append({"path": "plan_manifest.v5.json", "sha256": "0" * 64,
                                        "size_bytes": 1, "equivalence": "v5_own"})


def _n11_retired(ctx: Ctx, manifest: dict) -> None:
    manifest["supersedes"].append(
        {"path": "docs/plans/source-catalog-worker-recovery-2026-08-22/plan_manifest.v4.json",
         "sha256": sha(ctx.v4_manifest.read_bytes())})


def _n11_lookalike(ctx: Ctx, manifest: dict) -> None:
    manifest["supersedes"][0]["path"] = "baseline/history/plan_mаnifest.v4.json"


def _n12(ctx: Ctx, manifest: dict) -> None:
    manifest["investigation_source"] = {
        "path": "docs/plans/source-catalog-worker-recovery-2026-08-22/task_plan.md",
        "sha256": "0" * 64}


def _n13_drop(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"] = manifest["normative_files"][:-1]
    manifest["normative_file_count"] = len(manifest["normative_files"])


def _n13_nested(ctx: Ctx, manifest: dict) -> None:
    nested = ctx.baseline / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "plan_manifest.v4.json").write_text("{}\n", encoding="utf-8")


def _n14(ctx: Ctx, manifest: dict) -> None:
    manifest["normative_files"] = [e for e in manifest["normative_files"]
                                   if e["path"] != ".gitattributes"]


def _n15(ctx: Ctx, manifest: dict) -> None:
    capture = json.loads(ctx.import_manifest.read_text(encoding="utf-8"))
    capture["capture_generation"] = "v6"
    ctx.import_manifest.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")


def _n16(ctx: Ctx, manifest: dict) -> None:
    for entry in manifest["normative_files"]:
        if entry["path"] == "plan_manifest.schema.v5.json":
            entry["equivalence"] = "v4_exact"


def _n17_tool(ctx: Ctx, manifest: dict) -> None:
    manifest["evidence_tools"][0]["sha256"] = "0" * 64


def _n17_evidence(ctx: Ctx, manifest: dict) -> None:
    manifest["evidence"]["v5-baseline-equivalence.json"]["sha256"] = "0" * 64


N_CASES = (
    ("N1", "把 plan_manifest.v4.json 当作当前活动 manifest", ((_n1, False),)),
    ("N2", "manifest 指向已退役旧目录", ((_n2, False),)),
    ("N3", "版本轴混用", ((_n3, False),)),
    ("N4", "schema_version/未知字段/缺必填字段", ((_n4, False),)),
    ("N5", "normative sha256/size 与冻结记录不符", ((_n5, False),)),
    ("N6", "equivalence 类别与复算不符（含计数守恒互换）",
     ((_n6_swap, False), (_n6_single, False))),
    ("N7", "导入 artifact 被改名/改字节/改 $id",
     ((_n7_tamper, False), (_n7_v4_rewrite, False), (_n7_rename, False))),
    ("N8", "用伪造或旧 checker 输出冒充 v5 预冻结检查",
     ((_n8_fake, False), (_n8_consistent, True), (_n8_comment, False))),
    ("N9", "旧目录复活/未申报/处置被翻转",
     ((_n9_undeclared, False), (_n9_flip, False), (_n9_missing, False))),
    ("N10", "manifest 自身进入 normative 集", ((_n10, False),)),
    ("N11", "取代链指向旧目录或形近路径",
     ((_n11_retired, False), (_n11_lookalike, False))),
    ("N12", "investigation_source 不在 v5 目录内", ((_n12, False),)),
    ("N13", "normative 集缺项/计数不符/嵌套文件",
     ((_n13_drop, False), (_n13_nested, False))),
    ("N14", ".gitattributes 不在冻结集内", ((_n14, False),)),
    ("N15", "generation 与 capture manifest 不符", ((_n15, False),)),
    ("N16", "v5 治理件未绑定为 v5_own", ((_n16, False),)),
    ("N17", "证据工具/证据输出哈希不符",
     ((_n17_tool, False), (_n17_evidence, False))),
)


def self_test(base) -> int:
    global ONLY
    if not REAL.manifest.is_file():
        print("SELF-TEST SKIP: plan_manifest.v5.json missing (freeze first)")
        return 1
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for code, label, mutations in N_CASES:
            for index, (mutate, needs_git) in enumerate(mutations, start=1):
                tag = f"{code}.{index}" if len(mutations) > 1 else code
                repo = Path(tmp) / "repo"
                if repo.exists():
                    shutil.rmtree(repo)
                root = repo / "docs" / "plans" / REAL.root.name
                plans_root = root.parent
                old_dir = plans_root / REAL.old_dir.name
                shutil.copytree(REAL.root / "baseline", root / "baseline")
                shutil.copytree(REAL.root / "tools", root / "tools")
                for name in (".gitattributes", "plan_manifest.v5.json",
                             "plan_manifest.schema.v5.json", "plan_freeze_check.v5.txt",
                             "import_manifest.v5.json", "v5-baseline-equivalence.json",
                             "v5-version-reference-inventory.json", "v5-freeze-boundary.md"):
                    source = REAL.root / name
                    if source.is_file():
                        (root / name).write_bytes(source.read_bytes())
                shutil.copytree(REAL.old_dir, old_dir)
                if needs_git:
                    subprocess.run(["git", "init", "-q", str(repo)], timeout=60,
                                   capture_output=True)
                ctx = Ctx(
                    root=root, baseline=root / "baseline" / "plan",
                    manifest=root / "plan_manifest.v5.json",
                    schema=root / "plan_manifest.schema.v5.json",
                    freeze_output=root / "plan_freeze_check.v5.txt",
                    import_manifest=root / "import_manifest.v5.json",
                    boundary_record=root / "v5-freeze-boundary.md",
                    v4_manifest=root / "baseline" / "history" / "plan_manifest.v4.json",
                    plans_root=plans_root, old_dir=old_dir,
                    governing=GOVERNING, evidence_tools=EVIDENCE_TOOLS,
                    evidence_files=EVIDENCE_FILES, external=needs_git,
                )
                manifest = json.loads(ctx.manifest.read_text(encoding="utf-8"))
                mutate(ctx, manifest)
                _mutate_manifest(ctx, manifest)
                fired = []
                for scope in (None, {code}):
                    ONLY = scope
                    saved = (base.ERRORS, base.CHECKS)
                    base.ERRORS, base.CHECKS = [], 0
                    try:
                        verify_manifest(base, ctx, frozen_entries(ctx))
                        fired.append(code in {e.split(":", 1)[0] for e in base.ERRORS})
                    finally:
                        base.ERRORS, base.CHECKS = saved
                ONLY = None
                if all(fired):
                    print(f"SELF-TEST {tag} PASS: rejected (full+isolated) - {label}")
                else:
                    failures.append(tag)
                    print(f"SELF-TEST {tag} FAIL: full={fired[0]} isolated={fired[1]} - {label}")
    print(f"SELF-TEST: {len(N_CASES)} cases / "
          f"{sum(len(m) for _, _, m in N_CASES)} mutations; failures={failures or 'none'}")
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
