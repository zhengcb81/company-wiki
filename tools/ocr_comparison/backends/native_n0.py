"""N0 arm: born-digital native text extraction control.

Reads the PDF text layer with pypdfium2 for pages whose manifest role says
the page is born-digital.  This is a retrieval control only: it is never
OCR, never a scan capability, and never compared as a same-task speed winner
against a generative VLM.
"""

from __future__ import annotations

from pathlib import Path

from .base import serialize_lines, sha256_text


class NativeN0:
    arm = "N0"

    def __init__(self, sample_manifest_path: str | Path, *, gold_path: str | Path | None = None):
        import json

        self.manifest = json.loads(
            Path(sample_manifest_path).read_text(encoding="utf-8")
        )
        # R1 manifests carry absolute per-page source paths and no role; the
        # role then comes from the frozen gold.  Degraded variants are refused
        # exactly as in the legacy layout.
        self.roles = {}
        if gold_path is not None:
            gold = json.loads(Path(gold_path).read_text(encoding="utf-8"))
            self.roles = {pid: page.get("role", "eval")
                          for pid, page in gold.get("pages", {}).items()}
        self.identity_manifest = {
            "arm": self.arm,
            "backend": "pypdfium2-textpage",
            "note": "born-digital control only; not OCR",
        }

    def run_page(self, page_id: str) -> dict:
        page = next(p for p in self.manifest["pages"] if p["page_id"] == page_id)
        role = page.get("role") or self.roles.get(page_id, "eval")
        if role == "eval_degraded":
            # The degraded variant shares the same PDF page; a second native
            # read would double-count one page in the control denominators.
            return {"status": "unsupported", "error": "degraded_variant_shares_one_native_page"}
        if "doc" in page:
            import pypdfium2 as pdfium

            from ..render_pages import _resolve_physical

            pdf = pdfium.PdfDocument(_resolve_physical(self.manifest["documents"][page["doc"]]))
        else:
            # R1 layout: the page carries its own absolute source path.
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(page["pdf"])
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
