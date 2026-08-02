"""Packaged JSON Schema accessors for source-contract consumers."""

from importlib.resources import files
import json


def load_source_manifest_schema() -> dict:
    """Return a fresh copy of the published source-manifest v1 schema."""
    resource = files("company_wiki.source_contract.schemas").joinpath(
        "source_manifest.v1.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def load_evidence_span_schema() -> dict:
    """Return a fresh copy of the published evidence-span v1 schema."""
    resource = files("company_wiki.source_contract.schemas").joinpath(
        "evidence_span.v1.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))
