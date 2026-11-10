"""Multi-root immutable source catalog and versioned read APIs."""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING, Any

# Keep runtime owners lazy so clients of leaf value/reading modules need not
# initialize download, storage or parser modules.
if TYPE_CHECKING:
    from company_wiki.source_contract.source_version import (
        SOURCE_REF_SCHEMA_VERSION, SourceReadError, SourceRef, VerifiedContent,
    )

    from .config import CatalogConfigError, load_catalog_config
    from .models import (
        CATALOG_SCHEMA_VERSION,
        CatalogBrowseVersion,
        CatalogConfig,
        NORMALIZER_VERSION,
        ProcessingReport,
        ROOT_KINDS,
        RootSpec,
        SCANNER_VERSION,
        SUMMARIZER_VERSION,
        ScanReport,
        SECTION_EXTRACTOR_VERSION,
        SourceVersionIdentity,
    )
    from .service import SourceCatalog
    from .resolver import (
        ResolutionResult,
        ResolutionStatus,
        SOURCE_RESOLVER_SCHEMA_VERSION,
        SourceHandle,
        SourceRequest,
        SourceResolutionError,
        SourceResolver,
    )
    from .source_reader import (
        SourceQueryResult,
        SourceVersionReader,
    )
    from .lock import CatalogOperationLockedError
    from .acquisition import (
        ACQUISITION_SCHEMA_VERSION,
        AcquisitionCoordinator,
        AcquisitionError,
        AcquisitionResult,
        AcquisitionStatus,
        AdapterRegistry,
        DownloadAdapter,
        DownloadCandidate,
        DownloadReceipt,
        MarketRoutingError,
    )
    from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
    from .canonical_writer import (
        CANONICAL_IMPORT_SCHEMA_VERSION,
        CanonicalImportError,
        CanonicalImportResult,
        CanonicalImportStatus,
        CanonicalSourceWriter,
    )
    from .acquisition_journal import (
        ACQUISITION_JOURNAL_SCHEMA_VERSION,
        ACQUISITION_OUTCOMES,
        AcquisitionAttempt,
        AcquisitionJournal,
    )
    from .acquisition_service import (
        SOURCE_ENSURE_SCHEMA_VERSION,
        SourceAcquisitionService,
        SourceEnsureResult,
        SourceEnsureStatus,
    )
    from .adapter_process import AdapterProcessError, JsonCommandAdapter
    from .acquisition_config import (
        AcquisitionConfig,
        AcquisitionConfigError,
        AdapterCommandSpec,
        load_acquisition_config,
    )
    from .duplicate_cleanup import (
        DUPLICATE_CLEANUP_SCHEMA_VERSION,
        DuplicateCleanupError,
        DuplicateCleanupJournal,
        DuplicateCleanupService,
        recycle_to_windows_bin,
    )
    from .focus_cleanup import (
        FOCUS_CLEANUP_SCHEMA_VERSION,
        FocusScopeCleanupService,
    )
    from .extraction_quality import (
        EXTRACTION_QUALITY_SCHEMA_VERSION,
        MAX_QUALITY_LOCATOR_REFERENCES,
        ExtractionLocatorReference,
        ExtractionQualityAmbiguousError,
        ExtractionQualityError,
        ExtractionQualityInputError,
        ExtractionQualityIntegrityError,
        ExtractionQualityNotFoundError,
        ExtractionQualityReport,
        ExtractionQualityService,
        ExtractionQualityState,
        ExtractionQualityUnavailableError,
    )
    from .dayu_cli_adapter import DayuCliAdapterError, DayuCliDownloadAdapter
    from .security_identity import (
        CNINFO_STOCK_URL,
        HKEX_ACTIVE_STOCK_URL,
        HKEX_INACTIVE_STOCK_URL,
        HKEX_SECURITIES_URL,
        HKEX_STANDARD_TRANSFER_URL,
        NASDAQ_LISTED_URL,
        NASDAQ_OTHER_LISTED_URL,
        SEC_TICKER_URL,
        IdentityCandidate,
        IdentityResult,
        IdentityStatus,
        OfficialSecurityMasterRefresher,
        SecurityIdentityError,
        SecurityIdentityResolutionError,
        SecurityIdentityResolver,
        SecurityMaster,
        SecurityMasterStore,
        SecurityMasterUnavailableError,
        SecurityRecord,
        load_identity_master,
    )
    from . import narrative_evidence as narrative_evidence


