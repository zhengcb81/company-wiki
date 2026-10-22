"""New non-author observations over real source-owner/library operations."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from helpers.source_fact_fixture import lake, html, imported, close
from contract.test_local_request_relevance import request
from company_wiki.source_catalog import local_reconcile
from company_wiki.source_catalog.local_inventory import (
    LocalReadBudget,
    LocalPrepareLimits,
)
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.source_reader import SourceReadError

EVIDENCE = Path(__file__).parent


@pytest.fixture
def owned(tmp_path):
    (tmp_path / "keep.bin").write_bytes(b"preexisting source test sentinel")
    root = tmp_path / "owned"
    root.mkdir()
    cat = lake(root)
    try:
        yield cat, root
    finally:
        close(cat)
        assert root.resolve().parent == tmp_path.resolve()
        shutil.rmtree(root)
        assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == {
            "keep.bin": b"preexisting source test sentinel"
        }


def proof(name, value):
    (EVIDENCE / (name + ".json")).write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def test_real_discovery_completed_write_survives_later_unknown_failure(
    owned, monkeypatch
):
    cat, _root = owned
    folder = cat.config.roots[0].path / "Acme"
    folder.mkdir()
    originals = {
        "a-good.htm": html(),
        "z-unknown.htm": b"<html><body>Unresolved actual scope.</body></html>",
    }
    for name, data in originals.items():
        (folder / name).write_bytes(data)
    observed = []
    real = local_reconcile.restore_document_facts

    def capture(*args, **kwargs):
        result = real(*args, **kwargs)
        observed.append(
            {
                k: v
                for k, v in result.items()
                if k not in {"source_ref", "verified_locations"}
            }
        )
        return result

    monkeypatch.setattr(local_reconcile, "restore_document_facts", capture)
    requested = replace(
        request(),
        mode="latest_as_of",
        fiscal_year=None,
        fiscal_period=None,
        form_type=None,
        as_of_date="2026-10-22",
    )
    result = prepare_local_source(cat, requested)
    assert (
        result["status"] in {"blocked", "unavailable"} and result["blocks_download"]
    ), result
    completed = [row for row in observed if row["status"] in {"recorded", "restored"}]
    assert completed, observed
    assert (
        cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0] >= 1
    )
    for name, data in originals.items():
        assert (folder / name).read_bytes() == data
    proof(
        "discovery-before-later-failure",
        {"owner_completed": completed, "result": result},
    )
    assert all(row in result["operations"] for row in completed), result
    assert (
        len(
            [
                r
                for r in result["operations"]
                if r.get("operation") == "local_read_budget"
            ]
        )
        == 1
    )


def test_actual_metadata_read_then_cancel_observes_tail_but_not_accepted_bytes(
    tmp_path, monkeypatch
):
    path = tmp_path / "metadata.json"
    raw = b'{"machine":true}'
    path.write_bytes(raw)
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=1024))
    original_open = Path.open

    class ReadThenCancel:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, *args):
            result = self.stream.read(*args)
            budget.cancel()
            return result

    def intercept(self, *args, **kwargs):
        stream = original_open(self, *args, **kwargs)
        return (
            ReadThenCancel(stream)
            if self == path and args and args[0] == "rb"
            else stream
        )

    monkeypatch.setattr(Path, "open", intercept)
    with pytest.raises(SourceReadError, match="cancelled"):
        budget.read_metadata_observation(path, root=tmp_path)
    observed = budget.observation(reason="cancelled")
    assert observed["triggered_bound"] == "cancelled"
    assert observed["consumed"]["observed_charge_bytes"] == len(raw)
    assert observed["consumed"]["charged_read_bytes"] == 0
    assert str(tmp_path) not in json.dumps(observed)
    assert path.read_bytes() == raw
    path.unlink()
    proof("actual-cancel-after-read", observed)


def test_actual_nonrelevance_is_call_local_and_does_not_hide_later_requested_scope(
    owned, monkeypatch
):
    cat, _root = owned
    data = html(year=2022, end="2022-06-30")
    ref, path = imported(cat, data)
    path.with_name("meta.json").write_text("{broken", encoding="utf-8")
    real = local_reconcile._proven_facts
    calls = []

    def capture(catalog, original, *args, **kwargs):
        if original.ref.document_id == ref.document_id:
            calls.append(original.ref.content_sha256)
        return real(catalog, original, *args, **kwargs)

    monkeypatch.setattr(local_reconcile, "_proven_facts", capture)
    current = replace(request(), as_of_date="2026-10-22")
    first = prepare_local_source(cat, current)
    second = prepare_local_source(cat, current)
    assert first["status"] == second["status"] == "not_found"
    assert first["blocks_download"] is second["blocks_download"] is False
    assert calls == [ref.content_sha256, ref.content_sha256]
    target = prepare_local_source(cat, replace(current, fiscal_year=2022))
    assert target["blocks_download"] and target["status"] in {
        "blocked",
        "unavailable",
    }, target
    assert target["reason"] != "no_matching_local_period"
    assert path.read_bytes() == data
    proof(
        "negative-scope-is-not-persistent",
        {
            "first": first,
            "second": second,
            "target": target,
            "original_sha256": ref.content_sha256,
            "calls": len(calls),
        },
    )


@pytest.mark.parametrize(
    "current_body",
    [html(cik="99999"), b"<html><body>No issuer or fiscal scope.</body></html>"],
    ids=["conflicting-issuer", "unknown-scope"],
)
def test_wrong_old_label_cannot_extend_another_documents_nonrelevance(
    owned, current_body
):
    cat, _root = owned
    old, old_path = imported(cat, html(year=2022, end="2022-06-30"))
    base = cat.config.roots[0].path / "Acme"
    base.mkdir(exist_ok=True)
    new = base / "2022-old-label.htm"
    new.write_bytes(current_body)
    result = prepare_local_source(cat, replace(request(), as_of_date="2026-10-22"))
    assert (
        result["status"] in {"blocked", "unavailable"} and result["blocks_download"]
    ), result
    assert result["source_ref"] is None and result["download_events"] == 0
    assert result["reason"] != "no_matching_local_period"
    assert new.read_bytes() == current_body and old_path.read_bytes() == html(
        year=2022, end="2022-06-30"
    )


def test_latest_does_not_return_old_cached_match_before_new_bad_actual_period(owned):
    cat, _root = owned
    old, old_path = imported(
        cat,
        html(year=2024, end="2024-06-30"),
        published="2024-07-30",
        declared_year=2024,
    )
    assert (
        prepare_local_source(
            cat, replace(request(), fiscal_year=2024, as_of_date="2026-10-22")
        )["status"]
        == "ready"
    )
    base = cat.config.roots[0].path / "Acme"
    base.mkdir(exist_ok=True)
    body = html(end="June 30, 2026", transform="unknown:date-format")
    new = base / "2022-wrong-label.htm"
    new.write_bytes(body)
    result = prepare_local_source(
        cat,
        replace(
            request(),
            mode="latest_as_of",
            fiscal_year=None,
            fiscal_period=None,
            form_type=None,
            as_of_date="2026-10-22",
        ),
    )
    assert (
        result["status"] in {"blocked", "unavailable"} and result["blocks_download"]
    ), result
    assert result["source_ref"] is None and result["download_events"] == 0
    assert (
        new.read_bytes() == body
        and hashlib.sha256(old_path.read_bytes()).hexdigest() == old.content_sha256
    )
