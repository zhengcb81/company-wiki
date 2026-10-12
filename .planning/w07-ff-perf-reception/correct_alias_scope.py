from pathlib import Path
ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
p=ROOT/'tests/test_root_w07_matrix_boundaries.py'
p.write_text(p.read_text(encoding='utf-8')+'''
def test_independent_catalog_alias_counts_are_not_byte_identity():
    target={"proofs":{},"catalog_snapshot":[]}
    for group, aliases in [("g1",1),("g2",2)]:
        proof={"verified":True,"content_sha256":"a","byte_size":3,"source_versions":1,"physical_originals":1,"original_locations":aliases}
        cli_main._merge_source_proofs(target,{"proofs":{"doc":proof},"catalog_snapshot":[]},group)
    assert target["proofs"]["doc"]["verified"] is True
    assert target["worker_groups"]["g1"]["proofs"]["doc"]["original_locations"] == 1
    assert target["worker_groups"]["g2"]["proofs"]["doc"]["original_locations"] == 2
''',encoding='utf-8')
print('Alias scope counterexample added before correcting implementation.')
