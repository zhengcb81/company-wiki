"""Build historical artifacts in isolated fixtures, never as a runtime API.

The public catalog no longer writes full-document normalized/summary artifacts.
Reader, source-binding and cleanup tests still need small historical examples.
These helpers retain that fixture preparation without restoring public writers.
Their legacy generators will leave production after the final reader migration.
"""

from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.service import SourceCatalog


def legacy_normalize(catalog: SourceCatalog, **options):
    from company_wiki.source_catalog.normalizer import normalize_catalog

    with CatalogOperationLock(catalog.config.catalog_dir, operation="normalize"):
        return normalize_catalog(catalog.config, catalog.store, **options)


def legacy_summarize(catalog: SourceCatalog, **options):
    from company_wiki.source_catalog.summarizer import summarize_catalog

    with CatalogOperationLock(catalog.config.catalog_dir, operation="summarize"):
        return summarize_catalog(catalog.config, catalog.store, **options)


def legacy_summarize_with_llm(catalog: SourceCatalog, **options):
    from company_wiki.source_catalog.llm_summarizer import summarize_catalog_with_llm

    with CatalogOperationLock(catalog.config.catalog_dir, operation="summarize_llm"):
        return summarize_catalog_with_llm(catalog.config, catalog.store, **options)
