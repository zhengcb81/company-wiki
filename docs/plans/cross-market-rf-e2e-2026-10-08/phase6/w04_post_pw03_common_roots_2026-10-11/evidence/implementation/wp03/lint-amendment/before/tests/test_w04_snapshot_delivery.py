"""W04 native snapshot delivery challenges; all registry writes use pytest TEMP."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from revenue_backtest import create_snapshot, validate_snapshot, write_new_json
from test_recognition_bridge import forecast_document
from revenue_core import canonical_sha256
from publication_registry import _read_entries


@pytest.mark.parametrize("schema", ["3.7", "3.8", "3.9"])
def test_snapshot_header_uses_actual_native_schema_and_keeps_registry_binding(schema, tmp_path):
    data = forecast_document()
    data["schema_version"] = schema
    snapshot = create_snapshot(data, "w04-native-" + schema)
    assert snapshot["input_document"]["schema_version"] == schema
    assert snapshot["forecast_result"]["schema_version"] == schema
    assert snapshot["forecast_schema_version"] == schema
    validate_snapshot(snapshot)
    entry = next(e for e in _read_entries() if e["artifact_id"] == snapshot["snapshot_id"])
    assert entry["input_sha256"] == snapshot["input_sha256"]
    output = tmp_path / "snapshot.json"
    write_new_json(output, snapshot)
    encoded = output.read_bytes()
    assert json.loads(encoded) == snapshot
    assert len(encoded.splitlines()) == 1
    assert canonical_sha256(json.loads(encoded)["input_document"]) == snapshot["input_sha256"]
    with pytest.raises(FileExistsError):
        write_new_json(output, snapshot)


def test_historical_header_discrepancy_is_diagnostic_and_never_rewritten():
    from copy import deepcopy
    from revenue_backtest import snapshot_schema_diagnostic
    # Synthetic legacy metadata challenge; no existing snapshot/registry is touched.
    old = {"snapshot_id": "frozen-id", "forecast_schema_version": "3.7",
           "input_document": {"schema_version": "3.9"}, "forecast_result": {"schema_version": "3.9"}}
    before = deepcopy(old)
    seen = snapshot_schema_diagnostic(old)
    assert seen["status"] == "metadata_mismatch"
    assert seen["snapshot_rewritten"] is False
    assert old == before
