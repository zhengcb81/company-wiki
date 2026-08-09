"""WU-301/302: static, reviewed adapter registry (config references IDs only).

Configuration never imports module paths (D-011): it selects a registered
adapter ID + version range.  The registry is a code-reviewed static table
with declared capabilities; unknown IDs / versions / profiles fail closed.
"""

from __future__ import annotations

ADMISSION_PROFILES = {
    "financial_evidence_v1": {
        "official_providers": ("example-filing", "dayu", "sec", "hkex", "cninfo"),
        "allows_filing": True,
        "read_only_required": True,
    },
    "generic_document_v1": {
        "official_providers": (),
        "allows_filing": False,
        "read_only_required": True,
    },
}

REGISTERED_ADAPTERS = {
    "sidecar_filing_v1": {
        "version": "1.0.0",
        "admission_profile_id": "financial_evidence_v1",
        "capabilities": ("sidecar", "filing", "metadata_v2"),
        "read_only": True,
    },
    "dayu_filing_v1": {
        "version": "1.0.0",
        "admission_profile_id": "financial_evidence_v1",
        "capabilities": ("dayu_meta", "filing", "metadata_v2"),
        "read_only": True,
    },
    "company_raw_v1": {
        "version": "1.0.0",
        "admission_profile_id": "financial_evidence_v1",
        "capabilities": ("company_raw", "filing", "metadata_v2"),
        "read_only": False,  # canonical writer root
    },
    "generic_document_v1": {
        "version": "1.0.0",
        "admission_profile_id": "generic_document_v1",
        "capabilities": ("generic",),
        "read_only": True,
    },
}


def registered_adapter(adapter_id: str) -> dict | None:
    return REGISTERED_ADAPTERS.get(adapter_id)


def admission_profile(profile_id: str) -> dict | None:
    return ADMISSION_PROFILES.get(profile_id)
