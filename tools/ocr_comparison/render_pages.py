"""Deterministic page rendering shared by every arm.

Both engines always consume the exact same PNG bytes for a page: renders are
produced once from the frozen sample manifest (pypdfium2, 200 DPI, RGB) and
identified by SHA-256.  X1's model-side resize/crop is recorded separately by
the X1 backend; equal source bytes never imply equal model tensors.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def render_pages(manifest_path: str | Path, out_dir: str | Path) -> list[dict]:
    import pypdfium2 as pdfium

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docs: dict[str, object] = {}
    records = []
    scale = manifest["render"]["draw_scale"]
    for page in manifest["pages"]:
        doc = manifest["documents"][page["doc"]]
        key = page["doc"]
        if key not in docs:
            docs[key] = pdfium.PdfDocument(_resolve_physical(doc))
        pdf = docs[key]
        image = (
            pdf[page["pdf_page_index"]]
            .render(scale=scale)
            .to_pil()
            .convert("RGB")
        )
        if page["role"] == "eval_degraded":
            deg = page["degradation"]
            w, h = image.size
            from PIL import Image

            image = image.resize(
                (round(w * deg["scale"]), round(h * deg["scale"])),
                Image.Resampling.LANCZOS,
            )
            image = image.rotate(
                deg["rotate_deg"], resample=Image.Resampling.BICUBIC,
                expand=True, fillcolor=(255, 255, 255),
            )
        target = out_dir / f"{page['page_id']}.png"
        image.save(target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != page["png_sha256"]:
            raise RuntimeError(
                f"render mismatch for {page['page_id']}: {digest} != {page['png_sha256']}"
            )
        records.append({
            "page_id": page["page_id"],
            "png": str(target),
            "sha256": digest,
            "px": list(image.size),
        })
    for pdf in docs.values():
        pdf.close()
    return records


def _resolve_physical(doc: dict) -> str:
    import os

    root_id = doc["root_id"]
    base = Path(os.environ["CWP_PROJECT_ROOT"])
    if root_id == "company_raw":
        return str(base / "companies" / doc["relative_path"])
    if root_id == "dayu_portfolio":
        return str(base.parent / "dayu-agent" / "workspace" / "portfolio" / doc["relative_path"])
    if root_id == "dropbox_stock":
        return str(Path(os.environ["USERPROFILE"]) / "Dropbox" / "Stock" / doc["relative_path"])
    raise ValueError(f"unknown root_id {root_id}")
