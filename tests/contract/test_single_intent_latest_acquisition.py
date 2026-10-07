"""One latest intent must use one bounded selection/fetch/import transaction."""

from dataclasses import replace

import pytest

from company_wiki.source_catalog import AcquisitionError, SourceRequest
from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService, SourceEnsureStatus
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.download_budget import AcquisitionBudgetExceeded
from test_close_gap_fc801 import _FakeAdapter, _binding, _request, _txn


class BoundedAdapter(_FakeAdapter):
    supports_acquisition_budget = True

    def __init__(self, *, mutation=None, uncharged=False):
        super().__init__()
        self.discover_calls = 0
        self.mutation = mutation or {}
        self.uncharged = uncharged
        self.budgets = []

    def discover_bounded(self, request, budget):
        self.discover_calls += 1
        self.budgets.append(budget)
        budget.ensure_open()
        budget.consume_response_bytes(7)
        return tuple(replace(c, **self.mutation) for c in super().discover(request))

    def fetch_bounded(self, candidate, staging_dir, budget):
        self.budgets.append(budget)
        budget.ensure_open()
        if not self.uncharged:
            budget.consume_response_bytes(len(b"%PDF-2025"))
        return super().fetch(candidate, staging_dir)


def _budget():
    return AcquisitionBudget.from_limits(max_response_bytes=5_000_000, max_seconds=30, max_cost_usd="0")


def _service(tmp_path, adapter):
    transaction = _txn(tmp_path, adapter)
    return transaction, SourceAcquisitionService(coordinator=transaction.coordinator,
        writer=transaction.writer, journal=transaction.journal)


def test_latest_intent_without_snapshot_selects_once_imports_then_reuses(tmp_path):
    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        assert not (transaction.catalog.config.catalog_dir / "runtime_policy.json").exists()
        request = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=True)
        budget = _budget()
        first = service.ensure(request, budget=budget)
        assert first.status is SourceEnsureStatus.IMPORTED
        assert adapter.discover_calls == 1 and adapter.fetch_calls == 1
        assert all(b is budget for b in adapter.budgets)
        assert budget.response_bytes_used == 7 + len(b"%PDF-2025")
        assert first.resolution.matches[0].fiscal_year == 2025
        assert first.canonical_import is not None
        next_budget = _budget()
        second = service.ensure(request, budget=next_budget)
        assert second.status is SourceEnsureStatus.REUSED
        assert adapter.discover_calls == 2 and adapter.fetch_calls == 1
        assert second.resolution.matches[0].source_id == first.resolution.matches[0].source_id
        assert next_budget.response_bytes_used == 7
        assert len(tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))) == 1
    finally:
        transaction.catalog.close()


def test_readonly_latest_keeps_metadata_gap_and_never_downloads(tmp_path):
    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=False)
        result = service.ensure(request, budget=_budget())
        assert result.status is SourceEnsureStatus.GAP
        assert adapter.discover_calls == 1 and adapter.fetch_calls == 0
        assert not tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))
    finally:
        transaction.catalog.close()


def test_old_gap_hash_policy_and_expiry_are_diagnostics_without_snapshot(tmp_path):
    adapter = BoundedAdapter()
    transaction, _service_unused = _service(tmp_path, adapter)
    try:
        binding = _binding("0" * 64, policy_hash="a" * 64, expires_at="2000-01-01T00:00:00Z")
        result = transaction.execute(binding, _request(), budget=_budget())
        assert result.status == "completed", result
        assert result.fetch_events == 1
        assert adapter.fetch_calls == 1 and adapter.discover_calls == 1
        second = transaction.execute(replace(binding, expires_at="1999-01-01T00:00:00Z"),
                                     _request(), budget=_budget())
        assert second.status == "completed" and second.fetch_events == 0
        assert second.txn_id == result.txn_id
        assert adapter.fetch_calls == 1
    finally:
        transaction.catalog.close()


