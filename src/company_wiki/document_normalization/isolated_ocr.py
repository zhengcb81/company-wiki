"""Reusable owned CPU OCR child; one absolute deadline includes native startup.

Only configured LocalOCRAdapter engines cross this boundary.  Large image/result
bytes use bounded owned files; small atomic notifications cannot fill a pipe.
The stdin handle is a parent-liveness signal, never a payload transport.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import importlib
import errno
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from company_wiki._bounded_process import _WINDOWS_BOOTSTRAP
from company_wiki._process_tree import (
    WindowsJob,
    assign_windows_job,
    kill_owned_group,
    pid_is_alive,
)
from .errors import NormalizationLimitError
from .local_ocr import (
    ImageOCRResult,
    LocalOCRAdapter,
    LocalOCRConfig,
    LocalOCRError,
    OCRLimits,
    OCRLine,
    OCRDroppedRegion,
    OCRRegionDiagnostics,
    OCRRegionRecovery,
    OCRRecoveryAttempt,
    OCR_REGION_DIAGNOSTICS_SCHEMA,
)

DEFAULT_OCR_TIMEOUT_SECONDS = 90.0
MAX_TRANSFER_BYTES = 32 * 1024 * 1024
MAX_CONTROL_BYTES = 4096
CLEANUP_GRACE_SECONDS = 2.5
_POLL_SECONDS = 0.01
# A separate lightweight guardian never executes native OCR.  It can kill the
# session even when the worker retains the GIL and cannot run its EOF thread.
_POSIX_BOOTSTRAP = (
    "import os,select,signal,subprocess,sys,shutil\n"
    "p=subprocess.Popen(sys.argv[1:],stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr,close_fds=True)\n"
    "while p.poll() is None:\n"
    " if select.select([sys.stdin],[],[],0.05)[0] and not os.read(0,1):\n"
    "  shutil.rmtree(sys.argv[-1],ignore_errors=True)\n"
    "  os.killpg(os.getpgrp(),signal.SIGKILL)\n"
    "sys.exit(p.returncode)\n"
)


def _retry_owned_io(operation, *, deadline):
    """Retry only Windows owned-file sharing failures within the same deadline.

    This never retries a native operation, allocates another request budget or
    renews its timeout. A permanent lock expires honestly; other errors escape.
    """
    while True:
        if time.monotonic() >= deadline:
            raise NormalizationLimitError("deadline", deadline, "isolated OCR file handoff")
        try:
            result = operation()
            if time.monotonic() >= deadline:
                raise NormalizationLimitError("deadline", deadline, "isolated OCR file handoff")
            return result
        except PermissionError as error:
            if (os.name != "nt" or error.errno != errno.EACCES
                    or getattr(error, "winerror", None) not in {None, 5, 32, 33}):
                raise
            now = time.monotonic()
            if now >= deadline:
                raise NormalizationLimitError(
                    "deadline", deadline, "isolated OCR file handoff"
                ) from error
            time.sleep(min(_POLL_SECONDS, deadline - now))


def _read_bytes(path: Path, cap: int, *, deadline):
    def read():
        with path.open("rb") as stream:
            return stream.read(cap + 1)
    return _retry_owned_io(read, deadline=deadline)


def _read_json(path: Path, cap: int, *, deadline):
    raw = _read_bytes(path, cap, deadline=deadline)
    if len(raw) > cap:
        raise LocalOCRError("OCR_RESULT_BYTES_EXCEEDED")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise LocalOCRError("OCR_RESULT_INVALID") from None


def _write_json(path: Path, value, cap: int, *, deadline):
    pending = path.with_suffix(path.suffix + ".pending")
    def write():
        size = 0
        with pending.open("wb") as stream:
            for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(value):
                if time.monotonic() >= deadline:
                    raise NormalizationLimitError("deadline", deadline, "isolated OCR file handoff")
                raw = chunk.encode("utf-8")
                size += len(raw)
                if size > cap:
                    raise LocalOCRError("OCR_RESULT_BYTES_EXCEEDED")
                stream.write(raw)
    _retry_owned_io(write, deadline=deadline)
    _retry_owned_io(lambda: pending.replace(path), deadline=deadline)
    # Failure cleanup belongs to the existing owned worker-directory cleanup.
    # A racing unlink here could mask the original error or renew its deadline.


def _encode_result(result):
    if not isinstance(result, ImageOCRResult):
        raise LocalOCRError("OCR_RESULT_INVALID")
    return {
        "width": result.width,
        "height": result.height,
        "lines": [asdict(line) for line in result.lines],
        "region_diagnostics": None
        if result.region_diagnostics is None
        else result.region_diagnostics.to_dict(),
    }


def _decode_result(value):
    try:
        if set(value) != {"width", "height", "lines", "region_diagnostics"}:
            raise ValueError("unexpected OCR result fields")
        diagnostics = value["region_diagnostics"]
        if diagnostics is not None:
            if diagnostics.pop("schema_version") != OCR_REGION_DIAGNOSTICS_SCHEMA:
                raise ValueError("unexpected OCR diagnostic schema")
            diagnostics["dropped"] = tuple(
                OCRDroppedRegion(**record) for record in diagnostics["dropped"]
            )
            recovery = []
            for record in diagnostics["recovery"]:
                record["attempts"] = tuple(
                    OCRRecoveryAttempt(**item) for item in record["attempts"]
                )
                recovery.append(OCRRegionRecovery(**record))
            diagnostics["recovery"] = tuple(recovery)
            diagnostics = OCRRegionDiagnostics(**diagnostics)
        return ImageOCRResult(
            value["width"],
            value["height"],
            tuple(OCRLine(**line) for line in value["lines"]),
            diagnostics,
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        raise LocalOCRError("OCR_RESULT_INVALID") from None


def _worker_main(directory_text: str, startup_deadline: float):
    OCRLimits(deadline=startup_deadline)
    directory = Path(directory_text)
    payload = _read_json(directory / "config.json", 65536, deadline=startup_deadline)
    config = LocalOCRConfig.from_dict(payload["config"])
    module_name, qualified_name = payload["factory"].split(":", 1)
    factory: Any = importlib.import_module(module_name)
    for part in qualified_name.split("."):
        factory = getattr(factory, part)
    # Only the OS job / separate guardian owns parent liveness. A blocked
    # os.read(0) thread here would hold the Windows UCRT descriptor lock and
    # deadlock native initialization (for example NumPy/OpenBLAS fstat(0)).
    # Do not add native-worker stdin readers, even after engine import.
    _write_json(directory / "ready.json", {"pid": os.getpid()}, MAX_CONTROL_BYTES, deadline=startup_deadline)
    backend = None
    response: dict[str, Any]
    number = 0
    while True:
        command_path = directory / f"command-{number}.json"
        while not command_path.exists():
            time.sleep(_POLL_SECONDS)
        command = _read_json(command_path, MAX_CONTROL_BYTES, deadline=startup_deadline)
        response_path = directory / f"response-{number}.json"
        try:
            limits = OCRLimits(**command["limits"])
            limits.check_deadline()
            if backend is None:
                backend = factory(config)
            if command["op"] == "validate":
                backend.validate_environment()
                limits.check_deadline()
            elif command["op"] == "infer":
                input_path = directory / f"image-{number}.bin"
                data = _read_bytes(input_path, MAX_TRANSFER_BYTES, deadline=limits.deadline)
                if len(data) > MAX_TRANSFER_BYTES:
                    raise LocalOCRError("OCR_INPUT_BYTES_EXCEEDED")
                result = backend.transcribe(data, limits=limits)
                limits.check_deadline()
                _write_json(
                    directory / f"result-{number}.json",
                    _encode_result(result),
                    MAX_TRANSFER_BYTES, deadline=limits.deadline,
                )
            else:
                raise LocalOCRError("OCR_RESULT_INVALID")
            response = {"ok": True}
        except NormalizationLimitError as error:
            response = {
                "ok": False,
                "limit_name": error.limit_name,
                "limit_value": error.limit_value,
            }
        except LocalOCRError as error:
            response = {"ok": False, "error": error.code}
        except Exception:
            response = {"ok": False, "error": "OCR_INFERENCE_FAILED"}
        _write_json(response_path, response, MAX_CONTROL_BYTES, deadline=limits.deadline)
        number += 1


class OCRWorkerExitedError(LocalOCRError):
    """Retain a scalar exit observation without stderr, paths or model data."""

    def __init__(self, worker_returncode: int):
        self.worker_returncode = worker_returncode
        super().__init__("OCR_WORKER_FAILED")
        # The machine code stays stable; a real process exit must not be
        # indistinguishable from a deadline or guessed to be one in diagnosis.
        self.args = (f"OCR_WORKER_FAILED (worker_exit_code={worker_returncode})",)


class IsolatedOCRAdapter:
    """One lazy native child and one finite deadline per adapter/request.

    Explicit configured/request deadlines always win.  The 90s fallback starts
    on the first native operation only when no deadline was supplied, and is
    never renewed by a later image or ROI.  Instances are not thread-shared.
    ``close`` terminates/reaps the entire owned tree before removing scratch.
    """

    def __init__(
        self,
        config: LocalOCRConfig,
        *,
        deadline=None,
        default_timeout_seconds=DEFAULT_OCR_TIMEOUT_SECONDS,
        scratch_dir=None,
        _backend_factory=None,
    ):
        if not isinstance(config, LocalOCRConfig):
            raise TypeError("config must be LocalOCRConfig")
        if (
            isinstance(default_timeout_seconds, bool)
            or not isinstance(default_timeout_seconds, (int, float))
            or not math.isfinite(default_timeout_seconds)
            or default_timeout_seconds <= 0
        ):
            raise ValueError("default OCR timeout must be finite and positive")
        OCRLimits(deadline=deadline)  # reuse the public finite deadline validator
        self.config = config
        self.identity_manifest = config.identity_manifest
        self.fingerprint = config.fingerprint
        self.deadline = deadline
        self.default_timeout_seconds = default_timeout_seconds
        self._effective_deadline: float | None = None
        self._scratch_dir = scratch_dir
        self._backend_factory = _backend_factory or LocalOCRAdapter
        self._directory: Path | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._job: WindowsJob | None = None
        self._worker_pid: int | None = None
        self._number = 0
        self._closed = False

    @property
    def worker_pid(self):
        return self._worker_pid

    def _limits(self, limits=None, deadline=None):
        if self._closed:
            raise LocalOCRError("OCR_ADAPTER_CLOSED")
        OCRLimits(deadline=deadline)
        candidates = [
            value
            for value in (
                self.deadline,
                deadline,
                getattr(limits, "deadline", None),
                self._effective_deadline,
            )
            if value is not None
        ]
        self._effective_deadline = (
            min(candidates)
            if candidates
            else time.monotonic() + self.default_timeout_seconds
        )
        return replace(limits or OCRLimits(), deadline=self._effective_deadline)

    def _await_file(self, path: Path, deadline):
        while True:
            if time.monotonic() >= deadline:
                raise NormalizationLimitError(
                    "deadline", deadline, "isolated local OCR"
                )
            if path.exists():
                return
            process = self._process
            if process is None:
                raise LocalOCRError("OCR_WORKER_FAILED")
            returncode = process.poll()
            if returncode is not None:
                raise OCRWorkerExitedError(returncode)
            time.sleep(min(_POLL_SECONDS, max(0, deadline - time.monotonic())))

    def _ensure_worker(self, deadline):
        if self._process is not None:
            return
        if time.monotonic() >= deadline:
            raise NormalizationLimitError(
                "deadline", deadline, "isolated local OCR startup"
            )
        factory = self._backend_factory
        if "<locals>" in factory.__qualname__:
            raise ValueError("OCR backend factory must be importable")
        self._directory = Path(
            tempfile.mkdtemp(prefix="cwp-ocr-", dir=self._scratch_dir)
        )
        directory = self._directory
        try:
            _write_json(
                directory / "config.json",
                {
                    "config": self.config.to_dict(),
                    "factory": factory.__module__ + ":" + factory.__qualname__,
                },
                65536, deadline=deadline,
            )
            command = [
                sys.executable,
                "-B",
                "-c",
                "import sys; from company_wiki.document_normalization.isolated_ocr import _worker_main; _worker_main(sys.argv[2], float(sys.argv[1]))",
                str(deadline),
                str(directory),
            ]
            env = os.environ.copy()
            paths = [
                str(Path(__file__).resolve().parents[2]),
                *(str(Path(p).resolve()) for p in sys.path if p),
            ]
            env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(paths))
            env["PYTHONUTF8"] = "1"
            windows = os.name == "nt"
            argv = (
                [sys.executable, "-B", "-S", "-c", _WINDOWS_BOOTSTRAP, *command]
                if windows
                else [sys.executable, "-B", "-S", "-c", _POSIX_BOOTSTRAP, *command]
            )
            self._process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                close_fds=True,
                shell=False,
                bufsize=0,
                start_new_session=not windows,
                creationflags=subprocess.CREATE_NO_WINDOW if windows else 0,
            )
            if windows:
                self._job = assign_windows_job(self._process)
                assert self._process.stdin is not None
                self._process.stdin.write(b"\0")  # release only AFTER job assignment
            self._await_file(directory / "ready.json", deadline)
            ready = _read_json(directory / "ready.json", MAX_CONTROL_BYTES, deadline=deadline)
            if (
                set(ready) != {"pid"}
                or type(ready["pid"]) is not int
                or ready["pid"] <= 0
            ):
                raise LocalOCRError("OCR_WORKER_FAILED")
            self._worker_pid = ready["pid"]
            self._number = 0
        except BaseException:
            self._stop_worker()
            raise

    def _dispatch(self, operation, limits, data=None):
        try:
            limits.check_deadline()
            self._ensure_worker(limits.deadline)
            directory = self._directory
            assert directory is not None
            number = self._number
            if data is not None:
                if not isinstance(data, bytes):
                    raise LocalOCRError("OCR_IMAGE_INVALID")
                if len(data) > MAX_TRANSFER_BYTES:
                    raise LocalOCRError("OCR_INPUT_BYTES_EXCEEDED")
                def write_image():
                    with (directory / f"image-{number}.bin").open("wb") as stream:
                        for offset in range(0, len(data), 65536):
                            limits.check_deadline()
                            stream.write(data[offset : offset + 65536])
                _retry_owned_io(write_image, deadline=limits.deadline)
            limits.check_deadline()
            _write_json(
                directory / f"command-{number}.json",
                {"op": operation, "limits": asdict(limits)},
                MAX_CONTROL_BYTES, deadline=limits.deadline,
            )
            self._await_file(directory / f"response-{number}.json", limits.deadline)
            response = _read_json(
                directory / f"response-{number}.json", MAX_CONTROL_BYTES, deadline=limits.deadline
            )
            limits.check_deadline()
            if response != {"ok": True}:
                if response.get("ok") is False and "limit_name" in response:
                    raise NormalizationLimitError(
                        response["limit_name"],
                        response["limit_value"],
                        "isolated local OCR",
                    )
                raise LocalOCRError(response.get("error", "OCR_RESULT_INVALID"))
            result = (
                None
                if operation == "validate"
                else _decode_result(
                    _read_json(directory / f"result-{number}.json", MAX_TRANSFER_BYTES, deadline=limits.deadline)
                )
            )
            limits.check_deadline()
            self._number += 1
            for name in ("image", "command", "response", "result"):
                path = directory / f"{name}-{number}.{'bin' if name == 'image' else 'json'}"
                _retry_owned_io(lambda: path.unlink(missing_ok=True), deadline=limits.deadline)
            return result
        except BaseException:
            self._stop_worker()
            raise

    def validate_environment(self, *, deadline=None):
        self._dispatch("validate", self._limits(deadline=deadline))

    def transcribe(self, data: bytes, *, limits: OCRLimits):
        return self._dispatch("infer", self._limits(limits), data)

    def _stop_worker(self):
        process, job, native_pid = self._process, self._job, self._worker_pid
        self._process = None
        self._job = None
        self._worker_pid = None
        cleanup_deadline = time.monotonic() + CLEANUP_GRACE_SECONDS
        try:
            if process is not None:
                try:
                    if job is not None:
                        job.terminate()
                    elif os.name != "nt":
                        kill_owned_group(process.pid)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(
                        timeout=max(0.001, cleanup_deadline - time.monotonic())
                    )
                    if process.stdin is not None:
                        process.stdin.close()
        finally:
            if job is not None:
                job.close()
            # On Windows Job termination is asynchronous.  The bootstrap may
            # exit before the real native worker releases its file handles.
            while native_pid is not None and pid_is_alive(native_pid):
                if time.monotonic() >= cleanup_deadline:
                    raise LocalOCRError("OCR_WORKER_CLEANUP_FAILED")
                time.sleep(_POLL_SECONDS)
            if self._directory is not None:
                directory, self._directory = self._directory, None
                while True:
                    try:
                        shutil.rmtree(directory)
                        break
                    except FileNotFoundError:
                        break
                    except PermissionError:
                        # AV/file-close lag gets only the SAME cleanup grace;
                        # retries never renew the native request deadline.
                        if time.monotonic() >= cleanup_deadline:
                            raise
                        time.sleep(_POLL_SECONDS)

    def close(self):
        self._closed = True
        self._stop_worker()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass  # OS job / separate guardian, not destructor, owns crash cleanup
