"""Byte-only native PDF operations for callers that do not need normalization."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Literal

__all__ = ["NativePdfError", "read_native_pdf_pages", "read_native_pdf_prefix", "validate_native_pdf"]


class NativePdfError(ValueError):
    """The native PDF backend could not read the supplied document."""

    def __init__(
        self, message: str, *,
        reason: Literal["unreadable", "page_limit", "encrypted", "text_limit"] = "unreadable",
    ) -> None:
        super().__init__(message)
        self.reason = reason


@contextmanager
def _open_pdf(data: bytes) -> Iterator[Any]:
    import pymupdf

    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise NativePdfError("invalid PDF") from exc
    with document:
        if document.page_count < 1:
            raise NativePdfError("PDF has no pages")
        yield document


def validate_native_pdf(data: bytes) -> None:
    """Check that the byte buffer opens as a PDF with at least one page."""
    with _open_pdf(data):
        pass


def read_native_pdf_pages(
    data: bytes, *, max_pages: int, max_text_characters: int,
) -> tuple[str, ...]:
    """Read the complete physical page sequence, or fail without a partial result."""
    pages: list[str] = []
    text_characters = 0
    try:
        with _open_pdf(data) as document:
            if document.is_encrypted:
                raise NativePdfError("PDF is encrypted", reason="encrypted")
            if document.page_count > max_pages:
                raise NativePdfError("PDF page limit exceeded", reason="page_limit")
            for page in document:
                text = page.get_text("text")
                text_characters += len(text)
                if text_characters > max_text_characters:
                    raise NativePdfError("PDF text limit exceeded", reason="text_limit")
                pages.append(text)
    except (ImportError, NativePdfError):
        raise
    except Exception as exc:
        raise NativePdfError("unreadable PDF") from exc
    return tuple(pages)


def read_native_pdf_prefix(
    data: bytes, *, max_pages: int, max_chars_per_page: int, checkpoint: Callable[[], None],
) -> tuple[str, ...]:
    """Return the requested prefix in physical page order, including empty pages."""
    checkpoint()
    pages: list[str] = []
    with _open_pdf(data) as document:
        for number in range(min(max_pages, document.page_count)):
            checkpoint()
            try:
                pages.append(document[number].get_text("text")[:max_chars_per_page])
            except (RuntimeError, ValueError) as exc:
                raise NativePdfError("unreadable PDF page") from exc
    return tuple(pages)
