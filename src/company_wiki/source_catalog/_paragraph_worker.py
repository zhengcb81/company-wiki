"""Finite offline Docling worker. No imports of optional ML libraries at startup."""
from __future__ import annotations

import base64
from hashlib import sha256
from importlib.metadata import version, distributions
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, cast


def stage(name):
    print("CWP_PARAGRAPH_STAGE=" + name, file=sys.stderr, flush=True)


def environment_sha256():
    """Conservatively bind the optional ML environment, including transitives.

    Keeping a second hand-maintained list of model/backend dependencies would
    miss changes such as docling-parse/transformers/preprocessing releases.
    Native-only readers never inspect this environment.
    """
    packages = sorted((re.sub(r"[-_.]+", "-", d.metadata["Name"] or "").lower(), d.version)
                      for d in distributions())
    return sha256(json.dumps(packages, separators=(",", ":")).encode()).hexdigest()


def main():
    stage("INPUT")
    request = json.loads(sys.stdin.buffer.read(96 * 1024 * 1024 + 1))
    if request.get("schema_version") != "pdf-paragraph-request/1":
        raise ValueError("unsupported paragraph request")
    pages = request["pages"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= 16 or any(type(p) is not int or p < 1 for p in pages):
        raise ValueError("invalid paragraph pages")
    data = base64.b64decode(request["pdf_base64"], validate=True)
    if sha256(data).hexdigest() != request["source_sha256"]:
        raise ValueError("source SHA mismatch")
    # Set an OS memory ceiling before any heavy imports. Parent already owns
    # this entire process tree, including descendants, via bounded_process.
    memory_job = None
    if os.name == "nt":
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        import ctypes
        from company_wiki._process_tree import WindowsJob
        kernel = cast(Any, ctypes).WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        memory_job = WindowsJob(kernel.GetCurrentProcess(), memory_limit_bytes=request["max_memory_bytes"])
    else:
        import resource
        cast(Any, resource).setrlimit(cast(Any, resource).RLIMIT_AS,
            (request["max_memory_bytes"], request["max_memory_bytes"]))
    tick = time.monotonic()
    stage("IDENTITY")
    if version("docling") != request["docling_version"]:
        raise ValueError("configured Docling version changed")
    for name, expected in request["runtime_versions"].items():
        actual = ".".join(map(str, sys.version_info[:3])) if name == "python" else version(name)
        if actual != expected:
            raise ValueError("configured paragraph runtime dependency changed")
    if environment_sha256() != request["environment_sha256"]:
        raise ValueError("configured paragraph transitive environment changed")
    artifacts = Path(request["artifacts"])
    if not artifacts.is_dir() or not (artifacts / "config.json").is_file():
        raise ValueError("existing local model unavailable; downloads are forbidden")
    with (artifacts / "model.safetensors").open("rb") as weights:
        digest = sha256()
        for block in iter(lambda: weights.read(1024 * 1024), b""):
            digest.update(block)
        weights_sha256 = digest.hexdigest()
    if (weights_sha256 != request["model_sha256"]
            or sha256((artifacts / "config.json").read_bytes()).hexdigest() != request["model_config_sha256"]):
        raise ValueError("existing local model differs; downloads are forbidden")
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise ValueError("offline environment required")
    stage("IMPORT")
    from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore[import-not-found]
    from docling.datamodel.base_models import InputFormat, DocumentStream  # type: ignore[import-not-found]
    from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore[import-not-found]
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice  # type: ignore[import-not-found]
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=False, do_code_enrichment=False,
        do_formula_enrichment=False, generate_page_images=False, generate_picture_images=False,
        generate_parsed_pages=False, enable_remote_services=False, artifacts_path=artifacts,
        document_timeout=max(1, request["max_seconds"] - (time.monotonic() - tick)),
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=request["cpu_threads"]))
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    stage("CONVERTER_READY")
    items = []
    for page in pages:
        stage("PAGE_" + str(page))
        converted = converter.convert(DocumentStream(name="source.pdf", stream=BytesIO(data)),
            page_range=(page, page), max_file_size=len(data), raises_on_error=False)
        if str(converted.status) != "ConversionStatus.SUCCESS":
            print("CWP_CONVERSION_STATUS=" + str(converted.status), file=sys.stderr, flush=True)
            for error in converted.errors:
                print(str(error), file=sys.stderr, flush=True)
            raise ValueError("paragraph conversion incomplete")
        for item, _ in converted.document.iterate_items():
            if str(item.label) in {"text", "list_item"}:
                items.append({"label": str(item.label), "text": getattr(item, "text", ""),
                              "provenance": [p.model_dump(mode="json") for p in getattr(item, "prov", [])]})
        if len(items) > 2048:
            raise ValueError("paragraph item count exceeded")
    print(json.dumps({"schema_version": "pdf-paragraph-response/1", "source_sha256": request["source_sha256"],
        "pages": pages, "docling_version": version("docling"), "model_sha256": request["model_sha256"],
        "model_config_sha256": request["model_config_sha256"],
        "runtime_versions": request["runtime_versions"],
        "environment_sha256": request["environment_sha256"],
        "peak_job_commit_bytes": memory_job.peak_commit_bytes() if memory_job is not None else None,
        "converter_instances": 1, "items": items}, ensure_ascii=False), flush=True)
    # Do not close the nested kill-on-close job while this process is alive.
    # The OS closes its handle at exit; the parent always reaps the whole tree.
    _ = memory_job


if __name__ == "__main__":
    if sys.argv[1:] == ["--describe-environment"]:
        print(json.dumps({"schema_version": "pdf-paragraph-environment/1", "environment_sha256": environment_sha256()}))
    else:
        main()