@pytest.mark.parametrize("mutation", [
    {"entity": "OTHER"}, {"market": "HK"}, {"document_kind": "quarterly_report"},
])
def test_latest_checks_candidate_identity_before_fetch(tmp_path, mutation):
    adapter = BoundedAdapter(mutation=mutation)
    transaction, service = _service(tmp_path, adapter)
    try:
        request = SourceRequest(entity="ACME", market="US", security_id="ACME",
            document_kind="annual_report", as_of_date="2026-07-31",
            mode="latest_as_of", allow_download=True)
        with pytest.raises(AcquisitionError, match="candidate"):
            service.ensure(request, budget=_budget())
        assert adapter.fetch_calls == 0
        assert not tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))
    finally:
        transaction.catalog.close()


def test_future_publication_is_never_selected_for_download(tmp_path):
    adapter = BoundedAdapter(mutation={"filing_date": "2099-01-01"})
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=True)
        result = service.ensure(request, budget=_budget())
        assert result.status not in {SourceEnsureStatus.IMPORTED, SourceEnsureStatus.DEDUPLICATED,
                                     SourceEnsureStatus.REUSED}
        assert adapter.fetch_calls == 0
    finally:
        transaction.catalog.close()


def test_latest_uncharged_provider_bytes_are_rejected_before_canonical_import(tmp_path):
    adapter = BoundedAdapter(uncharged=True)
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=True)
        with pytest.raises(AcquisitionError, match="did not charge"):
            service.ensure(request, budget=_budget())
        assert adapter.fetch_calls == 1
        assert not tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))
    finally:
        transaction.catalog.close()


def test_discovery_budget_exhaustion_is_explicit_not_a_provider_gap(tmp_path):
    transaction, service = _service(tmp_path, BoundedAdapter())
    try:
        request = replace(_request(), mode="latest_as_of", fiscal_year=None, allow_download=True)
        budget = AcquisitionBudget.from_limits(max_response_bytes=5, max_seconds=30, max_cost_usd="0")
        with pytest.raises(AcquisitionBudgetExceeded, match="byte budget"):
            service.ensure(request, budget=budget)
        assert service.coordinator.adapters.for_market("US").fetch_calls == 0
    finally:
        transaction.catalog.close()


def test_invalid_receipt_cleans_only_owned_target_and_records_one_failure(tmp_path):
    adapter = BoundedAdapter()
    adapter.corrupt_receipt = True
    transaction, service = _service(tmp_path, adapter)
    neighbor = tmp_path / "staging" / "other-target" / "keep.txt"
    neighbor.parent.mkdir(parents=True)
    neighbor.write_text("unrelated pending operation", encoding="utf-8")
    try:
        request = replace(_request(), allow_download=True)
        with pytest.raises(AcquisitionError, match="SHA-256"):
            service.ensure(request, budget=_budget())
        assert tuple((tmp_path / "staging").rglob("*.pdf")) == ()
        assert neighbor.read_text(encoding="utf-8") == "unrelated pending operation"
        failures = [a for a in transaction.journal.read_all() if a.outcome == "failed"]
        assert len(failures) == 1
        assert transaction.catalog.store.fetchall("SELECT COUNT(*) c FROM documents")[0]["c"] == 0
    finally:
        transaction.catalog.close()


def test_import_failure_cleans_stage_keeps_usage_and_single_journal(tmp_path, monkeypatch):
    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    def fail_import(*args, **kwargs):
        raise RuntimeError("canonical import stopped")
    monkeypatch.setattr(service.writer, "import_staged", fail_import)
    budget = _budget()
    try:
        with pytest.raises(RuntimeError, match="canonical import stopped"):
            service.ensure(replace(_request(), allow_download=True), budget=budget)
        assert budget.response_bytes_used == 16
        assert not tuple((tmp_path / "staging").rglob("*.pdf"))
        failures = [a for a in transaction.journal.read_all() if a.outcome == "failed"]
        assert len(failures) == 1
        assert failures[0].reason == "canonical_import_failed"
        assert not tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))
    finally:
        transaction.catalog.close()


