"""Piecewise prefill under a Job Object cap: locate the crashing component.

Stages: patch_embed conv -> full vision tower -> language prefill on merged
embeddings.  Prints before each stage; a native crash identifies the stage.
argv: cap_gib page_png
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.ocr_comparison.job_limit import GIB, JobMemoryLimit, self_peak_commit_bytes  # noqa: E402

cap = JobMemoryLimit(int(float(sys.argv[1]) * GIB))
try:
    import torch

    torch.set_num_threads(10)
    from PIL import Image
    from transformers import AutoProcessor

    from tools.ocr_comparison.backends.xiaomi_x1 import MAX_IMAGE_EDGE, PROMPT_DOCUMENT
    from tools.ocr_comparison.mmap_loader import load_model_with_mapped_weights

    SNAP = (Path(__file__).resolve().parents[3] / ".w23_cache" / "hub"
            / "models--xiaomi-research--Xiaomi-OCR-0" / "snapshots"
            / "bbd8cf8d21f256b3644b44cb860f3a7cecb93c30")
    T0 = time.time()

    def mark(name):
        print(json.dumps({"stage": name, "t": round(time.time() - T0, 1),
                          "peak_self": self_peak_commit_bytes()}), flush=True)

    model, _ = load_model_with_mapped_weights(SNAP, weights_file="model.fp32.safetensors")
    mark("model_loaded")
    proc = AutoProcessor.from_pretrained(str(SNAP), trust_remote_code=False)
    image = Image.open(sys.argv[2]).convert("RGB")
    if image.width > MAX_IMAGE_EDGE or image.height > MAX_IMAGE_EDGE:
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    conv = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT_DOCUMENT}, {"type": "image", "image": image}]}]
    inputs = proc.apply_chat_template(conv, add_generation_prompt=True, tokenize=True,
                                      return_dict=True, return_tensors="pt", enable_thinking=False)
    pv = inputs["pixel_values"].to(model.dtype)
    grid = inputs["image_grid_thw"]
    mark("preprocess_done")

    with torch.inference_mode():
        mark("patch_embed_start")
        x = model.model.visual.patch_embed(pv)
        mark("patch_embed_done")
        vout = model.model.visual(hidden_states=pv, grid_thw=grid)
        mark("vision_tower_done")
        emb = model.model.language_model.get_input_embeddings()(inputs["input_ids"])
        out = model.model.language_model(inputs_embeds=emb, use_cache=True)
        mark("language_prefill_done")
        nxt = out.logits[:, -1, :].argmax(-1, keepdim=True)
        o2 = model.model.language_model(input_ids=nxt, past_key_values=out.past_key_values, use_cache=True)
        mark("language_step2_done")
    print(json.dumps({"done": True, "job_peak": cap.peak_process_bytes()}), flush=True)
finally:
    cap.close()
