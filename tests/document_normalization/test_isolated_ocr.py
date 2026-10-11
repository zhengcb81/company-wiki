"""Real process-boundary regressions; fake native backends, no models/network."""

import hashlib
import os
from pathlib import Path
import socket
import time

import pytest

from company_wiki._process_tree import pid_is_alive
from company_wiki.document_normalization import NormalizationLimitError
from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter
from company_wiki.document_normalization.local_ocr import (
    LocalOCRConfig,
    OCRModelFile,
    OCRLimits,
    OCRLine,
    ImageOCRResult,
    LocalOCRError,
)


def tiny_png():
    import io
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class NativeFake:
    def __init__(self, config):
        self.config = config
        self.root = Path(config.det.path).parent
        self.mode = config.engine_version
        self.calls = 0
        self.root.joinpath("backend-init").write_text(str(os.getpid()))

        def forbid(*args, **kwargs):
            raise AssertionError("network is forbidden in local OCR")

        socket.create_connection = forbid
        socket.socket.connect = forbid

    def validate_environment(self):
        self.root.joinpath("preflight-entered").write_text(str(os.getpid()))
        if self.mode == "stdin-inspect":
            assert isinstance(os.isatty(0), bool)
            self.root.joinpath("stdin-inspected").write_text("preflight")
        if self.mode.startswith("crt-"):
            import ctypes
            crt = ctypes.CDLL("ucrtbase")
            operation = self.mode.removeprefix("crt-")
            if operation == "_fstat64":
                buffer = ctypes.create_string_buffer(256)
                getattr(crt, operation)(0, ctypes.byref(buffer))
            else:
                getattr(crt, operation)(0)
            self.root.joinpath("crt-inspected").write_text(operation)
        if self.mode == "block-preflight":
            time.sleep(2)
        if self.mode == "error-preflight":
            raise LocalOCRError("OCR_MODEL_MISSING")

    def transcribe(self, data, *, limits):
        self.calls += 1
        self.root.joinpath("inference-entered").write_text(str(os.getpid()))
        if self.mode == "stdin-inspect":
            assert isinstance(os.isatty(0), bool)
            self.root.joinpath("stdin-inspected").write_text("infer")
        if self.mode == "block-inference":
            time.sleep(2)
        if self.mode == "gil-block-inference":
            import ctypes

            if os.name == "nt":
                ctypes.PyDLL("kernel32").Sleep(2000)
            else:
                ctypes.PyDLL(None).sleep(2)
        if self.mode == "descendant":
            import subprocess
            import sys

            child = subprocess.Popen(
                [sys.executable, "-B", "-S", "-c", "import time; time.sleep(30)"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.root.joinpath("descendant-pid").write_text(str(child.pid))
            time.sleep(2)
        if self.mode == "cumulative":
            time.sleep(0.12 if self.calls == 1 else 2)
        if self.mode == "crash":
            os._exit(7)
        if self.mode == "error":
            raise LocalOCRError("OCR_INFERENCE_FAILED")
        if self.mode == "invalid":
            return {"not": "ImageOCRResult"}
        return ImageOCRResult(
            1, 1, (OCRLine(f"body {self.calls}", (0, 0, 1, 1), 0.99),)
        )


def cfg(tmp_path, mode="normal"):
    files = {}
    for name in ("det", "cls", "rec"):
        p = tmp_path / (name + ".onnx")
        p.write_bytes(name.encode())
        files[name] = OCRModelFile(str(p), hashlib.sha256(name.encode()).hexdigest())
    return LocalOCRConfig(
        **files,
        engine_version=mode,
        runtime_version="fake-runtime",
        base_config_sha256="a" * 64,
    )


def warm(adapter):
    # Separate interpreter/bootstrap readiness from the tested native deadline.
    # Native backend construction/preflight are NOT part of this warm handshake.
    adapter._ensure_worker(time.monotonic() + 30)


@pytest.mark.parametrize(
    "mode,operation",
    [
        ("block-preflight", "preflight"),
        ("block-inference", "infer"),
        ("gil-block-inference", "infer"),
    ],
)
def test_noncooperative_native_stops_at_product_deadline(tmp_path, mode, operation):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path, mode), _backend_factory=NativeFake, scratch_dir=tmp_path
    )
    data = tiny_png()
    warm(adapter)
    pid = adapter.worker_pid
    started = time.monotonic()
    try:
        deadline = started + 0.12
        with pytest.raises(NormalizationLimitError, match="deadline"):
            if operation == "preflight":
                adapter.validate_environment(deadline=deadline)
            else:
                adapter.transcribe(data, limits=OCRLimits(deadline=deadline))
        assert time.monotonic() - started < 1.0, (
            "product waited for noncooperative native return"
        )
        assert pid is not None and not pid_is_alive(pid)
        assert adapter.worker_pid is None
    finally:
        adapter.close()


