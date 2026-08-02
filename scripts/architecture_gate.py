#!/usr/bin/env python3
"""Evaluate structural architecture rules without executing production pipelines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or not isinstance(config.get("rules"), list):
        raise ValueError("architecture config must have schema_version=1 and a rules list")
    return config


def _excluded(relative: str, patterns: list[str]) -> bool:
    path = Path(relative)
    return any(path.match(pattern) for pattern in patterns)


def evaluate_architecture(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    violations: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    flags = re.MULTILINE | re.DOTALL
    for rule in config["rules"]:
        rule_id = str(rule["id"])
        kind = str(rule["kind"])
        pattern = re.compile(str(rule["regex"]), flags)
        excluded = list(rule.get("exclude", []))
        files = [
            path
            for path in sorted(root.glob(str(rule["glob"])))
            if path.is_file() and not _excluded(path.relative_to(root).as_posix(), excluded)
        ]
        matches: list[dict[str, Any]] = []
        for path in files:
            relative = path.relative_to(root).as_posix()
            content = path.read_text(encoding="utf-8", errors="replace")
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                matches.append({"path": relative, "line": line, "text": match.group(0)[:240]})

        observation = {
            "id": rule_id,
            "kind": kind,
            "files_scanned": len(files),
            "matches": len(matches),
        }
        observations.append(observation)
        message = str(rule.get("message", rule_id))
        if kind == "required_regex" and not matches:
            violations.append({"id": rule_id, "message": message, "matches": []})
        elif kind == "forbidden_regex" and matches:
            violations.append({"id": rule_id, "message": message, "matches": matches})
        elif kind == "max_regex_matches":
            maximum = int(rule.get("max_matches", 0))
            if len(matches) > maximum:
                violations.append(
                    {
                        "id": rule_id,
                        "message": message,
                        "maximum": maximum,
                        "actual": len(matches),
                        "matches": matches,
                    }
                )
        elif kind not in {"required_regex", "forbidden_regex", "max_regex_matches"}:
            violations.append({"id": rule_id, "message": f"unknown rule kind: {kind}", "matches": []})

    return {
        "schema_version": 1,
        "result": "pass" if not violations else "fail",
        "violations": violations,
        "observations": observations,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("control/architecture.json"))
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    result = evaluate_architecture(root, load_config(config_path))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
