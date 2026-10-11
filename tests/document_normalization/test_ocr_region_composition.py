"""Composition integration: diagnostics feed, recovered units, shared budget.

The composer must consume the adapter's region diagnostics, run the bounded
recovery once per unique media, emit recovered lines as real units with
continuous locators, keep unrecovered regions as visible quality counts, and
charge ROI pixels against the request-wide OCR budget.
"""

from __future__ import annotations

import hashlib
import io
import json

import pytest

from company_wiki import document_normalization as dn
from company_wiki.document_normalization.local_ocr import (
    ImageOCRResult,
    OCRLimits,
    OCRLine,
    OCRDroppedRegion,
    OCRRegionDiagnostics,
)
from conftest import build_pptx, sha256_hex, source_id_for

MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
REGION = (10.0, 20.0, 300.0, 52.0)


def text_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46))):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for x0, y0, x1, y1 in blocks:
        draw.rectangle([x0, y0, x1, y1], fill=(10, 10, 10))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class RecoveryFakeOCR:
    """Content-addressed fake: responds by image size; full image carries
    two accepted lines plus one dropped business region."""

    def __init__(self, crop_lines, crop_size, full_size=(320, 80), crop_error=None):
        self.crop_lines = crop_lines
        self.crop_size = crop_size
        self.full_size = full_size
        self.crop_error = crop_error
        self.calls = []
        self.identity_manifest = {"adapter": "fake-composition-recovery/1"}
        self.fingerprint = hashlib.sha256(
            json.dumps(self.identity_manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _full(self):
        return ImageOCRResult(
            *self.full_size,
            (
                OCRLine("FY27 Segment changes title", (0.0, 0.0, 300.0, 12.0), 0.99),
                OCRLine("Industry solutions brings together offerings", (0.0, 60.0, 300.0, 76.0), 0.98),
            ),
            OCRRegionDiagnostics(
                detected=None,
                recognized=3,
                accepted=2,
                dropped=(
                    OCRDroppedRegion(REGION, 0.43236, " l s os i a i s", "low_text_score"),
                ),
            ),
        )

    def transcribe(self, data, *, limits):
        from PIL import Image

        self.calls.append(Image.open(io.BytesIO(data)).size)
        size = self.calls[-1]
        if size == self.full_size:
            return self._full()
        if size == self.crop_size:
            if self.crop_error is not None:
                raise self.crop_error
            return ImageOCRResult(size[0], size[1], tuple(self.crop_lines))
        raise AssertionError(f"unexpected crop size {size}")


def normalize(data, ocr, **kwargs):
    return dn.normalize_document(
        data,
        source_id=source_id_for(data),
        source_sha256=sha256_hex(data),
        mime_type=MIME,
        ocr=ocr,
        **kwargs,
    )


def picture_deck():
    """One slide whose only shape is the synthetic 320x80 text image."""
    from pptx import Presentation
    from pptx.util import Emu

    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_picture(io.BytesIO(text_png()), Emu(0), Emu(0), Emu(9144000), Emu(2286000))
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def crop_size_for(fake):
    from company_wiki.document_normalization.ocr_region_recovery import (
        MARGIN_RATIO,
        build_margin_crop,
    )

    _, transform = build_margin_crop(io.BytesIO(text_png()), REGION, margin_ratio=MARGIN_RATIO)
    return transform["size"]


def test_composer_emits_recovered_unit_with_flags_locator_and_counts():
    size = crop_size_for(None)
    line = OCRLine(
        "We will transition to two reporting segments for FY27",
        (2.0, 4.0, 286.0, 26.0),
        0.989,
    )
    fake = RecoveryFakeOCR((line,), size)
    doc = normalize(picture_deck(), fake)
    ocr_units = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"]
    assert [u.raw_text for u in ocr_units][-1] == line.text
    assert len(ocr_units) == 3
    recovered = ocr_units[-1]
    assert "ocr_recovered" in recovered.quality_flags
    assert recovered.metadata["ocr_recovered"] is True
    assert recovered.metadata["ocr_confidence"] == pytest.approx(0.989)
    # mapped back into original image coordinates inside the dropped region
    bx = recovered.metadata["ocr_box"]
    assert REGION[0] <= bx[0] and bx[2] <= REGION[2] + 1
    assert recovered.metadata["source_locator"].startswith("cwp-pptx-image-ocr/1|")
    assert "|l=2|" in recovered.metadata["source_locator"]
    page = doc.metadata["ocr"]["pages"][0]
    assert page["recovered_lines"] == 1
    assert page["unrecovered_regions"] == 0
    image_record = page["images"][0]
    assert image_record["dropped_regions"] == 1
    assert image_record["recovery_attempts"] == 1
    assert doc.metadata["ocr"]["region_recovery"]["attempts"] == 1
    assert doc.metadata["ocr"]["region_recovery"]["recovered_lines"] == 1
    assert fake.calls == [(320, 80), size]


def test_unrecovered_region_surfaces_quality_counts_and_keeps_good_lines():
    size = crop_size_for(None)
    fake = RecoveryFakeOCR(
        (OCRLine("g ar b l ed", (0.0, 0.0, 280.0, 30.0), 0.44),),
        size,
        # second attempt (split-stack, aspect 9.06) also low score
    )
    # split-stack response: same size as upscale? aspect>=4 -> split-stack; the
    # fake rejects unknown sizes -> AssertionError. Give it a low-score result
    # by mapping any crop size to a below-threshold line instead.
    fake.transcribe = lambda data, *, limits: _any_crop_low(fake, data)
    doc = normalize(picture_deck(), fake)
    units = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"]
    assert len(units) == 2  # no garbled or recovered line added
    assert all("ocr_recovered" not in u.quality_flags for u in units)
    page = doc.metadata["ocr"]["pages"][0]
    assert page["unrecovered_regions"] == 1
    assert page["recovery_attempts"] == 2
    assert page["status"] == "recognized"
    image_record = page["images"][0]
    diagnostics = image_record["region_diagnostics"]
    assert diagnostics["dropped"][0]["reason"] == "low_text_score"
    assert diagnostics["recovery"][0]["status"] == "unrecovered"
    assert len(diagnostics["recovery"][0]["attempts"]) == 2
    assert doc.metadata["ocr"]["region_recovery"]["unrecovered_regions"] == 1


def _any_crop_low(fake, data):
    from PIL import Image

    fake.calls.append(Image.open(io.BytesIO(data)).size)
    size = fake.calls[-1]
    if size == fake.full_size:
        return fake._full()
    return ImageOCRResult(
        size[0], size[1], (OCRLine("l o w  g o t", (0.0, 0.0, 10.0, 10.0), 0.30),)
    )


def test_roi_pixels_are_charged_request_wide_not_per_image():
    from PIL import Image as PILImage
    from pptx import Presentation
    from pptx.util import Emu

    def deck_with(two_pictures):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_picture(
            io.BytesIO(text_png()), Emu(0), Emu(0), Emu(4572000), Emu(1143000)
        )
        if two_pictures:
            other = PILImage.new("RGB", (640, 160), (255, 255, 255))
            buf = io.BytesIO()
            other.save(buf, format="PNG")
            slide.shapes.add_picture(io.BytesIO(buf.getvalue()), Emu(4572000), Emu(0), Emu(4572000), Emu(1143000))
        buffer = io.BytesIO()
        presentation.save(buffer)
        return buffer.getvalue()

    line = OCRLine("recovered body", (2.0, 4.0, 286.0, 26.0), 0.989)

    class TwoImageFake(RecoveryFakeOCR):
        def __init__(self):
            super().__init__((line,), crop_size_for(None))
            self.fulls = 0

        def transcribe(self, data, *, limits):
            from PIL import Image

            size = Image.open(io.BytesIO(data)).size
            self.calls.append(size)
            if size in ((320, 80), (640, 160)):
                self.fulls += 1
                return ImageOCRResult(
                    size[0],
                    size[1],
                    (OCRLine("kept line", (0.0, 0.0, 100.0, 12.0), 0.99),),
                    OCRRegionDiagnostics(
                        detected=None,
                        recognized=2,
                        accepted=1,
                        dropped=(OCRDroppedRegion(REGION, 0.43236, "x", "low_text_score"),),
                    ),
                )
            return ImageOCRResult(size[0], size[1], (line,))

    fake = TwoImageFake()
    data = deck_with(True)
    # 320*80 + 640*160 = 133120 full pixels; first recovery crop adds more;
    # cap the budget so the second image's ROI pixels must cross the line.
    first_roi = crop_size_for(None)[0] * crop_size_for(None)[1]
    cap = 320 * 80 + 640 * 160 + first_roi + 1
    with pytest.raises(dn.NormalizationLimitError, match="max_total_pixels"):
        normalize(data, fake, ocr_limits=OCRLimits(max_total_pixels=cap))
    assert fake.calls == [(320, 80), crop_size_for(None), (640, 160)]
    # the same deck parses when recovery fits the shared budget
    fake2 = TwoImageFake()
    doc = normalize(data, fake2, ocr_limits=OCRLimits(max_total_pixels=cap * 2))
    assert fake2.fulls == 2
    assert doc.metadata["ocr"]["region_recovery"]["recovered_lines"] == 2


def test_recovery_runs_once_per_unique_media():
    data = build_pptx(with_picture_only_slide=True, with_duplicate_picture=True)
    # tiny_png 1x1: reuse generic fake producing diagnostics + recovery
    size = (1, 1)

    class TinyFake(RecoveryFakeOCR):
        def __init__(self):
            super().__init__((), size, full_size=(1, 1))
            self.total = 0

        def transcribe(self, data, *, limits):
            self.total += 1
            return ImageOCRResult(
                1,
                1,
                (OCRLine("tiny line", (0.0, 0.0, 1.0, 1.0), 0.99),),
                OCRRegionDiagnostics(
                    detected=None, recognized=1, accepted=1, dropped=()
                ),
            )

    fake = TinyFake()
    normalize(data, fake)
    assert fake.total == 1  # one unique media -> one transcribe, no recovery


def test_old_adapters_without_diagnostics_are_unchanged():
    data = build_pptx(with_picture_only_slide=True)

    class OldFake:
        def __init__(self):
            self.calls = 0
            self.identity_manifest = {"adapter": "old-fake/1"}
            self.fingerprint = hashlib.sha256(
                json.dumps(
                    self.identity_manifest, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()

        def transcribe(self, data, *, limits):
            self.calls += 1
            return ImageOCRResult(
                1, 1, (OCRLine("We launched a new product", (0.0, 0.0, 1.0, 1.0), 0.95),)
            )

    fake = OldFake()
    doc = normalize(data, fake)
    lines = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"]
    assert len(lines) == 1 and fake.calls == 1
    assert doc.metadata["ocr"]["region_recovery"]["attempts"] == 0


def test_replay_round_trips_recovered_unit_with_identical_metadata():
    line = OCRLine(
        "Productivity and server licensing brings together offerings",
        (2.0, 4.0, 286.0, 26.0),
        0.986,
    )
    fake = RecoveryFakeOCR((line,), crop_size_for(None))
    data = picture_deck()
    doc = normalize(data, fake)
    recovered = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"][-1]
    fresh = RecoveryFakeOCR((line,), crop_size_for(None))
    assert (
        dn.replay_unit(
            data,
            source_sha256=sha256_hex(data),
            unit=recovered,
            limits=dn.NormalizationLimits(),
            ocr=fresh,
        )
        == recovered.raw_text
    )
    assert fresh.calls == [(320, 80), crop_size_for(None)]


def test_recovered_duplicate_of_accepted_line_is_not_emitted():
    # accepted line overlaps the dropped region entirely: recovery answer that
    # duplicates it must not create a second unit nor remove the original
    class OverlapFake(RecoveryFakeOCR):
        def _full(self):
            return ImageOCRResult(
                320,
                80,
                (
                    OCRLine(
                        "Industry solutions brings together offerings",
                        REGION,
                        0.98,
                    ),
                ),
                OCRRegionDiagnostics(
                    detected=None,
                    recognized=2,
                    accepted=1,
                    dropped=(
                        OCRDroppedRegion(REGION, 0.43236, "l o w", "low_text_score"),
                    ),
                ),
            )

    line = OCRLine(
        "Industry solutions brings together offerings",
        (2.0, 4.0, 286.0, 26.0),
        0.98,
    )

    class AnyCropOverlapFake(OverlapFake):
        def transcribe(self, data, *, limits):
            from PIL import Image

            size = Image.open(io.BytesIO(data)).size
            self.calls.append(size)
            if size == self.full_size:
                return self._full()
            if size == self.crop_size:
                return ImageOCRResult(size[0], size[1], tuple(self.crop_lines))
            # attempt 2 (upscale): same duplicate content, larger canvas
            scaled = OCRLine(
                self.crop_lines[0].text,
                (self.crop_lines[0].box[0], self.crop_lines[0].box[1],
                 self.crop_lines[0].box[2] * 2, self.crop_lines[0].box[3] * 2),
                self.crop_lines[0].confidence,
            )
            return ImageOCRResult(size[0], size[1], (scaled,))

    fake = AnyCropOverlapFake((line,), crop_size_for(None))
    doc = normalize(picture_deck(), fake)
    units = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"]
    assert len(units) == 1
    assert units[0].raw_text == "Industry solutions brings together offerings"
    assert doc.metadata["ocr"]["region_recovery"]["recovered_lines"] == 0



def test_recovery_pixel_budget_rejects_before_roi_inference():
    size = crop_size_for(None)
    fake = RecoveryFakeOCR((OCRLine("Recovered complete line", (2., 12., 280., 35.), .99),), size)
    with pytest.raises(dn.NormalizationLimitError, match="max_total_pixels"):
        normalize(picture_deck(), fake, ocr_limits=OCRLimits(max_total_pixels=320*80+1))
    assert fake.calls == [(320, 80)]
