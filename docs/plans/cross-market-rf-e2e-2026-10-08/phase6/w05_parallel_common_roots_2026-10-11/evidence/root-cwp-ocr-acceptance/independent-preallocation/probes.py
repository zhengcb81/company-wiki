"""Independent bounded synthetic ROI contract probes; no models/raw/network."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root')
sys.path.insert(0, str(TREE / 'src'))
from PIL import Image
from company_wiki.document_normalization import ocr_region_recovery as rr
from company_wiki.document_normalization.errors import NormalizationLimitError
from company_wiki.document_normalization.local_ocr import (
    ImageOCRResult, LocalOCRError, OCRDroppedRegion, OCRLimits, OCRRegionDiagnostics,
)

results = []
observations = {}


def record(name, function):
    try:
        observations[name] = function()
        results.append({'test': name, 'status': 'PASS'})
    except AssertionError as exc:
        results.append({'test': name, 'status': 'FAIL', 'detail': str(exc)})
    except Exception as exc:
        results.append({'test': name, 'status': 'HARNESS_OR_BUSINESS_ERROR', 'detail': repr(exc)})


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def png(image):
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def window(box, size, margin=.35):
    w, h = size
    x0 = max(0, min(w-1, int(round(box[0]))))
    x1 = max(x0+1, min(w, int(round(box[2]))))
    y0 = max(0, min(h-1, int(round(box[1]))))
    y1 = max(y0+1, min(h, int(round(box[3]))))
    extra = int(round(margin * (y1-y0)))
    return x0, max(0, y0-extra), x1, min(h, y1+extra)


def legacy_render(image, box, kind):
    """Small independent reference: original crop/grayscale raster semantics."""
    x0, y0, x1, y1 = window(box, image.size)
    crop = image.crop((x0, y0, x1, y1))
    w, h = crop.size
    if kind == 'margin':
        return png(crop), {'transform': 'roi-margin-crop/1', 'kind': 'translate',
            'origin': (float(x0), float(y0)), 'size': crop.size}
    if kind == 'upscale':
        resized = crop.resize((2*w, 2*h), Image.Resampling.LANCZOS)
        return png(resized), {'transform': 'upscale-2x/1', 'kind': 'scale',
            'origin': (float(x0), float(y0)), 'scale': .5, 'size': resized.size}
    gray = crop.convert('L')
    counts = [sum(gray.getpixel((x, y)) < 200 for y in range(0, h, 2)) for x in range(w)]
    maximum = max(1, int(6.5*h))
    cuts, x = [], 0
    while w-x > maximum:
        lo, hi = x+int(maximum*.3), min(x+maximum, w-1)
        best = run = None
        for cx in range(lo, hi+1):
            if counts[cx] == 0:
                if run is None:
                    run = cx
            else:
                if run is not None and cx-run >= 5:
                    best = run
                run = None
        if run is not None and hi+1-run >= 5:
            best = run
        x = min(x+maximum if best is None else best, w-1)
        cuts.append(x)
    bounds = [0, *cuts, w]
    chunks = [(a, b) for a, b in zip(bounds, bounds[1:]) if b-a >= 4]
    width = max(b-a for a, b in chunks)
    height = h*len(chunks)+8*(len(chunks)-1)
    stack = Image.new('RGB', (width, height), 'white')
    table = []
    for index, (a, b) in enumerate(chunks):
        sy = index*(h+8)
        stack.paste(crop.crop((a, 0, b, h)), (0, sy))
        table.append((0, sy, x0+a, y0, a, b))
    return png(stack), {'transform': 'split-stack/1', 'kind': 'split-stack',
        'size': stack.size, 'chunks': tuple(table)}


BUILDERS = {'margin': 'build_margin_crop', 'split': 'build_split_stack', 'upscale': 'build_upscale'}
TRANSFORMS = {'margin': rr.MARGIN_CROP_TRANSFORM, 'split': rr.SPLIT_STACK_TRANSFORM,
              'upscale': rr.UPSCALE_TRANSFORM}


class EmptyOCR:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def transcribe(self, data, *, limits):
        size = Image.open(io.BytesIO(data)).size
        self.calls.append(size)
        if self.fail:
            raise LocalOCRError('OCR_INFERENCE_FAILED')
        return ImageOCRResult(*size, ())


def fixture(kind):
    size, box = ((600, 80), (10., 26., 590., 46.)) if kind == 'split' else ((360, 90), (16., 24., 220., 60.))
    image = Image.new('RGB', size, 'white')
    full = ImageOCRResult(*size, (), OCRRegionDiagnostics(None, 1, 0,
        (OCRDroppedRegion(box, .4, 'unread original line', 'low_text_score'),)))
    return image, box, full


def reject(kind, limit_name):
    image, box, full = fixture(kind)
    # Dimension expectation comes from the independent old raster reference.
    target = legacy_render(image, box, kind)[1]['size']
    first = legacy_render(image, box, 'margin')[1]['size']
    target_pixels, first_pixels = target[0]*target[1], first[0]*first[1]
    used = image.width*image.height
    allowed_prior = 0 if kind == 'margin' else first_pixels
    cap = target_pixels-1 if limit_name == 'max_image_pixels' else used+allowed_prior+target_pixels-1
    limits = OCRLimits(**{limit_name: cap})
    budget = rr.RecoveryBudget()
    budget.reserve_pixels(used, limits=OCRLimits())
    calls = []
    builder = getattr(rr, BUILDERS[kind])
    def spy(*args, **kwargs):
        calls.append('render')
        return builder(*args, **kwargs)
    fake = EmptyOCR()
    with patch.object(rr, BUILDERS[kind], spy):
        try:
            rr.recover_regions(ocr=fake, image_bytes=png(image), result=full,
                limits=limits, budget=budget, accept_threshold=.5)
        except NormalizationLimitError as exc:
            assert exc.limit_name == limit_name, exc.limit_name
        else:
            raise AssertionError('limit did not reject oversized target')
    assert not calls, 'rejected output renderer was invoked'
    assert len(fake.calls) == (0 if kind == 'margin' else 1), fake.calls
    assert budget.total_pixels == used+allowed_prior
    assert budget.total_roi_pixels == allowed_prior
    assert budget.total_attempts == (0 if kind == 'margin' else 1)
    return {'kind': kind, 'limit': limit_name, 'cap': cap, 'target_canvas': target,
        'target_pixels': target_pixels, 'target_render_calls': len(calls),
        'native_fake_calls': len(fake.calls), 'pixel_charge': budget.total_pixels,
        'note': 'margin single-image vector exercises recovery seam after stricter limits; public unchanged source limit would reject the full image first'}


def failed_attempt(which):
    image, box, full = fixture('upscale')
    size = legacy_render(image, box, 'margin')[1]['size']
    roi_pixels = size[0]*size[1]
    budget = rr.RecoveryBudget(max_attempts_per_image=1)
    used = image.width*image.height
    budget.reserve_pixels(used, limits=OCRLimits())
    fake = EmptyOCR(fail=which == 'inference')
    def failure(*args, **kwargs):
        raise LocalOCRError('OCR_IMAGE_INVALID')
    context = patch.object(rr, 'build_margin_crop', failure) if which == 'render' else patch.object(rr, '_PREFLIGHT_TEST_UNUSED', None, create=True)
    with context:
        result = rr.recover_regions(ocr=fake, image_bytes=png(image), result=full,
            limits=OCRLimits(), budget=budget, accept_threshold=.5)
    assert budget.total_pixels == used+roi_pixels and budget.total_roi_pixels == roi_pixels
    assert budget.total_attempts == 1
    assert len(fake.calls) == (0 if which == 'render' else 1)
    assert not result.recovered_lines and result.diagnostics.recovery[0].attempts[0].outcome == 'error'
    return {'failure': which, 'roi_charge_kept': roi_pixels, 'attempts': 1,
            'fake_inference_calls': len(fake.calls)}


def colored(mode):
    image = Image.new('RGB', (213, 57))
    pixels = image.load()
    for x in range(image.width):
        for y in range(image.height):
            pixels[x,y] = ((43*x+3*y)%256, (17*x+51*y)%256, (89*x+29*y)%256)
    if mode == 'P':
        image = image.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
    else:
        image = image.convert(mode)
    return image


def legal_mode(mode, kind):
    image = colored(mode)
    box = (8.7, 7.2, 201.5, 36.6)
    builder = getattr(rr, BUILDERS[kind])
    try:
        expected_data, expected = legacy_render(image, box, kind)
    except OSError as reference_error:
        try:
            builder(image, box)
        except OSError as actual_error:
            assert str(reference_error) == str(actual_error)
            return {'unchanged_error': str(actual_error)}
        raise AssertionError('previous unsupported mode unexpectedly changed semantics')
    plan = rr._plan_transform(image, box, TRANSFORMS[kind])
    budget = rr.RecoveryBudget()
    size = plan.transform['size']
    budget.reserve_pixels(size[0]*size[1], limits=OCRLimits(), roi=True)
    actual_data, actual = builder(image, box, _plan=plan)
    assert actual_data == expected_data and actual == expected and plan.transform == expected
    rendered = Image.open(io.BytesIO(actual_data)).size
    assert rendered == size and budget.total_roi_pixels == rendered[0]*rendered[1]
    if kind == 'split':
        height = plan.window[3]-plan.window[1]
        assert size[1] == len(plan.chunks)*height+8*(len(plan.chunks)-1)
        assert size[0] == max(b-a for a,b in plan.chunks)
        for _sx, sy, ox, oy, a, b in actual['chunks']:
            right = min(5., float(b-a-1))
            if right > 1:
                assert rr.map_box(actual, (1., sy+1., right, sy+4.)) == (ox+1., oy+1., ox+right, oy+4.)
        if len(plan.chunks) > 1:
            sy = actual['chunks'][1][1]
            assert rr.map_box(actual, (1., sy-1., 2., sy+2.)) is None
    else:
        scale = 1 if kind == 'margin' else .5
        ox, oy = expected['origin']
        assert rr.map_box(actual, (2., 2., 6., 6.)) == (ox+2*scale, oy+2*scale, ox+6*scale, oy+6*scale)
    return {'png_sha256': hashlib.sha256(actual_data).hexdigest(), 'canvas': size,
        'reserved_pixels': budget.total_roi_pixels, 'transform_and_coordinates_exact': True,
        'padding_included': kind == 'split'}


def luminance_mode(mode):
    image = colored(mode)
    roi = (11, 5, 199, 44)
    gray = image.crop(roi).convert('L')
    expected = [sum(gray.getpixel((x,y)) < 200 for y in range(0, gray.height, 2)) for x in range(gray.width)]
    actual = rr._column_dark_counts(image, window=roi)
    assert actual == expected
    return {'columns': len(actual), 'sampled_rows': (gray.height+1)//2,
        'reference_luminance_exact': True}


def scan_deadline(stop):
    class SourceOnly:
        size = (173, 21)
        mode = 'RGB'
        reads = 0
        def load(self):
            return self
        def __getitem__(self, pair):
            x, y = pair
            assert 7 <= x < 163 and 3 <= y < 20 and (y-3) % 2 == 0
            self.reads += 1
            return (0, 0, 0)
        def crop(self, *args):
            raise AssertionError('source raster crop forbidden during scan')
        def convert(self, *args):
            raise AssertionError('source grayscale raster forbidden during scan')
    source = SourceOnly()
    class Deadline:
        checkpoints = []
        def check_deadline(self):
            self.checkpoints.append(source.reads)
            if stop and len(self.checkpoints) == 2:
                raise NormalizationLimitError('deadline', 0)
    limits = Deadline()
    if stop:
        try:
            rr._column_dark_counts(source, window=(7,3,163,20), limits=limits)
        except NormalizationLimitError as exc:
            assert exc.limit_name == 'deadline'
        else:
            raise AssertionError('scan ignored expired deadline')
        assert source.reads == 64*9 and limits.checkpoints == [0, 64*9]
    else:
        counts = rr._column_dark_counts(source, window=(7,3,163,20), limits=limits)
        assert counts == [9]*156
        assert source.reads == 156*9 and limits.checkpoints == [0,64*9,128*9,156*9]
    return {'sampled_pixels': source.reads, 'checkpoint_pixel_counts': limits.checkpoints,
        'only_source_roi_reads': True, 'auxiliary_column_count_length': None if stop else len(counts)}


def former_large_canvas():
    source = SimpleNamespace(size=(6000,2666))
    plan = rr._plan_transform(source, (0.,0.,6000.,2666.), rr.UPSCALE_TRANSFORM)
    assert plan.transform['size'] == (12000,5332)
    budget = rr.RecoveryBudget()
    try:
        budget.reserve_pixels(12000*5332, limits=OCRLimits(), roi=True)
    except NormalizationLimitError as exc:
        assert exc.limit_name == 'max_image_pixels'
    else:
        raise AssertionError('formerly oversized canvas was accepted')
    assert not budget.total_pixels and not budget.total_roi_pixels
    return {'planned_pixels': 12000*5332, 'source_has_no_pixels_or_renderer': True,
        'default_cap_rejected_before_raster': True}


source_paths = ['src/company_wiki/document_normalization/ocr_region_recovery.py',
    'tests/document_normalization/test_ocr_region_recovery.py',
    'src/company_wiki/document_normalization/isolated_ocr.py',
    'src/company_wiki/document_normalization/ocr_composition.py',
    'src/company_wiki/source_catalog/narrative_normalization.py']
before = {p:digest(TREE/p) for p in source_paths}
assert before[source_paths[0]] == 'd3890356211e7fe21fce22fcfb11ac71769941712dd77937d4d28e1d291f512c'
assert before[source_paths[1]] == '3acea08f310eb21549b5353e4f092ec4956bcba6be953f5eef6e52704211aa50'
started = time.perf_counter()
for kind in ('margin', 'split', 'upscale'):
    for limit in ('max_image_pixels', 'max_total_pixels'):
        record(f'reject_{kind}_{limit}', lambda kind=kind, limit=limit: reject(kind, limit))
for failure in ('render', 'inference'):
    record('failed_'+failure+'_keeps_budget', lambda failure=failure: failed_attempt(failure))
for mode in ('RGB', 'L', 'RGBA', 'P', 'CMYK'):
    for kind in ('margin', 'split', 'upscale'):
        record(f'legal_{mode}_{kind}', lambda mode=mode, kind=kind: legal_mode(mode, kind))
for mode in ('RGB', 'L', 'RGBA', 'P', 'CMYK', 'LA', '1', 'RGBX'):
    record('luminance_'+mode, lambda mode=mode: luminance_mode(mode))
record('source_scan_geometry_and_checkpoints', lambda: scan_deadline(False))
record('source_scan_expiry_at_column64', lambda: scan_deadline(True))
record('former_63_984_000_pixel_canvas_preallocation', former_large_canvas)
after = {p:digest(TREE/p) for p in source_paths}
assert before == after
receipt = {'schema_version':'root-w05-ocr-independent-preallocation-probes/1',
    'status': 'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
    'seconds': time.perf_counter()-started, 'source_before': before, 'source_after': after,
    'results': results, 'observations': observations,
    'scope': {'real_ocr': False, 'source_originals_opened': 0, 'providers': 0,
        'network_calls': 0, 'fees_usd': 0, 'scratch_created': False,
        'data_files_created': False, 'old_failure_files_written': False}}
(HERE/'probes.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'status':receipt['status'],'passed':sum(r['status']=='PASS' for r in results),
    'vectors':len(results),'seconds':receipt['seconds'],
    'failures':[r for r in results if r['status']!='PASS']}))
sys.exit(0 if receipt['status']=='PASS' else 1)
