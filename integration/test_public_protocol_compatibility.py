"""One public producer fixture is consumed by independent RF/Stock adapters."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RF = Path(os.environ.get("RF_CODE_ROOT", ROOT.parent / "revenue-forecast"))
sys.path.insert(0, str(RF / "scripts"))

from company_wiki_narrative_contracts import validate_narrative_response, NarrativeTransportError  # noqa: E402

CONSUMERS = ["rf"]
ERRORS = (NarrativeTransportError,)
if "STOCKWIKI_CODE_ROOT" in os.environ:
    sys.path.insert(0, os.environ["STOCKWIKI_CODE_ROOT"])
    from stockwiki.narrative_source import read_narrative, NarrativeSourceTransport, NarrativeSourceError
    CONSUMERS.append("stock")
    ERRORS += (NarrativeSourceError,)


def _wire(owner):
    golden = (ROOT / "tests/fixtures/narrative_transport_v1" if owner == "producer"
              else RF / "tests/fixtures/cwp_narrative_transport_v1")
    return tuple(json.loads((golden/name).read_bytes()) for name in
        ("read_request.json", "bundle.json", "read_receipt.json"))


def _read(consumer, request, body, receipt):
    raw = (json.dumps(receipt) + "\n").encode()
    if consumer == "rf":
        return validate_narrative_response(request, body, raw)
    transport = NarrativeSourceTransport(argv_prefix=["configured-producer"], timeout_s=5,
        max_stdout_bytes=len(body), runner=lambda *a, **k: (0,body,raw))
    return read_narrative(request, transport)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("owner", ["producer", "previous_portable"])
@pytest.mark.parametrize("pretty", [False, True])
def test_optional_extension_and_formatting_do_not_change_source_semantics(consumer, owner, pretty):
    request, bundle, receipt = _wire(owner)
    bundle["extensions"] = {"future_diagnostic": {"status": "unknown"}}
    receipt["extensions"] = {"observer": {"status": "unavailable"}}
    body = json.dumps(bundle, ensure_ascii=False, sort_keys=True,
        **({"indent": 2} if pretty else {"separators": (",", ":")})).encode()
    ref = request["narrative_ref"]
    ref["byte_size"], ref["artifact_sha256"] = len(body), hashlib.sha256(body).hexdigest()
    receipt["narrative_ref"] = deepcopy(ref)
    assert _read(consumer, request, body, receipt) is not None


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("owner", ["producer", "previous_portable"])
@pytest.mark.parametrize("fault", ["hash", "status", "core_field"])
def test_extension_cannot_override_a_core_mismatch(consumer, owner, fault):
    request, bundle, receipt = _wire(owner)
    receipt["extensions"] = {"verified": True}
    body = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if fault == "hash":
        body += b" "
    elif fault == "status":
        receipt["status"] = "unavailable"
    else:
        receipt["unknown_core_field"] = True
    with pytest.raises(ERRORS):
        _read(consumer, request, body, receipt)
