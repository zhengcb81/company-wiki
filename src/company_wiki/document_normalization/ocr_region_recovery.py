"""Finite source-owned ROI replay for OCR regions lost to score filtering.

The local OCR backend drops recognizer output below ``text_score`` before the
composition layer can see it.  ``local_ocr.LocalOCRAdapter`` therefore reports
those regions as :class:`~local_ocr.OCRRegionDiagnostics`; this module plans a
strictly bounded set of re-recognition attempts over deterministic geometric
transforms of the original image bytes and maps every accepted line back to
original-image coordinates.

Selection uses low score, geometry and generic text-candidate signals only --
never company, page or investment semantics.  Attempts are capped per region
and per image and charged against the caller's shared pixel/time budget.  The
acceptance threshold is never lowered: recovered lines must pass the same
``text_score`` that dropped the region, and garbled partial output is rejected
rather than stitched.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import io
import math

from .errors import NormalizationLimitError
from .local_ocr import (
    ImageOCRResult,
    LocalOCRError,
    OCRLine,
    OCRRegionDiagnostics,
    OCRRegionRecovery,
    OCRRecoveryAttempt,
)

__all__ = [
    "RecoveryBudget",
    "RegionRecoveryOutcome",
    "plan_regions",
    "recover_regions",
    "build_margin_crop",
    "build_split_stack",
    "build_upscale",
    "map_box",
    "box_iou",
]

# Deterministic planning thresholds (generic score/geometry signals only).
RECOVERY_SCORE_FLOOR = 0.2
MIN_REGION_WIDTH = 120.0
MIN_REGION_HEIGHT = 12.0
MIN_REGION_ASPECT = 2.0

# Attempt ladder transforms and parameters.
MARGIN_CROP_TRANSFORM = "roi-margin-crop/1"
SPLIT_STACK_TRANSFORM = "split-stack/1"
UPSCALE_TRANSFORM = "upscale-2x/1"
MARGIN_RATIO = 0.35
SPLIT_TARGET_RATIO = 6.5
SPLIT_GAP_ROWS = 8
SPLIT_MIN_GAP = 5
DARK_THRESHOLD = 200
TINY_CHUNK_WIDTH = 40.0
UPSCALE_FACTOR = 2.0

# A recovered line duplicating an already accepted line is dropped, never the
# other way around: originals always win.
OVERLAP_IOU_LIMIT = 0.5
OVERLAP_CONTAINMENT = 0.7
# Identical text at an overlapping position is the same content: repeated
# headers elsewhere in the image keep IoU near zero and stay untouched.
OVERLAP_TEXT_IOU = 0.2

_RETRYABLE_ATTEMPT_ERRORS = frozenset(
    {
        "OCR_IMAGE_INVALID",
        "OCR_MULTIFRAME_IMAGE_UNSUPPORTED",
        "OCR_INFERENCE_FAILED",
        "OCR_RESULT_INVALID",
        "OCR_BOX_INVALID",
        "OCR_BOX_OUTSIDE_IMAGE",
        "OCR_CONFIDENCE_INVALID",
        "OCR_TEXT_INVALID",
    }
)


class RecoveryBudget:
    """Per-request accumulator shared by every image in one composition run.

    Counts are reported with the composed document; enforcement stays with the
    caller's :class:`~local_ocr.OCRLimits` (pixels/time) plus the per-image and
    per-region attempt caps configured here.  There is deliberately no
    request-wide attempt ceiling: replay selects media subsets and must observe
    identical per-media outcomes to any full run, so request-wide state may
    accumulate but never changes a single image's recovery result.
    """

    def __init__(
        self,
        *,
        max_regions_per_image: int = 4,
        max_attempts_per_region: int = 2,
        max_attempts_per_image: int = 8,
    ):
        for name, value in (
            ("max_regions_per_image", max_regions_per_image),
            ("max_attempts_per_region", max_attempts_per_region),
            ("max_attempts_per_image", max_attempts_per_image),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.max_regions_per_image = max_regions_per_image
        self.max_attempts_per_region = max_attempts_per_region
        self.max_attempts_per_image = max_attempts_per_image
        self.regions_started = 0
        self.total_attempts = 0
        self.total_roi_pixels = 0

    def snapshot(self) -> dict:
        return {
            "regions_started": self.regions_started,
            "attempts": self.total_attempts,
            "roi_pixels": self.total_roi_pixels,
        }


@dataclass(frozen=True)
class RegionRecoveryOutcome:
    """Result of one image's bounded recovery pass."""

    recovered_lines: tuple
    diagnostics: OCRRegionDiagnostics | None
    roi_pixels: int
    attempts: int