def test_latest_tied_distinct_accessions_are_ambiguous_without_fetch(tmp_path):
    class TiedAdapter(BoundedAdapter):
        def discover_bounded(self, request, budget):
            first, = super().discover_bounded(request, budget)
            return first, replace(first, candidate_id="other", provider_document_id="other")
    adapter = TiedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        result = service.ensure(replace(_request(), mode="latest_as_of", fiscal_year=None,
                                       allow_download=True), budget=_budget())
        assert result.status is SourceEnsureStatus.AMBIGUOUS
        assert adapter.fetch_calls == 0
    finally:
        transaction.catalog.close()


def test_retryable_fetch_uses_same_selection_and_remaining_budget(tmp_path):
    from company_wiki.source_catalog.adapter_process import AdapterProcessError
    class BusyAdapter(BoundedAdapter):
        attempts = 0
        def fetch_bounded(self, candidate, staging_dir, budget):
            self.attempts += 1
            if self.attempts == 1:
                budget.consume_response_bytes(3)
                (staging_dir / "partial.tmp").write_bytes(b"bad")
                exc = AdapterProcessError("temporary busy")
                exc.retryable = True
                raise exc
            assert not (staging_dir / "partial.tmp").exists()
            return super().fetch_bounded(candidate, staging_dir, budget)
    adapter = BusyAdapter()
    transaction, service = _service(tmp_path, adapter)
    budget = _budget()
    try:
        result = service.ensure(replace(_request(), allow_download=True), budget=budget)
        assert result.status is SourceEnsureStatus.IMPORTED
        assert adapter.attempts == 2 and adapter.discover_calls == 1
        assert budget.response_bytes_used == 19
        assert all(b is budget for b in adapter.budgets)
    finally:
        transaction.catalog.close()


@pytest.mark.parametrize("market,kind,period", [
    ("US", "annual_report", "FY"),
    ("HK", "quarterly_report", "Q1"),
    ("CN", "quarterly_report", "Q1"),
    ("CN", "annual_report", "FY"),
])
def test_latest_does_not_invent_prior_calendar_year_for_provider(tmp_path, market, kind, period):
    class CalendarAdapter(BoundedAdapter):
        def discover_bounded(self, request, budget):
            self.discovery_request = request
            budget.consume_response_bytes(7)
            return (replace(super().discover(request)[0], market=market,
                            document_kind=kind, form_type=kind,
                            fiscal_year=2026, fiscal_period=period),)

    adapter = CalendarAdapter()
    transaction, service = _service(tmp_path, adapter)
    request = replace(_request(), market=market, document_kind=kind, form_type=kind,
                      fiscal_year=None, fiscal_period=period, mode="latest_as_of",
                      allow_download=True)
    try:
        result = service.ensure(request, budget=_budget())
        assert adapter.discovery_request.fiscal_year is None
        assert result.status is SourceEnsureStatus.IMPORTED
        assert result.resolution.matches[0].fiscal_year == 2026
    finally:
        transaction.catalog.close()


def test_staging_root_cannot_overlap_configured_original_roots(tmp_path):
    from company_wiki.source_catalog import AcquisitionCoordinator, AdapterRegistry
    adapter = BoundedAdapter()
    transaction, _unused = _service(tmp_path, adapter)
    raw_root = transaction.catalog.config.roots[0].path
    sentinel = raw_root / "original.pdf"
    sentinel.write_bytes(b"%PDF-protected original")
    try:
        with pytest.raises(AcquisitionError, match="staging.*original"):
            AcquisitionCoordinator(catalog=transaction.catalog,
                adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
                staging_root=raw_root)
        assert sentinel.read_bytes() == b"%PDF-protected original"
        assert adapter.fetch_calls == 0
    finally:
        transaction.catalog.close()


