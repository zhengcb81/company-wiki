"""Test-only worker construction: fail envelope decode after paid byte capture.

Everything else is the production factory. No runtime option/fault flag is
added to the application; the supervisor test substitutes this import path.
"""

import json
from pathlib import Path


def create_runtime(spec):
    from company_wiki.automation.narrative_http_model import (
        NarrativeHTTPModel,
        ModelEnvelopeError,
    )
    from company_wiki.automation.narrative_worker_factory import (
        create_runtime as real_factory,
    )

    options = json.loads(spec.runtime_options_json)
    marker = Path(options["project_root"]) / "du11-fail-envelope-on-purpose"
    if spec.role in {"model", "mixed"} and marker.is_file():

        def fail_envelope(*args, **kwargs):
            # Real generate has already fsynced complete bytes + attached AUTO
            # receipt before invoking this transport decoder seam.
            raise ModelEnvelopeError("json", http_status=200, duration_ms=0)

        NarrativeHTTPModel._response = fail_envelope
    return real_factory(spec)
