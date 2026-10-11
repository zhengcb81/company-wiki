# W05-CWP-OCR generic-mechanism probe on two non-Microsoft small images.
# SYNTHETIC images (marked synthetic everywhere; never a substitute for the
# real slide7 acceptance): one Chinese, one English, each with a strong line
# and a faint low-contrast line to exercise the generic low-score/geometry
# mechanism. Local CPU only; no network; output = one JSON log.
import hashlib
import io
import json
import os
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORKTREE = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKTREE, "src"))

OUT = os.path.join(HERE, "synthetic-probe.json")
CONFIG_PATH = os.path.join(WORKTREE, "config", "local_ocr.json")
CONFIG_SHA = "3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105"


def forbid(*a, **kw):
    raise AssertionError("network must never be reached")


socket.create_connection = forbid
socket.socket.connect = forbid


def make_image(lines, path):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    font_path = None
    for candidate in (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if os.path.exists(candidate):
            font_path = candidate
            break
    image = Image.new("RGB", (720, 160), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    for index, (text, color) in enumerate(lines):
        try:
            font = ImageFont.truetype(font_path, 26)
        except Exception:
            font = ImageFont.load_default()
        draw.text((24, 24 + index * 56), text, fill=color, font=font)
    # Render the second line at low resolution and upscale with NEAREST so
    # aliasing artifacts make recognition genuinely hard: either a
    # score-filtered drop or an honest miss, never forced text.
    band = Image.new("RGB", (180, 16), (255, 255, 255))
    bdraw = ImageDraw.Draw(band)
    try:
        tiny_font = ImageFont.truetype(font_path, 7)
    except Exception:
        tiny_font = ImageFont.load_default()
    bdraw.text((2, 2), lines[1][0], fill=(120, 120, 120), font=tiny_font)
    band = band.resize((720, 64), Image.Resampling.NEAREST)
    image.paste(band, (0, 64))
    image.save(path, format="PNG")
    with open(path, "rb") as f:
        return f.read()


def main():
    from PIL import Image

    from company_wiki.document_normalization.local_ocr import (
        ImageOCRResult,
        LocalOCRAdapter,
        LocalOCRConfig,
        OCRLimits,
    )
    from company_wiki.document_normalization.ocr_region_recovery import (
        RecoveryBudget,
        plan_regions,
        recover_regions,
    )

    cfg_bytes = open(CONFIG_PATH, "rb").read()
    assert hashlib.sha256(cfg_bytes).hexdigest() == CONFIG_SHA
    config = LocalOCRConfig.from_dict(json.loads(cfg_bytes.decode("utf-8")))
    adapter = LocalOCRAdapter(config)

    cases = [
        (
            "chinese-synthetic",
            [("云基础设施与办公套件收入合计增长明显", (20, 20, 20)),
             ("企业服务续约率保持稳定", (150, 150, 150))],
        ),
        (
            "english-synthetic",
            [("Server products revenue mix shifted this quarter", (20, 20, 20)),
             ("Consumer offerings remained broadly unchanged", (150, 150, 150))],
        ),
    ]
    report = {
        "schema_version": "w05-synthetic-probe/1",
        "synthetic": True,
        "note": "Synthetic images exercise the generic geometry/low-score mechanism only; "
        "they never substitute for the real slide7 acceptance.",
        "config_sha256": CONFIG_SHA,
        "cases": [],
        "network_calls": 0,
        "paid_calls": 0,
    }
    for name, lines in cases:
        png_path = os.path.join(HERE, f"{name}.png")
        data = make_image(lines, png_path)
        started = time.perf_counter()
        result = adapter.transcribe(data, limits=OCRLimits())
        diagnostics = result.region_diagnostics
        case = {
            "name": name,
            "synthetic": True,
            "image_bytes": len(data),
            "transcribe_seconds": round(time.perf_counter() - started, 3),
            "accepted_lines": [
                {"text": l.text, "box": list(l.box), "confidence": l.confidence}
                for l in result.lines
            ],
            "dropped": diagnostics.to_dict()["dropped"] if diagnostics else None,
        }
        if diagnostics is not None and diagnostics.dropped:
            selected = plan_regions(diagnostics, accept_threshold=config.text_score)
            case["planned_region_indexes"] = list(selected)
            outcome = recover_regions(
                ocr=adapter,
                image_bytes=data,
                result=result,
                limits=OCRLimits(),
                budget=RecoveryBudget(),
                accept_threshold=config.text_score,
            )
            case["recovery"] = outcome.diagnostics.to_dict()["recovery"]
            case["recovered_lines"] = [
                {"text": l.text, "box": list(l.box), "confidence": l.confidence}
                for l in outcome.recovered_lines
            ]
        report["cases"].append(case)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
