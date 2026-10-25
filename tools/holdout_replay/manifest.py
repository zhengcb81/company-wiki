"""Frozen manifest loading and consistency checks (no physical paths inside)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

MANIFEST_SCHEMA = "w18-holdout-manifest/1"

_REQUIRED_SAMPLE_FIELDS = (
    "sample_id", "gold_file", "gold_sha256", "document_kind", "market", "language",
    "carrier", "source_ref", "identity_evidence", "prior_use", "reading_scope",
    "designated_trap",
)
_REQUIRED_SOURCE_REF_FIELDS = (
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
)


class ManifestError(ValueError):
    """The manifest is structurally wrong; the replay refuses to run."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("schema_version") != MANIFEST_SCHEMA:
        raise ManifestError(f"manifest schema_version must be {MANIFEST_SCHEMA}")
    if not record.get("frozen_before_candidate_output"):
        raise ManifestError("manifest is not marked frozen_before_candidate_output")
    samples = record.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ManifestError("manifest.samples must be a non-empty list")
    seen: set[str] = set()
    seen_shas: set[str] = set()
    for index, sample in enumerate(samples):
        where = f"manifest.samples[{index}]"
        if not isinstance(sample, Mapping) or not set(_REQUIRED_SAMPLE_FIELDS) <= sample.keys():
            raise ManifestError(f"{where} is missing required fields")
        if sample["sample_id"] in seen:
            raise ManifestError(f"duplicate sample_id {sample['sample_id']!r}")
        seen.add(sample["sample_id"])
        sha = sample["source_ref"]["content_sha256"]
        if sha in seen_shas:
            raise ManifestError(
                f"two samples bind the same original content sha {sha[:12]} "
                "(one material cannot impersonate two independent originals)"
            )
        seen_shas.add(sha)
        ref = sample["source_ref"]
        if not isinstance(ref, Mapping) or not set(_REQUIRED_SOURCE_REF_FIELDS) <= ref.keys():
            raise ManifestError(f"{where}.source_ref is missing required fields")
        if not isinstance(sha, str) or len(sha) != 64 or sha != sha.lower():
            raise ManifestError(f"{where}.source_ref.content_sha256 must be a lowercase sha256")
        for key in ("document_id", "source_id"):
            if not ref[key].endswith(sha):
                raise ManifestError(f"{where}.source_ref.{key} does not bind the content sha")
        prior = sample["prior_use"]
        if not isinstance(prior, Mapping) or prior.get("status") not in {"fresh", "local-unseen", "development"}:
            raise ManifestError(f"{where}.prior_use.status must be fresh/local-unseen/development")
        if not isinstance(sample["reading_scope"], Mapping):
            raise ManifestError(f"{where}.reading_scope must be a mapping")
    return record


def gold_path_for(manifest_path: Path, sample: Mapping[str, Any]) -> Path:
    return manifest_path.parent / sample["gold_file"]


def verify_manifest_gold(manifest: Mapping[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    """Cross-check gold files: SHA, presence, and source binding."""
    rows = []
    for sample in manifest["samples"]:
        gold_file = gold_path_for(Path(manifest_path), sample)
        if not gold_file.exists():
            raise ManifestError(f"gold file missing for {sample['sample_id']}: {gold_file}")
        actual = sha256_file(gold_file)
        if actual != sample["gold_sha256"]:
            raise ManifestError(
                f"gold sha mismatch for {sample['sample_id']}: manifest "
                f"{sample['gold_sha256'][:12]} != actual {actual[:12]}"
            )
        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        if gold.get("sample_id") != sample["sample_id"]:
            raise ManifestError(f"gold sample_id mismatch for {sample['sample_id']}")
        if gold.get("source_sha256") != sample["source_ref"]["content_sha256"]:
            raise ManifestError(f"gold source_sha256 mismatch for {sample['sample_id']}")
        rows.append({"sample_id": sample["sample_id"], "facts": len(gold.get("facts", [])),
                     "gold_sha256": actual})
    return rows
