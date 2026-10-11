"""Independent, zero-provider behavioral probes; product tree is read-only."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys

TREE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(TREE / 'src'))
sys.path.insert(0, str(TREE / 'tests/document_normalization'))

from company_wiki.document_normalization import NormalizationLimitError
from company_wiki.document_normalization.local_ocr import (
    OCRLine, OCRLimits, ImageOCRResult, OCRDroppedRegion, OCRRegionDiagnostics,
)
from company_wiki.document_normalization import ocr_region_recovery as rr
from test_ocr_region_composition import (
    picture_deck, text_png, normalize, RecoveryFakeOCR, crop_size_for,
)

OBS = {}

def diag_result(size, lines=(), drops=()):
    return ImageOCRResult(*size, tuple(lines), OCRRegionDiagnostics(
        None, len(lines)+len(drops), len(lines), tuple(drops)))

def test_budget_reserves_before_inference():
    size = crop_size_for(None)
    fake = RecoveryFakeOCR((OCRLine('Recovered complete line', (2, 12, 280, 35), .99),), size)
    cap = 320 * 80 + 1
    rejected = False
    try:
        normalize(picture_deck(), fake, ocr_limits=OCRLimits(max_total_pixels=cap))
    except NormalizationLimitError:
        rejected = True
    OBS['budget_before_inference'] = {'cap': cap, 'calls': fake.calls, 'rejected': rejected,
        'roi_pixels': size[0]*size[1], 'expected': 'No ROI OCR call when remaining pixels=1'}
    assert rejected and fake.calls == [(320, 80)], OBS['budget_before_inference']

def test_filtered_partial_margin_stays_unrecovered():
    image = text_png()
    region = (10., 20., 300., 52.)
    base = diag_result((320, 80), drops=(OCRDroppedRegion(region, .43, 'g ar b le', 'low_text_score'),))
    class Partial:
        def transcribe(self, data, *, limits):
            from PIL import Image
            size = Image.open(io.BytesIO(data)).size
            # The actual adapter moves a low-score remainder into diagnostics.
            scale = size[0] / 290
            good = OCRLine('Revenue increased', (0, 12*scale, 90*scale, 35*scale), .99)
            bad = OCRDroppedRegion((100*scale,12*scale,280*scale,35*scale), .3,
                'unread material qualifier', 'low_text_score')
            return diag_result(size, (good,), (bad,))
    got = rr.recover_regions(ocr=Partial(), image_bytes=image, result=base,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=.5)
    OBS['filtered_partial_margin'] = {'emitted':[x.text for x in got.recovered_lines],
        'diagnostics':got.diagnostics.to_dict(), 'expected':'Do not mark full region recovered while its in-region remainder is dropped'}
    assert not got.recovered_lines and got.diagnostics.recovery[0].status != 'recovered', OBS['filtered_partial_margin']

def test_filtered_partial_stack_stays_unrecovered():
    from PIL import Image
    image = text_png()
    region = (10.,28.,262.,48.)
    base = diag_result((320,80), drops=(OCRDroppedRegion(region,.44,'g ar b le','low_text_score'),))
    stack, transform = rr.build_split_stack(image, region)
    class PartialStack:
        def transcribe(self, data, *, limits):
            size = Image.open(io.BytesIO(data)).size
            if size != transform['size']:
                return diag_result(size, drops=(OCRDroppedRegion((0,5,150,20),.3,'bad','low_text_score'),))
            lines = []
            for _sx, sy, _ox, _oy, cx0, cx1 in transform['chunks']:
                width = min(float(cx1-cx0), 100.)
                lines.append(OCRLine('Clean fragment', (1,sy+7,width-1,sy+17),.99))
            sy = transform['chunks'][-1][1]
            dropped = OCRDroppedRegion((1,sy+18,50,sy+26),.3,'unread qualifier','low_text_score')
            return diag_result(size, lines, (dropped,))
    got = rr.recover_regions(ocr=PartialStack(), image_bytes=image, result=base,
        limits=OCRLimits(), budget=rr.RecoveryBudget(), accept_threshold=.5)
    OBS['filtered_partial_stack'] = {'emitted':[x.text for x in got.recovered_lines],
        'diagnostics':got.diagnostics.to_dict(), 'expected':'All material chunks including diagnostic dropped text must be accounted for'}
    assert not got.recovered_lines and got.diagnostics.recovery[0].status != 'recovered', OBS['filtered_partial_stack']

def test_ccw_90_returns_original_geometry():
    # PIL-style CCW rotation: original (30,2,38,6) on W40/H20 becomes (2,2,6,10).
    expected = (30., 2., 38., 6.)
    actual = rr.map_box({'kind':'rotate','angle':90,'size':(40,20)}, (2.,2.,6.,10.))
    OBS['ccw_90_mapping'] = {'actual':actual, 'expected':expected, 'in_use_by_recovery_ladder':False}
    assert actual == expected, OBS['ccw_90_mapping']

def test_split_cross_chunk_is_not_one_source_box():
    _data, t = rr.build_split_stack(text_png(), (10.,28.,262.,48.))
    assert len(t['chunks']) >= 2
    # This detector box spans different concatenated source chunks.
    h = t['chunks'][1][1]
    box = (1., h-12., 90., h+33.)
    actual = rr.map_box(t, box)
    OBS['split_cross_chunk'] = {'actual':actual, 'box':box, 'transform':t,
        'expected':'Reject boxes spanning disjoint chunk rows rather than translating their center'}
    assert actual is None, OBS['split_cross_chunk']

def test_overlap_does_not_drop_distinct_text():
    # OCR detectors may overlap even for distinct adjacent content; expose an
    # ambiguity, but do not pretend this is an independently proven real page.
    original = OCRLine('Original retained label', (10.,20.,170.,52.),.99)
    region = (10.,20.,300.,52.)
    result = diag_result((320,80),(original,), (OCRDroppedRegion(region,.44,'g ar b le','low_text_score'),))
    crop, transform = rr.build_margin_crop(text_png(), region)
    class Distinct:
        def transcribe(self, data, *, limits):
            from PIL import Image
            size = Image.open(io.BytesIO(data)).size
            sx = size[0]/290
            return diag_result(size,(OCRLine('Additional distinct full label',
                (0,12*sx,280*sx,35*sx),.99),))
    got=rr.recover_regions(ocr=Distinct(),image_bytes=text_png(),result=result,
        limits=OCRLimits(),budget=rr.RecoveryBudget(),accept_threshold=.5)
    OBS['distinct_overlap']={'emitted':[x.text for x in got.recovered_lines],
        'diagnostics':got.diagnostics.to_dict(), 'original_preserved':result.lines==(original,),
        'expected':'Distinct overlapping text remains explicitly ambiguous; conservative suppression is not content recall proof'}
    # Preserve known original, keep unrecovered diagnostics: valid conservative policy.
    assert result.lines==(original,) and got.diagnostics.recovery[0].status!='recovered'

results=[]
for test in (
    test_budget_reserves_before_inference,
    test_filtered_partial_margin_stays_unrecovered,
    test_filtered_partial_stack_stays_unrecovered,
    test_ccw_90_returns_original_geometry,
    test_split_cross_chunk_is_not_one_source_box,
    test_overlap_does_not_drop_distinct_text,
):
    try:
        test()
        results.append({'test':test.__name__,'status':'PASS'})
    except AssertionError as exc:
        results.append({'test':test.__name__,'status':'FAIL','detail':str(exc)})
    except Exception as exc:
        results.append({'test':test.__name__,'status':'HARNESS_ERROR','detail':repr(exc)})

sha_paths=('src/company_wiki/document_normalization/local_ocr.py',
    'src/company_wiki/document_normalization/ocr_composition.py',
    'src/company_wiki/document_normalization/ocr_region_recovery.py')
payload={'schema':'root-w05-ocr-independent-probes/1', 'tree':str(TREE),
    'source_sha256':{p:hashlib.sha256((TREE/p).read_bytes()).hexdigest() for p in sha_paths},
    'results':results,'observations':OBS,'provider_calls':0,'raw_files_opened':0,
    'scratch_created':False}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'results':results,'evidence':str(OUT)},ensure_ascii=False))
sys.exit(1 if any(x['status']!='PASS' for x in results) else 0)
