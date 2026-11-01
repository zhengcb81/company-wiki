"""Result cache keyed by every identity axis that can change model output.

Different backend / model revision / precision / prompt / preprocessing never
share a cache key; a different page never shares a key.  Cache hits keep the
original measured engine time (never zero) and are flagged so reports can
separate cached from fresh inference.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


def cache_key(
    backend_identity: dict,
    page_image_sha256: str,
    prompt_sha256: str,
    params: dict,
) -> str:
    payload = json.dumps(
        {
            "schema": "cwp-ocr-comparison-cache/1",
            "backend_identity": backend_identity,
            "page_image_sha256": page_image_sha256,
            "prompt_sha256": prompt_sha256,
            "params": params,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache:
    def __init__(self, directory: str | Path | None = None):
        self._store: dict[str, dict] = {}
        self.directory = Path(directory) if directory is not None else None
        if self.directory is not None:
            self.directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _payload(record: dict) -> bytes:
        return json.dumps(record, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")

    def _path(self, key: str) -> Path:
        if not key or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in key):
            raise ValueError("invalid cache key")
        return self.directory / (key + ".json")

    def put(self, key: str, record: dict) -> None:
        stored = dict(record)
        stored.pop("cache_hit", None)
        if self.directory is not None:
            payload = self._payload(stored)
            envelope = {"key": key, "sha256": hashlib.sha256(payload).hexdigest(), "record": stored}
            fd, name = tempfile.mkstemp(prefix=".w23-cache-", suffix=".tmp", dir=self.directory)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(self._payload(envelope))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, self._path(key))
            finally:
                Path(name).unlink(missing_ok=True)
        self._store[key] = stored

    def get(self, key: str) -> dict | None:
        record = self._store.get(key)
        if record is None and self.directory is not None:
            try:
                envelope = json.loads(self._path(key).read_text(encoding="utf-8"))
                candidate = envelope["record"]
                if not isinstance(candidate, dict) or envelope["key"] != key:
                    return None
                if hashlib.sha256(self._payload(candidate)).hexdigest() != envelope["sha256"]:
                    return None
                record = candidate
                self._store[key] = record
            except (OSError, ValueError, TypeError, KeyError):
                return None  # partial/corrupt entry is an honest miss
        if record is None:
            return None
        return {**record, "cache_hit": True, "inference_runs": 0}

    def __len__(self) -> int:
        return len(self._store)
