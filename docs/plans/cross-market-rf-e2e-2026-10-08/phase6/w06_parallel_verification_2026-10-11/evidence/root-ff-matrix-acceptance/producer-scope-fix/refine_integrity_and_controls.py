from pathlib import Path
TREE=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
p=TREE/'src/company_wiki/source_catalog/canonical_scope.py'
s=p.read_text(encoding='utf-8')
s=s.replace('''        _validate_source_facts(facts, evidence)
        return SourceScope(facts, evidence, "source-facts")''','''        _validate_source_facts(facts, evidence)
        commit = payload.get("canonical_commit")
        if commit is not None:
            from .source_reader import SourceReadError
            valid = isinstance(commit,dict)
            if valid:
                digest = hashlib.sha256(canonical_json(
                    {k:v for k,v in commit.items() if k != "sha256"}).encode()).hexdigest()
                receipt = commit.get("receipt") or {}
                valid = (commit.get("owner") == "CanonicalSourceWriter"
                    and commit.get("schema_version") == "1.0" and commit.get("sha256") == digest
                    and isinstance(receipt,dict)
                    and (receipt.get("content_sha256"),receipt.get("byte_size"),receipt.get("mime_type"))
                        == (ref.content_sha256,ref.byte_size,ref.mime_type)
                    and all(proof.get("commit_sha256") == digest for proof in evidence.values()
                            if proof.get("extraction_method") == "provider-metadata-import/1"))
            if not valid:
                raise SourceReadError("blocked","canonical_capture_binding_conflict")
        return SourceScope(facts, evidence, "source-facts")''')
p.write_text(s,encoding='utf-8')
p=TREE/'tests/contract/test_canonical_acquisition_scope.py'
s=p.read_text(encoding='utf-8').replace('''    assert adapter.fetches == 1


def test_unknown_publication''','''    assert adapter.fetches == 1
    outcomes=[item.outcome for item in AcquisitionJournal(lake.config.catalog_dir).read_all()]
    assert outcomes == ["downloaded_new","failed"]


def test_unknown_publication''')
s+='''

def test_canonical_scope_claim_is_version_bound_and_conflict_is_named(lake):
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    # Catalog corruption is not scan metadata: it must never become exclusion proof.
    row=lake.store.fetchone("SELECT assertion_id,evidence_json FROM source_metadata_assertions")
    payload=json.loads(row["evidence_json"])
    payload["canonical_commit"]["receipt"]["byte_size"] += 1
    with lake.store.transaction() as connection:
        connection.execute("UPDATE source_metadata_assertions SET evidence_json=? WHERE assertion_id=?",
                           (json.dumps(payload),row["assertion_id"]))
    result=ensure(svc,request(year=2025))
    assert result.status.value == "missing"
    assert result.acquisition.local_preparation["reason"] == "canonical_capture_binding_conflict"
    assert adapter.fetches == 1
    assert Path(old.canonical_import.canonical_path).is_file()


def test_original_dei_evidence_is_not_overwritten_by_provider_declaration(lake):
    from company_wiki.source_catalog.assertion_service import record_source_facts,get_verified_assertion
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    ref=old.canonical_import.source_ref
    record_source_facts(lake,ref=ref,facts={"fiscal_year":2023},evidence={"fiscal_year":{
        "value":2023,"content_sha256":ref.content_sha256,"locator":"pdf:/page/1",
        "extraction_method":"original-cover/1"}})
    assertion=get_verified_assertion(lake.reader,ref.source_id,ref.content_sha256,reader="steady")
    candidate=adapter.discover(request())[0]
    receipt=adapter.fetch(candidate,svc.writer.staging_root)
    with pytest.raises(CanonicalImportError,match="canonical_scope_conflict:fiscal_year"):
        svc.writer.import_staged(request(),candidate,receipt)
    assert get_verified_assertion(lake.reader,ref.source_id,ref.content_sha256,reader="steady") == assertion
'''
# This last control uses the real source-facts API to model an original correction,
# not an eligibility assertion to force any acquisition case to pass.
p.write_text(s,encoding='utf-8')
with (TREE/'.planning/w06-cross-period-acquisition/progress.md').open('a',encoding='utf-8') as f:
    f.write('''\n### B 集中节点与具体归因\n首次范围128 PASS/6 FAIL，21.502s。历史侧车3负控需fresh catalog初扫：scanner保留先前equal-priority声明，不能误算新缺陷；按真实日志+fresh scan调整。unknown publication 原语义ambiguous拒绝合法，验零provider/无source而非强定missing。发现真实REUSED终点未实读：修为source owner verify_version在成功journal之前；发现直接writer PDF MIME未验、退役提前commit：先以3项unit/公共行为control-red固定（3FAIL1.894s），再修。初始8次跨期行为/伪scan仍保留原RED；集中失败日志未覆盖。\n修后43PASS9.151s。PDF字节先以.htm路径扫描导致source MIME猜HTML，CanonicalWriter实际SHA+PDFmagic验过后同事务更正该type observation；没有改扩展名掩盖风险，没有整套scanner sniff改造。新增HTML假PDF拒绝控与facts失败不重激活控通过。\n下一步仅最终集中受影响tests/lint与freeze；ROOT留原41matrix和非作者最终节点。\n''')
print('Version claim integrity and source-original precedence controls completed')