@pytest.mark.parametrize("supports_notes", [True, False])
def test_cleanup_failure_never_journals_successful_completion(tmp_path, monkeypatch, supports_notes):
    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    original_cleanup = transaction.coordinator.cleanup_target
    calls = 0

    class WithoutNotesError(OSError):
        @property
        def add_note(self):
            raise AttributeError("add_note is unavailable on Python 3.10")

    def cleanup(request, candidate):
        nonlocal calls
        calls += 1
        if calls > 1:
            error_type = OSError if supports_notes else WithoutNotesError
            raise error_type("staging cleanup unavailable")
        return original_cleanup(request, candidate)

    monkeypatch.setattr(transaction.coordinator, "cleanup_target", cleanup)
    try:
        with pytest.raises(OSError, match="cleanup unavailable"):
            service.ensure(replace(_request(), allow_download=True), budget=_budget())
        attempts = transaction.journal.read_all()
        assert [a.outcome for a in attempts] == ["failed"]
        assert transaction.catalog.reader.fetchone("SELECT COUNT(*) n FROM documents")["n"] == 1
        assert len(tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))) == 1
    finally:
        transaction.catalog.close()


def test_no_binding_no_budget_refuses_before_provider_egress(tmp_path):
    adapter = BoundedAdapter()
    transaction, _unused = _service(tmp_path, adapter)
    try:
        result = transaction.execute(None, _request())
        assert result.status == "rejected"
        assert result.reason == "acquisition_budget_required"
        assert adapter.discover_calls == 0 and adapter.fetch_calls == 0
    finally:
        transaction.catalog.close()


@pytest.mark.parametrize("release_lock", [False, True])
def test_canonical_lock_wait_shares_budget_without_rehash_or_refetch(tmp_path, monkeypatch, release_lock):
    import threading
    from company_wiki.source_catalog.lock import CatalogOperationLock

    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    ready, release = threading.Event(), threading.Event()

    def hold():
        with CatalogOperationLock(transaction.catalog.config.catalog_dir, operation="test_hold"):
            ready.set()
            release.wait(timeout=5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert ready.wait(timeout=3)
    validation_calls = []
    validate = transaction.writer._validate_staged

    def counted(*args, **kwargs):
        validation_calls.append(True)
        if release_lock:
            threading.Timer(0.15, release.set).start()
        return validate(*args, **kwargs)

    monkeypatch.setattr(transaction.writer, "_validate_staged", counted)
    budget = AcquisitionBudget.from_limits(max_response_bytes=5000,
        max_seconds=3 if release_lock else 0.3, max_cost_usd="0")
    try:
        request = replace(_request(), allow_download=True)
        if release_lock:
            assert service.ensure(request, budget=budget).status is SourceEnsureStatus.IMPORTED
        else:
            with pytest.raises(AcquisitionBudgetExceeded, match="deadline"):
                service.ensure(request, budget=budget)
            assert [a.outcome for a in transaction.journal.read_all()] == ["failed"]
            assert not tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))
        assert len(validation_calls) == 1
        assert adapter.discover_calls == 1 and adapter.fetch_calls == 1
        assert budget.response_bytes_used == 7 + len(b"%PDF-2025")
        assert all(b is budget for b in adapter.budgets)
        assert not tuple((tmp_path / "staging").rglob("*.pdf"))
    finally:
        release.set()
        holder.join(timeout=5)
        transaction.catalog.close()


def test_bound_amendment_final_read_matches_selected_accession(tmp_path):
    import hashlib

    class RevisedAdapter(BoundedAdapter):
        revised = False

        def discover_bounded(self, request, budget):
            self.mutation = ({"provider_document_id": "acc-amended", "candidate_id": "amended",
                              "filing_date": "2026-05-15", "amended": True}
                             if self.revised else {})
            return super().discover_bounded(request, budget)

        def fetch(self, candidate, staging_dir):
            receipt = super().fetch(candidate, staging_dir)
            if self.revised:
                from pathlib import Path
                body = b"%PDF-amended"
                Path(receipt.staged_path).write_bytes(body)
                return replace(receipt, byte_size=len(body), content_sha256=hashlib.sha256(body).hexdigest())
            return receipt

        def fetch_bounded(self, candidate, staging_dir, budget):
            self.budgets.append(budget)
            receipt = self.fetch(candidate, staging_dir)
            budget.consume_response_bytes(receipt.byte_size)
            return receipt

    adapter = RevisedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        original = service.ensure(replace(_request(), allow_download=True), budget=_budget())
        adapter.revised = True
        binding = _binding("old", policy_hash="old", accessions=("acc-amended",))
        result = transaction.execute(binding, _request(), budget=_budget())
        assert result.status == "completed", result
        assert result.resolution["matches"][0]["provider_document_id"] == "acc-amended"
        assert result.resolution["matches"][0]["content_sha256"] != original.resolution.matches[0].content_sha256
        assert adapter.fetch_calls == 2
        assert len(tuple(transaction.catalog.config.roots[0].path.rglob("*.pdf"))) == 2
    finally:
        transaction.catalog.close()


