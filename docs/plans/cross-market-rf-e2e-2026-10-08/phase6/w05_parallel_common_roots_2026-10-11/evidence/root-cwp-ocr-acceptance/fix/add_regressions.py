"""One-shot ROOT-owned W05 regression addition to the assigned isolated tree."""
from pathlib import Path

TREE = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root")
rec = TREE / "tests/document_normalization/test_ocr_region_recovery.py"
comp = TREE / "tests/document_normalization/test_ocr_region_composition.py"
assert TREE.resolve() == TREE
assert "test_filtered_low_score_remainder_prevents_partial_recovery" not in rec.read_text(encoding="utf-8")
rec.write_text(rec.read_text(encoding="utf-8") + '''


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
''', encoding="utf-8")
comp.write_text(comp.read_text(encoding="utf-8") + '''


def test_recovery_pixel_budget_rejects_before_roi_inference():
    size = crop_size_for(None)
    fake = RecoveryFakeOCR((OCRLine("Recovered complete line", (2., 12., 280., 35.), .99),), size)
    with pytest.raises(dn.NormalizationLimitError, match="max_total_pixels"):
        normalize(picture_deck(), fake, ocr_limits=OCRLimits(max_total_pixels=320*80+1))
    assert fake.calls == [(320, 80)]
''', encoding="utf-8")
# Strengthen the existing cross-image test: the second ROI must never run.
text = comp.read_text(encoding="utf-8")
old = '    # the same deck parses when recovery fits the shared budget\n'
assert text.count(old) == 1
text = text.replace(old, '    assert fake.calls == [(320, 80), crop_size_for(None), (640, 160)]\n' + old)
comp.write_text(text, encoding="utf-8")
print("Added genuine behavior regressions; product sources untouched.")
