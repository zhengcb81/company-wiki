# Local PPTX OCR interface and MAIN integration

## Public API

The existing `normalize_document(original, *, source_id, source_sha256, mime_type, limits=None)` call remains valid and performs pure parsing. It never imports RapidOCR or downloads a model. Add `ocr=LocalOCRAdapter(config)` and optional `ocr_limits=OCRLimits(...)` to perform explicit local CPU image recognition. `parser_version=` freezes the requested historical parser branch.

| Format / mode | Parser version | Locator schema | Compatibility |
|---|---|---|---|
| HTML/XHTML | 1.0.0 | cwp-html-dom/1 | Existing HTML implementation and identity retained |
| PPTX pure, current | 1.1.0 | cwp-pptx-shape/2 | `s` and EvidenceCoordinates.page_number are presentation display ordinals 1..N; OOXML slide_id stays separate metadata |
| PPTX pure, historical explicit read | 1.0.0 | cwp-pptx-shape/1 | Frozen old `s` means OOXML slide_id, e.g. 256/260; never reinterpret as ordinal |
| PPTX with explicit OCR | 2.0.0 | cwp-pptx-image-ocr/1; shape/2 with OCR fingerprint suffix for native text | Images and native text share the actual composition version |

`PARSER_VERSION` remains the HTML/legacy constant 1.0.0. MAIN must use `normalization_identity(mime_type, ocr=adapter)` instead of treating that constant as all-format current identity. Pure historical replay ignores a currently configured OCR adapter, so global OCR configuration cannot rewrite old 1.0.0/1.1.0 units; it makes zero image inference calls. Unknown parser versions are refused; requesting 2.0.0 without an adapter raises `OCR_ADAPTER_REQUIRED`.

```python
from company_wiki.document_normalization import (
    LocalOCRConfig, LocalOCRAdapter, OCRLimits, NormalizationLimits,
    normalize_document, normalization_identity, replay_evidence_spans,
)

# Read a caller/current-config object. The supplied non-secret inventory is an
# actual verified local example, not a production default or installed guarantee.
config = LocalOCRConfig.from_dict(local_ocr_config_object)
adapter = LocalOCRAdapter(config)
identity = normalization_identity(source_ref.mime_type, ocr=adapter)
document = normalize_document(
    original_bytes, source_id=source_ref.source_id,
    source_sha256=source_ref.content_sha256, mime_type=source_ref.mime_type,
    limits=NormalizationLimits(deadline=monotonic_deadline), ocr=adapter,
    ocr_limits=OCRLimits(max_images=100, max_image_pixels=16_000_000,
                         max_total_pixels=96_000_000, deadline=monotonic_deadline),
)
# These remain normal NarrativeUnits; selector must retain their source metadata.
span = selected_unit.to_evidence_span(
    topics=["business_progress"], selection_reasons=["original_operating_text"])
replayed_count = replay_evidence_spans(
    original_bytes, source_id=source_ref.source_id,
    source_sha256=source_ref.content_sha256, mime_type=source_ref.mime_type,
    evidence_spans=selected_spans, limits=NormalizationLimits(deadline=monotonic_deadline),
    ocr=adapter, ocr_limits=OCRLimits(deadline=monotonic_deadline),
)
```

`replay_unit` remains available; `replay_units(original, *, source_sha256, units, limits, ocr=None, ocr_limits=None)` returns all requested texts. `replay_evidence_spans` returns the number matched. Both prove source bytes, parser version, locator, text, coordinates, flags, media SHA, model/config fingerprint, box and confidence. They validate the entire original package once, then infer only media identified by verified selected OCR locators, once per unique SHA. Ten spans on two selected media cost two inferences even when a third image is present. Native text from an OCR composition needs no image inference. No persistent full-text cache is used.

## Configuration and derivation identity

`LocalOCRConfig.from_dict()` accepts exactly schema_version/models/engine_version/runtime_version/base_config_sha256/text_score/low_confidence_threshold/max_side_len/intra_op_threads/inter_op_threads. Three `models` entries det/cls/rec each require path + SHA-256. `to_dict()` returns the non-secret subprocess configuration. Explicit absolute local model paths are resource locators; relative/UNC paths and SHA mismatch are refused. No automatic installation, download, dictionary fallback or provider guess occurs.

`config.identity_manifest` and `config.fingerprint` contain only content/settings: RapidOCR and ORT versions, three actual model SHA values, pinned package config SHA, CPU, thresholds, max side length, thread bounds, RGB preprocessing, box/confidence rounding, reading-order version. Paths and credentials do not participate. The config is immutable. Relocating identical models preserves fingerprint; modifying a model SHA, runtime, default config or preprocessing/threshold changes it.

