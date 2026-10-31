"""X1 arm: Xiaomi-OCR-0 whole-page parsing on CPU transformers.

Follows the upstream evaluation contract at the frozen commit: the official
document prompt, non-thinking chat template, temperature 0 / top_p 0.8, the
2048-bound fit_image preprocessing, and the upstream postprocess (math
delimiters, OTSL tables, truncated-repeat cleanup).  No vLLM/Ollama/quantized
variant is involved; results are HF-checkpoint CPU behaviour, never the
official GPU leaderboard.

VLM output has no word boxes or confidences: bbox/confidence stay null and
locator_quality is "none" (whole-page) — never fabricated.
"""

from __future__ import annotations

import base64
import threading
import time
from io import BytesIO
from pathlib import Path

from .base import (
    classify_raw_output,
    detect_repetition,
    enforce_output_cap,
    serialize_lines,
    sha256_text,
)

# Verbatim upstream prompt (evaluation_pipeline/e2e_img2md.py, frozen commit).
PROMPT_DOCUMENT = (
    "Extract all information from the main body of the document image and represent it "
    "in markdown format, ignoring headers and footers. Tables should be expressed in OTSL "
    "format, formulas in the document should be represented using LATEX format, and the "
    "parsing should be organized according to the reading order."
)
MAX_IMAGE_EDGE = 2048


class MemoryCapExceeded(RuntimeError):
    pass


def _process_commit_bytes() -> int:
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
        handle, ctypes.byref(counters), ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    ):
        return 0
    return counters.PagefileUsage  # commit charge of this process


def start_memory_watchdog(cap_bytes: int, state: dict) -> threading.Thread:
    """Sample this process's commit every 0.5s; flag a cap violation.

    Generation cannot be safely interrupted mid-op, so the violation is
    reported honestly (status error) instead of silently ignored.
    """

    def sample():
        while not state.get("stop"):
            state["peak_commit"] = max(state.get("peak_commit", 0), _process_commit_bytes())
            if state["peak_commit"] > cap_bytes:
                state["exceeded"] = True
                return
            time.sleep(0.5)

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    return thread


