"""Single CLI entry for the W18 holdout replay (H07).

    python -m tools.holdout_replay --help
    python -m tools.holdout_replay verify-freeze --producer-repo R --producer-commit S
    python -m tools.holdout_replay bootstrap-lake --lake-dir D --bindings B
        --producer-repo R --producer-commit S
    python -m tools.holdout_replay run --producer-repo R --producer-commit S
        --manifest M (--bindings B | --source-root T) --out-dir O
        [--sample ID ...] [--lake-config C --llm-config L --llm-provider P]
        [--per-sample-timeout S] [--external-cwd D] [--extra-pythonpath P ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from .manifest import load_manifest, verify_manifest_gold
from .producer import ProducerError, verify_producer
from .runner import ReplayError, run_replay

LAKE_CONFIG_TEMPLATE = """\
schema_version: "1.0"
catalog_dir: "{lake_dir}/.source_catalog"
roots:
  - root_id: w18_lake
    kind: company_raw
    path: "{source_root}"
    priority: 10
"""


def _add_producer_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--producer-repo", type=Path, required=True,
                        help="git repo/worktree that must sit exactly at --producer-commit")
    parser.add_argument("--producer-commit", required=True,
                        help="frozen full commit the replay is allowed to measure")


def cmd_verify_freeze(args: argparse.Namespace) -> int:
    try:
        deploy = verify_producer(args.producer_repo, args.producer_commit)
    except ProducerError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, ensure_ascii=False))
        return 2
    manifest = load_manifest(args.manifest)
    rows = verify_manifest_gold(manifest, args.manifest)
    print(json.dumps({"status": "verified", "producer": deploy, "gold_rows": rows},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_bootstrap_lake(args: argparse.Namespace) -> int:
    """Register the manifest originals into an isolated lake catalog.

    The lake config points one root at the (read-only) tree that physically
    holds the originals; registration hashes and indexes without moving or
    copying bytes, and the production catalog is never touched.
    """
    try:
        deploy = verify_producer(args.producer_repo, args.producer_commit)
    except ProducerError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, ensure_ascii=False))
        return 2
    manifest = load_manifest(args.manifest)
    bindings = json.loads(Path(args.bindings).read_text(encoding="utf-8"))
    lake_dir = Path(args.lake_dir)
    lake_dir.mkdir(parents=True, exist_ok=True)
    source_root = Path(args.source_root)
    config_path = lake_dir / "source_catalog.yaml"
    config_path.write_text(
        LAKE_CONFIG_TEMPLATE.format(lake_dir=lake_dir.resolve(), source_root=source_root.resolve()),
        encoding="utf-8")
    from .producer import import_paths
    from .runner import ORCHESTRATOR_ROOT

    env = dict(os.environ,
               PYTHONPATH=os.pathsep.join(
                   [str(p.resolve()) for p in import_paths(Path(args.producer_repo))]
                   + [str(ORCHESTRATOR_ROOT)]),
               PYTHONDONTWRITEBYTECODE="1")
    relative = []
    for sample in manifest["samples"]:
        path = Path(bindings[sample["sample_id"]]).resolve()
        rel = path.relative_to(source_root.resolve()).as_posix()
        expected = sample["source_ref"]["content_sha256"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            print(json.dumps({"status": "refused",
                              "reason": f"{sample['sample_id']}: sha mismatch {actual[:12]}"}
                             , ensure_ascii=False))
            return 2
        relative.append(rel)
    command = [sys.executable, "-B", "-X", "utf8", "-m", "company_wiki.source_catalog.cli",
               "--config", str(config_path), "register", "--root-id", "w18_lake"]
    for rel in relative:
        command += ["--relative-path", rel]
    completed = subprocess.run(command, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=3600)
    receipt = {
        "status": "ok" if completed.returncode == 0 else "failed",
        "producer_commit": deploy["producer_commit"],
        "lake_config": str(config_path),
        "source_root": str(source_root.resolve()),
        "registered_relative_paths": relative,
        "register_exit": completed.returncode,
        "register_stdout_tail": completed.stdout[-1500:],
        "register_stderr_tail": completed.stderr[-800:] if completed.stderr else "",
    }
    (lake_dir / "bootstrap.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=1))
    return 0 if completed.returncode == 0 else 1


def cmd_run(args: argparse.Namespace) -> int:
    receipt = run_replay(
        producer_root=args.producer_repo,
        producer_commit=args.producer_commit,
        manifest_path=args.manifest,
        out_dir=args.out_dir,
        bindings_path=args.bindings,
        source_root=args.source_root,
        sample_ids=args.sample,
        lake_config=args.lake_config,
        lake_root=args.lake_root,
        llm_config=args.llm_config,
        llm_provider=args.llm_provider,
        per_sample_timeout=args.per_sample_timeout,
        external_cwd=args.external_cwd,
        extra_pythonpath=args.extra_pythonpath,
    )
    summary = {
        "overall": receipt["overall"],
        "attempt_dir": receipt["attempt_dir"],
        "samples": [{k: row.get(k) for k in ("sample_id", "status", "reason", "elapsed_seconds")}
                    for row in receipt["samples"]],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if receipt["overall"] == "ok" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tools.holdout_replay",
        description="Frozen-commit replay of real CWP parsing/selection/task compilation "
                    "against the W18 three-market holdout manifest and source-side gold.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-freeze", help="verify producer deploy and manifest/gold consistency")
    _add_producer_args(verify)
    verify.add_argument("--manifest", type=Path,
                        default=Path(__file__).resolve().parent / "manifest.json")
    verify.set_defaults(fn=cmd_verify_freeze)

    lake = sub.add_parser("bootstrap-lake", help="register manifest originals into an isolated lake catalog")
    _add_producer_args(lake)
    lake.add_argument("--manifest", type=Path,
                      default=Path(__file__).resolve().parent / "manifest.json")
    lake.add_argument("--lake-dir", type=Path, required=True)
    lake.add_argument("--bindings", type=Path, required=True)
    lake.add_argument("--source-root", type=Path, required=True,
                      help="read-only tree physically holding the originals")
    lake.set_defaults(fn=cmd_bootstrap_lake)

    run = sub.add_parser("run", help="replay one frozen producer commit over the manifest")
    _add_producer_args(run)
    run.add_argument("--manifest", type=Path,
                     default=Path(__file__).resolve().parent / "manifest.json")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--bindings", type=Path, help="{sample_id: absolute_path} local JSON")
    source.add_argument("--source-root", type=Path,
                        help="read-only tree; originals found by SHA-256 index")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--sample", action="append",
                     help="restrict to one sample_id (repeatable)")
    run.add_argument("--lake-config", type=Path,
                     help="isolated lake catalog config enabling the zero-POST compile stage")
    run.add_argument("--lake-root", type=Path,
                     help="project root for the compile stage (default: lake-config parent)")
    run.add_argument("--llm-config", type=Path,
                     help="existing LLM config read only for request composition (never sent)")
    run.add_argument("--llm-provider", default="minimax",
                     choices=("minimax", "mimo", "deepseek", "openai"))
    run.add_argument("--per-sample-timeout", type=float, default=900.0)
    run.add_argument("--external-cwd", type=Path,
                     help="cwd for the worker subprocess (default: user home, never the repo)")
    run.add_argument("--extra-pythonpath", type=Path, action="append", default=None,
                     help="paths prepended to worker PYTHONPATH (pollution test hook)")
    run.set_defaults(fn=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except (ReplayError, ProducerError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
