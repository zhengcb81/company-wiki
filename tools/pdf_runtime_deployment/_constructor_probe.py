"""No-document SDK constructor probe for a deployed interpreter.

Imports the real offline SDK, constructs the production DocumentConverter with
the configured ASCII artifacts path and exits. Zero documents, zero network,
capped from outside by the deployment deadline. This probe exists only as an
explicit deployment verification command.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import sys
import time


def main() -> None:
    started = time.monotonic()
    artifacts = Path(sys.argv[1])
    config_digest = sha256((artifacts / "config.json").read_bytes()).hexdigest()
    from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore[import-not-found]
    from docling.datamodel.base_models import InputFormat  # type: ignore[import-not-found]
    from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore[import-not-found]
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice  # type: ignore[import-not-found]
    options = PdfPipelineOptions(
        do_ocr=False, do_table_structure=False, do_code_enrichment=False,
        do_formula_enrichment=False, generate_page_images=False,
        generate_picture_images=False, generate_parsed_pages=False,
        enable_remote_services=False, artifacts_path=artifacts,
        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4))
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    assert converter is not None
    print(json.dumps({"status": "CONSTRUCTOR_OK", "seconds": round(time.monotonic() - started, 3),
                      "artifacts": str(artifacts), "config_sha256": config_digest,
                      "docling_version": __import__("importlib.metadata", fromlist=["version"]).version("docling")},
                     ensure_ascii=True))


if __name__ == "__main__":
    main()
