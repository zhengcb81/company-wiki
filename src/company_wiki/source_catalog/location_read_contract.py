"""Pathless contracts shared by registered-location byte readers."""

from dataclasses import dataclass

from company_wiki.source_contract.source_version import SourceByteObservation

from .models import RankedSourceLocation


@dataclass(frozen=True)
class RegisteredLocationBinding:
    """Opaque identity binding one catalog location to one source version."""

    location_id: str
    binding_sha256: str


@dataclass(frozen=True)
class SourceLocationReadResult:
    """Result of verifying one current registered location for a SourceRef."""

    location: RankedSourceLocation
    observation: SourceByteObservation | None
    status: str
    reason: str
    detail: str
    binding: RegisteredLocationBinding | None = None

    @property
    def ok(self) -> bool:
        return self.observation is not None and not self.status


@dataclass(frozen=True)
class RegisteredLocationDescriptor:
    """Current mapping for an earlier opaque registered-location binding."""

    location: RankedSourceLocation
    binding: RegisteredLocationBinding | None
    status: str
    reason: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.binding is not None and not self.status


__all__ = [
    "RegisteredLocationBinding",
    "RegisteredLocationDescriptor",
    "SourceLocationReadResult",
]
