# W05-CWP-OCR Node A bounded cause-locating experiment.
# Local CPU ONNX only; no network; hard process stop; bounded call list.
# Reads exact original via given extended path; verifies all SHA; writes one JSON log.
import hashlib
import io
import json
import os
import socket
import sys
import threading
import time
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "src"))

SCRATCH = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRATCH, "locate-cause.json")

PPTX_EXT = "\\\\?\\C:\\Users\\郑曾波\\Projects\\company-wiki\\.source-preservation\\w04-temp-20261011\\US-MSFT\\roots\\prior_scope_raw\\MICROSOFT CORP\\raw\\investor_relations\\unknown-date_official_c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4_FY27 Segments and Investor Metrics.pptx"
PPTX_SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
MEDIA_PART = "ppt/media/image7.png"
MEDIA_SHA = "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "config", "local_ocr.json")
CONFIG_SHA = "3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105"

ROIS = [
    {"name": "business-line-1", "box": (94.0, 177.0, 2320.0, 216.0), "score": 0.43236},
    {"name": "business-line-2", "box": (150.0, 763.0, 1719.0, 805.0), "score": 0.44278},
]
HARD_TIMEOUT = 240
CALL_BUDGET = 13  # 1 full image + 6 per ROI

state = {"status": "RUNNING", "calls": 0}


def hard_stop():
    state["status"] = "HARD_TIMEOUT"
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os._exit(124)


threading.Timer(HARD_TIMEOUT, hard_stop).start()


def forbid(*a, **kw):
    raise AssertionError("network must never be reached")


