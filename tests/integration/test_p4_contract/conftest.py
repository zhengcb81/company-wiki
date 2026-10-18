"""P4-CONSUMER-CONTRACT fixtures: opt-in, zero network, zero model.

Design (card sections 5-8):

* every test is ``skip`` unless ``CWP_P4_CATALOG_CONFIG`` is set, and the skip
  reason is explicit - a skip is never a silent pass;
* ``CWP_P4_REQUIRE=1`` turns those skips into failures;
* a catalog switch pointing at production config (or outside ``tmp_path`` and
  this card's ``fixtures/``) is the only permitted hard failure;
* ``socket.socket.connect`` is monkeypatched to raise ``AssertionError`` for the
  whole session, and any attempt is recorded as ``p4_network_attempted``.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, NoReturn

import pytest

from .support import constants as C
from .support import environment as E
from .support import netguard
from .support import cwp
from .support.report import LEDGER


@pytest.fixture(autouse=True)
def p4_opt_in_gate() -> None:
    """Every case in this lane is opt-in (card section 5.1 / 6).

    With no ``CWP_P4_CATALOG_CONFIG`` no case runs at all: each one ``skip``s
    with a readable reason, or ``fail``s when ``CWP_P4_REQUIRE=1``.  A skip is
    never a silent pass.
    """
    if E.catalog_config_path() is None:
        skip_or_fail(C.REQUIRE_CATALOG_REASON)


def pytest_sessionstart(session) -> None:  # noqa: ARG001 - pytest hook
    """Install the network guard before any collection-time import can dial out."""
    from .support import readonly

    netguard.reset_for_test()
    netguard.install()
    LEDGER.reset()
    LEDGER.start()
    readonly.capture_baseline()


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    """Emit ``p4-contract-receipt/1`` from what actually happened."""
    from .support import sessionreport

    sessionreport.finalize(session)


def pytest_runtest_logreport(report) -> None:
    """Feed real pytest outcomes into the session receipt (card section 5.4).

    Without this hook ``sessionreport.record_outcome`` never runs and every
    ``counts`` counter in the receipt stays zero - the RED the card's section 6
    asks the counts test to catch.
    """
    from .support import sessionreport

    if report.when not in ("setup", "call"):
        return
    reason: str | None = None
    if report.skipped and isinstance(report.longrepr, tuple):
        # pytest reports a skip as (path, lineno, reason)
        reason = str(report.longrepr[2]) if len(report.longrepr) > 2 else None
    sessionreport.record_outcome(report.nodeid, report.outcome, reason)


def pytest_report_header(config) -> str:  # noqa: ARG001
    return (
        "P4-CONSUMER-CONTRACT: opt-in lane; set "
        f"{C.ENV_CATALOG} to a test catalog to run it"
    )


# --- environment ------------------------------------------------------------

@pytest.fixture(scope="session")
def p4_catalog_config(tmp_path_factory) -> Path:
    """Resolve and bound-check ``CWP_P4_CATALOG_CONFIG``.

    A path outside ``tmp_path`` and this card's ``fixtures/`` - production config
    especially - raises, which is the one hard failure the card allows.
    """
    configured = E.catalog_config_path()
    if configured is None:
        skip_or_fail(C.REQUIRE_CATALOG_REASON)
    allowed_tmp = tmp_path_factory.getbasetemp()
    try:
        resolved = E.assert_catalog_config_allowed(configured, tmp_path=allowed_tmp)
    except E.ProductionConfigRefused as exc:
        pytest.fail(str(exc), pytrace=False)
    # The reader creates catalog/state beside its config.  When the switch points
    # at this card's committed fixtures, copy the whole catalog tree into tmp
    # first so the lane never writes into the repo it ships (card section 7.4).
    # A switch already under tmp_path is used as-is: that is ROOT's own catalog.
    if resolved.is_relative_to(C.FIXTURES_DIR.resolve()):
        working = tmp_path_factory.mktemp("p4-catalog") / "catalog"
        shutil.copytree(resolved.parent, working)
        resolved = working / resolved.name
    # Neither published CLI scans and the reader refuses to create a missing
    # database, so materialize state once; a catalog that already has state
    # (ROOT's read-only copy) is left untouched.
    try:
        cwp.ensure_catalog_state(resolved)
    except cwp.CwpUnavailable as exc:
        skip_or_fail(str(exc))
    return resolved


@pytest.fixture(scope="session")
def p4_catalog_root(p4_catalog_config: Path) -> Path:
    """Absolute directory that bounds the configured catalog."""
    return p4_catalog_config.resolve().parent


@pytest.fixture(scope="session")
def p4_expected() -> dict[str, Any]:
    return cwp.load_expected()


@pytest.fixture(scope="session")
def p4_sources(p4_expected: dict[str, Any]) -> list[dict[str, Any]]:
    return list(p4_expected["sources"])


@pytest.fixture(scope="session")
def p4_manifest(p4_catalog_config: Path, p4_sources: list[dict[str, Any]]):
    """Export every fixture ref once and return per-source bundles.

    ``spans`` carries the lane's own view of each fixture span, including
    ``unit_tokens`` from ``expected.json``; the wire request instead goes
    through ``cwp.wire_spans`` because the export CLI demands CWP's exact
    12-field ``EvidenceSpan`` shape with derived ids.
    """
    refs = [
        {
            "document_id": item["document_id"],
            "source_id": item["source_id"],
            "content_sha256": item["content_sha256"],
            "byte_size": item["byte_size"],
            "mime_type": item["mime_type"],
            "schema_version": C.SOURCE_REF_SCHEMA_VERSION,
        }
        for item in p4_sources
    ]
    spans = []
    for item in p4_sources:
        for span in item["spans"]:
            spans.append({
                "schema_version": C.EVIDENCE_SPAN_SCHEMA_VERSION,
                "source_id": item["source_id"],
                "locator": f"loc:v1/chars:{span['char_start']}-{span['char_end']}",
                "coordinates": {
                    "page_number": None, "paragraph_index": None,
                    "table_index": None, "row_index": None, "column_index": None,
                    "char_start": span["char_start"], "char_end": span["char_end"],
                },
                "raw_text": span["raw_text"],
                "structured_value": None,
                "parser_name": "p4-fixture-parser",
                "parser_version": "1.0.0",
                "parse_status": "parsed",
                "quality_flags": [],
                "unit_tokens": list(span["unit_tokens"]),
            })
    result = cwp.export_sources(
        p4_catalog_config, source_refs=refs, evidence_spans=cwp.wire_spans(p4_sources)
    )
    return {"bundle": result.bundle, "argv": list(result.argv), "spans": spans}


@pytest.fixture(scope="session")
def p4_reads(p4_catalog_config: Path, p4_sources: list[dict[str, Any]]):
    """Read every fixture source once through the published reader."""
    results = {}
    for item in p4_sources:
        results[item["relative_path"]] = cwp.read_source(
            p4_catalog_config,
            document_id=item["document_id"],
            source_id=item["source_id"],
            content_sha256=item["content_sha256"],
        )
    return results


# --- skip semantics ---------------------------------------------------------

def skip_or_fail(reason: str) -> NoReturn:
    """``skip`` by default, ``fail`` when ``CWP_P4_REQUIRE=1``.

    Both outcomes abort the current test, so this never returns - which is what
    lets mypy narrow a ``None`` catalog switch to ``Path`` after the call.  The
    trailing raise is unreachable at runtime (``pytest.skip`` raises ``Skipped``)
    but makes the no-return contract visible to mypy, whose ``follow_imports =
    "skip"`` config hides pytest's own ``NoReturn`` annotations.
    """
    if E.require_flag():
        pytest.fail(f"{reason} (CWP_P4_REQUIRE=1 turns skips into failures)")
    pytest.skip(reason)
    raise AssertionError(f"skip_or_fail must never return: {reason}")


@pytest.fixture(scope="session")
def p4_consumer_specs():
    """ROOT's ``p4-consumer-commands/1``, or ``None`` when absent.

    Session-scoped so the repo snapshot fixture below can depend on it.
    """
    from .support.consumer import ManifestRejected, load_manifest

    configured = E.consumer_commands_path()
    if configured is None:
        return None
    try:
        return load_manifest(configured)
    except ManifestRejected as exc:
        pytest.fail(f"consumer command manifest rejected ({exc.reason}): {exc.detail}",
                    pytrace=False)


@pytest.fixture(scope="session")
def p4_consumer_repos(p4_consumer_specs) -> dict[str, Path]:
    """Roots of the consumer repositories named by the environment switches."""
    repos: dict[str, Path] = {}
    for consumer in C.CONSUMERS:
        root = E.consumer_root(consumer)
        if root is not None and root.is_dir():
            repos[consumer] = root
    return repos


@pytest.fixture
def p4_case(request):
    """Register one case in the session ledger and return its recorder.

    The ledger name defaults to the test function name so it always matches the
    nodeid the session report derives.
    """
    from .support.report import case_name as _case_name

    def _case(name: str | None = None):
        return LEDGER.case(name or _case_name(request))

    return _case
