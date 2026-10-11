"""Temporary diagnostic only: transparent native lifecycle timings, no OCR overrides."""

import builtins
import json
import os
import socket
import time


def event(stage, **values):
    record = {
        "stage": stage,
        "pid": os.getpid(),
        "monotonic": time.monotonic(),
        "cpu": time.process_time(),
        **values,
    }
    with open(os.environ["CWP_OCR_PERF_TRACE"], "a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def forbid(*args, **kwargs):
    event("NETWORK_FORBIDDEN")
    raise AssertionError("diagnostic cannot reach network")


socket.create_connection = forbid
socket.socket.connect = forbid
event("diagnostic_backend_import")

from company_wiki.document_normalization.local_ocr import LocalOCRAdapter


class MeasuredCall:
    def __init__(self, native, label):
        self.native, self.label = native, label

    def __getattr__(self, name):
        return getattr(self.native, name)

    def __call__(self, *args, **kwargs):
        event(self.label + "_enter")
        try:
            return self.native(*args, **kwargs)
        finally:
            event(self.label + "_exit")


class MeasuredLocalOCRAdapter(LocalOCRAdapter):
    def __init__(self, config):
        event("adapter_construct_enter", fingerprint=config.fingerprint)
        super().__init__(config)
        event("adapter_construct_exit")

    def _load_engine(self):
        event("load_engine_enter")
        original_import = builtins.__import__
        instrumented = False

        def measured_import(name, *args, **kwargs):
            nonlocal instrumented
            observed = name in ("rapidocr", "onnxruntime")
            if observed:
                event("import_enter", module=name)
            result = original_import(name, *args, **kwargs)
            if observed:
                event("import_exit", module=name)
            if name == "onnxruntime" and not instrumented:
                instrumented = True
                session = result.InferenceSession
                old_init = session.__init__

                def timed_init(instance, *positional, **named):
                    opts = named.get("sess_options")
                    if opts is None and len(positional) > 1:
                        opts = positional[1]
                    event(
                        "onnx_session_enter",
                        model=os.path.basename(str(positional[0])) if positional else "",
                        intra=getattr(opts, "intra_op_num_threads", None),
                        inter=getattr(opts, "inter_op_num_threads", None),
                        providers=named.get("providers"),
                    )
                    try:
                        return old_init(instance, *positional, **named)
                    finally:
                        event("onnx_session_exit")

                session.__init__ = timed_init
            return result

        builtins.__import__ = measured_import
        try:
            super()._load_engine()
        finally:
            builtins.__import__ = original_import
            event("load_engine_exit")
        for name in ("text_det", "text_cls", "text_rec"):
            setattr(self._engine, name, MeasuredCall(getattr(self._engine, name), name))

    def validate_environment(self):
        event("preflight_enter")
        try:
            return super().validate_environment()
        finally:
            event("preflight_exit")

    def transcribe(self, data, *, limits):
        event("transcribe_enter", deadline=limits.deadline, bytes=len(data))
        try:
            result = super().transcribe(data, limits=limits)
            event("transcribe_result", accepted=len(result.lines))
            return result
        finally:
            event("transcribe_exit")