def box_iou(a, b) -> float:
    """Intersection-over-union of two ``(x0, y0, x1, y1)`` boxes."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _duplicates_box(candidate, accepted) -> bool:
    if box_iou(candidate, accepted) > OVERLAP_IOU_LIMIT:
        return True
    ix0, iy0 = max(candidate[0], accepted[0]), max(candidate[1], accepted[1])
    ix1, iy1 = min(candidate[2], accepted[2]), min(candidate[3], accepted[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter <= 0:
        return False
    smaller = min(
        (candidate[2] - candidate[0]) * (candidate[3] - candidate[1]),
        (accepted[2] - accepted[0]) * (accepted[3] - accepted[1]),
    )
    return smaller > 0 and inter / smaller > OVERLAP_CONTAINMENT


def _is_duplicate(box, text, accepted_pairs) -> bool:
    """Box overlap, or same text at an overlapping position, means the
    original line already covers this content; originals always win."""
    for accepted_box, accepted_text in accepted_pairs:
        if _duplicates_box(box, accepted_box):
            return True
        if text == accepted_text and box_iou(box, accepted_box) > OVERLAP_TEXT_IOU:
            return True
    return False


def plan_regions(
    diagnostics, *, accept_threshold: float, max_regions: int = 4
) -> tuple[int, ...]:
    """Select recoverable dropped-region indexes, best candidate first.

    Generic signals only: recognizer score in a hopeful band below the
    acceptance threshold, minimum width/height and a line-like aspect ratio.
    """
    selected = []
    for index, region in enumerate(diagnostics.dropped):
        if region.reason != "low_text_score":
            continue
        if not (RECOVERY_SCORE_FLOOR <= region.confidence < accept_threshold):
            continue
        width = region.box[2] - region.box[0]
        height = region.box[3] - region.box[1]
        if width < MIN_REGION_WIDTH or height < MIN_REGION_HEIGHT:
            continue
        if width / height < MIN_REGION_ASPECT:
            continue
        selected.append(index)
    selected.sort(
        key=lambda i: (-diagnostics.dropped[i].confidence, diagnostics.dropped[i].box)
    )
    return tuple(selected[:max_regions])


def _load_image(image_bytes: bytes):
    from PIL import Image

    with Image.open(io.BytesIO(image_bytes)) as image:
        return image.convert("RGB")


def _as_image(image):
    """Accept a loaded PIL image or raw/BytesIO PNG bytes."""
    if hasattr(image, "size"):
        return image
    return _load_image(image.getvalue() if hasattr(image, "getvalue") else image)


def _crop_window(box, image_size, *, margin_ratio: float):
    """Clamped integer crop window with symmetric vertical margin."""
    image_w, image_h = image_size
    x0, y0, x1, y1 = box
    cx0 = max(0, min(image_w - 1, int(round(x0))))
    cx1 = max(cx0 + 1, min(image_w, int(round(x1))))
    cy0 = max(0, min(image_h - 1, int(round(y0))))
    cy1 = max(cy0 + 1, min(image_h, int(round(y1))))
    margin = int(round(margin_ratio * (cy1 - cy0)))
    cy0 = max(0, cy0 - margin)
    cy1 = min(image_h, cy1 + margin)
    return cx0, cy0, cx1, cy1


def _png_bytes(pil_image) -> bytes:
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_margin_crop(image, box, *, margin_ratio: float = MARGIN_RATIO):
    """Axis-aligned crop with vertical margin; returns ``(png, transform)``."""
    image = _as_image(image)
    cx0, cy0, cx1, cy1 = _crop_window(box, image.size, margin_ratio=margin_ratio)
    crop = image.crop((cx0, cy0, cx1, cy1))
    transform = {
        "transform": MARGIN_CROP_TRANSFORM,
        "kind": "translate",
        "origin": (float(cx0), float(cy0)),
        "size": crop.size,
    }
    return _png_bytes(crop), transform


def _column_dark_counts(crop, *, dark_threshold: int = DARK_THRESHOLD) -> list[int]:
    grayscale = crop.convert("L")
    width, height = grayscale.size
    pixels = grayscale.load()
    counts = []
    for x in range(width):
        dark = 0
        for y in range(0, height, 2):
            if pixels[x, y] < dark_threshold:
                dark += 1
        counts.append(dark)
    return counts


def build_split_stack(image, box, *, margin_ratio: float = MARGIN_RATIO):
    """Split the region at whitespace gaps and stack chunks vertically.

    Returns ``(png, transform)``; the transform's chunk table maps stacked
    coordinates back to original-image coordinates per chunk.
    """
    image = _as_image(image)
    cx0, cy0, cx1, cy1 = _crop_window(box, image.size, margin_ratio=margin_ratio)
    crop = image.crop((cx0, cy0, cx1, cy1))
    width, height = crop.size
    counts = _column_dark_counts(crop)
    max_width = max(1, int(SPLIT_TARGET_RATIO * height))
    cuts = []
    x = 0
    while width - x > max_width:
        # Prefer the rightmost whitespace gap inside the window so each chunk
        # stays close to the target ratio instead of shattering into word
        # fragments; force a split only when no gap is wide enough.
        lo = x + int(max_width * 0.3)
        hi = min(x + max_width, width - 1)
        best_start = None
        run_start = None
        for cx in range(lo, hi + 1):
            if counts[cx] == 0:
                if run_start is None:
                    run_start = cx
            else:
                if run_start is not None and cx - run_start >= SPLIT_MIN_GAP:
                    best_start = run_start
                run_start = None
        if run_start is not None and hi + 1 - run_start >= SPLIT_MIN_GAP:
            best_start = run_start
        if best_start is None:
            cut, forced = x + max_width, True
        else:
            cut, forced = best_start, False
        cuts.append((min(cut, width - 1), forced))
        x = cuts[-1][0]
    bounds = [0] + [cut for cut, _ in cuts] + [width]
    chunks = []
    for i in range(len(bounds) - 1):
        x0, x1 = bounds[i], bounds[i + 1]
        if x1 - x0 >= 4:
            chunks.append((x0, x1))
    stack_width = max(x1 - x0 for x0, x1 in chunks)
    total_height = sum(height for _ in chunks) + SPLIT_GAP_ROWS * (len(chunks) - 1)
    from PIL import Image as PILImage

    stack = PILImage.new("RGB", (stack_width, total_height), (255, 255, 255))
    table = []
    y = 0
    for x0, x1 in chunks:
        stack.paste(crop.crop((x0, 0, x1, height)), (0, y))
        # (stack_x0, stack_y0, origin_x, origin_y, crop_x0, crop_x1)
        table.append((0, y, cx0 + x0, cy0, x0, x1))
        y += height + SPLIT_GAP_ROWS
    transform = {
        "transform": SPLIT_STACK_TRANSFORM,
        "kind": "split-stack",
        "size": stack.size,
        "chunks": tuple(table),
    }
    return _png_bytes(stack), transform


def build_upscale(image, box, *, factor: float = UPSCALE_FACTOR):
    """Uniform integer upscale of the region crop; ``(png, transform)``."""
    from PIL import Image as PILImage

    image = _as_image(image)
    cx0, cy0, cx1, cy1 = _crop_window(box, image.size, margin_ratio=MARGIN_RATIO)
    crop = image.crop((cx0, cy0, cx1, cy1))
    resized = crop.resize(
        (int(crop.size[0] * factor), int(crop.size[1] * factor)),
        PILImage.Resampling.LANCZOS,
    )
    transform = {
        "transform": UPSCALE_TRANSFORM,
        "kind": "scale",
        "origin": (float(cx0), float(cy0)),
        "scale": 1.0 / factor,
        "size": resized.size,
    }
    return _png_bytes(resized), transform


def map_box(transform: dict, box) -> tuple[float, float, float, float] | None:
    """Map a transform-space box back to original-image coordinates.

    Supports ``translate``, ``scale``, ``rotate`` (90/180/270 with the
    pre-rotation canvas size), ``pad`` and the split-stack chunk table.
    Returns ``None`` for degenerate, non-finite or unmappable input instead of
    guessing.
    """
    if not isinstance(box, (tuple, list)) or len(box) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in box)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    kind = transform.get("kind")
    if kind == "translate":
        ox, oy = transform["origin"]
        return (x0 + ox, y0 + oy, x1 + ox, y1 + oy)
    if kind == "scale":
        ox, oy = transform["origin"]
        scale = float(transform["scale"])
        return (
            ox + x0 * scale,
            oy + y0 * scale,
            ox + x1 * scale,
            oy + y1 * scale,
        )
    if kind == "rotate":
        width, height = transform["size"]
        angle = transform["angle"]
        if angle == 90:
            return (height - y1, x0, height - y0, x1)
        if angle == 180:
            return (width - x1, height - y1, width - x0, height - y0)
        if angle == 270:
            return (y0, width - x1, y1, width - x0)
        return None
    if kind == "pad":
        left = transform.get("left", 0)
        top = transform.get("top", 0)
        return (x0 - left, y0 - top, x1 - left, y1 - top)
    if kind == "split-stack":
        # Chunk rows are stacked top-to-bottom separated by gap rows; map the
        # box into whichever chunk's row range contains its vertical center,
        # then translate by that chunk's crop-offset delta.
        center_y = (y0 + y1) / 2
        for index, chunk in enumerate(transform["chunks"]):
            sx0, sy0, ox, oy, _cx0, _cx1 = chunk
            sy1 = (
                transform["chunks"][index + 1][1] - SPLIT_GAP_ROWS
                if index + 1 < len(transform["chunks"])
                else float("inf")
            )
            if sy0 <= center_y < sy1:
                return (x0 - sx0 + ox, y0 - sy0 + oy, x1 - sx0 + ox, y1 - sy0 + oy)
        return None
    return None


def _second_attempt_kind(image, box):
    """Choose the second transform from geometry: split wide crops, else upscale."""
    cx0, cy0, cx1, cy1 = _crop_window(box, image.size, margin_ratio=MARGIN_RATIO)
    width, height = cx1 - cx0, cy1 - cy0
    if width / height > SPLIT_TARGET_RATIO:
        return SPLIT_STACK_TRANSFORM
    return UPSCALE_TRANSFORM


def _clamp_box(box, width: int, height: int):
    x0, y0, x1, y1 = box
    x0 = max(0.0, min(float(width), x0))
    y0 = max(0.0, min(float(height), y0))
    x1 = max(0.0, min(float(width), x1))
    y1 = max(0.0, min(float(height), y1))
    if x1 <= x0 or y1 <= y0:
        return None
    return (round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3))


def _region_candidates(crop_result, transform, region_box):
    """Map crop lines into the region and keep those centered inside it."""
    mapped = []
    for line in crop_result.lines:
        original = map_box(transform, line.box)
        if original is None:
            continue
        center_x = (original[0] + original[2]) / 2
        center_y = (original[1] + original[3]) / 2
        if not (
            region_box[0] <= center_x <= region_box[2]
            and region_box[1] <= center_y <= region_box[3]
        ):
            continue
        mapped.append((original, line))
    return mapped


def _stack_chunk_rows(transform):
    """Per-chunk ``(stack_y0, stack_y1, crop_x0, crop_x1)`` row windows.

    Chunk rows are contiguous, separated by :data:`SPLIT_GAP_ROWS` blank rows.
    """
    if transform.get("kind") != "split-stack":
        return None
    chunks = transform["chunks"]
    rows = []
    for index, (_sx0, sy0, _ox, _oy, cx0, cx1) in enumerate(chunks):
        sy1 = (
            chunks[index + 1][1] - SPLIT_GAP_ROWS
            if index + 1 < len(chunks)
            else float("inf")
        )
        rows.append((sy0, sy1, cx0, cx1))
    return rows


def _evaluate_attempt(
    *,
    crop_result,
    transform,
    region_box,
    image_size,
    accept_threshold,
    accepted_pairs,
    chunk_rows=None,
):
    """Accept only clean, fully passing, non-duplicate recoveries.

    Returns ``(line | None, note)``.  ``chunk_rows`` (from a split-stack
    transform) activates the all-chunks-must-pass stitching rule: every
    non-tiny chunk must contribute at least one line and all its lines must
    pass the threshold, so partial garbage never gets stitched.
    """
    candidates = _region_candidates(crop_result, transform, region_box)
    if not candidates:
        return None, "no_overlapping_lines"
    if chunk_rows is None:
        selected = candidates
    else:
        by_chunk: dict[int, list[tuple[tuple[float, float, float, float], OCRLine]]] = {
            index: [] for index in range(len(chunk_rows))
        }
        for original, line in candidates:
            center_y = (line.box[1] + line.box[3]) / 2
            for index, (sy0, sy1, _cx0, _cx1) in enumerate(chunk_rows):
                if sy0 <= center_y < sy1:
                    by_chunk[index].append((original, line))
                    break
        selected = []
        for index, (_sy0, _sy1, cx0, cx1) in enumerate(chunk_rows):
            lines_in_chunk = by_chunk[index]
            if cx1 - cx0 < TINY_CHUNK_WIDTH:
                continue  # icon-sized chunks: recorded only, never stitched
            if not lines_in_chunk:
                return None, "chunk_without_passing_line"
            selected.extend(lines_in_chunk)
        if not selected:
            return None, "only_tiny_chunks"
    for _, line in selected:
        if line.confidence < accept_threshold:
            return None, "line_below_threshold"
    for original, line in selected:
        if _is_duplicate(original, line.text, accepted_pairs):
            return None, "overlaps_accepted_line"
    text = " ".join(line.text for _, line in selected)
    x0 = min(original[0] for original, _ in selected)
    y0 = min(original[1] for original, _ in selected)
    x1 = max(original[2] for original, _ in selected)
    y1 = max(original[3] for original, _ in selected)
    merged = _clamp_box((x0, y0, x1, y1), image_size[0], image_size[1])
    if merged is None or not text:
        return None, "degenerate_merged_box"
    confidence = round(min(line.confidence for _, line in selected), 6)
    try:
        return OCRLine(text, merged, confidence), None
    except LocalOCRError:
        return None, "recovered_line_invalid"


def recover_regions(
    *,
    ocr,
    image_bytes: bytes,
    result,
    limits,
    budget: RecoveryBudget,
    accept_threshold: float,
) -> RegionRecoveryOutcome:
    """Run the bounded recovery ladder for one already-transcribed image."""
    diagnostics = result.region_diagnostics
    if diagnostics is None or not diagnostics.dropped:
        return RegionRecoveryOutcome((), diagnostics, 0, 0)
    image = _load_image(image_bytes)
    image_size = image.size
    selected = plan_regions(
        diagnostics,
        accept_threshold=accept_threshold,
        max_regions=budget.max_regions_per_image,
    )
    selected_set = set(selected)
    image_attempts = 0
    roi_pixels = 0
    attempts_used = 0
    recovered_lines = []
    recovery_records = []
    accepted_pairs = [(line.box, line.text) for line in result.lines]
    for index, region in enumerate(diagnostics.dropped):
        if index not in selected_set:
            recovery_records.append(OCRRegionRecovery(region.box, "not_attempted"))
            continue
        budget.regions_started += 1
        attempts: list[OCRRecoveryAttempt] = []
        status = "unrecovered"
        second = _second_attempt_kind(image, region.box)
        for transform_name in (MARGIN_CROP_TRANSFORM, second):
            if (
                image_attempts >= budget.max_attempts_per_image
                or len(attempts) >= budget.max_attempts_per_region
            ):
                status = "budget_exhausted"
                break
            limits.check_deadline()
            if transform_name == MARGIN_CROP_TRANSFORM:
                data, transform = build_margin_crop(image, region.box)
                params = {"margin_ratio": MARGIN_RATIO}
            elif transform_name == SPLIT_STACK_TRANSFORM:
                data, transform = build_split_stack(image, region.box)
                params = {
                    "target_ratio": SPLIT_TARGET_RATIO,
                    "gap_rows": SPLIT_GAP_ROWS,
                    "min_gap": SPLIT_MIN_GAP,
                    "dark_threshold": DARK_THRESHOLD,
                }
            else:
                data, transform = build_upscale(image, region.box)
                params = {"factor": UPSCALE_FACTOR}
            width, height = transform["size"]
            limits.require_within("max_image_pixels", width * height)
            budget.total_roi_pixels += width * height
            roi_pixels += width * height
            image_attempts += 1
            budget.total_attempts += 1
            attempts_used += 1
            try:
                limits.check_deadline()
                crop_result = ocr.transcribe(data, limits=limits)
                limits.check_deadline()  # native return, cooperative only
            except NormalizationLimitError:
                raise
            except LocalOCRError as exc:
                if exc.code not in _RETRYABLE_ATTEMPT_ERRORS:
                    raise
                attempts.append(
                    OCRRecoveryAttempt(
                        transform_name, params, "error", (), error=exc.code
                    )
                )
                continue
            if not isinstance(crop_result, ImageOCRResult):
                attempts.append(
                    OCRRecoveryAttempt(
                        transform_name, params, "error", (), error="OCR_RESULT_INVALID"
                    )
                )
                continue
            observed = tuple(
                (line.text, line.confidence) for line in crop_result.lines
            )
            line, note = _evaluate_attempt(
                crop_result=crop_result,
                transform=transform,
                region_box=region.box,
                image_size=image_size,
                accept_threshold=accept_threshold,
                accepted_pairs=accepted_pairs,
                chunk_rows=_stack_chunk_rows(transform),
            )
            if line is None:
                attempts.append(
                    OCRRecoveryAttempt(
                        transform_name, params, "rejected", observed, note=note
                    )
                )
                continue
            attempts.append(
                OCRRecoveryAttempt(transform_name, params, "accepted", observed)
            )
            recovery_records.append(
                OCRRegionRecovery(
                    region.box,
                    "recovered",
                    tuple(attempts),
                    recovered_text=line.text,
                    recovered_box=line.box,
                    recovered_confidence=line.confidence,
                )
            )
            recovered_lines.append(line)
            accepted_pairs.append((line.box, line.text))
            status = "recovered"
            break
        if status != "recovered":
            recovery_records.append(
                OCRRegionRecovery(region.box, status, tuple(attempts))
            )
    updated = replace(diagnostics, recovery=tuple(recovery_records))
    return RegionRecoveryOutcome(tuple(recovered_lines), updated, roi_pixels, attempts_used)
