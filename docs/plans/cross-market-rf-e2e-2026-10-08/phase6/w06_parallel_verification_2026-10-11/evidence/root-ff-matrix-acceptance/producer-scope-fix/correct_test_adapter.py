from pathlib import Path
tree=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
p=tree/'tests/contract/test_canonical_acquisition_scope.py'
s=p.read_text(encoding='utf-8')
s=s.replace('    version = "1.0.0"\n','''    version = "1.0.0"
    supports_acquisition_budget = True

    def discover_bounded(self, request, budget):
        budget.ensure_open()
        return self.discover(request)

    def fetch_bounded(self, candidate, staging_dir, budget):
        budget.ensure_open()
        receipt = self.fetch(candidate, staging_dir)
        budget.consume_response_bytes(receipt.byte_size)
        return receipt
''',1)
s=s.replace('    lake.scan()\n    adapter = PeriodAdapter()\n    result = ensure(service(lake, adapter), request(year=2025))', '''    source.with_name(source.name + ".source.json").write_text(json.dumps({
        "company_name": "Acme", "document_kind": "annual_report", "fiscal_year": 2024,
        "market": "CN", "security_id": "600000", "fiscal_period": "FY",
    }), encoding="utf-8")
    lake.scan()
    adapter = PeriodAdapter()
    result = ensure(service(lake, adapter), request(year=2025))''')
p.write_text(s,encoding='utf-8')
print('Only own new test adapter corrected; no production edits')
