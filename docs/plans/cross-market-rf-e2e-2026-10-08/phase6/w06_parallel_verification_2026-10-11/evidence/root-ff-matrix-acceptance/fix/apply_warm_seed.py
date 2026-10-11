from pathlib import Path
TOOLS = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root/tools/offline_contract_matrix')
p = TOOLS / 'run.py'
s = p.read_text(encoding='utf-8')
index = s.index('    # -- FF public CLI')
s = s[:index] + '''    def warm_seed(self, identity: Identity, kind: str, year: int, period: str) -> dict:
        tag = f"seed_{identity.market.lower()}_{kind}"
        self.write_state(scenario="success", provider_scenario="serve", calls_file=self.env.calls_file(tag), receipt_tag=tag)
        cmd = [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli",
               "--config", str(self.env.wiki / "config/source_catalog.yaml"), "ensure",
               "--entity", identity.canonical_name, "--market", identity.market, "--security-id", identity.security_id,
               "--document-kind", kind, "--fiscal-year", str(year), "--fiscal-period", period,
               "--as-of-date", "2026-12-31", "--source-ref-v2", "--allow-download",
               "--acquisition-config", str(self.env.wiki / "config/source_acquisition.yaml"),
               "--max-download-bytes", "2000000", "--max-download-seconds", "10", "--max-download-cost-usd", "0"]
        proc = run_process(cmd, env=self.child_env(), cwd=self.scratch, deadline=self.batch_deadline)
        path = self.artifacts / f"{tag}.response.json"
        path.write_bytes(proc.stdout)
        (self.artifacts / f"{tag}.stderr.txt").write_bytes(proc.stderr)
        payload = json.loads(proc.stdout)
        return {"command":cmd, "exit_code":proc.returncode, "response":payload,
                "response_ref":path.name, "response_sha256":sha256_file(path), "scope":"fixture-only initial CWP acquisition/import; separate from local reuse counters"}

''' + s[index:]
p.write_text(s, encoding='utf-8')
p = TOOLS / 'matrix_cases.py'
s = p.read_text(encoding='utf-8')
start = s.index('    seeds = [')
end = s.index('    for identity, kind, year', start)
s = s[:start] + '    seeds = [(US, "annual_report", 2025, "FY", "FY", "apple_2025_annual")]\n' + s[end:]
s = s.replace('    ctx.scan()\n', '''    ctx.scan()
    ctx.seed_receipts = []
    for identity in (CN, HK, US):
        for kind, period in (("annual_report", "FY"), ("semi_annual_report", "S1"), ("quarterly_report", "Q1")):
            ctx.seed_receipts.append(ctx.warm_seed(identity, kind, 2024, period))
    (ctx.artifacts / "warm-seed-receipts.json").write_text(json.dumps(ctx.seed_receipts, ensure_ascii=False, indent=2), encoding="utf-8")
''', 1)
s = s.replace('t.get("status") == "upstream_error" and t.get("reason") == "provider_identity_or_host"', 't.get("status") in {"upstream_error", "provider_unavailable"} and t.get("reason") == "provider_identity_or_host"')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'extended_cases.py'
s = p.read_text(encoding='utf-8')
index = s.index('def additional_cases():')
s = s[:index] + '''def case_unverified_sidecar(ctx):
    cid = "unverified_sidecar_metadata_gap"
    from fixture_builder import make_valid_pdf
    ctx.env.seed_original(CN, document_kind="annual_report", fiscal_year=2032, fiscal_period="FY", form_type=None,
                          published_date="2033-03-14", content=make_valid_pdf("Synthetic CATL 300750 annual 2032"),
                          mime_type="application/pdf", filename_hint="unverified_catl_2032")
    ctx.scan()
    req = _mk_filing_request(CN, document_kind="annual_report", fiscal_year=2032, fiscal_period="FY", intent="reuse_only", as_of_date="2033-12-31")
    run = ctx.run_ff(req, case_id=cid)
    f = run["response"].get("filing") or {}
    ok = run["response"].get("status") != "source_candidate" and f.get("upstream_cause", {}).get("code") == "local_metadata_gap"
    return CaseResult(id=cid, title="unverified scanned sidecar is a diagnosed local metadata gap", declared_layer="ff+cwp", result="PASS" if ok else "FAIL",
        scope="explicit legacy/unverified fixture; not interchangeable with importer-verified warm state", expected={"diagnosed_gap":True},
        actual={"response":run["response"]}, request_ref=run["request_ref"], response_ref=run["response_ref"])


''' + s[index:]
s = s.replace('("original_max_bytes", lambda c: filing_negative(c, "oversize", "original_max_bytes")),', '("original_max_bytes", lambda c: filing_negative(c, "oversize", "original_max_bytes")),\n        ("unverified_sidecar_metadata_gap", case_unverified_sidecar),')
p.write_text(s, encoding='utf-8')
