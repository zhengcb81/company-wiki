"""Versioned in-memory OCR enrichment over verified PPTX opaque images."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json

from company_wiki.source_contract import EvidenceCoordinates
from .document import NormalizedDocument
from .local_ocr import (
    OCR_REGION_RECOVERY_SCHEMA,
    ImageOCRResult,
    LocalOCRError,
    OCRAdapter,
    OCRLimits,
    image_dimensions,
)
from .ocr_region_recovery import RecoveryBudget, recover_regions
from .units import FORMAT_PPTX, PPTX_OCR_PARSER_VERSION, build_unit

OCR_LOCATOR_SCHEMA = "cwp-pptx-image-ocr/1"


def adapter_identity(ocr: OCRAdapter):
    manifest = ocr.identity_manifest
    encoded = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    fingerprint = hashlib.sha256(encoded).hexdigest()
    if ocr.fingerprint != fingerprint:
        raise LocalOCRError("OCR_CONFIG_IDENTITY_MISMATCH")
    return json.loads(encoded), fingerprint


def enrich_pptx(
    document: NormalizedDocument,
    *,
    ocr: OCRAdapter,
    limits,
    ocr_limits: OCRLimits | None = None,
    selected_media_sha256s: frozenset[str] | None = None,
):
    """Compose configured native OCR behind one reusable hard process boundary.

    The backend adapter remains a cooperative primitive. Public normalization
    and replay passing that configured adapter get a request-owned child for
    preflight, full images and ROI attempts, closed before this call returns.
    Protocol adapters and already-isolated clients retain their own boundary.
    """
    from .local_ocr import LocalOCRAdapter

    if type(ocr) is LocalOCRAdapter:
        from .isolated_ocr import IsolatedOCRAdapter

        deadlines = [
            value for value in (
                limits.deadline,
                None if ocr_limits is None else ocr_limits.deadline,
            ) if value is not None
        ]
        deadline = min(deadlines) if deadlines else None
        with IsolatedOCRAdapter(ocr.config, deadline=deadline) as bounded:
            return _enrich_pptx(
                document, ocr=bounded, limits=limits, ocr_limits=ocr_limits,
                selected_media_sha256s=selected_media_sha256s,
            )
    return _enrich_pptx(
        document, ocr=ocr, limits=limits, ocr_limits=ocr_limits,
        selected_media_sha256s=selected_media_sha256s,
    )


def _enrich_pptx(
    document: NormalizedDocument,
    *,
    ocr: OCRAdapter,
    limits,
    ocr_limits: OCRLimits | None = None,
    selected_media_sha256s: frozenset[str] | None = None,
):
    ocr_limits = ocr_limits or OCRLimits()
    if limits.deadline is not None:
        deadline = (
            min(limits.deadline, ocr_limits.deadline)
            if ocr_limits.deadline is not None
            else limits.deadline
        )
        ocr_limits = replace(ocr_limits, deadline=deadline)
    manifest, fingerprint = adapter_identity(ocr)
    threshold = manifest.get("low_confidence_threshold", 0.8)
    accept_threshold = manifest.get("text_score", 0.5)
    units = []
    for old in document.units:
        metadata = {
            **old.metadata,
            "source_locator": old.metadata["source_locator"] + "|ocr=" + fingerprint,
            "ocr_fingerprint": fingerprint,
        }
        units.append(
            build_unit(
                source_id=old.source_id,
                source_sha256=document.source_sha256,
                format_name=FORMAT_PPTX,
                coordinates=old.coordinates,
                raw_text=old.raw_text,
                unit_kind=old.unit_kind,
                source_locator=metadata["source_locator"],
                transform=metadata["transform"],
                extra_metadata=metadata,
                quality_flags=old.quality_flags,
                parser_version=PPTX_OCR_PARSER_VERSION,
            )
        )
    text_bytes = sum(len(u.raw_text.encode()) for u in units)
    images = 0
    # One shared per-request accumulator: ROI pixels are charged against the
    # same max_total_pixels budget and attempts are counted request-wide, so
    # no image gets a fresh full budget of its own.
    recovery_budget = RecoveryBudget()
    total_recovered_lines = 0
    total_unrecovered_regions = 0
    cache: dict = {}
    page_records: dict = {}
    assets = []
    errors = list(document.structure.errors)
    for asset in document.opaque_assets:
        limits.check_deadline("OCR asset")
        ocr_limits.check_deadline()
        if (
            asset.asset_kind != "image"
            or asset.original_bytes is None
            or asset.slide_number is None
        ):
            assets.append(asset)
            continue
        digest = hashlib.sha256(asset.original_bytes).hexdigest()
        if selected_media_sha256s is not None and digest not in selected_media_sha256s:
            assets.append(asset)
            continue
        images += 1
        ocr_limits.require_within("max_images", images)
        if digest != asset.media_sha256 or len(asset.original_bytes) != asset.byte_size:
            raise LocalOCRError("OCR_MEDIA_SHA_MISMATCH")
        if digest not in cache:
            try:
                width, height = image_dimensions(asset.original_bytes, ocr_limits)
                recovery_budget.reserve_pixels(width * height, limits=ocr_limits)
                result = ocr.transcribe(asset.original_bytes, limits=ocr_limits)
                limits.check_deadline("OCR native return")
                ocr_limits.check_deadline()
                if not isinstance(result, ImageOCRResult) or (
                    result.width,
                    result.height,
                ) != (width, height):
                    raise LocalOCRError("OCR_RESULT_INVALID")
                recovered = ()
                diagnostics = result.region_diagnostics
                if diagnostics is not None and diagnostics.dropped:
                    outcome = recover_regions(
                        ocr=ocr,
                        image_bytes=asset.original_bytes,
                        result=result,
                        limits=ocr_limits,
                        budget=recovery_budget,
                        accept_threshold=accept_threshold,
                    )
                    recovered = outcome.recovered_lines
                    diagnostics = outcome.diagnostics
                cache[digest] = (result, recovered, diagnostics, None)
            except LocalOCRError as exc:
                # Runtime/configuration failures cannot masquerade as image gaps.
                if exc.code not in {
                    "OCR_IMAGE_INVALID",
                    "OCR_MULTIFRAME_IMAGE_UNSUPPORTED",
                    "OCR_INFERENCE_FAILED",
                    "OCR_RESULT_INVALID",
                    "OCR_BOX_INVALID",
                    "OCR_BOX_OUTSIDE_IMAGE",
                    "OCR_CONFIDENCE_INVALID",
                    "OCR_TEXT_INVALID",
                }:
                    raise
                cache[digest] = (None, (), None, exc.code)
        result, recovered, diagnostics, error = cache[digest]
        page = page_records.setdefault(
            asset.slide_number,
            {
                "page_number": asset.slide_number,
                "slide_id": document.metadata["slide_ids"][asset.slide_number],
                "line_count": 0,
                "low_confidence_lines": 0,
                "dropped_regions": 0,
                "recovered_lines": 0,
                "unrecovered_regions": 0,
                "recovery_attempts": 0,
                "status": "recognized",
                "images": [],
            },
        )
        base_lines = () if result is None else result.lines
        lines = base_lines + (recovered if result is not None else ())
        media_unrecovered = 0
        if diagnostics is not None:
            # Every dropped region without a recovered line stays visible:
            # attempted-and-failed, budget-exhausted and never-attempted all
            # count as unrecovered quality flags.
            media_unrecovered = sum(
                1 for record in diagnostics.recovery if record.status != "recovered"
            )
        low = sum(line.confidence < threshold for line in lines)
        status = (
            "failed"
            if error
            else "empty"
            if not lines
            else "low_confidence"
            if low
            else "recognized"
        )
        priority = {"recognized": 0, "low_confidence": 1, "empty": 2, "failed": 3}
        if priority[status] > priority[page["status"]]:
            page["status"] = status
        page["line_count"] += len(lines)
        page["low_confidence_lines"] += low
        if diagnostics is not None:
            media_attempts = sum(
                len(record.attempts) for record in diagnostics.recovery
            )
            page["dropped_regions"] += len(diagnostics.dropped)
            page["recovered_lines"] += len(recovered)
            page["unrecovered_regions"] += media_unrecovered
            page["recovery_attempts"] += media_attempts
        total_recovered_lines += len(recovered)
        total_unrecovered_regions += media_unrecovered
        image_record = {
            "shape_path": asset.shape_path,
            "media_sha256": digest,
            "line_count": len(lines),
            "status": status,
            "error": error,
            "dimensions": None if result is None else [result.width, result.height],
        }
        if diagnostics is not None:
            image_record.update(
                {
                    "dropped_regions": len(diagnostics.dropped),
                    "recovered_lines": len(recovered),
                    "unrecovered_regions": media_unrecovered,
                    "recovery_attempts": sum(
                        len(record.attempts) for record in diagnostics.recovery
                    ),
                    "region_diagnostics": diagnostics.to_dict(),
                }
            )
        page["images"].append(image_record)
        for index, line in enumerate(lines):
            limits.require_within("max_units", len(units) + 1)
            text_bytes += len(line.text.encode())
            limits.require_within("max_text_output_bytes", text_bytes)
            box = ",".join(format(v, ".3f") for v in line.box)
            locator = f"{OCR_LOCATOR_SCHEMA}|s={asset.slide_number}|p={asset.shape_path}|m={digest}|ocr={fingerprint}|l={index}|b={box}"
            is_recovered = result is not None and index >= len(base_lines)
            flags = ["ocr_used", "layout_ambiguous"]
            if is_recovered:
                flags.append("ocr_recovered")
            if line.confidence < threshold:
                flags.append("low_ocr_confidence")
            line_metadata = {
                "slide_number": asset.slide_number,
                "slide_id": document.metadata["slide_ids"][asset.slide_number],
                "shape_path": asset.shape_path,
                "media_sha256": digest,
                "ocr_fingerprint": fingerprint,
                "ocr_box": list(line.box),
                "coordinate_space": "image_pixels",
                "image_width": result.width,
                "image_height": result.height,
                "ocr_line_index": index,
                "ocr_confidence": line.confidence,
                "reading_order": "top-left-box/1",
                "table_cells_inferred": False,
                "recall_status": "unverified",
            }
            if is_recovered:
                line_metadata["ocr_recovered"] = True
            units.append(
                build_unit(
                    source_id=document.source_id,
                    source_sha256=document.source_sha256,
                    format_name=FORMAT_PPTX,
                    coordinates=EvidenceCoordinates(
                        page_number=asset.slide_number, paragraph_index=index
                    ),
                    raw_text=line.text,
                    unit_kind="pptx_image_ocr_line",
                    source_locator=locator,
                    transform="rapidocr-image-rgb/1",
                    parser_version=PPTX_OCR_PARSER_VERSION,
                    quality_flags=flags,
                    extra_metadata=line_metadata,
                )
            )
        assets.append(
            replace(
                asset,
                gap_reason=error or "ocr_empty"
                if error or not lines
                else "ocr_recall_unverified",
            )
        )
        if error:
            errors.append(error)
    # OCR attempts do not prove exhaustive text recall. Keep each image page
    # opaque/reviewable while exposing individually replayable detected lines.
    opaque = tuple(sorted(set(document.structure.opaque_pages) | set(page_records)))
    structure = replace(
        document.structure,
        units=tuple(units),
        opaque_pages=opaque,
        errors=tuple(errors),
        line_count=sum(u.unit_kind == "pptx_image_ocr_line" for u in units),
    )
    return NormalizedDocument(
        document.source_id,
        document.source_sha256,
        FORMAT_PPTX,
        document.parser_name,
        PPTX_OCR_PARSER_VERSION,
        structure,
        tuple(assets),
        {
            **document.metadata,
            "ocr": {
                "schema_version": "cwp-pptx-ocr-quality/1",
                "scope": "all_images"
                if selected_media_sha256s is None
                else "selected_media",
                "attempted_pages": sorted(page_records),
                "unattempted_image_pages": sorted(
                    {
                        a.slide_number
                        for a in assets
                        if a.asset_kind == "image" and a.slide_number is not None
                    }
                    - set(page_records)
                ),
                "identity": manifest,
                "fingerprint": fingerprint,
                "recall_status": "unverified",
                "table_cells_inferred": False,
                "reading_order": "top-left-box/1",
                "image_occurrences": images,
                "unique_media_count": len(cache),
                "total_decoded_pixels": recovery_budget.total_pixels,
                "region_recovery": {
                    "schema_version": OCR_REGION_RECOVERY_SCHEMA,
                    "regions_started": recovery_budget.regions_started,
                    "attempts": recovery_budget.total_attempts,
                    "roi_pixels": recovery_budget.total_roi_pixels,
                    "recovered_lines": total_recovered_lines,
                    "unrecovered_regions": total_unrecovered_regions,
                },
                "pages": [page_records[k] for k in sorted(page_records)],
            },
        },
    )
