from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS = ROOT / 'tools/offline_contract_matrix'
p = TOOLS / 'fixture_provider_adapter.py'
s = p.read_text(encoding='utf-8')
s = s.replace('    candidate = {', '''    security = payload.get("security_id") or payload.get("entity") or "synthetic-issuer"
    period = payload.get("fiscal_period") or "nonperiod"
    provider_id = f"w06-{market.lower()}-{security}-{document_kind}-{fiscal_year}-{period}"
    candidate = {''')
s = s.replace('f"w06-{market.lower()}-{document_kind}-{fiscal_year}"', 'provider_id')
s = s.replace('f"w06-{market.lower()}-{fiscal_year}"', 'provider_id', 1)
s = s.replace('f"Synthetic {document_kind} {fiscal_year}",', 'f"Synthetic {market} {security} {document_kind} {fiscal_year} {period}",', 1)
s = s.replace('f"https://fixture.invalid/w06/{market.lower()}/{document_kind}/{fiscal_year}"', 'f"https://fixture.invalid/w06/{provider_id}"')
s = s.replace('    title = f"Synthetic {document_kind} {fiscal_year}"', '    title = payload.get("title") or f"Synthetic {market} {payload.get(\'security_id\', \'synthetic-issuer\')} {document_kind} {fiscal_year} {payload.get(\'fiscal_period\', \'nonperiod\')}"')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'matrix_cases.py'
s = p.read_text(encoding='utf-8')
start = s.index('    seeds = [')
end = s.index('\n\n# ── cases', start)
s = s[:start] + '''    # Establish legitimate warm state through the real acquisition writer first.
    # A scanned sidecar is intentionally a separate legacy/incomplete control.
    ctx.seed_receipts = []
    for identity in (CN, HK, US):
        for kind, period in (("annual_report", "FY"), ("semi_annual_report", "S1"), ("quarterly_report", "Q1")):
            ctx.seed_receipts.append(ctx.warm_seed(identity, kind, 2024, period))
    ctx.seed_receipts.append(ctx.warm_seed(US, "annual_report", 2025, "FY"))
    (ctx.artifacts / "warm-seed-receipts.json").write_text(json.dumps(ctx.seed_receipts, ensure_ascii=False, indent=2), encoding="utf-8")
    from dataclasses import replace
    txt_identity = replace(US, provider="fmp", source_url="https://financialmodelingprep.com/stable/earning-call-transcript?symbol=AAPL&year=2024&quarter=2")
    ctx.env.seed_original(txt_identity, document_kind="investor_call_transcript", fiscal_year=2024,
                          fiscal_period="Q2", form_type=None, published_date="2024-07-01",
                          content=b"Synthetic original-language local TXT transcript.\\n", mime_type="text/plain", filename_hint="aapl_local_2024q2")
    ctx.scan()
''' + s[end:]
s = s.replace('from fixture_builder import make_valid_pdf, CN', 'from fixture_builder import CN')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'run.py'
s = p.read_text(encoding='utf-8').replace('tag = f"seed_{identity.market.lower()}_{kind}"', 'tag = f"seed_{identity.market.lower()}_{kind}_{year}_{period}"')
s = s.replace('    FAKE_FMP_KEY,', '    FAKE_FMP_KEY as FAKE_FMP_KEY,').replace('from runtime import Deadline, run_process, synthetic_env', 'from runtime import Deadline, run_process, synthetic_env  # noqa: E402')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'extended_cases.py'
s = p.read_text(encoding='utf-8').replace('from pathlib import Path\n', '').replace('from fixture_builder import US, CN, make_valid_txt', 'from fixture_builder import US, CN')
s = s.replace('unverified_sidecar_metadata_gap', 'incomplete_sidecar_metadata_gap').replace('unverified scanned sidecar', 'incomplete scanned sidecar')
s = s.replace('    ctx.env.seed_original(CN, document_kind="annual_report"', '    original = ctx.env.seed_original(CN, document_kind="annual_report"')
s = s.replace('    ctx.scan()\n    req = _mk_filing_request(CN, document_kind="annual_report", fiscal_year=2032', '''    sidecar = original.with_name(original.name + ".source.json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata.pop("published_date")
    metadata.pop("fiscal_period")
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    ctx.scan()
    req = _mk_filing_request(CN, document_kind="annual_report", fiscal_year=2032''')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'cli_main.py'
s = p.read_text(encoding='utf-8').replace('import hashlib\n', '')
for text in ('from run import ', 'from runtime import ', 'from report import ', 'from fixture_builder import ', 'from matrix_outcome import ', 'import oracle as '):
    s = '\n'.join(line + '  # noqa: E402' if line.startswith(text) and '# noqa:' not in line else line for line in s.splitlines()) + '\n'
s = s.replace('from matrix_cases import (', 'from matrix_cases import (  # noqa: E402')
p.write_text(s, encoding='utf-8')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
s = p.read_text(encoding='utf-8').replace('import run as runner\n', 'import run as runner  # noqa: E402\n').replace('import cli_main\n', 'import cli_main  # noqa: E402\n')
p.write_text(s, encoding='utf-8')
