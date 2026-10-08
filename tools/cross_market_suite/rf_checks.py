"""Executed inside the exported RF runtime, against newly generated artifacts."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.runtime / "scripts"))
    from revenue_report import validate_published_forecast
    from revenue_backtest import validate_snapshot
    from publication_registry import audit

    root = args.case_dir
    data, result, snapshot = [json.loads((root / name).read_text(encoding="utf-8"))
                              for name in ("input.json", "new_forecast.json", "new_snapshot.json")]
    validate_published_forecast(result, data)
    validate_snapshot(snapshot)
    assert snapshot["input_document"] == data
    assert snapshot["forecast_result"]["result_sha256"] == result["result_sha256"]
    assert not audit([root / "new_forecast.json", root / "new_snapshot.json"])
    print(json.dumps({"registered_artifact_audit": "pass", "strong_tuple_binding": "pass"}))


if __name__ == "__main__":
    main()