def test_one_deadline_accumulates_across_inferences(tmp_path):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path, "cumulative"), _backend_factory=NativeFake
    )
    data = tiny_png()
    warm(adapter)
    try:
        deadline = time.monotonic() + 0.35
        assert (
            adapter.transcribe(data, limits=OCRLimits(deadline=deadline)).lines[0].text
            == "body 1"
        )
        started = time.monotonic()
        with pytest.raises(NormalizationLimitError, match="deadline"):
            adapter.transcribe(data, limits=OCRLimits(deadline=deadline + 10))
        assert time.monotonic() - started < 1.0, "later call reset the request deadline"
    finally:
        adapter.close()


def test_worker_is_lazy_reused_and_close_reaps_and_restores_scratch(tmp_path):
    config = cfg(tmp_path)
    baseline = set(tmp_path.iterdir())
    with IsolatedOCRAdapter(
        config, _backend_factory=NativeFake, scratch_dir=tmp_path
    ) as adapter:
        assert adapter.worker_pid is None
        assert adapter.identity_manifest == config.identity_manifest
        assert adapter.fingerprint == config.fingerprint
        adapter.validate_environment()
        pid = adapter.worker_pid
        assert pid is not None and pid_is_alive(pid)
        a = adapter.transcribe(tiny_png(), limits=OCRLimits())
        b = adapter.transcribe(tiny_png(), limits=OCRLimits())
        assert [a.lines[0].text, b.lines[0].text] == ["body 1", "body 2"]
        assert adapter.worker_pid == pid
        assert int((tmp_path / "backend-init").read_text()) == pid
    assert not pid_is_alive(pid)
    assert adapter.worker_pid is None
    adapter.close()
    extra = set(tmp_path.iterdir()) - baseline
    assert {p.name for p in extra} == {
        "backend-init",
        "preflight-entered",
        "inference-entered",
    }


@pytest.mark.parametrize(
    "mode,code",
    [
        ("error-preflight", "OCR_MODEL_MISSING"),
        ("error", "OCR_INFERENCE_FAILED"),
        ("invalid", "OCR_RESULT_INVALID"),
        ("crash", "OCR_WORKER_FAILED"),
    ],
)
def test_failed_native_results_never_publish_and_worker_is_reaped(tmp_path, mode, code):
    adapter = IsolatedOCRAdapter(cfg(tmp_path, mode), _backend_factory=NativeFake)
    warm(adapter)
    pid = adapter.worker_pid
    try:
        with pytest.raises(LocalOCRError, match=code):
            if mode == "error-preflight":
                adapter.validate_environment()
            else:
                adapter.transcribe(tiny_png(), limits=OCRLimits())
        assert not pid_is_alive(pid)
        assert adapter.worker_pid is None
    finally:
        adapter.close()


def test_expired_deadline_never_spawns_or_preflights(tmp_path):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path), deadline=time.monotonic() - 1, _backend_factory=NativeFake
    )
    with pytest.raises(NormalizationLimitError, match="deadline"):
        adapter.validate_environment()
    assert adapter.worker_pid is None
    assert not (tmp_path / "backend-init").exists()


