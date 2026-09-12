"""R4 phase-B step B03 acceptance: stable read bytes ("serve the verified
version's bytes or fail explicitly").

Design §B03, with the rule list of
``assurance/runs/2026-09-11_r4-phase-b/evidence/b03-plan.md`` (section 2):

* the file is read ONCE and the digest is computed over **exactly the buffer
  that is returned**, so "the bytes are the verified bytes" holds by
  construction — checking a path and then letting the caller open it again
  cannot promise that (B-DR-07: on Windows a shared-mode open only arbitrates at
  open time);
* the **preferred** copy is subject to the same gate.  B02 serves it on the
  catalog's claim (decision S-10, "the byte-level hard gate belongs to B03's
  read path"), so a drifted preferred copy must be refused *here*;
* every refusal is one of the contract's five error values
  (``operation-contract.md`` §2.4) plus a human-readable reason — resource
  ceilings and cancellation are NOT states;
* nothing is served from a cloud placeholder (no implicit hydration), nothing
  outside the configured roots (no symlink escape / stale absolute path), and
  never a partial buffer.

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import resolver as resolver_module  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    B03_BYTES_SOURCE_HANDLE,
    SourceRequest,
    SourceResolver,
    _ReadBudget,
)

BODY = b"%PDF-1.4 r4b03-stable-bytes-payload"
DIGEST = hashlib.sha256(BODY).hexdigest()

# The five error values of the operation contract (A03 section 2.4).  A failure
# reported outside this set is a contract gap, not a new state.
CONTRACT_ERRORS = frozenset({"not_found", "not_indexed", "unavailable", "blocked", "ambiguous"})


def _sidecar() -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": DIGEST,
    }


def _write_copy(directory: Path, name: str = "2025.pdf") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8"
    )
    return target


def _scan(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _company_root(path: Path) -> RootSpec:
    return RootSpec(
        "company_raw",
        path,
        "company_raw",
        priority=10,
        adapter_id="company_raw_v1",
        read_only=False,
        canonical_write_target="companies",
    )


def _request() -> SourceRequest:
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id="doc-1",
        as_of_date="2026-08-10",
        mode="exact",
    )


def _served(tmp_path: Path):
    """Build the standard fixture and return ``(resolver, handle, path)``."""
    root = tmp_path / "companies"
    path = _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _scan(tmp_path, [_company_root(root)])
    result = SourceResolver(catalog).resolve(_request())
    assert len(result.matches) == 1, result.debug_trace
    return SourceResolver(catalog), result.matches[0], path


# ---------------------------------------------------------------------------
# The positive contract: verified bytes, with their evidence
# ---------------------------------------------------------------------------


def test_r4b03_serves_verified_bytes_with_evidence(tmp_path):
    """Happy path: the bytes, their digest and where they came from."""
    resolver, handle, path = _served(tmp_path)
    out = resolver.read_verified_bytes(handle)
    assert out.ok, (out.status, out.reason, out.detail)
    assert out.data == BODY
    assert out.byte_size == len(BODY)
    assert out.content_sha256 == DIGEST == handle.content_sha256
    assert out.document_id == handle.document_id
    assert out.bytes_source == B03_BYTES_SOURCE_HANDLE
    assert out.reason == "" and out.status == "verified"
    assert out.read_at.endswith("+00:00")
    assert path.read_bytes() == BODY


# ---------------------------------------------------------------------------
# The deferred byte-level hard gate (S-10): drift is refused HERE
# ---------------------------------------------------------------------------


def test_r4b03_same_size_content_change_is_refused(tmp_path):
    """A preferred copy is served by ``resolve`` on the catalog's claim (S-10),
    but the byte entry point re-digests what it returns: same size, different
    content must be refused, never returned."""
    resolver, handle, path = _served(tmp_path)
    drifted = bytes(reversed(BODY))  # same length, different bytes
    assert len(drifted) == len(BODY)
    path.write_bytes(drifted)
    out = resolver.read_verified_bytes(handle)
    assert not out.ok
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "content_sha256_mismatch"
    assert out.detail == hashlib.sha256(drifted).hexdigest()[:12]
    assert out.bytes_source == ""


def test_r4b03_catalog_claim_does_not_override_the_bytes(tmp_path):
    """The claim-trust level B02 keeps for the preferred copy is visible: the
    handle is still served, and it is the byte entry point that refuses."""
    resolver, handle, path = _served(tmp_path)
    path.write_bytes(b"%PDF-1.4 a completely different revision")
    result = resolver.resolve(_request())
    assert len(result.matches) == 1, result.debug_trace
    out = resolver.read_verified_bytes(result.matches[0])
    assert out.data is None and out.reason == "content_sha256_mismatch"


def test_r4b03_truncated_file_is_refused(tmp_path):
    """Truncation is a digest mismatch, not a shorter "valid" payload."""
    resolver, handle, path = _served(tmp_path)
    path.write_bytes(BODY[:10])
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason in {"content_sha256_mismatch", "changed_during_read"}
    assert out.byte_size == 0


# ---------------------------------------------------------------------------
# Refusals that must happen BEFORE any byte is handed out
# ---------------------------------------------------------------------------


def test_r4b03_placeholder_is_refused_without_hydrating(tmp_path, monkeypatch):
    """A cloud placeholder whose bytes are not local is refused without reading.

    The detection itself is B02's (``_needs_hydration`` reads the Windows recall
    attributes from ``stat``); this case pins the B03 rule that such a copy is
    never opened and never served.
    """
    resolver, handle, path = _served(tmp_path)
    monkeypatch.setattr(resolver_module, "_needs_hydration", lambda stat_result: True)
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "placeholder_not_hydrated"
    assert out.detail == ""


def test_r4b03_locator_outside_the_roots_is_not_found(tmp_path):
    """A stale absolute path / symlink escape is refused as an out-of-bounds
    locator: NOT_FOUND, with nothing read.

    The reason is the REGISTERED taxonomy code for "path outside the allowed
    roots" (the FC-1301 gate refuses unregistered ``reason="..."`` literals and a
    new code would need a registry edit plus a version bump outside this step)."""
    resolver, handle, _ = _served(tmp_path)
    outside = tmp_path.parent / "outside-the-roots.pdf"
    outside.write_bytes(BODY)  # the right bytes, but the wrong place
    out = resolver.read_verified_bytes(replace(handle, canonical_path=str(outside)))
    assert out.data is None
    assert out.status == "not_found"
    assert out.reason == "artifact_path_outside_allowed_root"


def test_r4b03_missing_file_is_unavailable_not_a_crash(tmp_path):
    resolver, handle, path = _served(tmp_path)
    path.unlink()
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "read_failed"
    assert out.detail == "FileNotFoundError"


def test_r4b03_directory_in_place_of_the_file_is_refused(tmp_path):
    resolver, handle, path = _served(tmp_path)
    path.unlink()
    path.mkdir()
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "not_regular_file"


def test_r4b03_size_ceiling_refuses_instead_of_serving_a_partial_buffer(tmp_path, monkeypatch):
    resolver, handle, _ = _served(tmp_path)
    monkeypatch.setattr(resolver_module, "_CANDIDATE_BYTES_CAP", 4)
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "exceeds_candidate_cap"


# ---------------------------------------------------------------------------
# Cancellation and the resource ceiling are reasons, not new states
# ---------------------------------------------------------------------------


def test_r4b03_cancelled_read_is_never_answered(tmp_path):
    resolver, handle, _ = _served(tmp_path)
    budget = _ReadBudget()
    budget.cancel()
    out = resolver.read_verified_bytes(handle, budget=budget)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "cancelled"


def test_r4b03_budget_exhaustion_is_a_reason_not_a_sixth_status(tmp_path):
    resolver, handle, _ = _served(tmp_path)
    budget = _ReadBudget(max_bytes=1)
    out = resolver.read_verified_bytes(handle, budget=budget)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "budget_exceeded"
    assert out.status in CONTRACT_ERRORS


def test_r4b03_every_refusal_stays_inside_the_contract_error_values(tmp_path, monkeypatch):
    """One sweep: no failure may invent a status outside the five values, and no
    failure may carry bytes or a bytes_source."""
    resolver, handle, path = _served(tmp_path)
    scenarios = []

    outside = tmp_path.parent / "r4b03-outside.pdf"
    outside.write_bytes(BODY)
    scenarios.append(("out_of_root", replace(handle, canonical_path=str(outside)), None))

    monkeypatch.setattr(resolver_module, "_needs_hydration", lambda stat_result: True)
    scenarios.append(("placeholder", handle, None))
    monkeypatch.undo()

    monkeypatch.setattr(resolver_module, "_CANDIDATE_BYTES_CAP", 4)
    scenarios.append(("too_large", handle, None))
    monkeypatch.undo()

    budget = _ReadBudget()
    budget.cancel()
    scenarios.append(("cancelled", handle, budget))

    drifted = path.with_name("2025.pdf")
    drifted.write_bytes(bytes(reversed(BODY)))
    scenarios.append(("drifted", handle, None))

    for label, candidate, read_budget in scenarios:
        out = resolver.read_verified_bytes(candidate, budget=read_budget)
        assert not out.ok, label
        assert out.status in CONTRACT_ERRORS, (label, out.status)
        assert out.reason, label
        assert out.data is None and out.byte_size == 0, label
        assert out.bytes_source == "", label


# ---------------------------------------------------------------------------
# The mid-read mutation branch, and the symlink case where the host allows it
# ---------------------------------------------------------------------------


def test_r4b03_change_during_read_is_refused(tmp_path, monkeypatch):
    """The file changes while its bytes are being read: the buffer may mix two
    revisions, so it is refused even though the digest of what was read is
    self-consistent."""
    resolver, handle, path = _served(tmp_path)
    real_open = Path.open

    class MutatingHandle:
        def __init__(self, stream):
            self._stream = stream
            self._mutated = False

        def read(self, size=-1):
            chunk = self._stream.read(size)
            if not self._mutated:
                self._mutated = True
                path.write_bytes(BODY + b"appended after the first chunk")
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return self._stream.__exit__(*exc)

    def fake_open(self, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        stream = real_open(self, *args, **kwargs)
        if str(self) == str(path) and mode == "rb":
            return MutatingHandle(stream)
        return stream

    monkeypatch.setattr(Path, "open", fake_open)
    out = resolver.read_verified_bytes(handle)
    assert out.data is None
    assert out.status == "unavailable"
    assert out.reason == "changed_during_read"


def test_r4b03_symlink_escape_is_refused_where_symlinks_exist(tmp_path):
    """A symlink inside a root that points outside it must not become readable
    through this entry point.

    The property is "the out-of-root bytes are never handed out", and it may be
    enforced at either layer: the scan can refuse to index a symlinked file at
    all (which is what happens on Linux, where this case really runs - the first
    version asserted a served handle and failed in CI), or the read refuses the
    out-of-root locator.  Both satisfy the property; leaking bytes does not.

    Skipped where the host cannot create symlinks (this Windows host does not,
    which is registered as a limitation of the local measurements).
    """
    root = tmp_path / "companies"
    real = tmp_path / "outside" / "2025.pdf"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(BODY)
    link_dir = root / "Acme" / "raw" / "financial_reports" / "annual"
    link_dir.mkdir(parents=True, exist_ok=True)
    link = link_dir / "2025.pdf"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("host cannot create symlinks (registered limitation)")
    (link_dir / "2025.pdf.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8"
    )
    catalog = _scan(tmp_path, [_company_root(root)])
    result = SourceResolver(catalog).resolve(_request())
    if not result.matches:
        # refused even earlier: the scan does not index an out-of-root symlink
        return
    out = SourceResolver(catalog).read_verified_bytes(result.matches[0])
    assert out.data is None, out
    assert out.status in {"not_found", "unavailable"}, out
    assert out.reason, out
