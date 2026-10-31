"""One-off converter: bf16 checkpoint -> fp32 safetensors copy (exact upcast).

bf16 is a truncated fp32, so the upcast is exact — the fp32 file carries the
same numbers, no quantization.  The output is written once next to the HF
snapshot as a declared experiment asset; the comparator loads it with the same
read-only file mapping (mapped pages, no private commit).  Streaming
tensor-by-tensor so peak private memory stays at the largest single tensor.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import torch
from safetensors.torch import save_file

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.ocr_comparison.mmap_loader import parse_safetensors_header  # noqa: E402

SNAP = (Path(__file__).resolve().parents[2] / ".w23_cache" / "hub"
        / "models--xiaomi-research--Xiaomi-OCR-0" / "snapshots"
        / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30")
SRC = SNAP / "model.safetensors"
DST = SNAP / "model.fp32.safetensors"


def main() -> None:
    if DST.exists():
        print("exists", DST, DST.stat().st_size)
        return
    tensors, _ = parse_safetensors_header(SRC)
    storage = torch.from_file(str(SRC), shared=False, size=SRC.stat().st_size, dtype=torch.uint8)
    out: dict[str, torch.Tensor] = {}
    n = 0
    for name, (dt, shape, start, end) in tensors.items():
        view = storage[start:end].view(torch.bfloat16).view(shape)
        out[name] = view.to(torch.float32)  # exact upcast, new private tensor
        n += 1
        if n % 100 == 0:
            print("converted", n, flush=True)
    save_file(out, str(DST), metadata={"source": "model.safetensors bf16 exact upcast"})
    # spot-verify exactness against the source mapping
    check = {"model.language_model.embed_tokens.weight",
             "model.visual.blocks.0.mlp.fc1.weight"}
    for name in check & set(tensors):
        dt, shape, start, end = tensors[name]
        bf = storage[start:end].view(torch.bfloat16).view(shape)
        f32 = out[name]
        assert torch.equal(bf.to(torch.float32), f32), name
    digest = hashlib.sha256()
    with open(DST, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    print(json.dumps({
        "written": str(DST), "bytes": DST.stat().st_size,
        "sha256": digest.hexdigest(), "n_tensors": len(out),
    }))


if __name__ == "__main__":
    main()
