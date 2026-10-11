"""Bounded ROI recovery: planning, transforms, back-mapping, stitching, budget.

All backends are fakes over synthetic PNG bytes; no model, no network.  The
acceptance threshold is never lowered: recovered lines must pass the same
text_score that dropped the region originally.
"""

from __future__ import annotations

import hashlib
import io
import json
import time

import pytest

from company_wiki.document_normalization.local_ocr import (
    ImageOCRResult,
    LocalOCRError,
    NormalizationLimitError,
    OCRLine,
    OCRLimits,
    OCRDroppedRegion,
    OCRRegionDiagnostics,
    OCRRegionRecovery,
    OCRRecoveryAttempt,
)
from company_wiki.document_normalization import ocr_region_recovery as rr

THRESHOLD = 0.5
WIDE = (10.0, 20.0, 300.0, 52.0)  # 290x32 aspect 9.1


def strip_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46))):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for x0, y0, x1, y1 in blocks:
        draw.rectangle([x0, y0, x1, y1], fill=(10, 10, 10))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def dropped(box, score=0.43, text="g ar b l ed", reason="low_text_score"):
    return OCRDroppedRegion(box, score, text, reason)


def result_with(dropped_regions, lines=(), width=320, height=80):
    return ImageOCRResult(
        width,
        height,
        tuple(lines),
        OCRRegionDiagnostics(
            detected=None,
            recognized=len(dropped_regions) + len(lines),
            accepted=len(lines),
            dropped=tuple(dropped_regions),
        ),
    )


class FakeOCR:
    """Content-addressed fake: responds per input-image pixel size."""

    def __init__(self, responses):
        # responses: {(w, h): ImageOCRResult | LocalOCRError}
        self.responses = responses
        self.calls = []
        self.identity_manifest = {"adapter": "fake-recovery/1"}
        self.fingerprint = hashlib.sha256(
            json.dumps(self.identity_manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def transcribe(self, data, *, limits):
        from PIL import Image

        self.calls.append(data)
        size = Image.open(io.BytesIO(data)).size
        action = self.responses[size]
        if isinstance(action, Exception):
            raise action
        return action


def crop_result(lines, width, height):
    return ImageOCRResult(width, height, tuple(lines))


def test_plan_selects_score_band_geometry_and_order():
    regions = [
        dropped((0, 0, 69, 17), score=0.458, text="·"),  # bullet: too narrow
        dropped((0, 0, 400, 20), score=0.05),  # hopeless floor
        dropped((0, 0, 400, 20), score=0.6),  # already above threshold
        dropped((0, 0, 40, 20), score=0.4),  # width below minimum
        dropped((0, 0, 300, 6), score=0.4),  # height below minimum
        dropped((0, 0, 60, 20), score=0.4),  # aspect below minimum
        dropped(WIDE, score=0.43236),
        dropped((20.0, 100.0, 340.0, 132.0), score=0.44278),
    ]
    diagnostics = OCRRegionDiagnostics(None, len(regions), 0, tuple(regions))
    assert rr.plan_regions(diagnostics, accept_threshold=THRESHOLD) == (7, 6)


def test_plan_caps_regions_per_image():
    regions = [
        dropped((float(i * 400), 0.0, float(i * 400 + 300), 30.0), score=0.3 + i * 0.01)
        for i in range(6)
    ]
    diagnostics = OCRRegionDiagnostics(None, len(regions), 0, tuple(regions))
    budget = rr.RecoveryBudget()  # default 4 regions per image
    assert (
        len(
            rr.plan_regions(
                diagnostics,
                accept_threshold=THRESHOLD,
                max_regions=budget.max_regions_per_image,
            )
        )
        == 4
    )


def test_margin_crop_roundtrip_maps_box_by_translation():
    image = strip_png()
    data, transform = rr.build_margin_crop(io.BytesIO(image), WIDE, margin_ratio=0.35)
    from PIL import Image

    crop = Image.open(io.BytesIO(data))
    # vertical margin 0.35 * 32 = 11.2 -> clamped ints; origin is translation only
    assert transform["transform"] == rr.MARGIN_CROP_TRANSFORM
    assert crop.size[0] == int(WIDE[2] - WIDE[0])
    mapped = rr.map_box(transform, (5.0, 7.0, 280.0, 30.0))
    assert mapped is not None
    assert mapped[0] == pytest.approx(WIDE[0] + 5.0, abs=1e-6)
    assert mapped[1] == pytest.approx(transform["origin"][1] + 7.0, abs=1e-6)
    assert mapped[2] == pytest.approx(WIDE[0] + 280.0, abs=1e-6)


def test_split_stack_chunks_gap_detection_and_chunk_mapping():
    # two text blocks separated by a 20px whitespace gap
    image = strip_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46)))
    region = (10.0, 28.0, 262.0, 48.0)
    data, transform = rr.build_split_stack(io.BytesIO(image), region)
    from PIL import Image

    stack = Image.open(io.BytesIO(data))
    assert transform["transform"] == rr.SPLIT_STACK_TRANSFORM
    chunks = transform["chunks"]
    assert len(chunks) >= 2
    # mapping a box inside stacked chunk 1 back lands inside the crop window
    # (region plus vertical margin), translated by the chunk's crop offset
    sx0, sy0, ox, oy, cx0, cx1 = chunks[0]
    assert cx1 > cx0
    mapped = rr.map_box(transform, (2.0, sy0 + 3.0, 40.0, sy0 + 15.0))
    assert mapped is not None
    assert 10.0 <= mapped[0] < 262.0
    assert 21.0 <= mapped[1] < 55.0  # crop window y range with 0.35 margin
    assert stack.size == transform["size"]


