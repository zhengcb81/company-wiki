"""Compare the same frozen selection with accepted development gold, not a holdout."""
from pathlib import Path
import gzip
import hashlib
import json
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT))
from tools.document_understanding_benchmark.evaluate import evaluate

BASE = Path(__file__).parent
output = BASE/'m2-final-real-selection/development-gold-evaluation.json'
if __name__ == '__main__':
    assert not output.exists(), 'Earlier observations remain immutable'
    rows = []
    for item in json.loads((BASE/'m2-final-real-selection/summary.json').read_text(encoding='utf-8')):
        sid = item['sample_id']
        source = BASE/'m2-final-real-selection'/f'{sid}.json.gz'
        gold = BASE/'m1-source-checkpoints/gold'/f'{sid}.json'
        data = json.loads(gzip.decompress(source.read_bytes()))
        expected = json.loads(gold.read_text(encoding='utf-8'))
        assert expected['source_sha256'] == item['source_sha256']
        result = evaluate(data['observed'], expected)
        rows.append({'sample_id': sid, 'observed_file_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                     'development_gold_sha256': hashlib.sha256(gold.read_bytes()).hexdigest(),
                     'producer_tree_sha256': item['producer_tree_sha256'],
                     'evaluation': result})
    receipt = {'scope': 'source-selection diagnostic on already-used development samples; no summary, semantic or RF acceptance',
               'evaluator': 'tools.document_understanding_benchmark.evaluate.evaluate',
               'new_provider_or_model_calls': 0, 'rows': rows}
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([{'sample': r['sample_id'], 'status': r['evaluation']['status'],
                      'metrics': r['evaluation'].get('metrics')} for r in rows], ensure_ascii=False))