_EXPORTS_BY_MODULE = {
    "..source_contract.source_version": (
        "SOURCE_REF_SCHEMA_VERSION", "SourceReadError", "SourceRef", "VerifiedContent",
    ),
    ".config": ("CatalogConfigError", "load_catalog_config"),
    ".models": (
        "CATALOG_SCHEMA_VERSION",
        "CatalogBrowseVersion",
        "CatalogConfig",
        "NORMALIZER_VERSION",
        "ProcessingReport",
        "ROOT_KINDS",
        "RootSpec",
        "SCANNER_VERSION",
        "SUMMARIZER_VERSION",
        "ScanReport",
        "SECTION_EXTRACTOR_VERSION",
        "SourceVersionIdentity",
    ),
    ".service": ("SourceCatalog",),
    ".resolver": (
        "ResolutionResult",
        "ResolutionStatus",
        "SOURCE_RESOLVER_SCHEMA_VERSION",
        "SourceHandle",
        "SourceRequest",
        "SourceResolutionError",
        "SourceResolver",
    ),
    ".source_reader": (
        "SourceQueryResult",
        "SourceVersionReader",
    ),
    ".lock": ("CatalogOperationLockedError",),
    ".acquisition": (
        "ACQUISITION_SCHEMA_VERSION",
        "AcquisitionCoordinator",
        "AcquisitionError",
        "AcquisitionResult",
        "AcquisitionStatus",
        "AdapterRegistry",
        "DownloadAdapter",
        "DownloadCandidate",
        "DownloadReceipt",
        "MarketRoutingError",
    ),
    ".download_budget": ("AcquisitionBudget", "AcquisitionBudgetExceeded"),
    ".canonical_writer": (
        "CANONICAL_IMPORT_SCHEMA_VERSION",
        "CanonicalImportError",
        "CanonicalImportResult",
        "CanonicalImportStatus",
        "CanonicalSourceWriter",
    ),
    ".acquisition_journal": (
        "ACQUISITION_JOURNAL_SCHEMA_VERSION",
        "ACQUISITION_OUTCOMES",
        "AcquisitionAttempt",
        "AcquisitionJournal",
    ),
    ".acquisition_service": (
        "SOURCE_ENSURE_SCHEMA_VERSION",
        "SourceAcquisitionService",
        "SourceEnsureResult",
        "SourceEnsureStatus",
    ),
    ".adapter_process": ("AdapterProcessError", "JsonCommandAdapter"),
    ".acquisition_config": (
        "AcquisitionConfig",
        "AcquisitionConfigError",
        "AdapterCommandSpec",
        "load_acquisition_config",
    ),
    ".duplicate_cleanup": (
        "DUPLICATE_CLEANUP_SCHEMA_VERSION",
        "DuplicateCleanupError",
        "DuplicateCleanupJournal",
        "DuplicateCleanupService",
        "recycle_to_windows_bin",
    ),
    ".focus_cleanup": ("FOCUS_CLEANUP_SCHEMA_VERSION", "FocusScopeCleanupService"),
    ".extraction_quality": (
        "EXTRACTION_QUALITY_SCHEMA_VERSION",
        "MAX_QUALITY_LOCATOR_REFERENCES",
        "ExtractionLocatorReference",
        "ExtractionQualityAmbiguousError",
        "ExtractionQualityError",
        "ExtractionQualityInputError",
        "ExtractionQualityIntegrityError",
        "ExtractionQualityNotFoundError",
        "ExtractionQualityReport",
        "ExtractionQualityService",
        "ExtractionQualityState",
        "ExtractionQualityUnavailableError",
    ),
    ".dayu_cli_adapter": ("DayuCliAdapterError", "DayuCliDownloadAdapter"),
    ".security_identity": (
        "CNINFO_STOCK_URL",
        "HKEX_ACTIVE_STOCK_URL",
        "HKEX_INACTIVE_STOCK_URL",
        "HKEX_SECURITIES_URL",
        "HKEX_STANDARD_TRANSFER_URL",
        "NASDAQ_LISTED_URL",
        "NASDAQ_OTHER_LISTED_URL",
        "SEC_TICKER_URL",
        "IdentityCandidate",
        "IdentityResult",
        "IdentityStatus",
        "OfficialSecurityMasterRefresher",
        "SecurityIdentityError",
        "SecurityIdentityResolutionError",
        "SecurityIdentityResolver",
        "SecurityMaster",
        "SecurityMasterStore",
        "SecurityMasterUnavailableError",
        "SecurityRecord",
        "load_identity_master",
    ),
    ".narrative_evidence": ("narrative_evidence",),
}
_PUBLIC_MODULE_BY_NAME = {
    name: module for module, exports in _EXPORTS_BY_MODULE.items() for name in exports
}


