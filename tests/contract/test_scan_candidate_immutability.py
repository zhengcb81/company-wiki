"""Adapter-to-scanner candidates are immutable value contracts."""

from __future__ import annotations

import json
import math

import pytest

from company_wiki.source_catalog.models import RootSpec
from company_wiki.source_catalog.scan_contract import ScanCandidate


def test_group_metadata_is_deeply_immutable_and_detached_from_adapter_input(tmp_path):
    metadata = {"capture": {"labels": ["annual", "original"]}}
    candidate = ScanCandidate(
        root=RootSpec("fixture", tmp_path, "directory"),
        path=tmp_path / "annual.pdf",
        relative_path="annual.pdf",
        group_key="annual.pdf",
        role="original_primary",
        entity_name="Example",
        group_metadata=metadata,
        source_status="active",
    )

    metadata["capture"]["labels"].append("mutated-after-boundary")
    assert candidate.group_metadata["capture"]["labels"] == ("annual", "original")

    with pytest.raises(TypeError):
        candidate.group_metadata["capture"]["new"] = "value"
    with pytest.raises(AttributeError):
        candidate.group_metadata["capture"]["labels"].append("mutable")

    payload = candidate.group_metadata_payload()
    payload["capture"]["labels"].append("storage-copy-only")
    assert json.loads(json.dumps(payload)) == {
        "capture": {"labels": ["annual", "original", "storage-copy-only"]}
    }
    assert candidate.group_metadata["capture"]["labels"] == ("annual", "original")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_group_metadata_rejects_nonfinite_float_values(tmp_path, value):
    with pytest.raises(ValueError, match="finite JSON number"):
        ScanCandidate(
            root=RootSpec("fixture", tmp_path, "directory"),
            path=tmp_path / "annual.pdf",
            relative_path="annual.pdf",
            group_key="annual.pdf",
            role="original_primary",
            entity_name="Example",
            group_metadata={"nonfinite": value},
            source_status="active",
        )
