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


class XiaomiX1:
    arm = "X1"

    def __init__(
        self,
        *,
        model_dir: str,
        deadline_seconds: float,
        max_new_tokens: int = 2048,
        output_char_cap: int = 60000,
    ):
        self.model_dir = str(model_dir)
        self.deadline_seconds = deadline_seconds
        self.max_new_tokens = max_new_tokens
        self.output_char_cap = output_char_cap
        self.identity_manifest = {
            "arm": self.arm,
            "backend": "xiaomi-ocr-0-transformers-cpu",
            "model_revision": "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30",
            "precision": "bfloat16->float32-cpu-offload",
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
        """Load once per process; CPU fp32 because this host has no CUDA."""
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
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=False,
        )
        self._model.eval()
        self.load_seconds = time.perf_counter() - start

    def run_page(self, png_path: str | Path) -> dict:
        import torch
        from PIL import Image

        self.load()
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
            generated = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
            )
        text = self._processor.batch_decode(
            generated[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )[0]
        engine_seconds = time.perf_counter() - start
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
            "preprocess": preprocess,
            "repetition": repetition,
            "generated_tokens": int(len(generated[0]) - inputs["input_ids"].shape[1]),
        }
