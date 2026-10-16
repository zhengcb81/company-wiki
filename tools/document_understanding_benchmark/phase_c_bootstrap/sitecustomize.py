"""Inherited by actual isolated worker subprocesses; no selector replacement."""

import os

if os.environ.get("CWP_PHASE_C_OBSERVER"):
    from tools.document_understanding_benchmark.phase_c_observer import install

    install()
