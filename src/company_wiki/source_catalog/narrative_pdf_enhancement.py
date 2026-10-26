"""On-demand paragraph enhancement inside the PDF reading implementation.

One finite child converts all demanded pages with one hot converter. Source
bytes travel through bounded pipes, never durable PDF/MD/image copies. Nothing
outside the reading layer knows SDK options, model locations or page geometry.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import time
from types import MappingProxyType
from typing import Any

from company_wiki._bounded_process import run_bounded, TransportError
from company_wiki.resource_budget import WorkBudget
from .narrative_document import DocumentStructure
from .narrative_pdf_environment import ENVIRONMENT_ALGORITHM, LEGACY_ENVIRONMENT_ALGORITHM
from .narrative_pdf_paragraphs import (
    PARAGRAPH_ALIGNMENT_VERSION, ParagraphProposal, align_paragraphs, triage_paragraph_gaps,
)


@dataclass(frozen=True)
class ParagraphRuntimeConfig:
    python: str
    artifacts: str
    model_sha256: str
    docling_version: str
    model_config_sha256: str
    runtime_versions: Mapping[str, str]
    environment_sha256: str
    max_seconds: float = 120
    max_pages: int = 3
    max_input_bytes: int = 64 * 1024 * 1024
    max_output_bytes: int = 2 * 1024 * 1024
    # Windows limits committed memory, not RSS. The pinned CPU SDK's measured
    # peak is ~3.10GiB even though its earlier sampled RSS was only ~1.06GB.
    max_memory_bytes: int = 4 * 1024 * 1024 * 1024
    cpu_threads: int = 4
    environment_algorithm: str = LEGACY_ENVIRONMENT_ALGORITHM

    def __post_init__(self) -> None:
        if self.environment_algorithm not in {LEGACY_ENVIRONMENT_ALGORITHM, ENVIRONMENT_ALGORITHM}:
            raise ValueError("unsupported PDF runtime environment algorithm")
        if (type(self.max_seconds) not in (int, float) or not 1 <= self.max_seconds <= 300
                or type(self.max_pages) is not int or not 1 <= self.max_pages <= 16):
            raise ValueError("invalid paragraph runtime time/page bound")
        for key in ("max_input_bytes", "max_output_bytes", "max_memory_bytes", "cpu_threads"):
            value = getattr(self, key)
            if type(value) is not int or value <= 0:
                raise ValueError(f"invalid paragraph runtime {key}")
        if (self.max_input_bytes > 64 * 1024**2 or self.max_output_bytes > 32 * 1024**2
                or self.max_memory_bytes > 8 * 1024**3 or self.cpu_threads > 16):
            raise ValueError("paragraph runtime resource ceiling exceeded")
        for digest in (self.model_sha256, self.model_config_sha256, self.environment_sha256):
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("paragraph runtime requires existing model and config byte SHA")
        if not all(isinstance(s, str) and s.strip() for s in (self.python, self.artifacts, self.docling_version)):
            raise ValueError("paragraph runtime deployment is incomplete")
        required = {"python", "docling-core", "docling-ibm-models", "torch", "pymupdf", "pypdfium2"}
        if (not isinstance(self.runtime_versions, Mapping) or set(self.runtime_versions) != required
                or not all(isinstance(v, str) and 0 < len(v) <= 128 for v in self.runtime_versions.values())):
            raise ValueError("paragraph runtime requires exact dependency versions")
        object.__setattr__(self, "runtime_versions", MappingProxyType(dict(self.runtime_versions)))

    def recipe(self) -> dict[str, Any]:
        binding = ({} if self.environment_algorithm == LEGACY_ENVIRONMENT_ALGORITHM else {
            "environment_algorithm": self.environment_algorithm,
            "environment_implementation_sha256": sha256(Path(__file__).with_name("narrative_pdf_environment.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
        return {**binding, "engine": "docling", "engine_version": self.docling_version,
                "model_sha256": self.model_sha256, "model_config_sha256": self.model_config_sha256,
                "runtime_versions": dict(self.runtime_versions),
                "environment_sha256": self.environment_sha256,
                "alignment": PARAGRAPH_ALIGNMENT_VERSION,
                "offline": True, "ocr": False, "table_structure": False,
                "cpu_threads": self.cpu_threads, "max_seconds": self.max_seconds,
                "max_pages": self.max_pages, "max_input_bytes": self.max_input_bytes,
                "max_output_bytes": self.max_output_bytes, "max_memory_bytes": self.max_memory_bytes,
                "worker_sha256": sha256(Path(__file__).with_name("_paragraph_worker.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "orchestration_sha256": sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "alignment_sha256": sha256(Path(__file__).with_name("narrative_pdf_paragraphs.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()}


def configured_paragraph_runtime() -> ParagraphEnhancement | None:
    """Explicit local deployment config. No implicit discovery/model downloads."""
    selected = os.environ.get("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG")
    if selected is None:
        return None
    raw = json.loads(Path(selected).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid PDF paragraph runtime configuration")
    schema = raw.pop("schema_version", None)
    if (schema not in {"pdf-paragraph-runtime/1", "pdf-paragraph-runtime/2"}
            or (schema.endswith("/1") and "environment_algorithm" in raw)
            or (schema.endswith("/2") and raw.get("environment_algorithm") != ENVIRONMENT_ALGORITHM)):
        raise ValueError("invalid PDF paragraph runtime environment algorithm binding")
    return ParagraphEnhancement(ParagraphRuntimeConfig(**raw))


def proposals_from_items(parsed: DocumentStructure, items: list[dict[str, Any]],
                         pages: tuple[int, ...]) -> tuple[ParagraphProposal, ...]:
    frames: dict[int | None, dict[str, Any]] = {}
    for unit in parsed.units:
        layout = unit.metadata.get("reading_layout", {}).get("layout", {})
        if unit.coordinates.page_number in pages and layout:
            frames.setdefault(unit.coordinates.page_number, layout)
    proposals = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("paragraph item is not an object")
        if item.get("label") not in {"text", "list_item"} or not isinstance(item.get("text"), str):
            continue
        provenance = item.get("provenance")
        if not isinstance(provenance, list) or len(provenance) != 1:
            continue
        row = provenance[0]
        if not isinstance(row, Mapping):
            raise ValueError("paragraph provenance is not an object")
        page = row.get("page_no")
        if type(page) is not int:
            raise ValueError("paragraph page is not an integer")
        frame, box = frames.get(page, {}), row.get("bbox", {})
        if not isinstance(box, Mapping):
            raise ValueError("paragraph box is not an object")
        if (page not in pages or frame.get("rotation") != 0 or box.get("coord_origin") != "BOTTOMLEFT"
                or not all(type(box.get(k)) in (float, int) for k in ("l", "t", "r", "b"))):
            continue
        height, width = frame.get("page_height"), frame.get("page_width")
        if not isinstance(height, (float, int)) or not isinstance(width, (float, int)):
            continue
        proposals.append(ParagraphProposal(parsed.source_id, parsed.source_sha256, page, item["text"],
            (box["l"], height - box["t"], box["r"], height - box["b"]), width, height,
            coordinate_frame=frame["coordinate_frame"]))
    return tuple(proposals)


class ParagraphEnhancement:
    def __init__(self, config: ParagraphRuntimeConfig, *, runner=run_bounded):
        self.config, self._runner = config, runner

    def describe_recipe(self) -> Mapping[str, Any]:
        return self.config.recipe()

    def enhance(self, data: bytes, parsed: DocumentStructure, *, work_budget: WorkBudget,
                deadline: float | None) -> DocumentStructure:
        triage = triage_paragraph_gaps(parsed, work_budget=work_budget, max_pages=self.config.max_pages)
        diagnostic: dict[str, Any] = {"code": "PDF_PARAGRAPH_ENHANCEMENT", "pages": list(triage.pages),
            "gap_signals": list(triage.reasons), "status": "not_needed", "accepted_groups": 0}
        result = parsed
        if triage.pages:
            remaining = self.config.max_seconds if deadline is None else min(self.config.max_seconds, deadline - time.monotonic())
            if remaining <= 0:
                diagnostic["status"] = "deadline_no_capacity"
            elif len(data) > self.config.max_input_bytes:
                diagnostic["status"] = "source_byte_limit"
            elif sha256(data).hexdigest() != parsed.source_sha256:
                raise ValueError("paragraph runtime source SHA mismatch")
            else:
                work_budget.charge(1 + (len(data) + 4095) // 4096 + len(triage.pages))
                diagnostic["status"] = "native_fallback"
                tick = time.monotonic()
                try:
                    v2 = self.config.environment_algorithm == ENVIRONMENT_ALGORITHM
                    version = "2" if v2 else "1"
                    algorithm_binding = {"environment_algorithm": self.config.environment_algorithm} if v2 else {}
                    request = {"schema_version": "pdf-paragraph-request/" + version, **algorithm_binding,
                        "source_sha256": parsed.source_sha256,
                        "pdf_base64": base64.b64encode(data).decode("ascii"), "pages": list(triage.pages),
                        "artifacts": self.config.artifacts, "model_sha256": self.config.model_sha256,
                        "model_config_sha256": self.config.model_config_sha256,
                        "runtime_versions": dict(self.config.runtime_versions),
                        "environment_sha256": self.config.environment_sha256,
                        "docling_version": self.config.docling_version, "cpu_threads": self.config.cpu_threads,
                        "max_seconds": remaining, "max_memory_bytes": self.config.max_memory_bytes}
                    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                               DO_NOT_TRACK="1", TOKENIZERS_PARALLELISM="false",
                               OMP_NUM_THREADS=str(self.config.cpu_threads), OPENBLAS_NUM_THREADS=str(self.config.cpu_threads),
                               MKL_NUM_THREADS=str(self.config.cpu_threads))
                    # Input cap is checked before base64 allocation; output is
                    # bounded before decoding. The child has no file output.
                    encoded = json.dumps(request).encode()
                    with tempfile.TemporaryDirectory(prefix="cw-paragraph-") as folder:
                        env.update(TEMP=folder, TMP=folder, TMPDIR=folder)
                        raw = self._runner([self.config.python, "-B", str(Path(__file__).with_name("_paragraph_worker.py"))],
                            input_bytes=encoded, env=env, timeout_seconds=max(0.001, remaining-(time.monotonic()-tick)),
                            stdout_cap_bytes=self.config.max_output_bytes, stderr_cap_bytes=65536)
                    diagnostic["temporary_root_restored_absent"] = not Path(folder).exists()
                    response = json.loads(raw["stdout"])
                    if (not isinstance(response, Mapping) or response.get("schema_version") != "pdf-paragraph-response/" + version
                            or (v2 and response.get("environment_algorithm") != self.config.environment_algorithm)
                            or response.get("source_sha256") != parsed.source_sha256
                            or response.get("pages") != list(triage.pages)
                            or response.get("docling_version") != self.config.docling_version
                            or response.get("model_sha256") != self.config.model_sha256
                            or response.get("model_config_sha256") != self.config.model_config_sha256
                            or response.get("runtime_versions") != dict(self.config.runtime_versions)
                            or response.get("environment_sha256") != self.config.environment_sha256
                            or response.get("converter_instances") != 1
                            or not isinstance(response.get("items"), list) or len(response["items"]) > 2048):
                        raise ValueError("paragraph runtime response binding mismatch")
                    aligned = align_paragraphs(parsed, proposals_from_items(parsed, response["items"], triage.pages), work_budget=work_budget)
                    result = aligned.parsed
                    diagnostic.update(status="enhanced" if aligned.accepted_groups else "unaligned_native_fallback",
                        accepted_groups=aligned.accepted_groups, rejected_groups=aligned.rejected_groups,
                        actual_engine="docling", engine_version=response["docling_version"],
                        model_sha256=response["model_sha256"], converter_instances=response.get("converter_instances"),
                        peak_job_commit_bytes=response.get("peak_job_commit_bytes"))
                except (TransportError, OSError, ValueError, TypeError, KeyError) as exc:
                    diagnostic["reason"] = type(exc).__name__  # no source text, stderr or deployment paths
                    stages = re.findall(rb"CWP_PARAGRAPH_STAGE=([A-Z_0-9]{1,40})\r?\n", getattr(exc, "stderr", b""))
                    if stages:
                        diagnostic["last_stage"] = stages[-1].decode("ascii")
                    classes = re.findall(rb"(?:^|\n)([A-Za-z_][A-Za-z_0-9]*(?:Error|Exception)):", getattr(exc, "stderr", b""))
                    if classes:
                        diagnostic["worker_error"] = classes[-1].decode("ascii")
                    returncode = getattr(exc, "returncode", None)
                    if isinstance(returncode, int):
                        diagnostic["worker_returncode"] = returncode
                diagnostic["seconds"] = round(time.monotonic() - tick, 4)
        # Actual execution is separate from the recipe's possible components.
        # Carry one bounded, source-free observation through existing coverage
        # and cache/publication; no downstream consumer interprets SDK options.
        actual = {key: diagnostic[key] for key in (
            "status", "pages", "accepted_groups", "rejected_groups", "actual_engine", "engine_version",
            "model_sha256", "converter_instances", "peak_job_commit_bytes", "seconds", "reason",
            "last_stage", "worker_error", "worker_returncode", "temporary_root_restored_absent") if key in diagnostic}
        coverage = dict(result.layout_coverage or {})
        coverage["reading_execution"] = {"schema_version": "pdf-reading-execution/1",
            "scope": "paragraph_boundary_proposals", **actual}
        return replace(result, layout_coverage=coverage, layout_diagnostics=(*result.layout_diagnostics, diagnostic))