class XiaomiX1:
    arm = "X1"

    def __init__(
        self,
        *,
        model_dir: str,
        deadline_seconds: float,
        max_new_tokens: int = 2048,
        output_char_cap: int = 60000,
        memory_cap_bytes: int | None = None,
        dtype: str = "bfloat16",
    ):
        self.model_dir = str(model_dir)
        self.deadline_seconds = deadline_seconds
        self.max_new_tokens = max_new_tokens
        self.output_char_cap = output_char_cap
        self.memory_cap_bytes = memory_cap_bytes
        self.dtype = dtype
        self.identity_manifest = {
            "arm": self.arm,
            "backend": "xiaomi-ocr-0-transformers-cpu",
            "model_revision": "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30",
            "precision": f"checkpoint-native-{dtype}-cpu",
            "prompt_sha256": sha256_text(PROMPT_DOCUMENT),
            "preprocess": f"fit_image_thumbnail_{MAX_IMAGE_EDGE}",
            "decoding": "greedy_temperature_0_top_p_0.8_no_think",
            "max_new_tokens": max_new_tokens,
            "output_char_cap": output_char_cap,
        }
        self._model = None
        self._processor = None
        self.load_seconds = None

    def load(self) -> None:
        """Load once per process in the checkpoint's own dtype (bf16), CPU."""
        if self._model is not None:
            return
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        start = time.perf_counter()
        self._processor = AutoProcessor.from_pretrained(
            self.model_dir, trust_remote_code=False
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            self.model_dir,
            torch_dtype=getattr(torch, self.dtype),
            device_map="cpu",
            trust_remote_code=False,
        )
        self._model.eval()
        self.load_seconds = time.perf_counter() - start

    def preflight_memory(self) -> dict | None:
        """Return an UNSUPPORTED record when the frozen memory cap cannot hold
        even the smallest possible load, with the arithmetic shown.

        Minimum feasible peak ≈ weight bytes on disk (bf16) × 2: the mmap'd
        safetensors plus the in-RAM weight copy, before activations or torch
        runtime overhead.  When the card cap (min(8GiB, avail/2), measured at
        run start) is below that, no load strategy can comply and thrashing
        the host would only produce noise.
        """
        if self.memory_cap_bytes is None:
            return None
        weights = Path(self.model_dir) / "model.safetensors"
        weight_bytes = weights.stat().st_size
        minimum_peak = weight_bytes * 2
        if minimum_peak > self.memory_cap_bytes:
            return {
                "status": "unsupported",
                "error": "memory_cap_below_minimum_load_peak",
                "cap_bytes": self.memory_cap_bytes,
                "weight_bytes": weight_bytes,
                "minimum_peak_bytes": minimum_peak,
                "arithmetic": (
                    f"cap={self.memory_cap_bytes} < 2 x weight_bytes({weight_bytes}) = "
                    f"{minimum_peak}; even a bf16 load (mmap + RAM copy) cannot comply"
                ),
            }
        return None

    def run_page(self, png_path: str | Path) -> dict:
        import torch
        from PIL import Image

        preflight = self.preflight_memory()
        if preflight is not None:
            return preflight
        watchdog_state: dict = {"stop": False, "peak_commit": 0, "exceeded": False}
        if self.memory_cap_bytes is not None:
            start_memory_watchdog(self.memory_cap_bytes, watchdog_state)
        self.load()
        if watchdog_state["exceeded"]:
            return {
                "status": "error",
                "error": (
                    f"memory_cap_exceeded during load: peak_commit="
                    f"{watchdog_state['peak_commit']} > cap={self.memory_cap_bytes}"
                ),
            }
        start = time.perf_counter()
        with Image.open(png_path) as source:
            image = source.convert("RGB")
            if image.width > MAX_IMAGE_EDGE or image.height > MAX_IMAGE_EDGE:
                image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
            preprocess = {
                "resized_px": list(image.size),
                "source_px": list(source.size),
            }
        conversation = [{"role": "user", "content": [
            {"type": "text", "text": PROMPT_DOCUMENT},
            {"type": "image", "image": image},
        ]}]
        inputs = self._processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        with torch.inference_mode():
            from transformers import StoppingCriteria

            class WallDeadline(StoppingCriteria):
                def __init__(self, limit):
                    self.limit = limit

                def __call__(self, input_ids, scores, **kwargs) -> bool:
                    return time.perf_counter() - start >= self.limit

            deadline_exceeded = False
            generated = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                stopping_criteria=[WallDeadline(self.deadline_seconds)],
            )
            if time.perf_counter() - start >= self.deadline_seconds and (
                len(generated[0]) - inputs["input_ids"].shape[1] < self.max_new_tokens
            ):
                deadline_exceeded = True
        text = self._processor.batch_decode(
            generated[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )[0]
        engine_seconds = time.perf_counter() - start
        if watchdog_state["exceeded"]:
            return {
                "status": "error",
                "error": (
                    f"memory_cap_exceeded during generation: peak_commit="
                    f"{watchdog_state['peak_commit']} > cap={self.memory_cap_bytes}"
                ),
            }
        watchdog_state["stop"] = True
        if deadline_exceeded:
            return {
                "status": "timeout",
                "error": f"wall deadline {self.deadline_seconds}s exceeded during generation",
                "generated_tokens": int(len(generated[0]) - inputs["input_ids"].shape[1]),
                "engine_seconds": engine_seconds,
                "peak_commit_bytes": watchdog_state["peak_commit"],
                "raw_output": text,
            }
        finish = "stop"
        if len(generated[0]) - inputs["input_ids"].shape[1] >= self.max_new_tokens:
            finish = "length"
        status = classify_raw_output(text, finish_reason=finish)
        capped, cap_status = enforce_output_cap(text, cap=self.output_char_cap)
        if status == "ok" and cap_status == "truncated":
            status = "truncated"
        repetition = detect_repetition(capped)
        return {
            "status": status,
            "text": capped.strip(),
            "raw_output": text,
            "raw_output_sha256": sha256_text(text),
            "lines": serialize_lines([
                {"text": capped.strip(), "bbox": None, "confidence": None,
                 "locator_quality": "none"},
            ]) if capped.strip() else [],
            "engine_seconds": engine_seconds,
            "load_seconds_cold": self.load_seconds,
            "peak_commit_bytes": watchdog_state["peak_commit"],
            "preprocess": preprocess,
            "repetition": repetition,
            "generated_tokens": int(len(generated[0]) - inputs["input_ids"].shape[1]),
        }
