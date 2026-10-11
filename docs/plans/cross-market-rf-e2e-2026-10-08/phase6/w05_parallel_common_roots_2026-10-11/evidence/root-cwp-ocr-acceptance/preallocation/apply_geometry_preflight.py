"""One-shot replacement of ROOT's ROI geometry/render seam only."""
from pathlib import Path

path = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w05\cwp-ocr-root\src\company_wiki\document_normalization\ocr_region_recovery.py")
text = path.read_text(encoding="utf-8")
start = text.index("def build_margin_crop(")
end = text.index("\ndef map_box(", start)
text = text[:start] + '''@dataclass(frozen=True)
class _ROIPlan:
    """Integer crop/canvas geometry with no allocated output raster."""

    window: tuple[int, int, int, int]
    transform: dict
    chunks: tuple[tuple[int, int], ...] = ()


def _column_dark_counts(
    image, *, window=None, dark_threshold: int = DARK_THRESHOLD, limits=None
) -> list[int]:
    """Read only sampled source pixels; no crop or grayscale image allocation.

    The RGB integer coefficients and rounding match PIL's convert("L").
    Other modes use the existing luminance component or one reusable 1px
    converter (palette lookups are cached in at most 256 entries). Production
    recovery always receives the already-loaded RGB original.
    """
    if window is None:
        window = (0, 0, *image.size)
    x0, y0, x1, y1 = window
    pixels = image.load()
    mode = image.mode
    converter = None
    palette_cache = {}
    if mode not in {"RGB", "RGBA", "RGBX", "L", "LA", "1"}:
        from PIL import Image

        converter = Image.new(mode, (1, 1))
        if mode == "P":
            converter.palette = image.palette
    counts = []
    for x in range(x0, x1):
        if limits is not None and (x - x0) % 64 == 0:
            limits.check_deadline()
        dark = 0
        for y in range(y0, y1, 2):
            value = pixels[x, y]
            if mode in {"RGB", "RGBA", "RGBX"}:
                r, g, b = value[:3]
                value = (19595*r + 38470*g + 7471*b + 32768) >> 16
            elif mode == "LA":
                value = value[0]
            elif converter is not None:
                if mode == "P" and value in palette_cache:
                    value = palette_cache[value]
                else:
                    converter.putpixel((0, 0), value)
                    gray = converter.convert("L").getpixel((0, 0))
                    if mode == "P":
                        palette_cache[value] = gray
                    value = gray
            if value < dark_threshold:
                dark += 1
        counts.append(dark)
    if limits is not None:
        limits.check_deadline()
    return counts


def _plan_transform(
    image, box, transform_name, *, margin_ratio=MARGIN_RATIO,
    factor=UPSCALE_FACTOR, limits=None
) -> _ROIPlan:
    """Plan exact output geometry before crop/resize/stack allocation.

    Split whitespace analysis reads only the chosen source ROI on every other
    row. Canvas dimensions include blank columns and inter-chunk padding;
    all other transforms depend solely on the integer crop window.
    """
    window = _crop_window(box, image.size, margin_ratio=margin_ratio)
    cx0, cy0, cx1, cy1 = window
    width, height = cx1-cx0, cy1-cy0
    origin = (float(cx0), float(cy0))
    if transform_name == MARGIN_CROP_TRANSFORM:
        return _ROIPlan(window, {"transform": transform_name, "kind": "translate",
            "origin": origin, "size": (width, height)})
    if transform_name == UPSCALE_TRANSFORM:
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("upscale factor must be positive and finite")
        size = (int(width*factor), int(height*factor))
        if min(size) <= 0:
            raise ValueError("upscale factor produced an empty canvas")
        return _ROIPlan(window, {"transform": transform_name, "kind": "scale",
            "origin": origin, "scale": 1.0/factor, "size": size})
    if transform_name != SPLIT_STACK_TRANSFORM:
        raise ValueError("unknown ROI transform")
    counts = _column_dark_counts(image, window=window, limits=limits)
    max_width = max(1, (13*height)//2)  # fixed SPLIT_TARGET_RATIO=6.5
    cuts = []
    x = 0
    while width - x > max_width:
        lo = x + (3*max_width)//10
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
        cut = x + max_width if best_start is None else best_start
        cuts.append(min(cut, width - 1))
        x = cuts[-1]
    bounds = [0] + cuts + [width]
    chunks = tuple((x0, x1) for x0, x1 in zip(bounds, bounds[1:]) if x1-x0 >= 4)
    stack_width = max(x1-x0 for x0, x1 in chunks)
    total_height = height*len(chunks) + SPLIT_GAP_ROWS*(len(chunks)-1)
    table = tuple((0, index*(height+SPLIT_GAP_ROWS), cx0+x0, cy0, x0, x1)
        for index, (x0, x1) in enumerate(chunks))
    return _ROIPlan(window, {"transform": transform_name, "kind": "split-stack",
        "size": (stack_width, total_height), "chunks": table}, chunks)


def build_margin_crop(image, box, *, margin_ratio: float = MARGIN_RATIO, _plan=None):
    """Render an axis-aligned crop from previously checked integer geometry."""
    image = _as_image(image)
    plan = _plan or _plan_transform(image, box, MARGIN_CROP_TRANSFORM, margin_ratio=margin_ratio)
    return _png_bytes(image.crop(plan.window)), plan.transform


def build_split_stack(image, box, *, margin_ratio: float = MARGIN_RATIO, _plan=None):
    """Render whitespace chunks and padding after geometry reservation."""
    from PIL import Image as PILImage

    image = _as_image(image)
    plan = _plan or _plan_transform(image, box, SPLIT_STACK_TRANSFORM, margin_ratio=margin_ratio)
    crop = image.crop(plan.window)
    height = plan.window[3]-plan.window[1]
    stack = PILImage.new("RGB", plan.transform["size"], (255, 255, 255))
    for index, (x0, x1) in enumerate(plan.chunks):
        stack.paste(crop.crop((x0, 0, x1, height)), (0, index*(height+SPLIT_GAP_ROWS)))
    return _png_bytes(stack), plan.transform


def build_upscale(image, box, *, factor: float = UPSCALE_FACTOR, _plan=None):
    """Render an upscale only after exact target canvas reservation."""
    from PIL import Image as PILImage

    image = _as_image(image)
    plan = _plan or _plan_transform(image, box, UPSCALE_TRANSFORM, factor=factor)
    resized = image.crop(plan.window).resize(plan.transform["size"], PILImage.Resampling.LANCZOS)
    return _png_bytes(resized), plan.transform

''' + text[end:]
old = '''            if transform_name == MARGIN_CROP_TRANSFORM:
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
            budget.reserve_pixels(width * height, limits=limits, roi=True)
            roi_pixels += width * height
            image_attempts += 1
            budget.total_attempts += 1
            attempts_used += 1
            try:
                limits.check_deadline()
                crop_result = ocr.transcribe(data, limits=limits)
'''
new = '''            if transform_name == MARGIN_CROP_TRANSFORM:
                builder = build_margin_crop
                params = {"margin_ratio": MARGIN_RATIO}
            elif transform_name == SPLIT_STACK_TRANSFORM:
                builder = build_split_stack
                params = {
                    "target_ratio": SPLIT_TARGET_RATIO,
                    "gap_rows": SPLIT_GAP_ROWS,
                    "min_gap": SPLIT_MIN_GAP,
                    "dark_threshold": DARK_THRESHOLD,
                }
            else:
                builder = build_upscale
                params = {"factor": UPSCALE_FACTOR}
            plan = _plan_transform(image, region.box, transform_name, limits=limits)
            transform = plan.transform
            width, height = transform["size"]
            budget.reserve_pixels(width * height, limits=limits, roi=True)
            roi_pixels += width * height
            image_attempts += 1
            budget.total_attempts += 1
            attempts_used += 1
            try:
                limits.check_deadline()
                data, transform = builder(image, region.box, _plan=plan)
                limits.check_deadline()
                crop_result = ocr.transcribe(data, limits=limits)
'''
assert text.count(old) == 1
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Reserved exact ROI canvas before raster allocation and inference; unchanged transform grammar.")
