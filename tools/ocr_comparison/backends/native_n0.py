"""N0 arm: born-digital native text extraction control.

Reads the PDF text layer with pypdfium2 for pages whose manifest role says
the page is born-digital.  This is a retrieval control only: it is never
OCR, never a scan capability, and never compared as a same-task speed winner
against a generative VLM.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import serialize_lines, sha256_text


class NativeN0:
    arm = "N0"

    def __init__(self, sample_manifest_path: str | Path):
        import json

        self.manifest = json.loads(
            Path(sample_manifest_path).read_text(encoding="utf-8")
        )
        self.identity_manifest = {
            "arm": self.arm,
            "backend": "pypdfium2-textpage",
            "note": "born-digital control only; not OCR",
        }

    def run_page(self, page_id: str) -> dict:
        page = next(p for p in self.manifest["pages"] if p["page_id"] == page_id)
        if page["role"] == "eval_degraded":
            # The degraded variant shares the same PDF page; a second native
            # read would double-count one page in the control denominators.
            return {"status": "unsupported", "error": "degraded_variant_shares_one_native_page"}
        doc = self.manifest["documents"][page["doc"]]
        import pypdfium2 as pdfium

        from ..render_pages import _resolve_physical

        pdf = pdfium.PdfDocument(_resolve_physical(doc))
        try:
            text = pdf[page["pdf_page_index"]].get_textpage().get_text_bounded() or ""
        finally:
            pdf.close()
        status = "ok" if text.strip() else "empty_response"
        return {
            "status": status,
            "text": text,
            "raw_output": text,
            "raw_output_sha256": sha256_text(text),
            "lines": serialize_lines([
                {"text": text, "bbox": None, "confidence": None,
                 "locator_quality": "pdf_text_layer"},
            ]) if text.strip() else [],
        }
