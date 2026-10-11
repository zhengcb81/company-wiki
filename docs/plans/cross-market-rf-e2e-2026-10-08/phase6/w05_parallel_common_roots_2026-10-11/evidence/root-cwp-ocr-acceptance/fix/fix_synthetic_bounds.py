"""Correct old fake bboxes that exceeded their actual synthetic source chunk."""
from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\tests\document_normalization\test_ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
replacements = {
    'OCRLine("part", (1.0, sy0 + 4.0, 100.0, sy0 + 16.0), 0.99)':
    'OCRLine("part", (1.0, sy0 + 4.0, min(100.0, cx1 - cx0 - 1.0), sy0 + 16.0), 0.99)',
    'OCRLine("Productivity and server", (1.0, 5.0, 150.0, 15.0), 0.99)':
    'OCRLine("Productivity and server", (1.0, 5.0, 70.0, 15.0), 0.99)',
    'OCRLine("recovered via stack", (1.0, 4.0, 150.0, 30.0), 0.97)':
    'OCRLine("recovered via stack", (1.0, 4.0, 70.0, 30.0), 0.97)',
}
for old, new in replacements.items():
    assert text.count(old) == 1, old
    text = text.replace(old, new)
text += '''


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
'''
path.write_text(text, encoding="utf-8")
print("Corrected three impossible fake chunk boxes; business expectations unchanged.")