def test_upscale_maps_box_with_scale():
    image = strip_png()
    region = (10.0, 20.0, 170.0, 52.0)  # crop 160x54 (margin) -> 320x108
    data, transform = rr.build_upscale(io.BytesIO(image), region, factor=2.0)
    from PIL import Image

    up = Image.open(io.BytesIO(data))
    assert up.size == (320, 108)
    mapped = rr.map_box(transform, (20.0, 10.0, 100.0, 40.0))
    assert mapped == pytest.approx((20.0, 14.0, 60.0, 29.0))


def test_map_box_matrix_rotate_padding_and_invalid():
    # Inverse PIL CCW rotation uses the pre-rotation width (40), not height.
    t90 = {"kind": "rotate", "angle": 90, "size": (40, 20)}
    assert rr.map_box(t90, (0.0, 0.0, 10.0, 4.0)) == pytest.approx((36.0, 0.0, 40.0, 10.0))
    t180 = {"kind": "rotate", "angle": 180, "size": (40, 20)}
    assert rr.map_box(t180, (2.0, 3.0, 10.0, 8.0)) == pytest.approx((30.0, 12.0, 38.0, 17.0))
    pad = {"kind": "pad", "top": 4, "left": 6}
    assert rr.map_box(pad, (1.0, 2.0, 3.0, 4.0)) == (-5.0, -2.0, -3.0, 0.0)
    assert rr.map_box({"kind": "translate", "origin": (1.0, 2.0)}, (0, 0, 1, 1)) == (1.0, 2.0, 2.0, 3.0)
    for bad_box in ((5.0, 0.0, 1.0, 1.0), (0.0, 0.0, float("nan"), 1.0), (0.0, 0.0, 1.0, 2.0, 3.0)):
        assert rr.map_box({"kind": "translate", "origin": (0.0, 0.0)}, bad_box) is None


def test_recover_accepts_margin_crop_line_and_reports_records():
    image = strip_png()
    full = result_with([dropped(WIDE, score=0.43236)])
    crop_w = int(WIDE[2] - WIDE[0])
    _, transform = rr.build_margin_crop(io.BytesIO(image), WIDE)
    crop_h = transform["size"][1]
    recovered_line = OCRLine("We will transition", (4.0, 9.0, 280.0, 26.0), 0.989)
    ocr = FakeOCR({(320, 80): full, (crop_w, crop_h): crop_result((recovered_line,), crop_w, crop_h)})
    budget = rr.RecoveryBudget()
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=budget,
        accept_threshold=THRESHOLD,
    )
    assert [line.text for line in outcome.recovered_lines] == ["We will transition"]
    mapped = outcome.recovered_lines[0].box
    assert (WIDE[0] + 4.0, transform["origin"][1] + 9.0) == (mapped[0], mapped[1])
    record = outcome.diagnostics.recovery[0]
    assert record.status == "recovered"
    assert record.recovered_confidence == pytest.approx(0.989)
    assert record.attempts[0].transform == rr.MARGIN_CROP_TRANSFORM
    assert record.attempts[0].outcome == "accepted"
    assert budget.total_attempts == 1
    assert budget.total_roi_pixels == crop_w * crop_h
    assert outcome.attempts == 1 and outcome.roi_pixels == crop_w * crop_h


