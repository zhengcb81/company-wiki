"""Mapped-weights loader for the X1 arm (memory-bound host).

Builds the model on the meta device, then assigns every checkpoint tensor as a
read-only file mapping (``torch.from_file``) instead of a private copy.  The
weight bytes are the frozen checkpoint's own bytes (same file, same SHA-256);
nothing is converted, quantized or re-saved.  Only the loading strategy
differs from ``from_pretrained``: mapped pages are file-backed, so the process
commit charge holds only the fixed stack plus activations, and the Job Object
limit continues to be enforced by the operating system on committed memory.

Declared identity: any run using this loader records
``weights_loading: "torch.from_file read-only file mapping (meta init + assign)"``
in its backend identity manifest.
"""

from __future__ import annotations

import json
import mmap as _mmap
import struct
from pathlib import Path

import torch

# Read-only file mappings and their handles must outlive every tensor view.
_KEEPALIVE: list = []

_DTYPES = {
    "BF16": torch.bfloat16, "F16": torch.float16, "F32": torch.float32,
    "F64": torch.float64, "I8": torch.int8, "U8": torch.uint8,
    "I16": torch.int16, "I32": torch.int32, "I64": torch.int64,
    "BOOL": torch.bool,
}


def _read_only_mapped_storage(weights_path: Path) -> torch.Tensor:
    """uint8 tensor over a true read-only file section.

    ``torch.from_file(shared=False)`` maps copy-on-write, which Windows charges
    in full against process commit; a READ section (like Python's mmap module
    uses) is file-backed and commit-free.  Verified in the W23 receipts.
    """
    handle = open(weights_path, "rb")
    view = _mmap.mmap(handle.fileno(), length=0, access=_mmap.ACCESS_READ)
    _KEEPALIVE.append((handle, view))
    return torch.frombuffer(view, dtype=torch.uint8, count=view.size())


def parse_safetensors_header(path: Path) -> tuple[dict, int]:
    """Return ({name: (dtype, shape, start, end)}, data_section_base)."""
    with open(path, "rb") as fh:
        (header_len,) = struct.unpack("<Q", fh.read(8))
        header = json.loads(fh.read(header_len).decode("utf-8"))
    base = 8 + header_len
    tensors = {}
    for name, spec in header.items():
        if name == "__metadata__":
            continue
        tensors[name] = (
            spec["dtype"], tuple(spec["shape"]),
            base + spec["data_offsets"][0], base + spec["data_offsets"][1],
        )
    return tensors, base


def load_model_with_mapped_weights(model_dir: str | Path, *, weights_file: str = "model.safetensors"):
    """Load the checkpoint with weights as read-only file mappings.

    ``weights_file`` selects the mapped artifact: the frozen bf16 checkpoint,
    or the exact fp32 upcast copy ("model.fp32.safetensors", bf16 numbers
    widened losslessly, no quantization).
    """
    from transformers import AutoConfig, AutoModelForImageTextToText

    model_dir = Path(model_dir)
    weights_path = model_dir / weights_file
    tensors, _base = parse_safetensors_header(weights_path)

    config = AutoConfig.from_pretrained(str(model_dir), trust_remote_code=False)
    with torch.device("meta"):
        model = AutoModelForImageTextToText.from_config(config, trust_remote_code=False)

    storage = _read_only_mapped_storage(weights_path)
    state = {}
    skipped_mtp = []
    dtypes_seen = set()
    for name, (dt, shape, start, end) in tensors.items():
        if name.startswith("mtp."):
            # Multi-token-prediction training head: from_config builds no such
            # module and from_pretrained ignores these keys; generation does
            # not use them.  Recorded, never silently dropped.
            skipped_mtp.append(name)
            continue
        view = storage[start:end]
        dtypes_seen.add(dt)
        if dt != "U8":
            view = view.view(_DTYPES[dt])
        state[name] = view.view(shape)

    incompatible = model.load_state_dict(state, strict=False, assign=True)
    unexpected = list(incompatible.unexpected_keys)
    missing = list(incompatible.missing_keys)
    if unexpected:
        raise RuntimeError(f"unexpected checkpoint keys: {unexpected[:8]}")
    model.tie_weights()
    tied = {"lm_head.weight"} if getattr(config, "tie_word_embeddings", False) else set()
    unexplained_missing = [k for k in missing if k not in tied]
    if unexplained_missing:
        raise RuntimeError(f"missing checkpoint keys: {unexplained_missing[:8]}")

    still_meta = []
    for name, tensor in model.state_dict().items():
        if tensor.is_meta:
            still_meta.append(name)
    if still_meta:
        raise RuntimeError(f"meta tensors remain after assign: {still_meta[:8]}")

    # Non-persistent buffers (rotary inv_freq and friends) are not in the
    # checkpoint and stay meta under a meta-device build.  Rebuild each owning
    # module on the CPU from its own config and graft it, so the computation
    # matches from_pretrained exactly.
    import inspect

    grafted = []
    holders = sorted({name.rsplit(".", 1)[0] for name, buf in model.named_buffers()
                      if buf.is_meta})
    for holder_name in holders:
        module = model.get_submodule(holder_name)
        signature = inspect.signature(type(module).__init__)
        has_config = "config" in signature.parameters and hasattr(module, "config")
        if not has_config:
            raise RuntimeError(
                f"meta buffers under {holder_name} with no config-based rebuild"
            )
        rebuilt = type(module)(module.config, device="cpu")
        parent_path, _, leaf = holder_name.rpartition(".")
        parent = model.get_submodule(parent_path) if parent_path else model
        setattr(parent, leaf, rebuilt)
        grafted.append(holder_name)
    leftover = [name for name, buf in model.named_buffers() if buf.is_meta]
    if leftover:
        raise RuntimeError(f"meta buffers remain after rebuild: {leftover[:8]}")

    model.eval()
    info = {
        "weights_file": str(weights_path),
        "weights_mode_file": weights_file,
        "weights_bytes": weights_path.stat().st_size,
        "n_tensors": len(state),
        "dtypes": sorted(dtypes_seen),
        "skipped_mtp_keys": len(skipped_mtp),
        "rebuilt_cpu_modules": grafted,
        "missing_keys_allowed": sorted(set(missing) & tied),
    }
    return model, info


def verify_mapped_tensors(model_dir: str | Path, keys: list[str]) -> dict:
    """Byte-compare selected mapped tensors against safe_open copies."""
    from safetensors import safe_open

    model_dir = Path(model_dir)
    weights_path = model_dir / "model.safetensors"
    tensors, _ = parse_safetensors_header(weights_path)
    storage = _read_only_mapped_storage(weights_path)
    results = {}
    with safe_open(str(weights_path), framework="pt", device="cpu") as handle:
        for key in keys:
            if key not in tensors:
                results[key] = "absent"
                continue
            dt, shape, start, end = tensors[key]
            mapped = storage[start:end].view(_DTYPES[dt]).view(shape)
            reference = handle.get_tensor(key)
            results[key] = bool(torch.equal(mapped, reference))
    return results
