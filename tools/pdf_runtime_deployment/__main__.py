"""CLI: plan | deploy | verify | status | constructor-probe.

Every subcommand takes explicit paths; nothing scans the machine and nothing
is hard-coded. ``deploy`` must run under the base interpreter that owns the
source environment's venv module.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from . import deployment

REPO_SRC = Path(__file__).resolve().parents[3] / "src"


def _compact(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)


def cmd_plan(arguments) -> int:
    source_config = Path(arguments.source_config)
    profile = json.loads(source_config.read_text(encoding="utf-8-sig"))
    probe = deployment.describe_source(source_config, repo_src=Path(arguments.repo_src))
    plan = deployment.build_plan(Path(arguments.target), profile, probe,
                                 source_config_sha256=sha256(source_config.read_bytes()).hexdigest())
    if plan["blocking_errors"]:
        Path(arguments.plan_out).write_text(json.dumps(plan, ensure_ascii=True), encoding="utf-8")
        print(_compact({"status": "BLOCKED", "blocking_errors": plan["blocking_errors"][:20],
                        "blocking_count": len(plan["blocking_errors"]),
                        "plan_out": arguments.plan_out}))
        return 1
    Path(arguments.plan_out).write_text(json.dumps(plan, ensure_ascii=True), encoding="utf-8")
    print(_compact({"status": "PLANNED", "plan_sha256": plan["plan_sha256"],
                    "target": plan["target"],
                    "distribution_count": len(plan["distribution_summary"]),
                    "env_files": len(plan["env_rows"]), "artifact_files": len(plan["artifact_rows"]),
                    "logical_shared_bytes": sum(row["bytes"] for row in
                                                (*plan["env_rows"], *plan["artifact_rows"])),
                    "diagnostics": {key: (len(value) if isinstance(value, list) else value)
                                    for key, value in plan["diagnostics"].items()},
                    "plan_out": arguments.plan_out}))
    return 0


def cmd_deploy(arguments) -> int:
    plan = json.loads(Path(arguments.plan).read_text(encoding="utf-8"))
    deployment.require_base_python(
        plan["source"]["base_prefix"], prefix=sys.prefix, base_prefix=sys.base_prefix)
    receipt = deployment.deploy(plan, host_python=sys.executable)
    print(_compact(receipt))
    return 0


def cmd_verify(arguments) -> int:
    config_path = Path(arguments.config)
    before = deployment.snapshot_tree(config_path.parent)
    light = deployment.verify_light(config_path, repo_src=Path(arguments.repo_src))
    loaded = deployment.verify_config_load(config_path, repo_src=Path(arguments.repo_src))
    after = deployment.snapshot_tree(config_path.parent)
    print(_compact({"light": light, "config_load": loaded,
                    "zero_write_verified": before == after,
                    "tree_files": after["files"], "tree_bytes": after["bytes"]}))
    return 0


def cmd_status(arguments) -> int:
    target = Path(arguments.target)
    receipt = deployment._read_receipt(target)  # noqa: SLF001 - status reads own marker
    if receipt is None:
        print(_compact({"target": str(target), "classification":
                        "ABSENT" if not target.exists() else
                        ("EMPTY" if not any(target.iterdir()) else "FOREIGN_OR_UNKNOWN")}))
        return 0
    classification = ("OWNED_COMPLETE" if receipt.get("status") == "COMPLETE"
                      else "OWNED_INCOMPLETE")
    print(_compact({"target": str(target), "classification": classification,
                    "receipt": receipt}))
    return 0


def cmd_constructor_probe(arguments) -> int:
    config_path = Path(arguments.config)
    raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    observation = deployment.constructor_probe(raw["python"], raw["artifacts"],
                                               timeout=arguments.deadline)
    print(_compact(observation))
    if observation.get("status") != "CONSTRUCTOR_OK" or observation["seconds"] > arguments.deadline:
        return 1
    return 0


def cmd_warm_cache(arguments) -> int:
    observation = deployment.warm_child_bytecode_cache(Path(arguments.config),
                                                       repo_src=Path(arguments.repo_src),
                                                       timeout=arguments.deadline)
    print(_compact(observation))
    return 0


def main(argv: list[str] | None = None) -> int:
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="freeze a projection plan from a source config")
    plan_parser.add_argument("--source-config", required=True)
    plan_parser.add_argument("--target", required=True)
    plan_parser.add_argument("--plan-out", required=True)
    plan_parser.add_argument("--repo-src", default=str(REPO_SRC))
    plan_parser.set_defaults(handler=cmd_plan)

    deploy_parser = subparsers.add_parser("deploy", help="create/recover/reuse the owned deployment")
    deploy_parser.add_argument("--plan", required=True)
    deploy_parser.set_defaults(handler=cmd_deploy)

    verify_parser = subparsers.add_parser("verify", help="light fresh-process verification")
    verify_parser.add_argument("--config", required=True)
    verify_parser.add_argument("--repo-src", default=str(REPO_SRC))
    verify_parser.set_defaults(handler=cmd_verify)

    status_parser = subparsers.add_parser("status", help="classify a deployment target")
    status_parser.add_argument("--target", required=True)
    status_parser.set_defaults(handler=cmd_status)

    probe_parser = subparsers.add_parser("constructor-probe", help="no-document SDK constructor")
    probe_parser.add_argument("--config", required=True)
    probe_parser.add_argument("--deadline", type=float, default=deployment.CONSTRUCTOR_DEADLINE_SECONDS)
    probe_parser.set_defaults(handler=cmd_constructor_probe)

    warm_parser = subparsers.add_parser("warm-cache",
                                        help="one-time child bytecode warm-up via the production launch command")
    warm_parser.add_argument("--config", required=True)
    warm_parser.add_argument("--deadline", type=float, default=600.0)
    warm_parser.add_argument("--repo-src", default=str(REPO_SRC))
    warm_parser.set_defaults(handler=cmd_warm_cache)

    arguments = parser.parse_args(argv)
    try:
        return arguments.handler(arguments)
    except deployment.DeploymentError as failure:
        print(f"{type(failure).__name__}: {failure}", file=sys.stderr)
        return 2
    except subprocess.SubprocessError as failure:
        print(f"{type(failure).__name__}: {failure}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
