"""Result cache keyed by every identity axis that can change model output.

Different backend / model revision / precision / prompt / preprocessing never
share a cache key; a different page never shares a key.  Cache hits keep the
original measured engine time (never zero) and are flagged so reports can
separate cached from fresh inference.
"""

from __future__ import annotations

import hashlib
import json


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
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResultCache:
    def __init__(self):
        self._store: dict[str, dict] = {}

    def put(self, key: str, record: dict) -> None:
        self._store[key] = dict(record)

    def get(self, key: str) -> dict | None:
        record = self._store.get(key)
        if record is None:
            return None
        hit = dict(record)
        hit["cache_hit"] = True
        return hit

    def __len__(self) -> int:
        return len(self._store)