def test_recover_rejects_below_threshold_and_garbled_stitching():
    image = strip_png()
    full = result_with([dropped(WIDE, score=0.43236)])
    # attempt 1 (margin crop) returns a low-score line; the WIDE crop is
    # 290x54 (5.4 aspect) so it will not be split and attempt 2 is upscale,
    # which also returns a below-threshold line
    margin_transform = rr.build_margin_crop(io.BytesIO(image), WIDE)[1]
    up = rr.build_upscale(io.BytesIO(image), WIDE)
    responses = {
        (320, 80): full,
        margin_transform["size"]: crop_result(
            (OCRLine("g ar b l ed", (0.0, 0.0, 280.0, 30.0), 0.44),),
            *margin_transform["size"],
        ),
        up[1]["size"]: crop_result(
            (OCRLine("g a r b a g e", (0.0, 0.0, 500.0, 60.0), 0.41),),
            *up[1]["size"],
        ),
    }
    ocr = FakeOCR(responses)
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    assert outcome.recovered_lines == ()
    record = outcome.diagnostics.recovery[0]
    assert record.status == "unrecovered"
    assert [a.outcome for a in record.attempts] == ["rejected", "rejected"]
    assert record.attempts[0].transform == rr.MARGIN_CROP_TRANSFORM
    assert record.attempts[1].transform == rr.UPSCALE_TRANSFORM
    assert record.attempts[0].note == "line_below_threshold"
    assert ocr.calls and all(isinstance(c, bytes) for c in ocr.calls)


