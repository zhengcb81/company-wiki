"""R0 arm: the production RapidOCR adapter through its real isolation and
region-recovery path.

Nothing here changes production configuration: the adapter is built from the
worktree's ``config/local_ocr.json`` and executed inside the production
``IsolatedOCRAdapter`` boundary (request-owned child process, deadline, pixel
limits).  Dropped low-score regions go through the production
``recover_regions`` ladder exactly as the composition path runs it — the
weak no-recovery variant is NOT presented as the baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import serialize_lines

from company_wiki.document_normalization.local_ocr import LocalOCRConfig
from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter


def load_production_config(config_path: str | Path) -> LocalOCRConfig:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return LocalOCRConfig.from_dict(payload)


class RapidOCRR0:
    """Whole-page transcribe + bounded region recovery, production identity."""

    arm = "R0"

    def __init__(self, config: LocalOCRConfig, *, deadline_seconds: float):
        self.config = config
        self.deadline_seconds = deadline_seconds
        self.identity_manifest = dict(config.identity_manifest)
        self.identity_manifest["arm"] = self.arm
        self.identity_manifest["recovery"] = "production-bounded-source-roi"

    def run_page(self, png_path: str | Path) -> dict:
        from company_wiki.document_normalization.local_ocr import OCRLimits
        from company_wiki.document_normalization.ocr_region_recovery import (
            RecoveryBudget,
            recover_regions,
        )

        data = Path(png_path).read_bytes()
        limits = OCRLimits(deadline=self.deadline_seconds)
        with IsolatedOCRAdapter(self.config, deadline=self.deadline_seconds) as adapter:
            adapter.validate_environment()
            result = adapter.transcribe(data, limits=limits)
            recovered = ()
            diagnostics = result.region_diagnostics
            if diagnostics is not None and diagnostics.dropped:
                outcome = recover_regions(
                    ocr=adapter,
                    image_bytes=data,
                    result=result,
                    limits=limits,
                    budget=RecoveryBudget(),
                    accept_threshold=self.config.text_score,
                )
                recovered = outcome.recovered_lines
                diagnostics = outcome.diagnostics
        lines = [
            {"text": line.text, "bbox": list(line.box), "confidence": line.confidence,
             "locator_quality": "word_box"}
            for line in result.lines
        ] + [
            {"text": line.text, "bbox": list(line.box), "confidence": line.confidence,
             "locator_quality": "word_box_recovered"}
            for line in recovered
        ]
        text = "\n".join(line["text"] for line in lines)
        return {
            "status": "ok",
            "text": text,
            "lines": serialize_lines(lines),
            "width": result.width,
            "height": result.height,
            "dropped_regions": None if diagnostics is None else len(diagnostics.dropped),
            "recovery_attempts": (
                0 if diagnostics is None
                else sum(len(record.attempts) for record in diagnostics.recovery)
            ),
        }
