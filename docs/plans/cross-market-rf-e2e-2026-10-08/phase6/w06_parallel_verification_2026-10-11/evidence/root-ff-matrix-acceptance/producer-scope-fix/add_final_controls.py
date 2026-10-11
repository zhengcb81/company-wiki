from pathlib import Path
TREE=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
u=TREE/'tests/unit/test_canonical_scope.py'
with u.open('a',encoding='utf-8') as f:
    f.write('''

def test_unverified_declaration_cannot_match_or_exclude_even_if_shape_complete():
    unverified=SourceScope(scope().facts,{},"unverified-declaration")
    assert scope_relatedness(unverified,request()) is ScopeRelation.UNKNOWN
    assert scope_relatedness(unverified,replace(request(),fiscal_year=2025)) is ScopeRelation.UNKNOWN
''')
p=TREE/'tests/contract/test_canonical_acquisition_scope.py'
with p.open('a',encoding='utf-8') as f:
    f.write('''

def test_public_writer_pdf_receipt_with_html_bytes_is_rejected(lake):
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    writer=CanonicalSourceWriter(lake)
    adapter=PeriodAdapter()
    candidate=adapter.discover(request())[0]
    receipt=adapter.fetch(candidate,writer.staging_root)
    html=b"<html><body>Acme report</body></html>"
    Path(receipt.staged_path).write_bytes(html)
    receipt=replace(receipt,content_sha256=hashlib.sha256(html).hexdigest(),byte_size=len(html))
    with pytest.raises(CanonicalImportError,match="PDF magic"):
        writer.import_staged(request(),candidate,receipt)
    assert lake.store.fetchone("SELECT count(*) n FROM documents")["n"] == 0


def test_failed_explicit_reacquisition_does_not_reactivate_retired_source(lake,monkeypatch):
    from company_wiki.source_catalog.store import retire_document
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    retire_document(lake.store,document_id=old.canonical_import.source_ref.document_id,
                    reason="withdrawn",created_by="test")
    candidate=adapter.discover(request())[0]
    receipt=adapter.fetch(candidate,svc.writer.staging_root)
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer,"_record_validated_capture",lambda *args: (_ for _ in ()).throw(RuntimeError("fact write failed")))
        with pytest.raises(RuntimeError,match="fact write failed"):
            svc.writer.import_staged(request(),candidate,receipt)
    assert lake.reader.exact_source_version(old.canonical_import.source_ref.document_id)["source_status"] == "retired"
''')
print('Actual unit authority/magic/retirement RED controls added before remaining fixes')