@pytest.mark.parametrize("minimal_binding", [False, True])
@pytest.mark.parametrize("operation,v2", [("close-gap", False), ("ensure", False), ("ensure", True)])
def test_close_gap_cli_uses_one_intent_and_optional_scope_file(
    tmp_path, monkeypatch, capsys, minimal_binding, operation, v2
):
    import json
    from types import SimpleNamespace
    from company_wiki.source_catalog import AdapterRegistry, cli
    from test_source_catalog_ensure_paused_guard import _write_configs

    project = tmp_path / "project"
    config = _write_configs(project)
    from company_wiki.source_catalog.runtime_policy import build_snapshot
    policy_dir = project / ".source_catalog"
    policy_dir.mkdir(exist_ok=True)
    (policy_dir / "runtime_policy.json").write_text(json.dumps(build_snapshot({
        "schema_version": "2.0", "mode": "steady", "policy_hash": "a" * 64,
        "updated_at": "2026-10-07T00:00:00Z"})), encoding="utf-8")
    acquisition_config = project / "config/source_acquisition.yaml"
    acquisition_config.write_text("{}", encoding="utf-8")
    adapter = BoundedAdapter()
    monkeypatch.setattr(cli, "load_acquisition_config", lambda *a, **k: SimpleNamespace(
        staging_root=tmp_path / "staging",
        build_registry=lambda: AdapterRegistry(cn=adapter, hk=adapter, us=adapter)))
    argv = ["--config", str(config), operation, "--entity", "ACME", "--market", "US",
            "--security-id", "ACME", "--document-kind", "annual_report",
            "--as-of-date", "2026-07-31", "--mode", "latest_as_of",
            "--max-download-bytes", "1000", "--max-download-seconds", "30",
            "--max-download-cost-usd", "0", "--acquisition-config", str(acquisition_config)]
    if operation == "ensure":
        argv += ["--allow-download"]
    if v2:
        argv += ["--source-ref-v2"]
    if minimal_binding:
        binding = project / "scope.json"
        binding.write_text(json.dumps({"provider": "sec", "allowed_accessions": ["acc-2025"],
                                       "max_bytes": 64}), encoding="utf-8")
        argv += ["--binding-file", str(binding)]
    assert cli.main(argv) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == ("completed" if operation == "close-gap" or v2 else "imported"), payload
    if operation == "close-gap":
        assert payload["fetch_events"] == 1
    elif v2:
        assert payload["source_ref"]["content_sha256"]
        assert payload["download_events"] == 1
        assert payload["gap_plan"] is None
    else:
        assert payload["acquisition"]["receipt"]["provider_document_id"] == "acc-2025"
        resolution = payload["resolution"]
        assert resolution["resolution_envelope"]["policy_hash"] == resolution["policy_export"]["policy_hash"]
        assert cli.main(["--config", str(config), "resolve", "--entity", "ACME", "--market", "US",
                         "--security-id", "ACME", "--document-kind", "annual_report", "--fiscal-year", "2025",
                         "--as-of-date", "2026-07-31"]) == 0
        readonly = json.loads(capsys.readouterr().out)
        assert readonly["resolution_envelope"]["policy_hash"] == readonly["policy_export"]["policy_hash"]
    assert adapter.discover_calls == 1 and adapter.fetch_calls == 1
    assert adapter.budgets[0] is adapter.budgets[1]
    assert adapter.budgets[0].max_response_bytes == (64 if minimal_binding else 1000)
    assert not tuple((tmp_path / "staging").rglob("*.pdf"))
