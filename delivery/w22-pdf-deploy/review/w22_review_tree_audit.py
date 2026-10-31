"""W22 independent reviewer: full read-only audit of the deployed tree.

Verifies, for every planned row: target safety, destination existence/bytes,
samefile hardlink identity to the declared source, and (via destination hashing)
that deployed bytes equal the plan-frozen source bytes. Independently re-checks
wheel RECORD hashes for all 104 distributions, model artifact identity, output
config content, isolation, scaffold/extra-file accounting. Writes nothing
outside this review directory.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
import os
from io import StringIO
from pathlib import Path
import sys
import time

PLAN_PATH = Path("C:/cwp-runtime/w22-pdf-sdk-plan.local.json")
TARGET = Path("C:/cwp-runtime/w22-pdf-sdk")
RECEIPT_PATH = TARGET / "deployment.json"
CONFIG_PATH = TARGET / "paragraph-runtime.config.json"
OUT = Path(__file__).resolve().parent / "w22-review-tree-audit.json"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    started = time.monotonic()
    report: dict[str, object] = {"scope": "independent row-by-row audit of the deployed W22 tree",
                                 "plan_path": str(PLAN_PATH), "target": str(TARGET)}
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    # -- receipt binding ------------------------------------------------------
    report["receipt_plan_sha_matches_plan"] = receipt["plan_sha256"] == plan["plan_sha256"]
    report["receipt_target_matches"] = receipt["target"] == str(TARGET)
    report["receipt_created_links_matches_rows"] = (
        receipt["created_links"] == len(plan["env_rows"]) + len(plan["artifact_rows"]))

    # -- row-level verification ----------------------------------------------
    bad_rows: list[dict[str, str]] = []
    unsafe_targets = 0
    dest_bytes_total = 0
    samefile_failures = 0
    rows = [(row, "env") for row in plan["env_rows"]] + [(row, "artifact") for row in plan["artifact_rows"]]
    sources_outside_declared = 0
    for index, (row, kind) in enumerate(rows):
        rel = row["target"].replace("\\", "/")
        pure = [part for part in rel.split("/") if part]
        if (not rel or rel.startswith("/") or ":" in rel or ".." in pure
                or not os.path.normpath(rel).replace("\\", "/") == "/".join(pure)):
            unsafe_targets += 1
            bad_rows.append({"target": rel, "problem": "unsafe_target"})
            continue
        expected_root = TARGET / "env" if kind == "env" else TARGET / "artifacts"
        if not (TARGET / pure[0]) == expected_root:
            bad_rows.append({"target": rel, "problem": "row outside declared root"})
            continue
        destination = TARGET.joinpath(*pure)
        source = Path(row["source"])
        if not destination.is_file():
            bad_rows.append({"target": rel, "problem": "destination_missing"})
            continue
        if destination.stat().st_size != row["bytes"]:
            bad_rows.append({"target": rel, "problem": "size_mismatch"})
            continue
        digest = file_sha256(destination)
        if digest != row["sha256"]:
            bad_rows.append({"target": rel, "problem": "content_mismatch"})
            continue
        dest_bytes_total += row["bytes"]
        try:
            if not os.path.samefile(source, destination):
                samefile_failures += 1
                bad_rows.append({"target": rel, "problem": "not_samefile"})
        except OSError:
            samefile_failures += 1
            bad_rows.append({"target": rel, "problem": "samefile_oserror"})
        # source must still exist with the plan-frozen bytes (in-place mutation
        # would change both sides of the hardlink, so this also detects it)
        try:
            if not source.is_file() or file_sha256(source) != row["sha256"]:
                bad_rows.append({"target": rel, "problem": "source_changed_or_missing"})
        except OSError:
            bad_rows.append({"target": rel, "problem": "source_unreadable"})
        outside = not (str(source).startswith("C:\\Users\\郑曾波\\Projects\\company-wiki\\.planning\\c3-20261028\\pdf-sdk-isolated\\")
                       or str(source).startswith("C:\\Users\\郑曾波\\.cache\\huggingface\\hub\\models--docling-project--docling-layout-heron\\"))
        if outside:
            sources_outside_declared += 1
        if index % 5000 == 0:
            print(f"...row {index}/{len(rows)}", flush=True)
    report["rows_total"] = len(rows)
    report["unsafe_targets"] = unsafe_targets
    report["samefile_failures"] = samefile_failures
    report["sources_outside_declared_roots"] = sources_outside_declared
    report["bad_rows"] = bad_rows[:50]
    report["bad_row_count"] = len(bad_rows)
    report["logical_shared_bytes_recomputed"] = dest_bytes_total
    report["logical_shared_bytes_matches_receipt"] = (
        dest_bytes_total == receipt["logical_shared_bytes"] == sum(r[0]["bytes"] for r in rows))

    # -- independent wheel RECORD verification --------------------------------
    record_mismatches: list[dict[str, str]] = []
    dists_checked = 0
    for name, entry in plan["distributions"].items():  # plan carries all 104 RECORDs
        dist_path = Path(entry["path"])
        record_text = (dist_path / "RECORD").read_text(encoding="utf-8")
        if sha256((dist_path / "RECORD").read_bytes()).hexdigest() != entry["record_sha256"]:
            record_mismatches.append({"distribution": name, "path": "RECORD", "problem": "record_changed"})
        dists_checked += 1
        for row in csv.reader(StringIO(record_text)):
            if not row:
                continue
            relative = row[0]
            declared = row[1] if len(row) > 1 else ""
            if not declared:
                continue
            target_file = dist_path / relative
            if not target_file.is_file():
                record_mismatches.append({"distribution": name, "path": relative, "problem": "missing"})
                continue
            algorithm, _, encoded = declared.partition("=")
            if algorithm != "sha256":
                record_mismatches.append({"distribution": name, "path": relative, "problem": f"algorithm:{algorithm}"})
                continue
            if file_sha256(target_file) != encoded.rstrip("="):
                record_mismatches.append({"distribution": name, "path": relative, "problem": "hash_mismatch"})
    report["distributions_record_checked"] = dists_checked
    report["record_mismatch_count"] = len(record_mismatches)
    report["record_mismatches"] = record_mismatches[:30]
    plan_deviation_set = {(d["distribution"], d["path"].replace("\\", "/")) for d in plan["diagnostics"]["record_deviations"]}
    observed_deviation_set = {(m["distribution"], m["path"].replace("\\", "/")) for m in record_mismatches}
    report["record_mismatches_equal_plan_deviations"] = observed_deviation_set == plan_deviation_set

    # -- model artifacts -------------------------------------------------------
    artifacts_report = []
    for row in plan["artifact_rows"]:
        source = Path(row["source"])
        dest = TARGET.joinpath(*row["target"].split("/"))
        artifacts_report.append({"target": row["target"], "sha_matches": file_sha256(dest) == row["sha256"],
                                 "samefile": os.path.samefile(source, dest), "source": str(source)})
    report["artifact_rows"] = artifacts_report
    profile = plan["source_profile"]
    weights = next(r for r in artifacts_report if r["target"] == "artifacts/model.safetensors")
    config = next(r for r in artifacts_report if r["target"] == "artifacts/config.json")
    report["model_sha_matches_profile"] = file_sha256(TARGET / "artifacts" / "model.safetensors") == profile["model_sha256"]
    report["model_config_sha_matches_profile"] = file_sha256(TARGET / "artifacts" / "config.json") == profile["model_config_sha256"]
    report["artifact_weights_ok"] = weights["sha_matches"] and weights["samefile"]
    report["artifact_config_ok"] = config["sha_matches"] and config["samefile"]

    # -- output config ----------------------------------------------------------
    config_raw = CONFIG_PATH.read_bytes()
    report["config_sha_matches_receipt"] = sha256(config_raw).hexdigest() == receipt["output_config_sha256"]
    emitted = json.loads(config_raw.decode("utf-8"))
    expected = dict(profile)
    expected["python"] = str(TARGET / "env" / "Scripts" / "python.exe")
    expected["artifacts"] = str(TARGET / "artifacts")
    report["config_equals_source_profile_with_ascii_paths"] = emitted == expected
    report["config_ascii"] = all(ord(c) < 128 for c in emitted["python"] + emitted["artifacts"])

    # -- isolation ---------------------------------------------------------------
    site_packages = TARGET / "env" / "Lib" / "site-packages"
    dist_infos = sorted(p.name for p in site_packages.iterdir()
                        if p.is_dir() and (p.name.endswith(".dist-info") or p.name.endswith(".egg-info")))
    report["dist_info_count"] = len(dist_infos)
    report["pip_present"] = any("pip" in name.lower() for name in dist_infos) or (TARGET / "env" / "Scripts" / "pip.exe").exists()
    pyvenv = (TARGET / "env" / "pyvenv.cfg").read_text(encoding="utf-8")
    report["pyvenv_no_system_site"] = "include-system-site-packages = false" in pyvenv
    active_pth = []
    for pth in site_packages.glob("*.pth"):
        lines = pth.read_text(encoding="utf-8", errors="replace").splitlines()
        active = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
        if active:
            active_pth.append({"path": pth.name, "lines": active})
    report["active_pth_hooks"] = active_pth
    report["active_pth_match_plan"] = (sorted(h["path"] for h in active_pth)
                                       == sorted(Path(h["path"]).name for h in plan["diagnostics"]["active_pth_hooks"]))
    scripts_dir = TARGET / "env" / "Scripts"
    report["scripts_dir_entries"] = sorted(p.name.lower() for p in scripts_dir.iterdir())[:40]

    # -- extra-file / scaffold accounting ---------------------------------------
    planned_rel = {row["target"].replace("\\", "/").lower() for row in rows}
    extra_files: list[str] = []
    scaffold_bytes = 0
    env_planned = {row["target"][len("env/"):].lower() for row in plan["env_rows"]}
    for path in TARGET.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(TARGET).as_posix().lower()
        if rel in planned_rel or rel in {"deployment.json", "paragraph-runtime.config.json"}:
            continue
        extra_files.append(rel)
        if rel.startswith("env/") and rel[len("env/"):] not in env_planned:
            scaffold_bytes += path.stat().st_size
    report["extra_file_count"] = len(extra_files)
    report["extra_files"] = extra_files[:40]
    report["scaffold_bytes_recomputed"] = scaffold_bytes
    report["scaffold_bytes_matches_receipt"] = scaffold_bytes == receipt["new_scaffold_file_bytes"]

    report["seconds"] = round(time.monotonic() - started, 1)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"bad_rows", "record_mismatches", "extra_files"}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
