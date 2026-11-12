"""The document work budget is an injected port, not an ambient file read."""
import pathlib
from types import SimpleNamespace

import pytest

from company_wiki.resource_budget import (
    WorkBudget,
    WorkBudgetExceeded,
    document_work_budget_factory,
)
from company_wiki.source_catalog import narrative_selector_binding as binding
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading
from company_wiki.source_catalog.narrative_selection import (
    NarrativeMaterialError,
    RawNarrativeSelector,
)


def _payload():
    return SimpleNamespace(
        source_ref=SimpleNamespace(
            mime_type="application/pdf", source_id="source", content_sha256="a" * 64,
        ),
        source_metadata=SimpleNamespace(
            source_class="filing", language="en", title="Annual Report",
            document_kind="annual_report",
        ),
    )


def _select(work_budget_factory):
    """Run one PDF selection with the given budget port."""
    observed = {}

    def parser(data, **kwargs):
        budget = kwargs.get("work_budget")
        assert budget is not None, "A replacement lost the caller's shared account"
        observed["budget"] = budget
        budget.charge(17)
        from company_wiki.source_catalog.narrative_document import DocumentStructure

        return DocumentStructure("source", "a" * 64, "en", (), page_count=1, pages_read=1)

    reading = RawNarrativeSelector(
        pdf_reading=PdfReading(parser=parser),
        selector=binding.bind_narrative_selector(selector_version="0.9.0"),
        work_budget_factory=work_budget_factory,
    )
    payload = _payload()
    reading.select(
        b"fixture", source_ref=payload.source_ref, source_metadata=payload.source_metadata,
        checkpoint=lambda: None,
    )
    return observed


def test_raw_selector_uses_injected_work_budget_without_config_io(monkeypatch):
    """The injected ceiling is the only budget; no configuration file is read."""
    original = pathlib.Path.read_text

    def refuse_budget_policy(self, *args, **kwargs):
        if self.name == "resource_budget.yaml":
            raise AssertionError("the selection algorithm read a configuration file")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", refuse_budget_policy)
    monkeypatch.delenv("COMPANY_WIKI_BUDGET_CONFIG", raising=False)

    observed = _select(document_work_budget_factory(max_work_units=1000))
    assert observed["budget"].max_work_units == 1000
    # One read owns one account: the parser and the selector charge it.
    assert observed["budget"].used > 0
    assert observed["budget"].exhausted is False


def test_two_runtime_configs_do_not_share_implicit_budget():
    """Two selectors with different ceilings keep separate accounts."""
    first = _select(document_work_budget_factory(max_work_units=1000))
    second = _select(document_work_budget_factory(max_work_units=500))
    assert first["budget"].max_work_units == 1000
    assert second["budget"].max_work_units == 500
    assert first["budget"] is not second["budget"]
    assert first["budget"].used == second["budget"].used > 0


def test_exhausted_injected_budget_stops_before_the_next_stage():
    """An exhausted account refuses the read instead of starting more work."""
    def exhausted():
        return WorkBudget(0)

    with pytest.raises(NarrativeMaterialError) as refusal:
        _select(exhausted)
    assert refusal.value.code == "PARSER_INCOMPLETE"
    assert "document_work limit reached" in refusal.value.detail


def test_a_cancelled_read_keeps_its_own_refusal():
    """A cancelled read is not reported as a budget failure."""
    def cancel():
        raise TimeoutError("cancelled")

    with pytest.raises(TimeoutError):
        _select(cancel)


def test_budget_factory_resolves_one_ceiling_for_every_account(monkeypatch):
    """The ceiling is read once, where the caller binds it."""
    reads = []
    original = pathlib.Path.read_text

    def counting(self, *args, **kwargs):
        reads.append(self)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", counting)
    factory = document_work_budget_factory()
    first = factory()
    second = factory()
    assert first.max_work_units == second.max_work_units
    assert first is not second
    assert first.used == second.used == 0
    assert len(reads) == 1


def test_work_budget_factory_rejects_a_negative_ceiling():
    with pytest.raises(ValueError):
        document_work_budget_factory(max_work_units=-1)


def test_scoped_account_still_charges_the_shared_parent():
    parent = WorkBudget(10)
    child = parent.scoped(5)
    child.charge(4)
    assert child.used == 4
    assert parent.used == 4
    with pytest.raises(WorkBudgetExceeded):
        child.charge(2)
    assert parent.used == 4
    assert parent.exhausted is False