def test_finite_default_is_resolved_once_and_explicit_longer_does_not_reset(tmp_path):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path, "cumulative"),
        default_timeout_seconds=0.35,
        _backend_factory=NativeFake,
    )
    warm(adapter)
    try:
        assert (
            adapter.transcribe(tiny_png(), limits=OCRLimits()).lines[0].text == "body 1"
        )
        with pytest.raises(NormalizationLimitError, match="deadline"):
            adapter.transcribe(
                tiny_png(), limits=OCRLimits(deadline=time.monotonic() + 10)
            )
    finally:
        adapter.close()


def test_owned_tree_kills_native_descendant_on_timeout(tmp_path):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path, "descendant"), _backend_factory=NativeFake
    )
    data = tiny_png()
    warm(adapter)
    native_pid = adapter.worker_pid
    try:
        with pytest.raises(NormalizationLimitError, match="deadline"):
            adapter.transcribe(data, limits=OCRLimits(deadline=time.monotonic() + 0.4))
        descendant = int((tmp_path / "descendant-pid").read_text())
        assert not pid_is_alive(native_pid)
        assert not pid_is_alive(descendant)
    finally:
        adapter.close()


def test_startup_is_included_in_explicit_deadline(tmp_path):
    adapter = IsolatedOCRAdapter(
        cfg(tmp_path),
        deadline=time.monotonic() - 1,
        default_timeout_seconds=90,
        _backend_factory=NativeFake,
    )
    with pytest.raises(NormalizationLimitError, match="deadline"):
        adapter.transcribe(
            tiny_png(), limits=OCRLimits(deadline=time.monotonic() + 100)
        )
    assert adapter.worker_pid is None
    assert not (tmp_path / "backend-init").exists()


