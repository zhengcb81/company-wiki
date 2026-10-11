from pathlib import Path
TREE=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
p=TREE/'tests/contract/test_canonical_acquisition_scope.py'
s=p.read_text(encoding='utf-8')
s+='''

def warm_legacy(lake, monkeypatch):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    # The old public writer validated and registered bytes, but had no automatic fact projection.
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer, "_record_validated_capture", lambda *args: None)
        old = ensure(svc, request())
    assert old.status.value == "imported"
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    assert AcquisitionJournal(lake.config.catalog_dir).read_all()[0].outcome == "downloaded_new"
    return svc, adapter, old


def test_real_historical_commit_request_excludes_old_period(lake, monkeypatch):
    svc, adapter, old = warm_legacy(lake, monkeypatch)
    from company_wiki.source_catalog import local_reconcile
    monkeypatch.setattr(local_reconcile,"_identity",lambda *args: pytest.fail("old trusted scope cannot relookup identity"))
    monkeypatch.setattr(local_reconcile,"restore_document_facts",lambda *args,**kw: pytest.fail("old scope cannot reread bytes"))
    newer = ensure(svc, request(year=2025))
    assert newer.status.value == "imported"
    assert adapter.fetches == 2
    assert Path(old.canonical_import.canonical_path).is_file()
    assert ensure(svc,request(year=2025)).status.value == "reused"


@pytest.mark.parametrize("tamper", ["journal_digest", "request_scope", "version_sha", "candidate_binding"])
def test_historical_origin_requires_real_attempt_request_and_version_binding(lake, monkeypatch, tamper):
    svc, adapter, old = warm_legacy(lake, monkeypatch)
    if tamper == "journal_digest":
        journal = AcquisitionJournal(lake.config.catalog_dir).path
        item = json.loads(journal.read_text(encoding="utf-8"))
        item["attempt_id"] = "urn:company-wiki:acquisition-attempt:sha256:" + "a"*64
        journal.write_text(json.dumps(item)+"\\n",encoding="utf-8")
    else:
        sidecar = Path(old.canonical_import.provenance_path)
        item = json.loads(sidecar.read_text(encoding="utf-8"))
        if tamper == "request_scope":
            item["request"]["fiscal_year"] = 2023
        elif tamper == "version_sha":
            item["receipt"]["content_sha256"] = "f"*64
        else:
            item["candidate"]["provider_document_id"] = "forged"
        sidecar.write_text(json.dumps(item),encoding="utf-8")
        lake.scan()
    newer = ensure(svc,request(year=2025))
    assert newer.status.value == "missing"
    assert adapter.fetches == 1
    assert newer.acquisition.local_preparation["blocks_download"] is True


def test_trusted_old_retirement_does_not_block_or_restore_new_period(lake):
    from company_wiki.source_catalog.store import retire_document
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    retire_document(lake.store,document_id=old.canonical_import.source_ref.document_id,
                    reason="explicit withdrawal",created_by="test")
    assert ensure(svc,request(year=2025)).status.value == "imported"
    row = lake.reader.exact_source_version(old.canonical_import.source_ref.document_id)
    assert row["source_status"] == "retired"
    assert lake.store.fetchone("SELECT count(*) n FROM document_restore_audit")["n"] == 0


def test_target_tampering_remains_unavailable_and_never_downloads(lake):
    from company_wiki.source_catalog.source_reader import SourceReadError
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    path = Path(old.canonical_import.canonical_path)
    before = path.read_bytes()
    path.write_bytes(before.replace(b"Acme",b"Else"))
    # PDF text may be compressed; use a same-size mutation guaranteed to change actual bytes.
    changed = bytearray(before)
    changed[-8] ^= 1
    path.write_bytes(changed)
    with pytest.raises(SourceReadError):
        ensure(svc,request())
    assert adapter.fetches == 1


def test_unknown_publication_for_target_is_not_a_cold_download(lake):
    adapter = PeriodAdapter()
    candidate = replace(adapter.discover(request())[0],filing_date=None)
    writer = CanonicalSourceWriter(lake)
    receipt = adapter.fetch(candidate,writer.staging_root)
    old = writer.import_staged(request(),candidate,receipt)
    result = ensure(service(lake,adapter),request())
    assert result.status.value == "missing"
    assert result.acquisition.local_preparation["blocks_download"] is True
    assert "publication_date_unknown" in result.acquisition.local_preparation["causes"]
    assert adapter.fetches == 1
    assert Path(old.canonical_path).is_file()


def test_writer_failure_rolls_back_registered_rows_and_facts_then_recovers(lake,monkeypatch):
    writer = CanonicalSourceWriter(lake)
    adapter = PeriodAdapter()
    candidate = adapter.discover(request())[0]
    receipt = adapter.fetch(candidate,writer.staging_root)
    original = writer._record_validated_capture
    with monkeypatch.context() as patch:
        patch.setattr(writer,"_record_validated_capture",lambda *args: (_ for _ in ()).throw(RuntimeError("fact transaction failed")))
        with pytest.raises(RuntimeError,match="fact transaction failed"):
            writer.import_staged(request(),candidate,receipt)
    assert lake.store.fetchone("SELECT count(*) n FROM documents")["n"] == 0
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    assert Path(receipt.staged_path).is_file()
    assert writer._record_validated_capture == original
    restored = writer.import_staged(request(),candidate,receipt)
    assert restored.source_ref.content_sha256 == receipt.content_sha256
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1


def test_same_bytes_conflicting_period_does_not_rewrite_facts_or_original(lake):
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    source = Path(old.canonical_import.canonical_path)
    sidecar = Path(old.canonical_import.provenance_path)
    before = (source.read_bytes(),sidecar.read_bytes())
    candidate = adapter.discover(request(year=2025))[0]
    writer = svc.writer
    receipt = adapter.fetch(candidate,writer.staging_root)
    Path(receipt.staged_path).write_bytes(before[0])
    receipt = replace(receipt,content_sha256=old.canonical_import.content_sha256,byte_size=len(before[0]))
    with pytest.raises(CanonicalImportError,match="canonical_scope_conflict:fiscal_year"):
        writer.import_staged(request(year=2025),candidate,receipt)
    assert (source.read_bytes(),sidecar.read_bytes()) == before
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1


def test_scan_does_not_erase_automatic_canonical_facts(lake):
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    lake.scan()
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1
    assert ensure(svc,request(year=2025)).status.value == "imported"
    assert Path(old.canonical_import.canonical_path).is_file()
'''
p.write_text(s,encoding='utf-8')
u=TREE/'tests/unit/test_canonical_scope.py'
u.write_text('''"""Source-layer scope algebra, independent from storage and identity providers."""
from dataclasses import replace
import pytest
from company_wiki.source_catalog.canonical_scope import SourceScope, ScopeRelation, scope_relatedness
from company_wiki.source_catalog.resolver import SourceRequest


def request():
    return SourceRequest(entity="Acme",market="HK",security_id="09999",
        document_kind="annual_report",fiscal_year=2024,fiscal_period="FY",as_of_date="2026-01-01")


def scope():
    req=request()
    facts={key:value for key,value in req.identity_dict().items() if value is not None}
    return SourceScope(facts,{},"source-facts")


def test_known_target_matches_and_other_year_is_irrelevant():
    assert scope_relatedness(scope(),request()) is ScopeRelation.MATCH
    assert scope_relatedness(scope(),replace(request(),fiscal_year=2025)) is ScopeRelation.NOT_RELEVANT


@pytest.mark.parametrize("field",["entity","market","security_id","document_kind","fiscal_year","fiscal_period"])
def test_missing_requested_scope_is_unknown(field):
    known=scope()
    facts={key:value for key,value in known.facts.items() if key != field}
    assert scope_relatedness(SourceScope(facts,{},known.authority),request()) is ScopeRelation.UNKNOWN


def test_identity_conflict_is_unknown_even_if_old_period():
    facts={**scope().facts,"security_id":"00001","fiscal_year":2023}
    assert scope_relatedness(SourceScope(facts,{},"source-facts"),request()) is ScopeRelation.UNKNOWN


def test_fiscal_period_and_kind_are_compared_without_calendar_guesses():
    known=SourceScope({**scope().facts,"document_kind":"quarterly_report","fiscal_period":"Q2"},{},"source-facts")
    req=replace(request(),document_kind="quarterly_report",fiscal_period="Q3")
    assert scope_relatedness(known,req) is ScopeRelation.NOT_RELEVANT
''',encoding='utf-8')
print('History/control public behavior + scope unit tests added; no manual fact assertions')
