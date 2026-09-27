"""Full local read-policy fingerprint for path-independent v2 consumers.

RootPolicy 2.x is an existing cross-project wire contract.  Its hash excludes
some active admission fields, so a separate pin covers every config field and
the runtime activation snapshot without changing that older contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import CatalogConfig


READ_POLICY_FINGERPRINT_SCHEMA_VERSION = "1.0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _plain(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def source_read_policy_sha256(
    config: CatalogConfig, runtime_snapshot: Mapping[str, Any] | None
) -> str:
    """Hash all root admission fields and the pinned activation snapshot."""
    if not isinstance(config, CatalogConfig):
        raise TypeError("config must be CatalogConfig")
    if runtime_snapshot is None:
        activation: str | None = None
    else:
        activation = runtime_snapshot.get("snapshot_sha256")
        if not isinstance(activation, str) or not _SHA256.fullmatch(activation):
            raise ValueError("runtime snapshot must carry a valid SHA-256")
    payload = {
        "schema_version": READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        "catalog_config": _plain(asdict(config)),
        "runtime_snapshot_sha256": activation,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "READ_POLICY_FINGERPRINT_SCHEMA_VERSION",
    "source_read_policy_sha256",
]