def __getattr__(name: str) -> Any:
    module_name = _PUBLIC_MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = _import_module(module_name, __name__)
    exported = module if name == "narrative_evidence" else getattr(module, name)
    globals()[name] = exported
    return exported


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    'ACQUISITION_SCHEMA_VERSION',
    'ACQUISITION_JOURNAL_SCHEMA_VERSION',
    'ACQUISITION_OUTCOMES',
    'AcquisitionCoordinator',
    'AcquisitionBudget',
    'AcquisitionBudgetExceeded',
    'AcquisitionConfig',
    'AcquisitionConfigError',
    'AcquisitionError',
    'AcquisitionResult',
    'AcquisitionStatus',
    'AcquisitionAttempt',
    'AcquisitionJournal',
    'AdapterRegistry',
    'AdapterCommandSpec',
    'AdapterProcessError',
    'CANONICAL_IMPORT_SCHEMA_VERSION',
    'CATALOG_SCHEMA_VERSION',
    'CatalogBrowseVersion',
    'CatalogConfig',
    'CatalogConfigError',
    'CatalogOperationLockedError',
    'CanonicalImportError',
    'CanonicalImportResult',
    'CanonicalImportStatus',
    'CanonicalSourceWriter',
    'CNINFO_STOCK_URL',
    'DownloadAdapter',
    'DownloadCandidate',
    'DownloadReceipt',
    'DayuCliAdapterError',
    'DayuCliDownloadAdapter',
    'DUPLICATE_CLEANUP_SCHEMA_VERSION',
    'DuplicateCleanupError',
    'DuplicateCleanupJournal',
    'DuplicateCleanupService',
    'FOCUS_CLEANUP_SCHEMA_VERSION',
    'FocusScopeCleanupService',
    'EXTRACTION_QUALITY_SCHEMA_VERSION',
    'ExtractionLocatorReference',
    'ExtractionQualityAmbiguousError',
    'ExtractionQualityError',
    'ExtractionQualityInputError',
    'ExtractionQualityIntegrityError',
    'ExtractionQualityNotFoundError',
    'ExtractionQualityReport',
    'ExtractionQualityService',
    'ExtractionQualityState',
    'ExtractionQualityUnavailableError',
    'HKEX_ACTIVE_STOCK_URL',
    'HKEX_INACTIVE_STOCK_URL',
    'HKEX_SECURITIES_URL',
    'HKEX_STANDARD_TRANSFER_URL',
    'IdentityCandidate',
    'IdentityResult',
    'IdentityStatus',
    'JsonCommandAdapter',
    'MarketRoutingError',
    'MAX_QUALITY_LOCATOR_REFERENCES',
    'NORMALIZER_VERSION',
    'NASDAQ_LISTED_URL',
    'NASDAQ_OTHER_LISTED_URL',
    'OfficialSecurityMasterRefresher',
    'ProcessingReport',
    'ResolutionResult',
    'ResolutionStatus',
    'ROOT_KINDS',
    'RootSpec',
    'SCANNER_VERSION',
    'SEC_TICKER_URL',
    'SOURCE_RESOLVER_SCHEMA_VERSION',
    'SOURCE_REF_SCHEMA_VERSION',
    'SOURCE_ENSURE_SCHEMA_VERSION',
    'SUMMARIZER_VERSION',
    'ScanReport',
    'SECTION_EXTRACTOR_VERSION',
    'SourceCatalog',
    'SourceAcquisitionService',
    'SourceEnsureResult',
    'SourceEnsureStatus',
    'SourceHandle',
    'SourceRequest',
    'SourceResolutionError',
    'SourceResolver',
    'SourceQueryResult',
    'SourceReadError',
    'SourceRef',
    'SourceVersionReader',
    'SourceVersionIdentity',
    'VerifiedContent',
    'SecurityIdentityError',
    'SecurityIdentityResolutionError',
    'SecurityIdentityResolver',
    'SecurityMaster',
    'SecurityMasterStore',
    'SecurityMasterUnavailableError',
    'SecurityRecord',
    'load_catalog_config',
    'load_acquisition_config',
    'load_identity_master',
    'recycle_to_windows_bin',
    'narrative_evidence',
]
