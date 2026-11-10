"""Public parser adapters for native input and audited legacy output."""

from .native_pdf import NativePdfError, read_native_pdf_prefix, validate_native_pdf
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
    "NativePdfError",
    "PAGE_AWARE_PDF_PARSER_NAME",
    "PDF_EXTRACT_V3_PARSER_NAME",
    "PageAwarePDFAdapterError",
    "PageAwarePDFResult",
    "PDFExtractV3AdapterError",
    "adapt_pdf_pages",
    "adapt_pdf_extract_v3",
    "read_native_pdf_prefix",
    "validate_native_pdf",
]
