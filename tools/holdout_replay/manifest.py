"""Replay manifest content contracts and declared sample independence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

MANIFEST_SCHEMA = "w18-holdout-manifest/1"

_REQUIRED_SAMPLE_FIELDS = (
    "sample_id", "gold_file", "gold_sha256", "document_kind", "market", "language",
    "carrier", "source_ref", "identity_evidence", "reading_scope",
    "designated_trap",
)
_REQUIRED_SOURCE_REF_FIELDS = (
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
)


class ManifestError(ValueError):
    """The manifest is structurally wrong; the replay refuses to run."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_committed_bytes(path: Path) -> str:
    """SHA-256 over the file's committed (LF) bytes.

    JSON payloads are committed with LF endings; a CRLF checkout must not
    change what a pinned sha means, so manifest/gold bindings hash the
    line-ending-normalized bytes. The original's own sha256 is never computed
    this way - only in-repo JSON receipts.
    """
    data = Path(path).read_bytes().replace(bytes([13, 10]), bytes([10]))
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("schema_version") != MANIFEST_SCHEMA:
        raise ManifestError(f"manifest schema_version must be {MANIFEST_SCHEMA}")
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
        ref = sample["source_ref"]
        if not isinstance(ref, Mapping) or not set(_REQUIRED_SOURCE_REF_FIELDS) <= ref.keys():
            raise ManifestError(f"{where}.source_ref is missing required fields")
        sha = ref["content_sha256"]
        if not isinstance(sha, str) or len(sha) != 64 or sha != sha.lower():
            raise ManifestError(f"{where}.source_ref.content_sha256 must be a lowercase sha256")
        for key in ("document_id", "source_id"):
            if not ref[key].endswith(sha):
                raise ManifestError(f"{where}.source_ref.{key} does not bind the content sha")
        if sha in seen_shas:
            raise ManifestError(
                f"two samples bind the same original content sha {sha[:12]} "
                "(one material cannot impersonate two independent originals)"
            )
        seen_shas.add(sha)
        if not isinstance(sample["reading_scope"], Mapping):
            raise ManifestError(f"{where}.reading_scope must be a mapping")
    return record


def declared_holdout_qualification(
    manifest: Mapping[str, Any], samples: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe eligibility, never permission, quality PASS or loop-stop counts.

    Development and nonfrozen data remain runnable. A declared clean holdout
    requires both a true prior-freeze declaration and nondevelopment samples.
    This is not a certificate of unseen data or a substitute for content review.
    """
    selected = manifest['samples'] if samples is None else samples
    frozen = manifest.get('frozen_before_candidate_output') is True
    rows: list[dict[str, Any]] = []
    for sample in selected:
        reasons = []
        if not frozen:
            reasons.append('prior_freeze_not_declared_true')
        prior = sample.get('prior_use')
        status = prior.get('status') if isinstance(prior, Mapping) else None
        if status not in ('fresh', 'local-unseen'):
            reasons.append('development_sample' if status == 'development'
                           else 'prior_use_not_declared_fresh_or_unseen')
        rows.append({'sample_id': sample['sample_id'], 'eligible_for_clean_holdout': not reasons,
                     'reasons': reasons})
    eligible = sum(1 for row in rows if row['eligible_for_clean_holdout'])
    return {'schema_version': 'holdout-qualification/1',
            'scope': 'declared_sample_independence_not_quality_or_loop_stopping',
            'frozen_before_candidate_output': (manifest.get('frozen_before_candidate_output')
                if type(manifest.get('frozen_before_candidate_output')) is bool else None),
            'eligible_for_clean_holdout': bool(rows) and eligible == len(rows),
            'eligible_sample_count': eligible, 'samples': rows}


def gold_path_for(manifest_path: Path, sample: Mapping[str, Any]) -> Path:
    return manifest_path.parent / sample["gold_file"]


def verify_manifest_gold(manifest: Mapping[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    """Cross-check gold files: SHA, presence, and source binding."""
    rows = []
    for sample in manifest["samples"]:
        gold_file = gold_path_for(Path(manifest_path), sample)
        if not gold_file.exists():
            raise ManifestError(f"gold file missing for {sample['sample_id']}: {gold_file}")
        actual = sha256_committed_bytes(gold_file)
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