def test_parent_death_kills_native_even_when_worker_holds_gil(tmp_path):
    import json
    import subprocess
    import sys
    from company_wiki.document_normalization import isolated_ocr as boundary

    config = cfg(tmp_path, "gil-block-inference")
    config_path = tmp_path / "parent-config.json"
    config_path.write_text(json.dumps(config.to_dict()), encoding="utf-8")
    pid_path = tmp_path / "native-pid.json"
    script = """
import json,sys,time
from pathlib import Path
from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter
from company_wiki.document_normalization.local_ocr import LocalOCRConfig,OCRLimits
from test_isolated_ocr import NativeFake,tiny_png
root=Path(sys.argv[1]); config=LocalOCRConfig.from_dict(json.loads((root/'parent-config.json').read_text()))
with IsolatedOCRAdapter(config, scratch_dir=root, _backend_factory=NativeFake) as adapter:
    data=tiny_png(); adapter._ensure_worker(time.monotonic()+30)
    (root/'native-pid.json').write_text(json.dumps({'pid':adapter.worker_pid}))
    adapter.transcribe(data,limits=OCRLimits(deadline=time.monotonic()+30))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(boundary.__file__).resolve().parents[2]), str(Path(__file__).parent)]
    )
    parent = subprocess.Popen(
        [sys.executable, "-B", "-c", script, str(tmp_path)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    native_pid = None
    try:
        until = time.monotonic() + 30
        while not (pid_path.exists() and (tmp_path / "inference-entered").exists()):
            assert parent.poll() is None, "test parent exited before native readiness"
            assert time.monotonic() < until, (
                "test parent never reached native readiness"
            )
            time.sleep(0.01)
        native_pid = json.loads(pid_path.read_text())["pid"]
        assert pid_is_alive(native_pid)
        parent.kill()
        parent.wait(timeout=5)
        until = time.monotonic() + 3
        while pid_is_alive(native_pid) and time.monotonic() < until:
            time.sleep(0.01)
        assert not pid_is_alive(native_pid), "native process survived owner death"
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=5)
        # An uncatchable owner kill can leave its small owned scratch directory;
        # test cleanup removes only that test-owned directory, never production.
        import shutil

        for owned in tmp_path.glob("cwp-ocr-*"):
            assert owned.resolve().parent == tmp_path.resolve()
            shutil.rmtree(owned)


def test_subprocess_adapter_is_compatible_with_daemon_auto_worker(tmp_path):
    import multiprocessing

    owner = multiprocessing.current_process()
    previous = owner.daemon
    adapter = IsolatedOCRAdapter(cfg(tmp_path), _backend_factory=NativeFake)
    try:
        owner.daemon = (
            True  # AUTO workers have this flag; multiprocessing children are forbidden.
        )
        adapter.validate_environment()
        assert adapter.worker_pid is not None and pid_is_alive(adapter.worker_pid)
    finally:
        adapter.close()
        owner.daemon = previous


def test_narrative_default_proxy_carries_deadline_without_starting_native(tmp_path):
    from company_wiki.source_catalog.narrative_normalization import (
        NarrativeNormalization,
    )

    config = cfg(tmp_path)
    deadline = time.monotonic() + 20
    with NarrativeNormalization(config, deadline=deadline) as port:
        adapter = port.ocr_adapter
        assert isinstance(adapter, IsolatedOCRAdapter)
        assert adapter.deadline == deadline
        assert adapter.worker_pid is None
        assert adapter.fingerprint == config.fingerprint
    with pytest.raises(LocalOCRError, match="OCR_ADAPTER_CLOSED"):
        adapter.validate_environment()


def test_injected_narrative_fake_protocol_requires_no_new_deadline_keyword(tmp_path):
    from company_wiki.source_catalog.narrative_normalization import (
        NarrativeNormalization,
    )

    class Legacy:
        def __init__(self, config):
            self.validated = 0

        def validate_environment(self):
            self.validated += 1

    with NarrativeNormalization(
        cfg(tmp_path), adapter_factory=Legacy, deadline=time.monotonic() + 20
    ) as port:
        a = port._prepare_ocr()
        assert a.validated == 1
        assert port._prepare_ocr() is a and a.validated == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows CRT descriptor lock regression")
@pytest.mark.parametrize("operation", ["preflight", "infer"])
def test_native_stdin_probe_does_not_deadlock_liveness_monitor(tmp_path, operation):
    """Native runtimes may inspect stdin while initializing/importing; never lock fd0."""
    with IsolatedOCRAdapter(
        cfg(tmp_path, "stdin-inspect"), _backend_factory=NativeFake, scratch_dir=tmp_path
    ) as adapter:
        data = tiny_png()
        warm(adapter)
        pid = adapter.worker_pid
        # Bootstrap/import warmup is separate. This is a fast real CRT metadata call.
        deadline = time.monotonic() + 1.0
        if operation == "preflight":
            adapter.validate_environment(deadline=deadline)
        else:
            result = adapter.transcribe(data, limits=OCRLimits(deadline=deadline))
            assert result.lines[0].text == "body 1"
        assert (tmp_path / "stdin-inspected").read_text() == operation
        assert adapter.worker_pid == pid and pid_is_alive(pid)
    assert not pid_is_alive(pid)
    assert not list(tmp_path.glob("cwp-ocr-*"))


@pytest.mark.skipif(os.name != "nt", reason="Windows UCRT native metadata regression")
@pytest.mark.parametrize("operation", ["_isatty", "_get_osfhandle", "_fstat64"])
def test_native_crt_stdin_probe_does_not_deadlock_liveness_monitor(tmp_path, operation):
    with IsolatedOCRAdapter(
        cfg(tmp_path, "crt-" + operation), _backend_factory=NativeFake, scratch_dir=tmp_path
    ) as adapter:
        warm(adapter)
        adapter.validate_environment(deadline=time.monotonic() + 1.0)
        assert (tmp_path / "crt-inspected").read_text() == operation
    assert not list(tmp_path.glob("cwp-ocr-*"))
