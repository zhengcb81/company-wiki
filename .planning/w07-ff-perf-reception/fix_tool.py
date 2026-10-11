from pathlib import Path

ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
def replace(relative,before,after):
    p=ROOT/relative
    text=p.read_text(encoding='utf-8')
    assert before in text,(relative,before[:80])
    p.write_text(text.replace(before,after,1),encoding='utf-8')

# Fix ROOT fixture construction before the next behavioral RED.
replace('tests/test_root_w07_matrix_boundaries.py','from fixture_builder import Identity','')
replace('tests/test_root_w07_matrix_boundaries.py','Identity("US","Apple Inc.","US:AAPL")','SimpleNamespace(market="US",canonical_name="Apple Inc.",security_id="US:AAPL")')
print('ROOT fixture corrected; run behavioral RED before applying fixes.')
