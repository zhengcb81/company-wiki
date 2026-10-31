"""Explicit, bounded-memory BF16 -> F32 checkpoint conversion.

The caller must choose both paths; no cache/snapshot is implicitly modified.
Conversion widens stored values exactly. It does not establish compute parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import struct
import tempfile
from pathlib import Path


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_checkpoint(source: Path, output: Path) -> dict:
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.exists():
        raise FileExistsError("output must be a new, explicitly selected file")
    source_sha = _sha(source)
    with source.open("rb") as inp:
        length = struct.unpack("<Q", inp.read(8))[0]
        header = json.loads(inp.read(length))
        base = 8 + length
        converted = {"__metadata__": {"conversion": "BF16 exact value widening to F32",
                                      "source_sha256": source_sha}}
        offset = 0
        for key, spec in header.items():
            if key == "__metadata__":
                continue
            if spec["dtype"] != "BF16":
                raise ValueError(f"expected BF16 tensor: {key}")
            start, end = spec["data_offsets"]
            if start < 0 or end < start or (end - start) % 2 or base + end > source.stat().st_size:
                raise ValueError(f"invalid tensor extent: {key}")
            size = 2 * (end - start)
            converted[key] = {"dtype": "F32", "shape": spec["shape"],
                              "data_offsets": [offset, offset + size]}
            offset += size
        encoded = json.dumps(converted, separators=(",", ":")).encode("utf-8")
        encoded += b" " * (-len(encoded) % 8)
        fd, name = tempfile.mkstemp(prefix="w23-fp32-", suffix=".tmp", dir=output.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(struct.pack("<Q", len(encoded)))
                out.write(encoded)
                for key, spec in header.items():
                    if key == "__metadata__":
                        continue
                    start, end = spec["data_offsets"]
                    inp.seek(base + start)
                    remaining = end - start
                    while remaining:
                        raw = inp.read(min(remaining, 1024 * 1024))
                        if not raw:
                            raise ValueError("truncated checkpoint")
                        widened = bytearray(len(raw) * 2)
                        widened[2::4], widened[3::4] = raw[::2], raw[1::2]
                        out.write(widened)
                        remaining -= len(raw)
                out.flush()
                os.fsync(out.fileno())
            # Hard-link publication is atomic and refuses a concurrent output.
            os.link(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
    return {"source_sha256": source_sha, "output_sha256": _sha(output),
            "bytes": output.stat().st_size, "tensors": len(converted) - 1}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(convert_checkpoint(args.source, args.output)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
