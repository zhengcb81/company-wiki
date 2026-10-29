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

from company_wiki._bounded_process import run_bounded, TransportError, ChildTimeout, ChildFailed
from company_wiki.resource_budget import WorkBudget
from .narrative_document import DocumentStructure
from .narrative_pdf_environment import ENVIRONMENT_ALGORITHM, LEGACY_ENVIRONMENT_ALGORITHM
from . import narrative_pdf_page_checkpoints as page_checkpoints
from .narrative_pdf_paragraphs import (
    PARAGRAPH_ALIGNMENT_VERSION, ParagraphProposal, align_paragraphs, triage_paragraph_gaps,
    paragraph_triage_dependencies,
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
        if (type(self.max_seconds) not in (int, float) or not 1 <= self.max_seconds <= page_checkpoints.MAX_SECONDS
                or type(self.max_pages) is not int or not 1 <= self.max_pages <= page_checkpoints.MAX_PAGES):
            raise ValueError("invalid paragraph runtime time/page bound")
        for key in ("max_input_bytes", "max_output_bytes", "max_memory_bytes", "cpu_threads"):
            value = getattr(self, key)
            if type(value) is not int or value <= 0:
                raise ValueError(f"invalid paragraph runtime {key}")
        if (self.max_input_bytes > page_checkpoints.MAX_INPUT_BYTES or self.max_output_bytes > page_checkpoints.MAX_OUTPUT_BYTES
                or self.max_memory_bytes > page_checkpoints.MAX_MEMORY_BYTES or self.cpu_threads > page_checkpoints.MAX_CPU_THREADS):
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
                "checkpoint_protocol": page_checkpoints.CHECKPOINT_PROTOCOL,
                "checkpoint_implementation_sha256": sha256(Path(page_checkpoints.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "model_sha256": self.model_sha256, "model_config_sha256": self.model_config_sha256,
                "runtime_versions": dict(self.runtime_versions),
                "environment_sha256": self.environment_sha256,
                "alignment": PARAGRAPH_ALIGNMENT_VERSION,
                "triage_dependencies": paragraph_triage_dependencies(),
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


# The child reads no parent Python search configuration: isolated interpreter
# flags plus an explicit OS-essential allowlist keep injected PYTHONPATH/
# PYTHONHOME/user sites out, while the configured interpreter's own
# site-packages and the first-party source tree stay authoritative.
CHILD_LAUNCH_FLAGS = ("-B", "-I", "-X", "utf8")
_CHILD_ENV_ALLOWLIST = ("APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
    "PATH", "PATHEXT", "PROGRAMDATA", "SYSTEMDRIVE", "SYSTEMROOT", "USERPROFILE", "WINDIR")


def child_launch_command(python: str, script: Path) -> list[str]:
    return [python, *CHILD_LAUNCH_FLAGS, str(script)]


def child_environment(cpu_threads: int) -> dict[str, str]:
    env = {name: os.environ[name] for name in _CHILD_ENV_ALLOWLIST if name in os.environ}
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
        PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
        DO_NOT_TRACK="1", TOKENIZERS_PARALLELISM="false",
        PYTHONNOUSERSITE="1", PYTHON_DOTENV_DISABLED="1",
        OMP_NUM_THREADS=str(cpu_threads), OPENBLAS_NUM_THREADS=str(cpu_threads),
        MKL_NUM_THREADS=str(cpu_threads))
    return env


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
                diagnostic.update(completed_pages=[], pending_pages=list(triage.pages), stream_complete=False,
                    truncated_final_record=False, checkpoint_protocol=page_checkpoints.CHECKPOINT_PROTOCOL)
                tick = time.monotonic()
                try:
                    v2 = self.config.environment_algorithm == ENVIRONMENT_ALGORITHM
                    version = "2" if v2 else "1"
                    algorithm_binding = {"environment_algorithm": self.config.environment_algorithm} if v2 else {}
                    request = {"schema_version": "pdf-paragraph-request/" + version, **algorithm_binding,
                        "checkpoint_protocol": page_checkpoints.CHECKPOINT_PROTOCOL,
                        "source_id": parsed.source_id, "source_page_count": parsed.page_count,
                        "source_sha256": parsed.source_sha256,
                        "pdf_base64": base64.b64encode(data).decode("ascii"), "pages": list(triage.pages),
                        "artifacts": self.config.artifacts, "model_sha256": self.config.model_sha256,
                        "model_config_sha256": self.config.model_config_sha256,
                        "runtime_versions": dict(self.config.runtime_versions),
                        "environment_sha256": self.config.environment_sha256,
                        "docling_version": self.config.docling_version, "cpu_threads": self.config.cpu_threads,
                        "max_seconds": remaining, "max_memory_bytes": self.config.max_memory_bytes,
                        "max_output_bytes": self.config.max_output_bytes}
                    request["request_sha256"] = page_checkpoints.request_sha256(request)
                    env = child_environment(self.config.cpu_threads)
                    # Input cap is checked before base64 allocation; output is
                    # bounded before decoding. The child has no file output.
                    encoded = json.dumps(request).encode()
                    process_failure: ChildTimeout | ChildFailed | None = None
                    with tempfile.TemporaryDirectory(prefix="cw-paragraph-") as folder:
                        env.update(TEMP=folder, TMP=folder, TMPDIR=folder)
                        try:
                            raw = self._runner(child_launch_command(self.config.python,
                                Path(__file__).with_name("_paragraph_worker.py")),
                                input_bytes=encoded, env=env, timeout_seconds=max(0.001, remaining-(time.monotonic()-tick)),
                                stdout_cap_bytes=self.config.max_output_bytes, stderr_cap_bytes=65536)
                        except (ChildTimeout, ChildFailed) as failure:
                            process_failure = failure
                            raw = {"stdout": getattr(failure, "stdout", b"")}
                    diagnostic["temporary_root_restored_absent"] = not Path(folder).exists()
                    if process_failure is not None:
                        _observe_failure(diagnostic, process_failure)
                    stdout = raw["stdout"]
                    if not isinstance(stdout, bytes) or len(stdout) > self.config.max_output_bytes:
                        raise ValueError("paragraph runtime output byte bound exceeded")
                    response = None
                    if process_failure is None:
                        try:
                            response = page_checkpoints.decode_single_json(stdout)
                        except ValueError:
                            pass  # A new checkpoint stream contains multiple JSON records.
                    if isinstance(response, Mapping) and response.get("schema_version") == "pdf-paragraph-response/" + version:
                        # Explicit successful single-JSON compatibility. Failed
                        # legacy fragments never become page checkpoints.
                        if ((v2 and response.get("environment_algorithm") != self.config.environment_algorithm)
                                or response.get("source_sha256") != parsed.source_sha256
                                or response.get("pages") != list(triage.pages)
                                or not isinstance(response.get("pages"), list)
                                or any(type(page) is not int for page in response["pages"])
                                or response.get("docling_version") != self.config.docling_version
                                or response.get("model_sha256") != self.config.model_sha256
                                or response.get("model_config_sha256") != self.config.model_config_sha256
                                or response.get("runtime_versions") != dict(self.config.runtime_versions)
                                or response.get("environment_sha256") != self.config.environment_sha256
                                or type(response.get("converter_instances")) is not int or response["converter_instances"] != 1
                                or ("source_id" in response and response["source_id"] != parsed.source_id)
                                or ("request_sha256" in response and response["request_sha256"] != request["request_sha256"])
                                or not isinstance(response.get("items"), list) or len(response["items"]) > 2048):
                            raise ValueError("paragraph runtime response binding mismatch")
                        observed_peak = response.get("peak_job_commit_bytes")
                        if observed_peak is not None and (type(observed_peak) is not int
                                or not 0 <= observed_peak <= self.config.max_memory_bytes):
                            raise ValueError("paragraph runtime memory observation is invalid")
                        items, completed, complete = response["items"], triage.pages, True
                        peak, truncated, protocol = response.get("peak_job_commit_bytes"), False, "legacy-single-json"
                    else:
                        pages = page_checkpoints.decode_output(stdout, request, process_failed=process_failure is not None)
                        items, completed, complete = list(pages.items), pages.pages, pages.complete
                        peak, truncated, protocol = pages.peak_job_commit_bytes, pages.truncated_final_record, page_checkpoints.CHECKPOINT_PROTOCOL
                    diagnostic["truncated_final_record"] = truncated
                    if not completed:
                        if process_failure is not None:
                            raise process_failure
                        raise ValueError("paragraph runtime has no completed pages")
                    aligned = align_paragraphs(parsed, proposals_from_items(parsed, items, completed), work_budget=work_budget)
                    result = aligned.parsed
                    status = "enhanced" if aligned.accepted_groups else "unaligned_native_fallback"
                    if not complete:
                        status = "partial_enhanced" if aligned.accepted_groups else "partial_unaligned_native_fallback"
                    diagnostic.update(status=status,
                        accepted_groups=aligned.accepted_groups, rejected_groups=aligned.rejected_groups,
                        actual_engine="docling", engine_version=self.config.docling_version,
                        model_sha256=self.config.model_sha256, converter_instances=1,
                        peak_job_commit_bytes=peak, completed_pages=list(completed),
                        pending_pages=[page for page in triage.pages if page not in completed], stream_complete=complete,
                        truncated_final_record=truncated, checkpoint_protocol=protocol)
                except (TransportError, OSError, ValueError, TypeError, KeyError) as exc:
                    _observe_failure(diagnostic, exc)
                diagnostic["seconds"] = round(time.monotonic() - tick, 4)
        # Actual execution is separate from the recipe's possible components.
        # Carry one bounded, source-free observation through existing coverage
        # and cache/publication; no downstream consumer interprets SDK options.
        actual = {key: diagnostic[key] for key in (
            "status", "pages", "accepted_groups", "rejected_groups", "actual_engine", "engine_version",
            "model_sha256", "converter_instances", "peak_job_commit_bytes", "seconds", "reason",
            "last_stage", "worker_error", "worker_returncode", "temporary_root_restored_absent",
            "completed_pages", "pending_pages", "stream_complete", "truncated_final_record",
            "checkpoint_protocol") if key in diagnostic}
        coverage = dict(result.layout_coverage or {})
        coverage["reading_execution"] = {"schema_version": "pdf-reading-execution/1",
            "scope": "paragraph_boundary_proposals", **actual}
        return replace(result, layout_coverage=coverage, layout_diagnostics=(*result.layout_diagnostics, diagnostic))


def _observe_failure(diagnostic: dict[str, Any], error: Exception) -> None:
    """Bounded source-free observations, also retained after partial success."""
    diagnostic["reason"] = type(error).__name__
    stages = re.findall(rb"CWP_PARAGRAPH_STAGE=([A-Z_0-9]{1,40})\r?\n", getattr(error, "stderr", b""))
    if stages:
        diagnostic["last_stage"] = stages[-1].decode("ascii")
    classes = re.findall(rb"(?:^|\n)([A-Za-z_][A-Za-z_0-9]*(?:Error|Exception)):", getattr(error, "stderr", b""))
    if classes:
        diagnostic["worker_error"] = classes[-1].decode("ascii")
    returncode = getattr(error, "returncode", None)
    if isinstance(returncode, int):
        diagnostic["worker_returncode"] = returncode