Verified machine-specific example: `verified_local_config.json` (RapidOCR 3.8.1, ORT 1.26.0). This proves this development machine only. MAIN must explicitly carry the config into its finite worker process and current read path. `from_dict`, adapter construction, `identity_manifest`/`fingerprint` and `normalization_identity` perform no model validation or inference. Optional explicit `adapter.validate_environment()` verifies all three local SHA values, exact engine/runtime/default config, embedded dictionary and CPU engine initialization without an OCR inference call. MAIN can use that controlled composition preflight; actual worker engines remain independent. Each process owns its adapter/engine. The fingerprint belongs in the per-source generation manifest beside source/raw/parser/prompt/profile/version identity. Explicit refresh creates a new derivative generation; changed OCR config is a normal identity miss. A historic OCR generation must replay with its recorded config/model hashes or fail explicitly, never silently switch models. HTML identity does not include OCR config.

## Evidence and extraction quality

An OCR line carries original-language text, `pptx_image_ocr_line`, and `ocr_used`/`layout_ambiguous` flags; lines below the configured threshold also carry `low_ocr_confidence`. Metadata contains source SHA, versioned source_locator, display page, OOXML slide_id, shape path, verified media SHA, config fingerprint, line index, bbox, image dimensions, confidence, RGB transform and reading-order version. Bbox is in `image_pixels`, not slide coordinates; financial table cells are never inferred. Canonical IDs bind source SHA, parser version and locator/config/media/box plus text hash.

`document.metadata["ocr"]` holds schema cwp-pptx-ocr-quality/1, identity/fingerprint, scope (`all_images` during initial normalization or `selected_media` internally during replay), attempted_pages, unattempted_image_pages, per-page line counts/low-confidence counts/status (`recognized`, `low_confidence`, `empty`, `failed`), per-image identity/dimensions/error, unique-media count and decoded pixel total. Existing parser errors and opaque assets remain. `structure.line_count` counts recognized OCR lines; `structure.pages_read` means package pages walked, not correct OCR recall. The current immutable `NormalizedDocument` exposes quality in-memory; callers persist only the small selected bundle plus quality record.

All image pages remain opaque/reviewable and coverage_complete stays false: confidence is not recall. MAIN should distinguish whole-source coverage from exact selected-span replay. Parser errors, missing/unattempted image pages, failed/corrupt images and low-confidence selected spans require refusal or explicit partial. Verified high-confidence operating text can remain useful while unselected small footers/icons and uncertain table relations are explicitly recorded. Replay returns selected-span evidence only and never proves full source coverage.

Top-left bbox sorting is deterministic reading order, with layout_ambiguous retained. It can interleave table columns or break bullet/paragraph relationships; high-confidence numerals can still be wrong. OCR does not replace cleaned financial APIs or source review.

## Limits, named failures and process ownership

NormalizationLimits bounds source/uncompressed/media bytes, pages, units, emitted text and monotonic deadline. OCRLimits bounds image occurrences, per-image and total unique decoded pixels and monotonic deadline; pixels are checked before decode/inference. Repeated media is inferred once with independent per-page locations. No output is returned after a raised limit. ONNX is noncooperative: checks before/after native calls are soft; MAIN must keep the existing outer child-process hard deadline. Responsibility test kills a sleeping noncooperative adapter before its success publisher runs.

Configuration/runtime failures are fatal named LocalOCRError: OCR_ADAPTER_REQUIRED, OCR_MODEL_PATH_NOT_LOCAL, OCR_MODEL_MISSING, OCR_MODEL_SHA_MISMATCH, OCR_RUNTIME_VERSION_MISMATCH, OCR_DEPENDENCY_MISSING, OCR_DEFAULT_CONFIG_MISMATCH, OCR_CHARACTER_DICTIONARY_MISSING, OCR_MODEL_LOAD_FAILED, OCR_ENGINE_INIT_FAILED, OCR_CONFIG_IDENTITY_MISMATCH, OCR_MEDIA_SHA_MISMATCH. Image/result errors become explicit per-page failures while retaining opaque review state: OCR_IMAGE_INVALID, OCR_MULTIFRAME_IMAGE_UNSUPPORTED, OCR_INFERENCE_FAILED, OCR_RESULT_INVALID and invalid box/confidence/text errors. Empty output is `empty`, never skip_success. Unknown replay/config fails, never silent fallback.

## Shared files for MAIN only

- `automation/narrative_formats.py`: choose per-format current identity and recorded historical version instead of universal PARSER_VERSION.
- `automation/narrative_batch_request.py`, `narrative_batch.py`, `narrative_worker_factory.py`, `narrative_runtime.py`: serialize explicit local config/limits into the bounded worker, include pathless OCR identity in derivation manifest, retain process hard deadlines and run budget semantics.
- `automation/narrative_select.py`: normalize with the adapter, sample detected text for original-language classification, retain OCR source metadata/quality, bound small selections; do not invent table cells.
- `automation/narrative_replay.py`, `narrative_verify.py`, `narrative_transport.py`: use one `replay_evidence_spans` call per original, respect recorded versions/config and separate verified selected spans from source-level incomplete state; keep current source/policy/as-of read gates.
- `source_catalog/official_source_flow.py`: MAIN owns genuine PPTX import validation/suffix support. Frozen benchmark alias must map to a real isolated public-import SourceRef, not a fabricated ID.

This package changes none of those shared files. MAIN still owns public batch/select/verify/NarrativeRef integration, real text-model budgeted validation and concentrated final acceptance.
