"""W23 Xiaomi-vs-RapidOCR comparison tooling (experiment-only; no production wiring).

Arms:
  R0  production LocalOCRAdapter (RapidOCR CPU) incl. region recovery,
      identity-frozen by config/local_ocr.json.
  X1  Xiaomi-OCR-0 whole-page generation through the upstream processor,
      prompt, non-thinking chat template and postprocess on CPU transformers.
  X2  two-stage (layout + region) variant; only when resource bounds allow,
      otherwise NOT_RUN with a reason.
  N0  born-digital native text extraction control (never presented as OCR).

This package never modifies production code and is imported only by the
W23 tests and runner scripts.
"""
