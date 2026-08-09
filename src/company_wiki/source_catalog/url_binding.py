"""WU-403: document-level URL binding (no company-name broadcast).

URLs bind only via strong one-to-one immutable keys: provider_document_id
(default) or content_sha256.  A company_name key is never a valid binding —
the same company has many filings, and broadcasting one document's URL to
the others is the F-052 defect this module prevents.
"""

from __future__ import annotations

STRONG_KEYS = ("provider_document_id", "content_sha256")


def bind_url(docs: list[dict], key: str = "provider_document_id") -> dict[str, str]:
    """Return {strong_key: url} for documents that actually carry a URL."""
    if key not in STRONG_KEYS:
        raise ValueError(f"binding key must be one of {STRONG_KEYS}, got {key!r}")
    binding: dict[str, str] = {}
    for doc in docs:
        url = doc.get("source_url")
        strong = doc.get(key)
        if url and strong:
            binding[str(strong)] = url
    return binding


def detect_url_broadcast(
    docs: list[dict], candidate_binding: dict[str, str]
) -> list[str]:
    """Reject any binding entry whose key is not the document's own strong
    key (a broadcast assigns one URL to multiple documents)."""
    problems: list[str] = []
    for doc in docs:
        strong = str(doc.get("provider_document_id", ""))
        url = doc.get("source_url")
        assigned = candidate_binding.get(strong)
        if assigned is not None and assigned != url:
            problems.append(
                f"{strong}: assigned URL {assigned!r} does not belong to this "
                "document (company-name broadcast detected)"
            )
    return problems
