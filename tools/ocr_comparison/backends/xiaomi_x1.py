"""X1 arm: Xiaomi-OCR-0 whole-page parsing on CPU transformers.

Follows the upstream evaluation contract at the frozen commit b1a9bb4c: the
document prompt, the non-thinking chat template (enable_thinking=False),
greedy decoding, the 2048-bound fit_image resize, and the upstream
postprocessing (truncated-repeat cleanup, OTSL tables to HTML), vendored
byte-identically under ../_upstream.  Scoring text removes only declared
markup syntax (metrics.markup_strip).  No vLLM/Ollama/quantized variant.

Timing contract: a page request is measured from run_page entry and includes
model load when the model is cold, preprocessing, generation and
postprocessing.  Interpreter and library import time is reported separately.

VLM output has no word boxes or confidences: bbox/confidence stay null and
locator_quality is "none" (whole-page), never fabricated.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from ..metrics import markup_strip
from .base import (
    classify_raw_output,
    detect_repetition,
    enforce_output_cap,
    serialize_lines,
    sha256_text,
)

_UPSTREAM_ROOT = Path(__file__).resolve().parents[1] / "_upstream"
if str(_UPSTREAM_ROOT) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM_ROOT))
from postprocess.document import _clean_truncated_repeats, postprocess_e2e_markdown  # noqa: E402

# Verbatim upstream prompt (evaluation_pipeline/e2e_img2md.py, frozen commit).
PROMPT_DOCUMENT = (
    "Extract all information from the main body of the document image and represent it "
    "in markdown format, ignoring headers and footers. Tables should be expressed in OTSL "
    "format, formulas in the document should be represented using LATEX format, and the "
    "parsing should be organized according to the reading order."
)
MAX_IMAGE_EDGE = 2048
UPSTREAM_COMMIT = "b1a9bb4c07060c453785e9151715ccda6b96f0b1"
MODEL_REVISION = "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30"


class XiaomiX1:
    arm = "X1"

    def __init__(
        self,
        *,
        model_dir: str,
        deadline_seconds: float,
        max_new_tokens: int = 4096,
        output_char_cap: int = 60000,
        dtype: str = "bfloat16",
        on_stage=None,
        weights_mode: str = "copy",
    ):
        # weights_mode: "copy" = from_pretrained private copies (upstream load
        # path); "mapped" = frozen bf16 file mapping; "mapped-f32" = exact
        # fp32 upcast copy mapping (bf16 numbers widened losslessly; chosen on
        # this host because its CPU lacks AMX/AVX512-BF16 and torch's bf16
        # GEMM path falls back to an unoptimized kernel, see the receipts).
        self.model_dir = str(model_dir)
        self.deadline_seconds = float(deadline_seconds)
        self.max_new_tokens = int(max_new_tokens)
        self.output_char_cap = int(output_char_cap)
        self.dtype = dtype
        self.on_stage = on_stage
        if weights_mode not in ("copy", "mapped", "mapped-f32"):
            raise ValueError("weights_mode must be 'copy', 'mapped' or 'mapped-f32'")
        self.weights_mode = weights_mode
        self.identity_manifest = {
            "arm": self.arm,
            "backend": "xiaomi-ocr-0-transformers-cpu",
            "upstream_commit": UPSTREAM_COMMIT,
            "model_revision": MODEL_REVISION,
            "precision": f"checkpoint-native-{dtype}-cpu",
            "prompt_sha256": sha256_text(PROMPT_DOCUMENT),
            "preprocess": (
                f"upstream fit_image thumbnail to {MAX_IMAGE_EDGE}px longest edge, "
                "then processor smart_resize"
            ),
            "decoding": "greedy; chat template enable_thinking=False",
            "max_new_tokens": self.max_new_tokens,
            "request_deadline_seconds": self.deadline_seconds,
            "output_char_cap": self.output_char_cap,
            "weights_loading": {
                "copy": "from_pretrained private copies",
                "mapped": ("torch.from_file read-only file mapping of the frozen bf16 "
                           "checkpoint (meta init + assign); loading strategy only"),
                "mapped-f32": ("torch.from_file replaced by a true read-only mmap section "
                               "of the exact fp32 upcast copy (bf16 widened losslessly); the "
                               "fp32 file's sha256 is recorded in the run receipt and "
                               "x1_feasibility_measured.json, not by the loader; loading "
                               "strategy and compute dtype only, no quantization"),
            }[weights_mode],
            "postprocess": (
                "upstream postprocess.document: _clean_truncated_repeats + "
                "postprocess_e2e_markdown(convert_otsl=True); scoring strips declared markup "
                "(metrics.markup_strip: HTML tags, markdown heading and bold markers)"
            ),
        }
        self._model = None
        self._processor = None
        self.load_seconds = None

    def _stage(self, name: str) -> None:
        """Observation hook only: lets the parent attribute a failure to a stage."""
        if self.on_stage is not None:
            self.on_stage(name)

    def load(self) -> None:
        """Load once per process in the checkpoint's own dtype, on CPU."""
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        start = time.perf_counter()
        self._stage("processor_load_start")
        self._processor = AutoProcessor.from_pretrained(self.model_dir, trust_remote_code=False)
        self._stage("processor_loaded")
        self._stage("model_load_start")
        if self.weights_mode in ("mapped", "mapped-f32"):
            from ..mmap_loader import load_model_with_mapped_weights

            weights_file = "model.safetensors" if self.weights_mode == "mapped"                 else "model.fp32.safetensors"
            self._model, self._load_info = load_model_with_mapped_weights(
                self.model_dir, weights_file=weights_file)
        else:
            self._model = AutoModelForImageTextToText.from_pretrained(
                self.model_dir,
                dtype=getattr(torch, self.dtype),
                trust_remote_code=False,
            )
            self._load_info = {"weights_loading": "from_pretrained copies"}
        self._stage("model_loaded")
        self.load_seconds = time.perf_counter() - start

    def run_page(self, png_path: str | Path, *, budget_seconds: float | None = None) -> dict:
        import torch
        from PIL import Image

        budget = self.deadline_seconds if budget_seconds is None else float(budget_seconds)
        request_start = time.perf_counter()
        self._stage("page_start")
        cold = self._model is None
        self.load()
        load_seconds = self.load_seconds if cold else 0.0

        with Image.open(png_path) as source:
            image = source.convert("RGB")
            source_px = list(source.size)
        if image.width > MAX_IMAGE_EDGE or image.height > MAX_IMAGE_EDGE:
            from PIL import Image as _Image

            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), _Image.Resampling.LANCZOS)
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
            enable_thinking=False,
        )
        inputs = {
            key: (value.to(self._model.dtype) if torch.is_floating_point(value) else value)
            for key, value in inputs.items()
        }
        input_len = int(inputs["input_ids"].shape[1])
        self._stage("preprocess_done")

        # Manual greedy decode (same math as upstream greedy temperature-0).
        # transformers' generate() ran each decode step without an effective
        # cache for this hybrid linear-attention architecture (measured in the
        # X1 receipts); explicit past_key_values use is ~15x faster per step.
        tokenizer = getattr(self._processor, "tokenizer", None)
        eos_ids = set()
        eos_attr = getattr(tokenizer, "eos_token_id", None)
        if isinstance(eos_attr, int):
            eos_ids.add(eos_attr)
        if tokenizer is not None:
            im_end = tokenizer.convert_tokens_to_ids("<|im_end|>")
            if isinstance(im_end, int):
                eos_ids.add(im_end)

        gen_start = time.perf_counter()
        self._stage("generate_start")
        finish = "stop"
        prefill_overran = False
        with torch.inference_mode():
            # logits_to_keep=1: the giant all-positions logits tensor
            # (~3 GB fp32 at page-scale vocab) is both unnecessary for greedy
            # decode and the single largest allocation of the request.
            out = self._model(**inputs, use_cache=True, logits_to_keep=1)
            self._stage("prefill_done")
            if time.perf_counter() - request_start >= budget:
                # Prefill itself is one uninterruptible forward; the wall
                # clock past the budget is reported, never truncated.
                prefill_overran = True
                finish = "deadline"
                step_ids = []
            else:
                cache = out.past_key_values
                next_id = out.logits[:, -1, :].argmax(dim=-1, keepdim=True)
                step_ids = [next_id]
                while int(next_id.item()) not in eos_ids and len(step_ids) < self.max_new_tokens:
                    if time.perf_counter() - request_start >= budget:
                        finish = "deadline"
                        break
                    out = self._model(
                        input_ids=next_id, past_key_values=cache, use_cache=True,
                    )
                    next_id = out.logits[:, -1, :].argmax(dim=-1, keepdim=True)
                    step_ids.append(next_id)
                if finish == "stop" and len(step_ids) >= self.max_new_tokens:
                    finish = "length"
        engine_seconds = time.perf_counter() - gen_start
        if step_ids:
            new_ids = torch.cat(step_ids, dim=1)
            generated_tokens = int(new_ids.shape[1])
            raw = self._processor.batch_decode(new_ids, skip_special_tokens=True)[0]
        else:
            generated_tokens = 0
            raw = ""
        self._stage("generate_done")

        error = None
        try:
            post = postprocess_e2e_markdown(_clean_truncated_repeats(raw), convert_otsl=True)
        except Exception as exc:  # noqa: BLE001 - recorded, raw output kept
            post = raw
            error = f"postprocess_{type(exc).__name__}"
        scoring, cap_status = enforce_output_cap(markup_strip(post), cap=self.output_char_cap)
        self._stage("postprocess_done")

        status = {"deadline": "timeout", "length": "truncated"}.get(finish, "ok")
        if status == "ok":
            status = classify_raw_output(scoring, finish_reason="stop")
        if cap_status == "truncated" and status == "ok":
            status = "truncated"

        from ..job_limit import self_peak_commit_bytes

        return {
            "status": status,
            "text": scoring.strip(),
            "postprocessed_text": post,
            "raw_output": raw,
            "raw_output_sha256": sha256_text(raw),
            "text_sha256": sha256_text(scoring.strip()),
            "lines": serialize_lines([
                {"text": scoring.strip(), "bbox": None, "confidence": None,
                 "locator_quality": "none"},
            ]) if scoring.strip() else [],
            "finish_reason": finish,
            "prefill_overran_deadline": prefill_overran,
            "generated_tokens": generated_tokens,
            "max_new_tokens": self.max_new_tokens,
            "request_seconds": time.perf_counter() - request_start,
            "budget_seconds": budget,
            "load_seconds_cold": load_seconds,
            "engine_seconds": engine_seconds,
            "input_tokens": input_len,
            "source_px": source_px,
            "resized_px": list(image.size),
            "repetition": detect_repetition(scoring),
            "error": error,
            "process_peak_commit_bytes_self": self_peak_commit_bytes(),
            "weights_load_info": getattr(self, "_load_info", None),
        }
