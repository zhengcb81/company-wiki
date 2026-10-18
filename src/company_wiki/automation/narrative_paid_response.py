"""Bounded private paid-response artifacts, referenced by the existing AUTO row.

This is a byte port, not a task store or a public narrative bundle. The AUTO
reservation remains the only authority associating bytes with a paid request.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Protocol


class PaidResponseError(RuntimeError):
    """Paid bytes could not be recorded or verified; never authorize a resend."""


class ResponseObjects(Protocol):
    def put(self, data: bytes) -> str: ...
    def read(self, key: str, *, expected_sha256: str, expected_size: int) -> bytes: ...


_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class PaidResponsePin:
    request_sha256: str
    body_sha256: str
    object_key: str
    byte_size: int
    model_id: str
    adapter_id: str
    prompt_version: str
    http_status: int
    duration_ms: int
    schema_version: str = "narrative-paid-response/1"

    def __post_init__(self) -> None:
        if self.schema_version != "narrative-paid-response/1":
            raise PaidResponseError("paid response schema is unavailable")
        if not all(isinstance(s, str) and _SHA.fullmatch(s)
                   for s in (self.request_sha256, self.body_sha256)):
            raise PaidResponseError("paid response digest is invalid")
        if self.object_key != f"objects/sha256/{self.body_sha256[:2]}/{self.body_sha256}.json":
            raise PaidResponseError("paid response object key is invalid")
        if type(self.byte_size) is not int or not 0 <= self.byte_size <= 262144:
            raise PaidResponseError("paid response size is invalid")
        for name in ("model_id", "adapter_id", "prompt_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip() or len(value) > 256:
                raise PaidResponseError("paid response identity is invalid")
        if type(self.http_status) is not int or not 200 <= self.http_status < 300:
            raise PaidResponseError("paid response status is invalid")
        if type(self.duration_ms) is not int or self.duration_ms < 0:
            raise PaidResponseError("paid response elapsed time is invalid")

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> PaidResponsePin:
        if not isinstance(value, str) or len(value.encode("utf-8")) > 4096:
            raise PaidResponseError("paid response receipt is oversized")
        try:
            data = json.loads(value)
            pin = cls(**data)
        except (ValueError, TypeError, RecursionError) as exc:
            raise PaidResponseError("paid response receipt is invalid") from exc
        if pin.to_json() != value:
            raise PaidResponseError("paid response receipt is not canonical")
        return pin


class PaidResponseArtifacts:
    def __init__(self, objects: ResponseObjects, *, max_response_bytes: int,
                 preflight: Callable[[int], None] | None = None) -> None:
        if type(max_response_bytes) is not int or not 0 < max_response_bytes <= 262144:
            raise ValueError("response artifact bound must respect the HTTP body cap")
        self.objects = objects
        self.max_response_bytes = max_response_bytes
        self._preflight = preflight

    def admit(self) -> None:
        if self._preflight is not None:
            self._preflight(self.max_response_bytes)

    def validate_identity(self, *, request_sha256: str, model_id: str,
                          adapter_id: str, prompt_version: str) -> None:
        """Validate the actual receipt identity before reserving or paying."""
        digest = hashlib.sha256(b"").hexdigest()
        PaidResponsePin(request_sha256=request_sha256, body_sha256=digest,
            object_key=f"objects/sha256/{digest[:2]}/{digest}.json", byte_size=0,
            model_id=model_id, adapter_id=adapter_id, prompt_version=prompt_version,
            http_status=200, duration_ms=0)

    def put(self, body: bytes, **identity) -> PaidResponsePin:
        if not isinstance(body, bytes) or len(body) > self.max_response_bytes:
            raise PaidResponseError("paid response exceeds its byte bound")
        digest = hashlib.sha256(body).hexdigest()
        pin = PaidResponsePin(body_sha256=digest, byte_size=len(body),
            object_key=f"objects/sha256/{digest[:2]}/{digest}.json", **identity)
        try:
            key = self.objects.put(body)
        except Exception as exc:
            raise PaidResponseError("paid response object is unavailable") from exc
        if key != pin.object_key:
            raise PaidResponseError("paid response object key differs")
        return pin

    def read(self, pin: PaidResponsePin) -> bytes:
        if pin.byte_size > self.max_response_bytes:
            raise PaidResponseError("paid response exceeds the configured byte bound")
        try:
            data = self.objects.read(pin.object_key, expected_sha256=pin.body_sha256,
                                     expected_size=pin.byte_size)
        except Exception as exc:
            raise PaidResponseError("paid response object failed verification") from exc
        if len(data) != pin.byte_size or hashlib.sha256(data).hexdigest() != pin.body_sha256:
            raise PaidResponseError("paid response object failed verification")
        return data
