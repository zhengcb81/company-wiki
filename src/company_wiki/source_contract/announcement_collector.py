"""Compatibility imports for the former announcement collector module."""

from typing import TYPE_CHECKING, Any

from .announcement_receipt import (
    ANNOUNCEMENT_COLLECTION_ID_PREFIX,
    ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION,
    ANNOUNCEMENT_COLLECTOR_NAME,
    ANNOUNCEMENT_COLLECTOR_VERSION,
    DEFAULT_MAX_BYTES,
    OFFICIAL_EXCHANGE_DOMAINS,
    AnnouncementCollectionError,
    AnnouncementCollectionReceipt,
    AnnouncementConflictError,
    AnnouncementContentError,
    AnnouncementDownloadError,
    AnnouncementURLPolicyError,
    DownloadedAnnouncement,
    validate_official_announcement_url,
)

if TYPE_CHECKING:
    from company_wiki.source_catalog.announcement_collector import (
        collect_announcement as collect_announcement,
        download_announcement as download_announcement,
    )


def __getattr__(name: str) -> Any:
    if name in {"collect_announcement", "download_announcement"}:
        from company_wiki.source_catalog.announcement_collector import (
            collect_announcement,
            download_announcement,
        )

        return collect_announcement if name == "collect_announcement" else download_announcement
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ANNOUNCEMENT_COLLECTION_ID_PREFIX",
    "ANNOUNCEMENT_COLLECTION_SCHEMA_VERSION",
    "ANNOUNCEMENT_COLLECTOR_NAME",
    "ANNOUNCEMENT_COLLECTOR_VERSION",
    "DEFAULT_MAX_BYTES",
    "OFFICIAL_EXCHANGE_DOMAINS",
    "AnnouncementCollectionError",
    "AnnouncementCollectionReceipt",
    "AnnouncementConflictError",
    "AnnouncementContentError",
    "AnnouncementDownloadError",
    "AnnouncementURLPolicyError",
    "DownloadedAnnouncement",
    "collect_announcement",
    "download_announcement",
    "validate_official_announcement_url",
]
