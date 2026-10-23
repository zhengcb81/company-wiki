"""W11: offline deterministic discovery regression for classification and coverage.

Issuer-neutral synthetic fixtures only. No network, no model, no production
catalog. Fixtures derived from the sealed wuxi IR result are marked
``derived_minimal_fixture`` and bound to that result's SHA; they are not a
replay of the original page, which is not retained anywhere in scope.
"""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from company_wiki.source_catalog.official_discovery import (
    discover_official_documents,
)

# The hermetic autouse fixture blocks every socket; the CLI subprocess only
# needs a local socket pair for asyncio's loop (no external connection).
_SOCKET_CONNECT = socket.socket.connect


def _local_pair_only(sock, address):
    if address[0] not in {"127.0.0.1", "::1"}:
        raise RuntimeError("external network forbidden in W11 offline tests")
    return _SOCKET_CONNECT(sock, address)


@pytest.fixture(autouse=True)
def _offline_socket_guard(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _local_pair_only)


def _cli_env(repo: Path) -> dict:
    """Subprocess env: keep the host environment (a stripped env breaks
    WSAStartup/asyncio on Windows) and pin only the import path."""
    return {
        **os.environ,
        "PYTHONPATH": str(repo / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

# Sealed real discover result (result_receipt, not the 486789B body):
# sha256 of execution_replays/r1-remediation-01/roles/executor/commands/
# faa5bf2650964e9480566759c565ce11/stdout.txt
SEALED_RESULT_SHA256 = (
    "1c33f18b24354c5a30e1d71258cf09c89ad23baec43bc42111082bc2fe7e7f52"
)
DERIVED_FIXTURE_NOTE = (
    "derived_minimal_fixture: titles mirror the sealed faa5bf result SHA "
    + SEALED_RESULT_SHA256
    + "; not an original page replay; body_available=false"
)


def _page(body: str, url="https://ir.example/ir", capture="fx"):
    return {
        "url": url,
        "original": ("<html><body>" + body + "</body></html>").encode("utf-8"),
        "mime_type": "text/html",
        "capture_id": capture,
    }


def _discover(pages, entity="Neutral Instruments", as_of="2026-10-21",
              start="2026-01-01", **kw):
    return discover_official_documents(
        pages, entity=entity, as_of_date=as_of, start_date=start, **kw
    )


class TestMaterialClassification:
    """Positive controls: business material leads stay candidates."""

    def test_deck_and_reports_are_candidates_with_shared_kind(self):
        out = _discover([_page(
            '<a href="/deck.pdf">Investor Presentation H1 2026</a>'
            '<a href="/annual.pdf">Annual Report 2025</a>'
            '<a href="/interim.pdf">2026 Interim Report</a>'
        )])
        by = {c["source_url"]: c for c in out["candidates"]}
        assert set(by) == {
            "https://ir.example/deck.pdf",
            "https://ir.example/annual.pdf",
            "https://ir.example/interim.pdf",
        }
        for c in by.values():
            assert c["is_business_original"] is False
            assert c["metadata_only"] is True
            assert c["materiality"] == "not_assessed"

    def test_true_transcript_identity_requires_call_or_transcript_clue(self):
        out = _discover([_page(
            '<a href="/t1.pdf">Second Quarter 2026 Earnings Call Transcript</a>'
            '<a href="/t2.pdf">Q2 2026 earnings release</a>'
            '<a href="/t3.pdf">Q2 2026 earnings presentation</a>'
        )])
        by = {c["source_url"]: c["document_kind"] for c in out["candidates"]}
        assert by["https://ir.example/t1.pdf"] == "investor_call_transcript"
        # W11-B: "earnings" alone is a release/deck, never a call transcript.
        assert by["https://ir.example/t2.pdf"] != "investor_call_transcript"
        assert by["https://ir.example/t3.pdf"] != "investor_call_transcript"

    def test_cn_report_and_activity_kinds_are_classified(self):
        out = _discover([_page(
            '<a href="/semi.pdf">2026年半年度报告</a>'
            '<a href="/act.pdf">投资者关系活动记录</a>'
            '<a href="/notice.pdf">关于召开业绩说明会的会议通知</a>'
        )])
        by = {c["source_url"]: (c["document_kind"], c["disposition"])
              for c in out["candidates"]}
        assert by["https://ir.example/semi.pdf"][0] == "semi_annual_report"
        assert by["https://ir.example/act.pdf"][0] == "investor_relations"
        assert by["https://ir.example/notice.pdf"] == (
            "meeting_notice", "index_notice",
        )


class TestNonMaterialExclusion:
    """Negative controls: legal/static navigation never becomes material."""

    def test_legal_navigation_pdfs_are_not_candidates(self):
        # Titles mirror the sealed faa5bf result (privacy/terms anchors).
        out = _discover([_page(
            '<a href="/privacy.pdf">Privacy Statement</a>'
            '<a href="/terms.pdf">Terms of Use</a>'
            '<a href="/privacy2.pdf">|  隐私声明</a>'
            '<a href="/legal.pdf">Legal Notice and Disclaimer</a>'
        )])
        assert out["candidates"] == []
        assert out["no_documents_claimed"] is False
        # The discovery result stays honest: zero material leads is a partial
        # coverage fact, never a "no documents exist" claim.
        assert out["coverage_status"] in {"partial", "checked_index_only"}

    def test_generic_navigation_keywords_are_not_material_clues(self):
        out = _discover([_page(
            '<a href="/nav1.html">Conference</a>'
            '<a href="/nav2.html">Business</a>'
            '<a href="/nav3.html">Investor</a>'
            '<a href="/nav4.pdf">Contact Information</a>'
        )])
        assert out["candidates"] == []

    def test_event_notice_is_index_notice_not_a_business_original(self):
        out = _discover([_page(
            '<a href="/notice.pdf">Notice of Upcoming Investor Conference</a>'
        )])
        assert len(out["candidates"]) == 1
        notice = out["candidates"][0]
        assert notice["disposition"] == "index_notice"
        assert notice["is_business_original"] is False


class TestTimeWindowBoundaries:
    def test_window_is_inclusive_on_both_ends(self):
        out = _discover([_page(
            '<article><time datetime="2026-01-01"></time>'
            '<a href="/start.pdf">Investor presentation start day</a></article>'
            '<article><time datetime="2026-10-21"></time>'
            '<a href="/end.pdf">Investor presentation as-of day</a></article>'
        )])
        by = {c["source_url"]: c["disposition"] for c in out["candidates"]}
        assert by["https://ir.example/start.pdf"] == "candidate"
        assert by["https://ir.example/end.pdf"] == "candidate"

    def test_future_and_before_window_are_excluded_with_reasons(self):
        out = _discover([_page(
            '<article><time datetime="2026-10-22"></time>'
            '<a href="/future.pdf">Investor presentation future</a></article>'
            '<article><time datetime="2025-12-31"></time>'
            '<a href="/old.pdf">Investor presentation before window</a></article>'
        )])
        assert out["candidates"] == []
        reasons = {e["source_url"]: e["reason"] for e in out["excluded"]}
        assert reasons["https://ir.example/future.pdf"] == "after_as_of"
        assert reasons["https://ir.example/old.pdf"] == "before_window"

    def test_invalid_or_missing_dates_stay_unknown(self):
        out = _discover([_page(
            '<article><time datetime="not-a-date"></time>'
            '<a href="/bad.pdf">Investor presentation bad time</a></article>'
            '<a href="/nodate.pdf">Investor presentation no date</a>'
        )])
        for c in out["candidates"]:
            assert c["published_date"] is None
            assert c["disposition"] == "date_unknown"
        assert "publication_date_unknown" in out["limitations"]

    def test_page_retrieval_marker_is_not_a_publication_date(self):
        # A capture timestamp near the anchor must not be adopted as the
        # material's published date.
        out = _discover([_page(
            '<article><time datetime="2026-10-21T19:39:09Z"></time>'
            '<a href="/m.pdf">Investor presentation</a></article>'
        )])
        assert out["candidates"][0]["published_date"] == "2026-10-21"
        # in-window date is a candidate; the point is the date comes from the
        # index's own time element only, never from our fetch time.


class TestUrlAndDedup:
    def test_relative_and_nested_urls_resolve_against_page(self):
        out = _discover([_page(
            '<a href="rel.pdf">Investor presentation relative</a>'
            '<a href="sub/dir/rel2.pdf">Investor presentation nested</a>',
            url="https://ir.example/pages/index.html",
        )])
        assert {c["source_url"] for c in out["candidates"]} == {
            "https://ir.example/pages/rel.pdf",
            "https://ir.example/pages/sub/dir/rel2.pdf",
        }

    def test_same_url_multiple_anchors_dedup_to_one(self):
        out = _discover([_page(
            '<a href="/dup.pdf">Earnings call transcript first</a>'
            '<a href="/dup.pdf">Earnings call transcript second anchor</a>'
        )])
        assert len(out["candidates"]) == 1

    def test_query_and_fragment_variants_stay_distinct(self):
        out = _discover([_page(
            '<a href="/doc.pdf">Earnings call transcript plain</a>'
            '<a href="/doc.pdf?x=1">Earnings call transcript query</a>'
            '<a href="/doc.pdf#s1">Earnings call transcript fragment</a>'
        )])
        assert len(out["candidates"]) == 3

    def test_same_title_different_originals_are_kept(self):
        out = _discover([_page(
            '<a href="/a.pdf">Annual Report 2025</a>'
            '<a href="/b.pdf">Annual Report 2025</a>'
        )])
        assert len(out["candidates"]) == 2

    def test_bad_scheme_and_credentials_never_become_candidates(self):
        out = _discover([_page(
            '<a href="javascript:void(0)">Investor presentation js</a>'
            '<a href="mailto:ir@example.com">Investor presentation mail</a>'
            '<a href="ftp://ir.example/x.pdf">Investor presentation ftp</a>'
            '<a href="https://user:pass@ir.example/x.pdf">'
            "Investor presentation credentials</a>"
        )])
        assert out["candidates"] == []


class TestPagePayloadHonesty:
    def test_empty_dynamic_shell_is_partial_not_no_documents(self):
        out = _discover([_page(
            "<div id='app'></div><script src='/app.js'></script>",
            capture="shell",
        )])
        assert out["candidates"] == []
        assert out["limitations"] == ["dynamic_content_unresolved"]
        assert out["coverage_status"] == "partial"
        assert out["no_documents_claimed"] is False

    def test_static_page_with_material_links_is_checked_index_only(self):
        # A dated material link on a static page yields no limitations at all;
        # the result honestly scopes coverage to the checked index only.
        out = _discover([_page(
            '<article><time datetime="2026-09-01"></time>'
            '<a href="/deck.pdf">Investor Presentation</a></article>'
        )])
        assert out["limitations"] == []
        assert out["coverage_status"] == "checked_index_only"
        assert out["no_documents_claimed"] is False

    def test_undated_material_link_is_partial_with_unknown_date(self):
        out = _discover([_page(
            '<a href="/deck.pdf">Investor Presentation</a>'
        )])
        assert "publication_date_unknown" in out["limitations"]
        assert out["coverage_status"] == "partial"

    def test_unsupported_index_format_is_a_limitation(self):
        out = _discover([{
            "url": "https://ir.example/x",
            "original": b"binary-ish",
            "mime_type": "application/pdf",
            "capture_id": "pdf-index",
        }])
        assert "unsupported_index_format" in out["limitations"]
        assert out["receipt"]["event_ids"] == ["pdf-index"]

    def test_inline_declarative_script_is_not_dynamic_unresolved(self):
        # script WITHOUT src (e.g. JSON-LD) is a declarative block, not
        # evidence of an unresolved dynamic shell.
        out = _discover([_page(
            '<script type="application/ld+json">'
            '{"@type":"Event","name":"Investor Day"}</script>'
            '<a href="/deck.pdf">Investor Presentation</a>'
        )])
        assert "dynamic_content_unresolved" not in out["limitations"]


class TestLimitsHonesty:
    def test_item_limit_keeps_partial_and_never_claims_no_documents(self):
        out = _discover([_page(
            '<a href="/one.pdf">Earnings call one</a>'
            '<a href="/two.pdf">Earnings call two</a>'
        )], max_items=1)
        assert len(out["candidates"]) == 1
        assert "item_limit_reached" in out["limitations"]
        assert out["coverage_status"] == "partial"
        assert out["no_documents_claimed"] is False

    def test_byte_limit_stops_processing_with_honest_limitation(self):
        big = ('<html><body>'
               + '<a href="/x1.pdf">Earnings call big</a>' * 200
               + '</body></html>')
        out = _discover([
            _page(big, capture="BIG"),
            _page('<a href="/y1.pdf">Earnings call small</a>', capture="SMALL"),
        ], max_bytes=len(big.encode("utf-8")) + 10)
        assert "byte_limit_reached" in out["limitations"]
        assert all(c["capture_id"] == "BIG" for c in out["candidates"])
        assert out["coverage_status"] == "partial"

    def test_invalid_limits_are_refused(self):
        with pytest.raises(ValueError, match="invalid_discovery_limits"):
            _discover([_page('<a href="/x.pdf">Earnings call</a>')],
                      start="2026-10-21", as_of="2026-01-01")
        with pytest.raises(ValueError, match="invalid_discovery_limits"):
            _discover([_page('<a href="/x.pdf">Earnings call</a>')], max_items=31)
        with pytest.raises(ValueError, match="invalid_discovery_limits"):
            _discover([_page('<a href="/x.pdf">Earnings call</a>')], max_bytes=0)


class TestPublicCliEndToEnd:
    """Real subprocess through the public discover pages branch, offline."""

    def test_two_neutral_issuers_same_semantics_swapped(self, tmp_path):
        issuers = {
            "Neutral Instruments": _page(
                '<article><time datetime="2026-09-15"></time>'
                '<a href="/deck.pdf">Investor Presentation</a></article>'
                '<a href="/privacy.pdf">Privacy Statement</a>'
                '<a href="/t.pdf">Earnings Call Transcript</a>',
                url="https://neutral-a.example/ir",
                capture="issuer-a",
            ),
            "Neutral Materials": _page(
                '<article><time datetime="2026-09-16"></time>'
                '<a href="/deck.pdf">Investor Presentation</a></article>'
                '<a href="/privacy.pdf">Privacy Statement</a>'
                '<a href="/t.pdf">Earnings Call Transcript</a>',
                url="https://neutral-b.example/ir",
                capture="issuer-b",
            ),
        }
        repo = Path(__file__).resolve().parents[2]
        results = []
        for entity, page in (list(issuers.items()) + list(issuers.items())[::-1]):
            html_file = tmp_path / (entity.replace(" ", "-") + ".html")
            html_file.write_bytes(page["original"])
            request = {
                "schema_version": "official-discovery-request/1",
                "entity": entity,
                "start_date": "2026-01-01",
                "as_of_date": "2026-10-21",
                "max_items": 30,
                "max_bytes": 65536,
                "pages": [{
                    "input_file": str(html_file),
                    "url": page["url"],
                    "mime_type": "text/html",
                    "capture_id": page["capture_id"],
                }],
            }
            request_file = tmp_path / (entity.replace(" ", "-") + ".json")
            request_file.write_text(json.dumps(request), encoding="utf-8")
            call = subprocess.run(
                [
                    sys.executable, "-X", "utf8", "-B",
                    "-m", "company_wiki.source_catalog.official_source_cli",
                    "--operation", "discover",
                    "--request", str(request_file),
                ],
                cwd=tmp_path,
                env=_cli_env(repo),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            assert call.returncode == 0, call.stderr
            out = json.loads(call.stdout)
            assert out["schema_version"] == "official-discovery-result/1"
            assert out["receipt"]["entity"] == entity
            kinds = {c["source_url"].rsplit("/", 1)[1]:
                     c["document_kind"] for c in out["candidates"]}
            assert kinds["deck.pdf"] == "investor_relations"
            assert kinds["t.pdf"] == "investor_call_transcript"
            assert "privacy.pdf" not in kinds
            assert out["no_documents_claimed"] is False
            results.append((entity, kinds))
        # Swapping order/names preserves identical semantics per issuer.
        assert results[0][1] == results[1][1] == results[2][1] == results[3][1]

    def test_cli_local_pages_refuses_non_absolute_input(self, tmp_path):
        repo = Path(__file__).resolve().parents[2]
        html_file = tmp_path / "rel.html"
        html_file.write_bytes(b"<html><a href='/x.pdf'>Earnings call</a></html>")
        request = {
            "schema_version": "official-discovery-request/1",
            "entity": "Neutral Instruments",
            "start_date": "2026-01-01",
            "as_of_date": "2026-10-21",
            "pages": [{
                "input_file": "relative.html",
                "url": "https://ir.example/ir",
                "mime_type": "text/html",
                "capture_id": "rel",
            }],
        }
        request_file = tmp_path / "req.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        call = subprocess.run(
            [
                sys.executable, "-X", "utf8", "-B",
                "-m", "company_wiki.source_catalog.official_source_cli",
                "--operation", "discover",
                "--request", str(request_file),
            ],
            cwd=tmp_path,
            env=_cli_env(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert call.returncode == 2
        failure = json.loads(call.stderr)
        assert failure["status"] == "failed"

    def test_cli_local_truncation_stays_partial(self, tmp_path):
        repo = Path(__file__).resolve().parents[2]
        body = b'<html><a href="/one.pdf">Earnings call</a></html>'
        first = tmp_path / "one.html"
        first.write_bytes(body)
        second = tmp_path / "two.html"
        second.write_bytes(body.replace(b"one", b"two"))
        request = {
            "schema_version": "official-discovery-request/1",
            "entity": "Neutral Instruments",
            "start_date": "2026-02-01",
            "as_of_date": "2026-10-09",
            "max_bytes": len(body),
            "pages": [
                {"input_file": str(first), "url": "https://ir.example/ir",
                 "mime_type": "text/html", "capture_id": "one"},
                {"input_file": str(second), "url": "https://ir.example/ir",
                 "mime_type": "text/html", "capture_id": "two"},
            ],
        }
        request_file = tmp_path / "req.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        call = subprocess.run(
            [
                sys.executable, "-X", "utf8", "-B",
                "-m", "company_wiki.source_catalog.official_source_cli",
                "--operation", "discover",
                "--request", str(request_file),
            ],
            cwd=tmp_path,
            env=_cli_env(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert call.returncode == 0, call.stderr
        out = json.loads(call.stdout)
        assert out["coverage_status"] == "partial"
        assert "byte_limit_reached" in out["limitations"]
        assert out["no_documents_claimed"] is False