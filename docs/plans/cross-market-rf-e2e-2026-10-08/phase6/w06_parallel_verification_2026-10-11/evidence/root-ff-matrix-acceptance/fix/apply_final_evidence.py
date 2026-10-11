from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS = ROOT / 'tools/offline_contract_matrix'
p = TOOLS / 'source_proofs.py'
s = p.read_text(encoding='utf-8')
index = s.index('def main():')
s = s[:index] + '''def catalog_snapshot(reader):
    snapshot = []
    for row in reader.fetchall("SELECT d.document_id,d.document_kind,d.published_date,d.metadata_json,s.source_id,s.content_sha256,s.byte_size,s.mime_type,d.source_status FROM documents d JOIN sources s ON s.source_id=d.primary_source_id"):
        record = dict(row)
        record["metadata"] = json.loads(record.pop("metadata_json") or "{}").get("acquisition") or {}
        snapshot.append(record)
    return snapshot


''' + s[index:]
start = s.index('        snapshot = []')
end = s.index('        print(json.dumps', start)
s = s[:start] + '        snapshot = catalog_snapshot(catalog.reader)\n' + s[end:]
p.write_text(s, encoding='utf-8')
p = TOOLS / 'cli_main.py'
s = p.read_text(encoding='utf-8')
s = s.replace('    path.write_bytes(proc.stdout)', '    path.write_bytes(proc.stdout)\n    (ctx.artifacts / "fresh-source-proofs.stderr.txt").write_bytes(proc.stderr)')
s = s.replace('    findings = oracle_mod.audit(report)\n', '''    findings = oracle_mod.audit(report)
    # Unmeasured downstream evidence cannot leave a base predicate labelled PASS.
    missing = {f.case_id for f in findings if f.vector in {"source_bytes_not_verified", "missing_bound_evidence", "invalid_bound_evidence"}}
    for case in report["cases"]:
        if case["id"] in missing and case["result"] == "PASS":
            case["result"] = "PARTIAL"
            case["diagnostics"].append("fresh byte/evidence verification did not close; base predicate alone is insufficient")
    by_id = {c["id"]:c["result"] for c in report["cases"]}
    for result in results:
        result.result = by_id[result.id]
''')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'run.py'
s = p.read_text(encoding='utf-8')
s = s.replace('        self.traces.setdefault(case_id, []).append(trace)', '''        for kind in ("result", "usage"):
            receipt = self.artifacts / f"{state.get('receipt_tag')}.{kind}.json"
            if receipt.is_file():
                trace[f"et_{kind}_receipt"] = {"file":receipt.name, "sha256":sha256_file(receipt)}
        self.traces.setdefault(case_id, []).append(trace)''')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'oracle.py'
s = p.read_text(encoding='utf-8')
index = s.index('            for kind in ("filing", "transcript"):')
s = s[:index] + '''            if run.get("et_fixture_requests", 0) > 0:
                for receipt_kind in ("result", "usage"):
                    try:
                        record = run[f"et_{receipt_kind}_receipt"]
                        receipt_path = (root / record["file"]).resolve()
                        if not receipt_path.is_relative_to(root):
                            raise ValueError("ET receipt escapes attempt")
                        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != record["sha256"]:
                            raise ValueError("ET receipt bytes changed")
                    except Exception as exc:
                        findings.append(Finding("missing_bound_evidence", cid, f"ET {receipt_kind}: {exc}"))
''' + s[index:]
p.write_text(s, encoding='utf-8')
p = TOOLS / 'report.py'
s = p.read_text(encoding='utf-8').replace('RUNNER_VERSION = "1.0.0"', 'RUNNER_VERSION = "2.0.0"').replace('# PASS | FAIL | NOT_RUN', '# PASS | FAIL | PARTIAL | NOT_RUN')
p.write_text(s, encoding='utf-8')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
s = p.read_text(encoding='utf-8') + '''

def test_catalog_snapshot_uses_document_status_not_source_status():
    import sqlite3
    from source_proofs import catalog_snapshot
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("CREATE TABLE sources(source_id TEXT,content_sha256 TEXT,byte_size INTEGER,mime_type TEXT); CREATE TABLE documents(document_id TEXT,document_kind TEXT,published_date TEXT,metadata_json TEXT,primary_source_id TEXT,source_status TEXT);")
    db.execute("INSERT INTO sources VALUES (?,?,?,?)", ("source", "a"*64, 3, "application/pdf"))
    db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?)", ("document", "annual_report", "2025-01-01", '{"acquisition":{"fiscal_year":2024}}', "source", "active"))
    class Reader:
        def fetchall(self, sql): return db.execute(sql).fetchall()
    try:
        result = catalog_snapshot(Reader())
        assert result[0]["source_status"] == "active"
        assert result[0]["metadata"] == {"fiscal_year":2024}
    finally:
        db.close()
'''
p.write_text(s, encoding='utf-8')
