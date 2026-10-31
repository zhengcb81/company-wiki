"""Diagnose the 0xC0000005 crash at generate: mapped model, image size ladder,
thread and oneDNN variations.  Each phase prints before running so a native
crash still identifies the failing phase."""
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

PHASE = sys.argv[1]
THREADS = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SNAP = (REPO / ".w23_cache/hub/models--xiaomi-research--Xiaomi-OCR-0/snapshots"
        / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30")
PAGE = REPO / ".w23_cache/x1_pilot_page.png"

import torch  # noqa: E402

if THREADS:
    torch.set_num_threads(THREADS)
if PHASE == "small_mkldnn_off":
    torch.backends.mkldnn.enabled = False

from tools.ocr_comparison.mmap_loader import load_model_with_mapped_weights  # noqa: E402
from transformers import AutoProcessor  # noqa: E402
from PIL import Image  # noqa: E402

model, info = load_model_with_mapped_weights(SNAP)
proc = AutoProcessor.from_pretrained(str(SNAP), trust_remote_code=False)
print(json.dumps({"phase": PHASE, "loaded": True, "n_tensors": info["n_tensors"]}), flush=True)

PROMPT = ("Extract the text in the image.")

def build_inputs(px):
    if px is None:
        image = Image.open(PAGE).convert("RGB")
    else:
        image = Image.new("RGB", (px, px), (255, 255, 255))
    conv = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT}, {"type": "image", "image": image}]}]
    return proc.apply_chat_template(conv, add_generation_prompt=True, tokenize=True,
                                    return_dict=True, return_tensors="pt", enable_thinking=False)

sizes = {"small": 112, "mid": 640, "page": None}
inputs = build_inputs(sizes.get(PHASE))
n_tokens = int(inputs["input_ids"].shape[1])
print(json.dumps({"phase": PHASE, "threads": torch.get_num_threads(), "input_tokens": n_tokens,
                  "pixel_values": list(inputs.get("pixel_values", torch.empty(0)).shape)}), flush=True)

t0 = time.time()
budget = 170.0
state = {"stop": False}

from transformers import StoppingCriteria, StoppingCriteriaList  # noqa: E402

class Deadline(StoppingCriteria):
    def __call__(self, input_ids, scores, **kwargs):
        done = time.perf_counter() - t0 >= budget
        return torch.full((input_ids.shape[0],), done, dtype=torch.bool)

prefill_start = time.time()
with torch.inference_mode():
    out = model(**inputs)
prefill_s = time.time() - prefill_start
print(json.dumps({"phase": PHASE, "prefill_seconds": round(prefill_s, 2)}), flush=True)

start = time.time()
with torch.inference_mode():
    gen = model.generate(**inputs, max_new_tokens=512, do_sample=False,
                         use_cache=True,
                         stopping_criteria=StoppingCriteriaList([Deadline()]))
new = gen[:, inputs["input_ids"].shape[1]:]
text = proc.batch_decode(new, skip_special_tokens=True)[0]
print(json.dumps({"phase": PHASE, "prefill_seconds2": round(prefill_s, 2), "gen_seconds": round(time.time() - start, 1),
                  "new_tokens": int(new.shape[1]),
                  "text_head": text[:160]}), flush=True)
