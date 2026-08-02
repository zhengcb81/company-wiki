"""Fixed command-line gate for the RR-12.2d synthetic gold corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from common import atomic_write  # noqa: E402
from helpers.gold_evaluator import (  # noqa: E402
    evaluate,
    gold_to_perfect_predictions,
    load_gold,
    receipt_sha256,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate predictions against the independent synthetic gold corpus."
    )
    parser.add_argument("--corpus", required=True, type=Path)
    prediction_source = parser.add_mutually_exclusive_group(required=True)
    prediction_source.add_argument("--predictions", type=Path)
    prediction_source.add_argument(
        "--perfect",
        action="store_true",
        help="Use a gold-derived ceiling artifact for evaluator self-verification only.",
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--as-of", dest="as_of")
    return parser


def _load_predictions(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid predictions file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("predictions document must be a JSON object")
    return value


def _write_receipt(path: Path, receipt: dict) -> Path:
    """Write only below artifacts/gates through the central guarded writer."""
    allowed_root = (ROOT / "artifacts" / "gates").resolve()
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(
            f"receipt path must stay below {allowed_root}: {path}"
        ) from exc
    resolved.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        resolved,
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        gold = load_gold(args.corpus)
        predictions = (
            gold_to_perfect_predictions(gold)
            if args.perfect
            else _load_predictions(args.predictions)
        )
        receipt = evaluate(predictions, gold, as_of=args.as_of)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    receipt["receipt_sha256"] = receipt_sha256(receipt)
    try:
        receipt_path = _write_receipt(args.receipt, receipt)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "receipt": str(receipt_path),
                "receipt_sha256": receipt["receipt_sha256"],
                "all_critical_pass": receipt["all_critical_pass"],
                "failures": len(receipt["failures"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if receipt["all_critical_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
