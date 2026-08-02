"""Pure adapters from audited legacy parser outputs to canonical results."""

from .pdf_extract_v3 import (
    PDF_EXTRACT_V3_PARSER_NAME,
    PDFExtractV3AdapterError,
    adapt_pdf_extract_v3,
)
from .pdf_page_aware import (
    PAGE_AWARE_PDF_PARSER_NAME,
    PageAwarePDFAdapterError,
    PageAwarePDFResult,
    adapt_pdf_pages,
)

__all__ = [
    "PAGE_AWARE_PDF_PARSER_NAME",
    "PDF_EXTRACT_V3_PARSER_NAME",
    "PageAwarePDFAdapterError",
    "PageAwarePDFResult",
    "PDFExtractV3AdapterError",
    "adapt_pdf_pages",
    "adapt_pdf_extract_v3",
]
