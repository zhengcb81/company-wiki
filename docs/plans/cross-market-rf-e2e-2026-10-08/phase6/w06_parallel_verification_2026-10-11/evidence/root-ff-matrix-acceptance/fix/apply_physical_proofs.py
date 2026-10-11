from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS = ROOT / 'tools/offline_contract_matrix'
p = TOOLS / 'source_proofs.py'
s = p.read_text(encoding='utf-8')
s = s.replace('def main():', '''def physical_originals(locations):
    identities = set()
    for row in locations:
        path = Path(row["absolute_path"])
        stat = path.stat()
        identities.add((stat.st_dev, stat.st_ino) if stat.st_ino else str(path.resolve()).casefold())
    return len(identities)


def main():''')
s = s.replace('                source_content = None', '''                location_rows = catalog.reader.fetchall("SELECT root_id, relative_path, absolute_path FROM locations WHERE source_id=? AND role='original_primary' AND location_status='active'", (ref.source_id,))
                physical_count = physical_originals(location_rows)
                source_content = None''')
s = s.replace('"source_versions": versions, "original_locations": locations,', '"source_versions": versions, "original_locations": locations, "physical_originals":physical_count,\n                    "location_records":[dict(x) for x in location_rows],')
s = s.replace('"metadata": json.loads(row["metadata_json"] or "{}"),', '"metadata": (json.loads(row["metadata_json"] or "{}").get("acquisition") or {}),')
s = s.replace('        print(json.dumps({"schema_version": "w06-fresh-source-proofs/1", "proofs": result}', '''        snapshot = []
        for row in catalog.reader.fetchall("SELECT d.document_id,d.document_kind,d.published_date,d.metadata_json,s.source_id,s.content_sha256,s.byte_size,s.mime_type,s.source_status FROM documents d JOIN sources s ON s.source_id=d.primary_source_id"):
            record = dict(row)
            record["metadata"] = json.loads(record.pop("metadata_json") or "{}").get("acquisition") or {}
            snapshot.append(record)
        print(json.dumps({"schema_version": "w06-fresh-source-proofs/1", "proofs": result, "catalog_snapshot":snapshot}''')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'oracle.py'
s = p.read_text(encoding='utf-8').replace('proof.get("original_locations") != 1', 'proof.get("physical_originals") != 1')
p.write_text(s, encoding='utf-8')
p = TOOLS / 'matrix_cases.py'
s = p.read_text(encoding='utf-8')
s = s.replace('    ok = Outcome.observe(t).rejected_quarter()', '''    from extended_cases import _receipt
    et_result = _receipt(ctx, case_id) if hasattr(ctx, "artifacts") else {}
    explicit_provenance = (t.get("status") == "upstream_error" and t.get("reason") == "provider_identity_or_host" and
                           et_result.get("status") == "provenance_rejected" and et_result.get("error_code") == "provider_identity_or_host" and ctx.fixture_requests(calls) == 1)
    ok = Outcome.observe(t).rejected_quarter() or explicit_provenance''')
p.write_text(s, encoding='utf-8')
p = ROOT / 'tests/test_w06_matrix_runtime.py'
s = p.read_text(encoding='utf-8') + '''

def test_physical_original_count_separates_alias_rows_from_copies(tmp_path):
    from source_proofs import physical_originals
    one = tmp_path / "one.pdf"
    two = tmp_path / "two.pdf"
    one.write_bytes(b"synthetic-original")
    two.write_bytes(b"synthetic-original")
    assert physical_originals([{"absolute_path":str(one)}, {"absolute_path":str(one.parent / "." / one.name)}]) == 1
    assert physical_originals([{"absolute_path":str(one)}, {"absolute_path":str(two)}]) == 2
'''
p.write_text(s, encoding='utf-8')
