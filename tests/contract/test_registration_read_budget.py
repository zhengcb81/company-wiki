"""Actual registration reads must share the current bounded local budget."""

import pytest
from helpers.source_fact_fixture import lake, close
from test_company_source_layout import original
from company_wiki.source_catalog.local_inventory import (
    LocalReadBudget,
    LocalPrepareLimits,
)
from company_wiki.source_catalog.source_reader import SourceReadError


def test_registration_budget_refuses_oversized_raw_before_read(tmp_path, monkeypatch):
    cat = lake(tmp_path)
    try:
        path, data = original(cat, "Acme/raw/annual.htm")
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=32))
        from pathlib import Path

        real = Path.open
        opened = []

        def observe(self, *a, **kw):
            if self == path:
                opened.append(str(self))
            return real(self, *a, **kw)

        monkeypatch.setattr(Path, "open", observe)
        with pytest.raises(SourceReadError) as error:
            cat.register_sources(
                root_id="company_raw",
                relative_paths={"Acme/raw/annual.htm"},
                budget=budget,
            )
        assert error.value.reason == "budget_exceeded"
        assert not opened
        assert cat.reader.fetchone("SELECT COUNT(*) FROM sources")[0] == 0
        monkeypatch.setattr(Path, "open", real)
        assert path.read_bytes() == data
    finally:
        close(cat)


@pytest.mark.parametrize("cause", ["deadline", "growth"])
def test_registration_stream_checks_deadline_and_changing_bytes(
    tmp_path, monkeypatch, cause
):
    cat = lake(tmp_path)
    try:
        path, data = original(cat, "Acme/raw/annual.htm")
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=8192))
        from pathlib import Path

        real = Path.open

        class ChangedRead:
            def __init__(self, stream):
                self.stream = stream
                self.reads = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def read(self, size):
                result = self.stream.read(size)
                self.reads += 1
                if self.reads == 1:
                    if cause == "deadline":
                        budget.deadline = 0
                    else:
                        with real(path, "ab") as growing:
                            growing.write(b"changed by test")
                return result

        def observe(self, *a, **kw):
            stream = real(self, *a, **kw)
            return (
                ChangedRead(stream) if self == path and a and a[0] == "rb" else stream
            )

        monkeypatch.setattr(Path, "open", observe)
        with pytest.raises(SourceReadError) as error:
            cat.register_sources(
                root_id="company_raw",
                relative_paths={"Acme/raw/annual.htm"},
                budget=budget,
            )
        assert error.value.reason == (
            "local_prepare_deadline" if cause == "deadline" else "local_source_changed"
        )
        assert cat.reader.fetchone("SELECT COUNT(*) FROM sources")[0] == 0
        monkeypatch.setattr(Path, "open", real)
        if cause == "growth":
            path.write_bytes(data)
        assert path.read_bytes() == data
    finally:
        close(cat)


@pytest.mark.parametrize("adapter", [None, "company_raw_v1"])
def test_registration_metadata_bytes_share_limit_before_open(
    tmp_path, monkeypatch, adapter
):
    cat = lake(tmp_path)
    try:
        if adapter:
            from dataclasses import replace

            cat.config = replace(
                cat.config, roots=(replace(cat.config.roots[0], adapter_id=adapter),)
            )
        path, data = original(cat, "Acme/raw/annual.htm")
        sidecar = path.with_name(path.name + ".source.json")
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=32))
        from pathlib import Path

        real = Path.open
        opened = []

        def observe(self, *a, **kw):
            if self == sidecar:
                opened.append(self)
            return real(self, *a, **kw)

        monkeypatch.setattr(Path, "open", observe)
        with pytest.raises(SourceReadError) as error:
            cat.register_sources(
                root_id="company_raw",
                relative_paths={"Acme/raw/annual.htm"},
                budget=budget,
            )
        assert error.value.reason == "budget_exceeded"
        assert not opened
        assert cat.reader.fetchone("SELECT COUNT(*) FROM sources")[0] == 0
    finally:
        close(cat)


@pytest.mark.parametrize("adapter", [None, "dayu_filing_v1"])
def test_dayu_attachment_enumeration_consumes_same_entry_ceiling(tmp_path, adapter):
    cat = lake(tmp_path, portfolio=True)
    try:
        if adapter:
            from dataclasses import replace

            cat.config = replace(
                cat.config,
                roots=(
                    cat.config.roots[0],
                    replace(cat.config.roots[1], adapter_id=adapter),
                ),
            )
        group = cat.config.roots[1].path / "ACME/filings/fil_0000012345-26-000007"
        group.mkdir(parents=True)
        (group / "original.htm").write_text("actual primary")
        import json

        (group / "meta.json").write_text(
            json.dumps({"primary_document": "original.htm"})
        )
        for i in range(6):
            (group / f"attachment{i}.txt").write_text("attachment")
        budget = LocalReadBudget(LocalPrepareLimits(max_discovery_entries=3))
        with pytest.raises(SourceReadError) as error:
            cat.register_sources(
                root_id="provider",
                relative_paths={"ACME/filings/fil_0000012345-26-000007/original.htm"},
                budget=budget,
            )
        assert error.value.reason == "local_discovery_entry_limit"
        assert budget.discovery_entries == 4 and budget.bytes_read == 0
        assert cat.reader.fetchone("SELECT COUNT(*) FROM documents")[0] == 0
    finally:
        close(cat)


def test_cached_ready_uses_remaining_task_budget_before_open(tmp_path, monkeypatch):
    cat = lake(tmp_path)
    try:
        from helpers.source_fact_fixture import html, imported, evidence
        from company_wiki.source_catalog.local_reconcile import prepare_local_source
        from test_company_source_layout import request

        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        from pathlib import Path

        real = Path.open
        opened = []

        def observe(self, *a, **kw):
            if self == path:
                opened.append(self)
            return real(self, *a, **kw)

        monkeypatch.setattr(Path, "open", observe)
        result = prepare_local_source(
            cat, request(), limits=LocalPrepareLimits(max_bytes=32)
        )
        assert result["status"] == "unavailable" and result["blocks_download"]
        assert result["reason"] == "budget_exceeded"
        assert not opened and result["download_events"] == 0
    finally:
        close(cat)


def test_public_verify_supplied_budget_never_resets_or_exceeds(tmp_path):
    cat = lake(tmp_path)
    try:
        from helpers.source_fact_fixture import html, imported
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2026)
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=ref.byte_size + 1))
        budget.charge(2)
        with pytest.raises(SourceReadError) as error:
            SourceVersionReader(cat).verify_version(ref, budget=budget)
        assert error.value.reason == "budget_exceeded"
        assert budget.bytes_read == 2
    finally:
        close(cat)
