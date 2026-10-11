from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
with p.open('a', encoding='utf-8') as handle:
    handle.write('''

def test_fixture_originals_distinguish_issuer_market_and_period(tmp_path):
    import fixture_provider_adapter as adapter
    from unittest.mock import patch
    hashes = []
    with patch.object(adapter, "_state", return_value={"provider_scenario":"serve"}):
        for market, security in (("CN", "300750"), ("HK", "00700"), ("US", "AAPL")):
            payload = {"market":market, "security_id":security, "document_kind":"annual_report", "fiscal_year":2024, "fiscal_period":"FY"}
            discovered = adapter._discover(payload)["candidates"][0]
            returned = adapter._fetch(["--staging-dir", str(tmp_path / market)], discovered)
            hashes.append(returned["receipt"]["content_sha256"])
        annual = adapter._discover({"market":"CN", "security_id":"300750", "document_kind":"annual_report", "fiscal_year":2024})["candidates"][0]
        quarterly = adapter._discover({"market":"CN", "security_id":"300750", "document_kind":"quarterly_report", "fiscal_year":2024, "fiscal_period":"Q1"})["candidates"][0]
    assert len(set(hashes)) == 3, "fixture company originals collided in immutable SHA store"
    assert annual["provider_document_id"] != quarterly["provider_document_id"]
''')
