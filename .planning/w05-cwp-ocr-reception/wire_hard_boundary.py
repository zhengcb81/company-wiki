"""One-shot ROOT integration seam; run only in the assigned integration tree."""
from pathlib import Path

project = Path(__file__).resolve().parents[2]
tree = project.parent / '_harness_worktrees/w05/cwp-ocr-root'
path = tree/'src/company_wiki/document_normalization/ocr_composition.py'
raw = path.read_bytes()
text = raw.decode('utf-8')
eol = '\r\n' if '\r\n' in text else '\n'
text = text.replace('\r\n','\n')
assert text.count('def enrich_pptx(')==1 and 'def _enrich_pptx(' not in text
text=text.replace('def enrich_pptx(', 'def _enrich_pptx(', 1)
marker='def _enrich_pptx('
wrapper='''def enrich_pptx(
    document: NormalizedDocument,
    *,
    ocr: OCRAdapter,
    limits,
    ocr_limits: OCRLimits | None = None,
    selected_media_sha256s: frozenset[str] | None = None,
):
    """Compose configured native OCR behind one reusable hard process boundary.

    The backend adapter remains a cooperative primitive. Public normalization
    and replay passing that configured adapter get a request-owned child for
    preflight, full images and ROI attempts, closed before this call returns.
    Protocol adapters and already-isolated clients retain their own boundary.
    """
    from .local_ocr import LocalOCRAdapter

    if type(ocr) is LocalOCRAdapter:
        from .isolated_ocr import IsolatedOCRAdapter

        deadlines = [
            value for value in (
                limits.deadline,
                None if ocr_limits is None else ocr_limits.deadline,
            ) if value is not None
        ]
        deadline = min(deadlines) if deadlines else None
        with IsolatedOCRAdapter(ocr.config, deadline=deadline) as bounded:
            return _enrich_pptx(
                document, ocr=bounded, limits=limits, ocr_limits=ocr_limits,
                selected_media_sha256s=selected_media_sha256s,
            )
    return _enrich_pptx(
        document, ocr=ocr, limits=limits, ocr_limits=ocr_limits,
        selected_media_sha256s=selected_media_sha256s,
    )


'''
text=text.replace(marker,wrapper+marker,1)
path.write_bytes(text.replace('\n',eol).encode('utf-8'))
print('wired configured OCR hard boundary',path)