def test_recover_split_stack_all_chunks_pass_stitches_in_reading_order():
    image = strip_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46)))
    region = (10.0, 28.0, 262.0, 48.0)
    full = result_with([dropped(region, score=0.44)], width=320, height=80)
    margin_transform = rr.build_margin_crop(io.BytesIO(image), region)[1]
    stack_bytes, stack_transform = rr.build_split_stack(io.BytesIO(image), region)
    chunk_lines = []
    for sx0, sy0, ox, oy, cx0, cx1 in stack_transform["chunks"]:
        chunk_lines.append(OCRLine("part", (1.0, sy0 + 4.0, min(100.0, cx1 - cx0 - 1.0), sy0 + 16.0), 0.99))
    responses = {
        (320, 80): full,
        (int(region[2] - region[0]), margin_transform["size"][1]): crop_result(
            (OCRLine("low", (0, 0, 10, 10), 0.30),),
            int(region[2] - region[0]),
            margin_transform["size"][1],
        ),
        stack_transform["size"]: crop_result(tuple(chunk_lines), *stack_transform["size"]),
    }
    outcome = rr.recover_regions(
        ocr=FakeOCR(responses),
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    assert outcome.recovered_lines and outcome.recovered_lines[0].text == "part part"
    assert outcome.diagnostics.recovery[0].attempts[-1].outcome == "accepted"


def test_split_stack_with_failing_chunk_is_rejected_not_stitched():
    image = strip_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46)))
    region = (10.0, 28.0, 262.0, 48.0)  # crop 252x34 -> 7.4 aspect: will split
    full = result_with([dropped(region, score=0.44)], width=320, height=80)
    margin_transform = rr.build_margin_crop(io.BytesIO(image), region)[1]
    _stack_bytes, stack_transform = rr.build_split_stack(io.BytesIO(image), region)
    responses = {
        (320, 80): full,
        margin_transform["size"]: crop_result(
            (OCRLine("low", (0, 0, 10, 10), 0.30),), *margin_transform["size"]
        ),
        stack_transform["size"]: crop_result(
            (
                # chunk 1 passes
                OCRLine("Productivity and server", (1.0, 5.0, 70.0, 15.0), 0.99),
                # chunk 2 has one passing and one garbled line -> whole attempt rejected
                OCRLine("nsing", (1.0, 47.0, 120.0, 55.0), 0.98),
                OCRLine("+..", (1.0, 56.0, 60.0, 64.0), 0.32),
            ),
            *stack_transform["size"],
        ),
    }
    outcome = rr.recover_regions(
        ocr=FakeOCR(responses),
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    record = outcome.diagnostics.recovery[0]
    assert record.status == "unrecovered"
    assert record.attempts[1].transform == rr.SPLIT_STACK_TRANSFORM
    assert record.attempts[1].note == "line_below_threshold"
    assert outcome.recovered_lines == ()


def test_recover_low_aspect_uses_upscale_as_second_attempt():
    image = strip_png(width=320, height=80, blocks=((12, 20, 150, 70),))
    region = (10.0, 18.0, 152.0, 72.0)  # 142x54 aspect 2.63 < 4
    full = result_with([dropped(region, score=0.42)], width=320, height=80)
    margin_transform = rr.build_margin_crop(io.BytesIO(image), region)[1]
    up_bytes, up_transform = rr.build_upscale(io.BytesIO(image), region)
    responses = {
        (320, 80): full,
        (int(region[2] - region[0]), margin_transform["size"][1]): crop_result(
            (OCRLine("x", (0, 0, 5, 5), 0.2),),
            int(region[2] - region[0]),
            margin_transform["size"][1],
        ),
        up_transform["size"]: crop_result(
            (OCRLine("tall label recovered", (10.0, 20.0, 260.0, 90.0), 0.95),),
            *up_transform["size"],
        ),
    }
    outcome = rr.recover_regions(
        ocr=FakeOCR(responses),
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    record = outcome.diagnostics.recovery[0]
    assert record.status == "recovered"
    assert [a.transform for a in record.attempts] == [
        rr.MARGIN_CROP_TRANSFORM,
        rr.UPSCALE_TRANSFORM,
    ]
    mapped = outcome.recovered_lines[0].box
    assert mapped[0] == pytest.approx(region[0] + 5.0)
    assert mapped[2] == pytest.approx(region[0] + 130.0)


def test_recovered_duplicate_of_accepted_line_is_rejected_not_duplicated():
    accepted = OCRLine("Accepted body line", (0.0, 20.0, 300.0, 52.0), 0.99)
    full = result_with([dropped(WIDE, score=0.43)], lines=(accepted,))
    image = strip_png()
    transform = rr.build_margin_crop(io.BytesIO(image), WIDE)[1]
    up = rr.build_upscale(io.BytesIO(image), WIDE)
    duplicate = OCRLine("Accepted body line", (0.0, 5.0, 286.0, 29.0), 0.99)
    duplicate_up = OCRLine("Accepted body line", (0.0, 10.0, 572.0, 58.0), 0.99)
    ocr = FakeOCR(
        {
            (320, 80): full,
            transform["size"]: crop_result((duplicate,), *transform["size"]),
            up[1]["size"]: crop_result((duplicate_up,), *up[1]["size"]),
        }
    )
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    assert outcome.recovered_lines == ()
    assert full.lines == (accepted,)  # originals never removed
    record = outcome.diagnostics.recovery[0]
    assert record.status == "unrecovered"
    assert [a.note for a in record.attempts] == [
        "overlaps_accepted_line",
        "overlaps_accepted_line",
    ]


def test_budget_exhaustion_before_second_attempt_is_recorded():
    image = strip_png()
    full = result_with([dropped(WIDE, score=0.43)])
    transform = rr.build_margin_crop(io.BytesIO(image), WIDE)[1]
    ocr = FakeOCR(
        {
            (320, 80): full,
            (int(WIDE[2] - WIDE[0]), transform["size"][1]): crop_result(
                (OCRLine("low", (0, 0, 5, 5), 0.2),),
                int(WIDE[2] - WIDE[0]),
                transform["size"][1],
            ),
        }
    )
    budget = rr.RecoveryBudget(max_attempts_per_image=1)
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=budget,
        accept_threshold=THRESHOLD,
    )
    record = outcome.diagnostics.recovery[0]
    assert record.status == "budget_exhausted"
    assert len(record.attempts) == 1
    assert len(ocr.calls) == 1  # only the margin-crop attempt ran


def test_deadline_between_attempts_propagates_without_partial_recovery():
    image = strip_png()
    full = result_with([dropped(WIDE, score=0.43)])
    transform = rr.build_margin_crop(io.BytesIO(image), WIDE)[1]
    ocr = FakeOCR(
        {
            (320, 80): full,
            (int(WIDE[2] - WIDE[0]), transform["size"][1]): crop_result(
                (OCRLine("low", (0, 0, 5, 5), 0.2),),
                int(WIDE[2] - WIDE[0]),
                transform["size"][1],
            ),
        }
    )
    clock = iter([10.0, 10.0, 10.0, 999.0])
    real_monotonic = time.monotonic

    def fake_monotonic():
        try:
            return next(clock)
        except StopIteration:
            return real_monotonic()

    monkeypatched = pytest.MonkeyPatch()
    monkeypatched.setattr(time, "monotonic", fake_monotonic)
    try:
        with pytest.raises(NormalizationLimitError, match="deadline"):
            rr.recover_regions(
                ocr=ocr,
                image_bytes=image,
                result=full,
                limits=OCRLimits(deadline=500.0),
                budget=rr.RecoveryBudget(),
                accept_threshold=THRESHOLD,
            )
    finally:
        monkeypatched.undo()


def test_engine_failure_attempt_is_recorded_and_ladder_continues():
    image = strip_png(width=320, height=80, blocks=((12, 30, 90, 46), (110, 30, 260, 46)))
    region = (10.0, 28.0, 262.0, 48.0)  # crop 252x34: splits for attempt 2
    full = result_with([dropped(region, score=0.43)], width=320, height=80)
    transform = rr.build_margin_crop(io.BytesIO(image), region)[1]
    stack = rr.build_split_stack(io.BytesIO(image), region)
    stack_lines = (
        OCRLine("recovered via stack", (1.0, 4.0, 70.0, 30.0), 0.97),
        OCRLine("chunk two", (1.0, 46.0, 150.0, 60.0), 0.96),
    )
    ocr = FakeOCR(
        {
            (320, 80): full,
            transform["size"]: LocalOCRError("OCR_IMAGE_INVALID"),
            stack[1]["size"]: ImageOCRResult(
                stack[1]["size"][0], stack[1]["size"][1], stack_lines
            ),
        }
    )
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    record = outcome.diagnostics.recovery[0]
    assert record.status == "recovered"
    assert record.attempts[0].outcome == "error"
    assert record.attempts[0].error == "OCR_IMAGE_INVALID"
    assert record.attempts[1].transform == rr.SPLIT_STACK_TRANSFORM
    assert record.recovered_text == "recovered via stack chunk two"


def test_unattempted_regions_carry_not_attempted_status():
    image = strip_png(width=2400, height=80, blocks=((12, 30, 90, 46),))
    wide = (10.0, 20.0, 310.0, 60.0)
    regions = [dropped(wide, score=0.43)] + [
        dropped((float(400 + i * 400), 0.0, float(400 + i * 400 + 60), 30.0), score=0.3)
        for i in range(4)
    ]
    full = ImageOCRResult(
        2400,
        80,
        (),
        OCRRegionDiagnostics(None, len(regions), 0, tuple(regions)),
    )
    transform = rr.build_margin_crop(io.BytesIO(image), wide)[1]
    ocr = FakeOCR(
        {
            (2400, 80): full,
            (int(wide[2] - wide[0]), transform["size"][1]): crop_result(
                (OCRLine("only this one", (2.0, 5.0, 290.0, 30.0), 0.9),),
                int(wide[2] - wide[0]),
                transform["size"][1],
            ),
        }
    )
    outcome = rr.recover_regions(
        ocr=ocr,
        image_bytes=image,
        result=full,
        limits=OCRLimits(),
        budget=rr.RecoveryBudget(),
        accept_threshold=THRESHOLD,
    )
    statuses = {tuple(r.box): r.status for r in outcome.diagnostics.recovery}
    assert statuses[tuple(wide)] == "recovered"
    assert sum(v == "not_attempted" for v in statuses.values()) == 4
    assert len(outcome.diagnostics.dropped) == 5


def test_iou_and_diagnostic_record_validation():
    a = (0.0, 0.0, 10.0, 10.0)
    assert rr.box_iou(a, (0.0, 0.0, 10.0, 10.0)) == pytest.approx(1.0)
    assert rr.box_iou(a, (5.0, 0.0, 15.0, 10.0)) == pytest.approx(0.3333, abs=1e-3)
    assert rr.box_iou(a, (20.0, 20.0, 30.0, 30.0)) == 0.0
    with pytest.raises(LocalOCRError):
        OCRRegionRecovery((0.0, 0.0, 10.0, 10.0), "bogus_status")
    with pytest.raises(LocalOCRError):
        OCRRecoveryAttempt("t/1", {}, "bogus_outcome")



@pytest.mark.parametrize("stack", [False, True])
def test_filtered_low_score_remainder_prevents_partial_recovery(stack):
    """The adapter excludes low-score text from lines, not from diagnostics."""
    from PIL import Image

    region = (10., 28., 262., 48.) if stack else WIDE
    image = strip_png()
    full = result_with([dropped(region)])
    stack_transform = rr.build_split_stack(image, region)[1]

    class PartialOCR:
        def transcribe(self, data, *, limits):
            size = Image.open(io.BytesIO(data)).size
            if stack and size != stack_transform["size"]:
                return result_with([dropped((0., 5., 150., 20.), .3)], width=size[0], height=size[1])
            if stack:
                lines = tuple(OCRLine("Clean fragment", (1., sy+7., min(cx1-cx0, 100.)-1., sy+17.), .99)
                    for _sx, sy, _ox, _oy, cx0, cx1 in stack_transform["chunks"])
                sy = stack_transform["chunks"][-1][1]
                remainder = dropped((1., sy+18., 50., sy+26.), .3, "unread qualifier")
            else:
                scale = size[0] / 290
                lines = (OCRLine("Revenue increased", (0., 12*scale, 90*scale, 35*scale), .99),)
                remainder = dropped((100*scale, 12*scale, 280*scale, 35*scale), .3, "unread material qualifier")
            return result_with([remainder], lines=lines, width=size[0], height=size[1])

    got = rr.recover_regions(ocr=PartialOCR(), image_bytes=image, result=full,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=THRESHOLD)
    assert got.recovered_lines == ()
    assert got.diagnostics.recovery[0].status == "unrecovered"
    assert any(a.note == "in_region_dropped_text" for a in got.diagnostics.recovery[0].attempts)
    assert got.diagnostics.dropped == full.region_diagnostics.dropped


def test_dropped_neighbor_outside_source_region_does_not_veto_recovery():
    image = strip_png()
    full = result_with([dropped(WIDE)])
    size = rr.build_margin_crop(image, WIDE)[1]["size"]
    clean = OCRLine("Complete source line", (1., 12., 280., 35.), .99)
    # y=0..6 maps into the crop margin above the source region (20..52).
    neighbor = dropped((1., 0., 100., 6.), .3, "adjacent unread text")
    fake = FakeOCR({size: result_with([neighbor], (clean,), width=size[0], height=size[1])})
    got = rr.recover_regions(ocr=fake, image_bytes=image, result=full,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=THRESHOLD)
    assert [line.text for line in got.recovered_lines] == [clean.text]


@pytest.mark.parametrize("angle", [90, 180, 270])
def test_rotation_forward_inverse_matches_pil_canvas_geometry(angle):
    from PIL import Image

    # Derive the rotated box from actual pixels, rather than the inverse code.
    mask = Image.new("L", (40, 20), 0)
    mask.paste(255, (30, 2, 38, 6))
    forward = mask.rotate(angle, expand=True).getbbox()
    assert forward is not None
    assert rr.map_box({"kind": "rotate", "angle": angle, "size": mask.size}, forward) == (30., 2., 38., 6.)


@pytest.mark.parametrize("bad_kind", ["cross_chunk", "right_padding", "below_last_chunk"])
def test_split_stack_requires_whole_box_inside_actual_chunk(bad_kind):
    transform = rr.build_split_stack(strip_png(), (10., 28., 262., 48.))[1]
    chunks = transform["chunks"]
    assert len(chunks) >= 2
    if bad_kind == "cross_chunk":
        sy = chunks[1][1]
        box = (1., sy-12., 50., sy+15.)
    elif bad_kind == "right_padding":
        width = chunks[0][5]-chunks[0][4]
        box = (1., 5., width+1., 15.)
    else:
        height = transform["size"][1]
        box = (1., height-3., 50., height+3.)
    assert rr.map_box(transform, box) is None



def test_stack_unmappable_extra_text_cannot_hide_behind_passing_chunks():
    image = strip_png()
    region = (10., 28., 262., 48.)
    full = result_with([dropped(region)])
    margin = rr.build_margin_crop(image, region)[1]
    stack = rr.build_split_stack(image, region)[1]
    lines = [OCRLine("Clean source fragment", (1., sy+7., min(cx1-cx0, 100.)-1., sy+17.), .99)
        for _sx, sy, _ox, _oy, cx0, cx1 in stack["chunks"]]
    sy = stack["chunks"][1][1]
    lines.append(OCRLine("Ambiguous cross-chunk text", (1., sy-12., 50., sy+15.), .99))
    fake = FakeOCR({
        margin["size"]: crop_result((), *margin["size"]),
        stack["size"]: crop_result(lines, *stack["size"]),
    })
    got = rr.recover_regions(ocr=fake, image_bytes=image, result=full,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=THRESHOLD)
    assert got.recovered_lines == ()
    assert got.diagnostics.recovery[0].attempts[-1].note == "unmappable_region_text"


def test_pixel_reservation_is_atomic_and_failed_backend_budget_remains_charged():
    budget = rr.RecoveryBudget()
    limits = OCRLimits(max_total_pixels=100)
    budget.reserve_pixels(80, limits=limits)
    with pytest.raises(NormalizationLimitError, match="max_total_pixels"):
        budget.reserve_pixels(21, limits=limits, roi=True)
    assert budget.total_pixels == 80 and budget.total_roi_pixels == 0
    budget.reserve_pixels(20, limits=limits, roi=True)
    assert budget.total_pixels == 100 and budget.total_roi_pixels == 20


def test_recovery_algorithm_revision_cannot_reuse_original_identity():
    from company_wiki.document_normalization.local_ocr import LocalOCRConfig, OCRModelFile

    model = OCRModelFile("unused-local-model.onnx", "a" * 64)
    config = LocalOCRConfig(model, model, model, "test-engine", "test-runtime", "b" * 64)
    new_identity = config.identity_manifest
    assert new_identity["region_recovery"] == "cwp-ocr-region-recovery/1"
    assert new_identity["region_recovery_algorithm"] == "bounded-source-roi/2"
    old_identity = {k: v for k, v in new_identity.items() if k != "region_recovery_algorithm"}
    old_fingerprint = hashlib.sha256(json.dumps(old_identity, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    assert old_fingerprint != config.fingerprint



def test_dropped_source_fragment_with_outside_center_stays_unrecovered():
    from PIL import Image

    image = strip_png()
    full = result_with([dropped(WIDE)])

    class OverlappingRemainder:
        def transcribe(self, data, *, limits):
            width, height = Image.open(io.BytesIO(data)).size
            scale = width / 290
            clean = OCRLine("Clean part of source", (1., 12*scale, 280*scale, 35*scale), .99)
            # Original crop y origin is 9: this qualifier spans y=11..23,
            # centered above the source ROI y=20..52, but its bytes overlap it.
            remainder = dropped((1., 2*scale, 100*scale, 14*scale), .3, "unread overlapping qualifier")
            return result_with([remainder], (clean,), width=width, height=height)

    got = rr.recover_regions(ocr=OverlappingRemainder(), image_bytes=image, result=full,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=THRESHOLD)
    assert got.recovered_lines == ()
    assert got.diagnostics.recovery[0].status == "unrecovered"



@pytest.mark.parametrize("kind", ["margin", "split", "upscale"])
@pytest.mark.parametrize("limit_name", ["max_image_pixels", "max_total_pixels"])
def test_roi_budget_preflight_never_calls_rejected_renderer(monkeypatch, kind, limit_name):
    """A resource limit must stop raster allocation, not just later OCR."""
    if kind == "split":
        image = strip_png(width=3000, height=80)
        region = (10., 28., 2990., 48.)
        full = result_with([dropped(region)], width=3000, height=80)
        target_name = "build_split_stack"
    else:
        image = strip_png()
        region = WIDE
        full = result_with([dropped(region)])
        target_name = "build_margin_crop" if kind == "margin" else "build_upscale"
    # Tiny synthetic fixture only; inspect the existing valid renderer's real
    # dimensions, then spy on application calls under an insufficient cap.
    target_size = getattr(rr, target_name)(image, region)[1]["size"]
    target_pixels = target_size[0] * target_size[1]
    first_size = rr.build_margin_crop(image, region)[1]["size"]
    first_pixels = first_size[0] * first_size[1]
    if kind != "margin":
        assert target_pixels > first_pixels
    budget = rr.RecoveryBudget()
    already_used = full.width * full.height
    budget.reserve_pixels(already_used, limits=OCRLimits())
    limits = OCRLimits(**{limit_name: target_pixels - 1 if limit_name == "max_image_pixels"
        else already_used + (0 if kind == "margin" else first_pixels) + target_pixels - 1})
    renders = []
    original_builder = getattr(rr, target_name)

    def render_spy(*args, **kwargs):
        renders.append(target_name)
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(rr, target_name, render_spy)
    # Empty first-attempt OCR output permits a bounded second-attempt branch.
    fake = FakeOCR({first_size: crop_result((), *first_size)})
    with pytest.raises(NormalizationLimitError, match=limit_name):
        rr.recover_regions(ocr=fake, image_bytes=image, result=full,
            limits=limits, budget=budget, accept_threshold=THRESHOLD)
    assert renders == [], "rejected ROI rendered before resource reservation"
    assert len(fake.calls) == (0 if kind == "margin" else 1)
    assert budget.total_pixels == already_used + (0 if kind == "margin" else first_pixels)


def test_rejected_render_attempt_keeps_reserved_budget(monkeypatch):
    image = strip_png()
    full = result_with([dropped(WIDE)])
    size = rr.build_margin_crop(image, WIDE)[1]["size"]
    budget = rr.RecoveryBudget(max_attempts_per_image=1)

    def render_failure(*args, **kwargs):
        raise LocalOCRError("OCR_IMAGE_INVALID")

    monkeypatch.setattr(rr, "build_margin_crop", render_failure)
    fake = FakeOCR({})
    try:
        got = rr.recover_regions(ocr=fake, image_bytes=image, result=full,
            limits=OCRLimits(), budget=budget, accept_threshold=THRESHOLD)
    except LocalOCRError:
        got = None
    assert budget.total_pixels == size[0]*size[1], "render failed before pixels were reserved"
    assert budget.total_roi_pixels == size[0]*size[1]
    assert budget.total_attempts == 1 and not fake.calls
    assert got is not None and got.recovered_lines == ()
    assert got.diagnostics.recovery[0].attempts[0].outcome == "error"



def test_upscale_preflight_accounts_for_64m_canvas_without_allocating_it():
    from types import SimpleNamespace

    # Size-only sentinel has no pixels, crop or resize method: planning the
    # problematic 16M->64M case cannot allocate any actual raster.
    source = SimpleNamespace(size=(4000, 4000))
    plan = rr._plan_transform(source, (0., 0., 4000., 4000.), rr.UPSCALE_TRANSFORM)
    assert plan.transform["size"] == (8000, 8000)
    budget = rr.RecoveryBudget()
    with pytest.raises(NormalizationLimitError, match="max_image_pixels"):
        budget.reserve_pixels(8000*8000, limits=OCRLimits(), roi=True)
    assert budget.total_pixels == 0 and budget.total_roi_pixels == 0


@pytest.mark.parametrize("mode", ["RGB", "L", "RGBA", "P", "CMYK"])
def test_split_read_scan_matches_original_pil_luminance_and_row_sampling(mode):
    from PIL import Image

    image = Image.new("RGB", (192, 45))
    pixels = image.load()
    for x in range(192):
        for y in range(45):
            pixels[x,y] = ((37*x+11*y)%256, (13*x+67*y)%256, (97*x+23*y)%256)
    image = image.convert(mode)
    window = (7, 5, 181, 40)
    crop = image.crop(window).convert("L")  # reference only in test
    expected = [sum(crop.getpixel((x,y)) < rr.DARK_THRESHOLD
        for y in range(0, crop.height, 2)) for x in range(crop.width)]
    assert rr._column_dark_counts(image, window=window) == expected


@pytest.mark.parametrize("name", ["build_margin_crop", "build_split_stack", "build_upscale"])
def test_preflight_geometry_and_rendered_pixels_are_identical_with_padding(name):
    from PIL import Image

    image = Image.open(io.BytesIO(strip_png()))
    transform_name = {"build_margin_crop": rr.MARGIN_CROP_TRANSFORM,
        "build_split_stack": rr.SPLIT_STACK_TRANSFORM,
        "build_upscale": rr.UPSCALE_TRANSFORM}[name]
    region = (10., 28., 262., 48.)
    plan = rr._plan_transform(image, region, transform_name)
    png, transform = getattr(rr, name)(image, region, _plan=plan)
    fresh_png, fresh_transform = getattr(rr, name)(image, region)
    assert png == fresh_png and transform == fresh_transform == plan.transform
    assert Image.open(io.BytesIO(png)).size == plan.transform["size"]
    if name == "build_split_stack":
        crop_height = plan.window[3]-plan.window[1]
        assert plan.transform["size"][1] == len(plan.chunks)*crop_height + (len(plan.chunks)-1)*rr.SPLIT_GAP_ROWS
        assert plan.transform["size"][0] == max(x1-x0 for x0,x1 in plan.chunks)
