"""Pure integer bounds from frozen ROI constants; never allocates image/OCR arrays."""
import json
import math
from pathlib import Path

M = 16_000_000
ratio = 6.5
gap = 8
records = []
for height in range(12, math.isqrt(M) + 1):
    width = M // height
    max_width = max(1, int(ratio * height))
    if width <= max_width:
        continue
    minimum_cut_step = int(max_width * 0.3)
    # Every cut advances by at least minimum_cut_step; the final remainder
    # is no wider than max_width. Actual whitespace may reduce this bound.
    chunks_upper = math.ceil((width - max_width) / minimum_cut_step) + 1
    stack_height_upper = chunks_upper * height + gap * (chunks_upper - 1)
    records.append({'source_width': width, 'source_height': height,
        'source_pixels': width * height, 'maximum_chunk_width': max_width,
        'minimum_cut_step': minimum_cut_step, 'chunks_upper': chunks_upper,
        'stack_height_upper': stack_height_upper,
        'stack_pixels_upper': max_width * stack_height_upper})
result = {
    'schema_version': 'root-w05-ocr-pure-geometry-upper-bound/1',
    'method': 'Static formulas only; no image allocation, native inference, or runtime peak-RSS claim',
    'default_max_image_pixels': M,
    'default_max_total_pixels': 96_000_000,
    'pre_render_fixed_max_side': None,
    'rapidocr_config_max_side_len': 3000,
    'margin_pixels_upper': M,
    'upscale_factor_per_edge': 2,
    'upscale_pixels_upper': 4 * M,
    'upscale_rgb_payload_bytes_lower_bound_at_upper': 3 * 4 * M,
    'plausible_upscale_case': {'source': [6000, 2666], 'source_pixels': 6000 * 2666,
        'aspect_ratio': 6000 / 2666, 'transform': 'upscale-2x/1',
        'rendered': [12000, 5332], 'rendered_pixels': 12000 * 5332,
        'rendered_rgb_payload_bytes_lower_bound': 3 * 12000 * 5332,
        'default_max_image_cap_checked_after_render': True},
    'split_stack_conservative_upper': max(records, key=lambda r: r['stack_pixels_upper']),
    'notes': ['PIL internal storage and ancillary buffers can exceed nominal three-byte RGB payload; not measured',
        'Split bound is conservative and depends on ROI whitespace; not an asserted observed allocation',
        'Both transform methods materialize PNG before RecoveryBudget.reserve_pixels rejects the transformed size',
        'The configured OCR max_side_len acts inside RapidOCR after dispatch and does not cap this parent-side rendering'],
}
(Path(__file__).resolve().parent / 'geometry-bounds.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