socket.create_connection = forbid
socket.socket.connect = forbid


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    from PIL import Image, ImageOps

    from company_wiki.document_normalization.local_ocr import (
        LocalOCRAdapter,
        LocalOCRConfig,
        OCRLimits,
    )

    with open(CONFIG_PATH, "rb") as f:
        cfg_bytes = f.read()
    assert sha(cfg_bytes) == CONFIG_SHA, "config sha mismatch"
    cfg = LocalOCRConfig.from_dict(json.loads(cfg_bytes.decode("utf-8")))

    with open(PPTX_EXT, "rb") as f:
        pptx_bytes = f.read()
    assert sha(pptx_bytes) == PPTX_SHA, "pptx sha mismatch"
    with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zf:
        media = zf.read(MEDIA_PART)
    assert sha(media) == MEDIA_SHA, "media sha mismatch"

    adapter = LocalOCRAdapter(cfg)
    adapter.validate_environment()
    engine = adapter._engine

    def call(tag, image, use_cls=True):
        assert state["calls"] < CALL_BUDGET, "call budget exhausted"
        state["calls"] += 1
        started = time.perf_counter()
        out = engine(image, use_cls=use_cls, text_score=0.0)
        elapsed = time.perf_counter() - started
        txts = list(out.txts) if out.txts is not None else []
        scores = [round(float(s), 5) for s in (out.scores if out.scores is not None else [])]
        raw_boxes = out.boxes if out.boxes is not None else []
        boxes = [[round(float(v), 1) for v in (min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box))] for box in raw_boxes]
        rec = {
            "tag": tag,
            "use_cls": use_cls,
            "elapsed": round(elapsed, 3),
            "txts": txts,
            "scores": scores,
            "boxes": boxes,
        }
        state.setdefault("records", []).append(rec)
        print(f"[{state['calls']}/{CALL_BUDGET}] {tag} cls={use_cls} {elapsed:.1f}s n={len(rec['txts'])}", flush=True)
        return rec

    # E0: full image baseline with floor threshold (pre-filter observation).
    full_rgb = Image.open(io.BytesIO(media)).convert("RGB")
    prior = None
    if os.path.exists(OUT):
        try:
            prior = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            prior = None
    prior_e0 = next((r for r in (prior or {}).get("records", []) if r["tag"] == "E0-full-image"), None) if prior else None
    if prior_e0 is not None:
        state["calls"] += 1
        state.setdefault("records", []).append(prior_e0)
        e0 = prior_e0
        print(f"[reuse] E0-full-image n={len(e0['txts'])}", flush=True)
    else:
        e0 = call("E0-full-image", full_rgb)

    # Verify the 0.5-filtered accepted set matches the root-cause baseline 22 lines.
    baseline = json.load(open(os.path.join(SCRATCH, "..", "input", "slide7-root-cause.json"), encoding="utf-8"))
    expected = [(l["text"], l["box"]) for l in baseline["configured_probe"]["normalized_lines"]]
    accepted = sorted(
        (t, b)
        for t, s, b in zip(e0["txts"], e0["scores"], e0["boxes"])
        if s >= 0.5
    )
    state["e0_accepted_matches_root_cause"] = sorted((t, [round(v, 1) for v in bx]) for t, bx in expected) == accepted
    state["e0_counts"] = {"engine_returned": len(e0["txts"]), "accepted_at_0.5": len(accepted)}

    def luminance_gap_columns(crop, dark_thresh=200):
        g = crop.convert("L")
        w, h = g.size
        px = g.load()
        cols = []
        for x in range(w):
            dark = 0
            for y in range(0, h, 2):
                if px[x, y] < dark_thresh:
                    dark += 1
            cols.append(dark)
        return cols

    def split_points(crop, target_ratio=6.5, min_gap=5):
        w, h = crop.size
        cols = luminance_gap_columns(crop)
        max_w = int(target_ratio * h)
        cuts = []
        x = 0
        while w - x > max_w:
            # find widest zero-gap inside [x + 0.55*max_w, x + max_w]
            lo, hi = x + int(max_w * 0.55), min(x + max_w, w - 1)
            best, best_w = None, 0
            run_start = None
            for cx in range(lo, hi + 1):
                if cols[cx] == 0:
                    if run_start is None:
                        run_start = cx
                else:
                    if run_start is not None and cx - run_start > best_w:
                        best, best_w = run_start, cx - run_start
                    run_start = None
            if run_start is not None and hi + 1 - run_start > best_w:
                best, best_w = run_start, hi + 1 - run_start
            if best is None or best_w < min_gap:
                best = x + max_w  # forced split, may cut glyphs
                forced = True
            else:
                best = best + best_w // 2
                forced = False
            cuts.append((best, forced))
            x = best
        return cuts

    def build_split_stack(crop, gap_rows=8, bg=(255, 255, 255)):
        cuts = split_points(crop)
        w, h = crop.size
        bounds = [0] + [c for c, _ in cuts] + [w]
        chunks = []
        for i in range(len(bounds) - 1):
            x0, x1 = bounds[i], bounds[i + 1]
            if x1 - x0 >= 4:
                chunks.append((x0, x1, crop.crop((x0, 0, x1, h))))
        total_h = sum(c.size[1] for _, _, c in chunks) + gap_rows * (len(chunks) - 1)
        stack = Image.new("RGB", (max(c.size[0] for _, _, c in chunks), total_h), bg)
        y = 0
        placed = []
        for x0, x1, c in chunks:
            stack.paste(c, (0, y))
            placed.append((x0, x1, y, y + c.size[1]))
            y += c.size[1] + gap_rows
        return stack, bounds, placed, any(f for _, f in cuts)

    for roi in ROIS:
        x0, y0, x1, y1 = roi["box"]
        m = max(2, int((y1 - y0) * 0.35))
        box = (int(x0), int(max(0, y0 - m)), int(x1), int(min(full_rgb.size[1], y1 + m)))
        crop = full_rgb.crop(box)
        gw, gh = crop.size
        state.setdefault("roi_meta", []).append({"name": roi["name"], "crop_box": list(box), "size": [gw, gh], "orig_score": roi["score"]})

        call(f"{roi['name']}:plain-cls", crop, use_cls=True)
        call(f"{roi['name']}:plain-nocls", crop, use_cls=False)
        stack, bounds, placed, forced = build_split_stack(crop)
        r = call(f"{roi['name']}:splitstack{'-forced' if forced else ''}", stack, use_cls=True)
        r["split_bounds"] = bounds
        r["stack_places"] = placed
        gray = ImageOps.autocontrast(ImageOps.grayscale(crop)).convert("RGB")
        call(f"{roi['name']}:gray-autocontrast", gray, use_cls=True)
        up = crop.resize((gw * 2, gh * 2), Image.Resampling.LANCZOS)
        call(f"{roi['name']}:up2x", up, use_cls=True)
        rot = crop.rotate(180)
        call(f"{roi['name']}:rot180", rot, use_cls=True)

    state["status"] = "COMPLETED"
    state["config_sha256"] = CONFIG_SHA
    state["source_sha256"] = PPTX_SHA
    state["media_sha256"] = MEDIA_SHA
    state["network_calls"] = 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
