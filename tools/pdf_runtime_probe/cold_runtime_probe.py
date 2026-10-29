"""Bounded offline no-document SDK cold observation (W21 probe revision).

The child runs under the configured isolated interpreter with the production
launch owner's exact flags and sanitized environment. The audit guard observes
only Python-level audit events: it is evidence about CPython API calls, never
a claim of exhaustive native syscall interception.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _is_discard_device(raw) -> bool:
    """True only for the actual os.devnull device, not for lookalike names.

    A device name embedded in a longer path (e.g. ``sub/NUL`` or ``./nul`` on
    Windows) or a file merely named like the device never matches: the decoded
    text must be exactly ``os.devnull`` and must also canonicalize to the
    device through realpath.
    """
    try:
        text = os.fsdecode(raw)
    except (TypeError, ValueError):
        return False
    if text != os.devnull and not (os.name == "nt" and text.casefold() == os.devnull.casefold()):
        return False
    try:
        return Path(os.path.abspath(text)).resolve() == Path(os.devnull).resolve()
    except OSError:
        return False


def classify_open(raw, mode, flags, temp) -> str | None:
    """Return a rejection reason for one guarded open(), or None when allowed.

    ``temp`` is the one owned directory root that may receive persistent
    writes. The standard discard device (``os.devnull``) persists no bytes and
    is therefore allowed in any mode — torch/dill legitimately open it during
    import. Original documents (.pdf) and secret files (.env) are never opened
    even for reading.
    """
    if not isinstance(raw, (str, bytes, os.PathLike)):
        return None
    text = os.fsdecode(raw)
    if os.path.splitext(text)[1].lower() == ".pdf" or os.path.basename(text).lower() == ".env":
        return "original_or_secret"
    write = isinstance(mode, str) and any(char in mode for char in "wax+") or (
        isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if write and not _is_discard_device(raw) and not Path(text).resolve().is_relative_to(Path(temp).resolve()):
        return "persistent_write"
    return None


def make_audit_hook(temp, emit):
    """Build the probe audit hook; callers install it inside the child only."""

    def audit(name, arguments):
        if name in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            emit("GUARD_REJECTED", operation=name)
            raise PermissionError("isolated SDK probe forbids networking")
        if name == "open":
            reason = classify_open(arguments[0] if arguments else None,
                arguments[1] if len(arguments) > 1 else "r",
                arguments[2] if len(arguments) > 2 else 0, temp)
            if reason == "original_or_secret":
                emit("GUARD_REJECTED", operation=reason)
                raise PermissionError("probe forbids original documents and secret files")
            if reason == "persistent_write":
                emit("GUARD_REJECTED", operation=reason)
                raise PermissionError("probe writes only owned TEMP")
        if name in {"os.mkdir", "os.remove", "os.rmdir", "os.rename"}:
            for value in arguments[:2] if name == "os.rename" else arguments[:1]:
                if isinstance(value, (str, bytes, os.PathLike)) and not Path(
                        os.fsdecode(value)).resolve().is_relative_to(temp):
                    emit("GUARD_REJECTED", operation=name)
                    raise PermissionError("probe directory changes only in owned TEMP")

    return audit


def main() -> None:
    import ctypes
    import faulthandler
    import sys
    import threading
    import time

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "src"))
    from company_wiki._process_tree import WindowsJob

    request = json.loads(sys.stdin.buffer.read())
    started = time.monotonic()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    job = WindowsJob(kernel.GetCurrentProcess(), memory_limit_bytes=request["max_memory_bytes"])
    temp = Path(request["temp"]).resolve()
    active = "BOOT"

    def event(stage, **extra):
        print(json.dumps({"stage": stage, "active": active,
            "seconds": round(time.monotonic() - started, 6), "cpu_seconds": round(time.process_time(), 6),
            "pid": os.getpid(), "peak_job_commit_bytes": job.peak_commit_bytes(), **extra}, ensure_ascii=True), flush=True)

    sys.addaudithook(make_audit_hook(temp, lambda stage, **extra: event(stage, **extra)))
    faulthandler.enable()
    faulthandler.dump_traceback_later(10, repeat=True)
    stop = threading.Event()

    def sample():
        while not stop.wait(5):
            event("SAMPLE")

    threading.Thread(target=sample, daemon=True).start()
    event("BOOT", python_name=Path(sys.executable).name, prefix_name=Path(sys.prefix).name,
        base_prefix_name=Path(sys.base_prefix).name,
        flags={"isolated": bool(sys.flags.isolated), "safe_path": bool(sys.flags.safe_path),
               "utf8": bool(sys.flags.utf8_mode), "no_site": bool(sys.flags.no_site)})
    try:
        active = "IMPORT_DOCUMENT_CONVERTER"
        event("BEGIN")
        from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore[import-not-found]
        event("END")
        active = "IMPORT_BASE_MODELS"
        event("BEGIN")
        from docling.datamodel.base_models import InputFormat  # type: ignore[import-not-found]
        event("END")
        active = "IMPORT_OPTIONS"
        event("BEGIN")
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore[import-not-found]
        from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice  # type: ignore[import-not-found]
        event("END")
        active = "CONSTRUCT_NO_DOCUMENT"
        event("BEGIN")
        options = PdfPipelineOptions(do_ocr=False, do_table_structure=False, do_code_enrichment=False,
            do_formula_enrichment=False, generate_page_images=False, generate_picture_images=False,
            generate_parsed_pages=False, enable_remote_services=False, artifacts_path=Path(request["artifacts"]),
            document_timeout=request["document_timeout"],
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=request["cpu_threads"]))
        converter = DocumentConverter(allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
        event("END", constructed=type(converter).__name__)
        active = "DONE_NO_DOCUMENT"
        event("DONE")
    except BaseException as failure:
        event("ERROR", error_type=type(failure).__name__, message=str(failure)[:1800])
        raise
    finally:
        stop.set()
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    main()
