"""Add bounded behavioral RED cases to ROOT's assigned ROI test file."""
from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\tests\document_normalization\test_ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
assert "test_roi_budget_preflight_never_calls_rejected_renderer" not in text
text += '''


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
'''
path.write_text(text, encoding="utf-8")
print("Added six pre-render budget cases and one reserved render-failure case.")
