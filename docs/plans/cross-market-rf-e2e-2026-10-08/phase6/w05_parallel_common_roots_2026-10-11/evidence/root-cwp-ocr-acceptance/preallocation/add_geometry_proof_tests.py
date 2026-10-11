"""Bounded reference tests for exact raster sizing and PIL-equivalent scan."""
from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\tests\document_normalization\test_ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
assert "test_upscale_preflight_accounts_for_64m_canvas_without_allocating_it" not in text
text += '''


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
'''
path.write_text(text, encoding="utf-8")
