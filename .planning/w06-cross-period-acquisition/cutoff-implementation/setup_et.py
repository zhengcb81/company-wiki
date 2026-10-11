"""Authorized narrow ET setup and immutable input capture, not product implementation."""
import hashlib
import json
from pathlib import Path

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root')
EVIDENCE = Path(__file__).resolve().parent / 'et'
PLAN = TREE / '.planning/w06-cutoff-result'
EVIDENCE.mkdir(exist_ok=True)
PLAN.mkdir(parents=True, exist_ok=True)

texts = {
    'task_plan.md': '''# W06 ET cutoff result 共用修复

PLAN_ID=w06-cutoff-result；独占 TREE et-cutoff-root，base c91f5f54。
诊断依据：canonical CWP .planning/w06-cross-period-acquisition/cutoff-diagnosis/report.md。
写集仅 transcript_api.py、tests/test_transcript_api.py、tests/test_retrieval_cli_e2e.py、本文3PWF与自身handoff；FF由并行作者处理。

## 接口与函数决定

result /1、/2、discovery /1和成功goldens不变。合法目标期记录因日期过晚排除仍 not_found/candidate_count=0，optional error_code=call_after_as_of（FMP）或 publication_after_as_of（Motley）；普通空结果不填cutoff。无新增reason同义字段或日期公开字段。call_date不冒充publication，原publication unknown不变。
FMP在现有实际身份/期间/日期验证、唯一性判断后记录cutoff原因，不取消多候选歧义。Motley exact fetch/discover共用listing selection：_candidate_urls验证身份后先筛目标期，再比较published_date；返回eligible与真实excluded标记；batch listing继续复用已有_dict接口，原近期N语义不变。不追加HTTP、正文、许可或第二身份库。supervisor/tool透明传递不修改。

## 三个大节点

- A：先正规业务RED。强化已存在两个cutoff测试，加入empty/边界日/晚一天/错symbol-quarter+晚日期/多候选与Motley fetch-discover别期未来控制；CLI真实worker原因+usage/cleanup。不得缺文件/importerror冒RED。
- B：实现上述共用选择和最小诊断；一次ET+FF责任package、success golden --check、相关lint/diff。仅为具名剩余风险扩查。
- C：冻结所有本包产品SHA、已有golden和其他工作树变动；独立owned短scratch恢复。ROOT原41矩阵回放、独立验收和发布，本作者不跑41、不commit/merge/push/install。

## 资源与恢复

真实HTTP/LLM/费用0；假HTTP、合成HOME/TEMP/key、socket拒绝；不读生产config/key/raw、不复制真实配置。旧40/1及diagnosis/freeze不覆盖。短scratch仅删除自有绝对目标并确认在workspace .tmp内；已有文件/空目录保留。

Next Step：A业务RED，封存后直接B，无小节点签收。
''',
    'findings.md': '''# Findings

已有40PASS/1FAIL证明日期排除有效、import0，但ET把未来call与空列表压成同形JSON，FF又把所有非fetched泛化provider unavailable。测试只assertnot_found，缺原因传递契约。已选复用error_code有限诊断，不升级wire、不重验其他层身份。ET CodeGraph未初始化，只读诊断已按正式knownpath直接读，不初始化。
''',
    'progress.md': '''# Progress

2026-10-11 ROOT已授权永久ET/FF升级范围内的窄修复。独立ET TREE base c91f5f54 tracked clean，未复制config/keys/raw。接口和函数决定先落本3PWF。当前A待RED；FF并行作者排他处理其责任树。

Next Step：记录正规业务RED→共用实现→集中责任节点→freeze/STOP交ROOT。
''',
}
for name, text in texts.items():
    path = PLAN / name
    if path.exists():
        raise RuntimeError(f'Refusing to overwrite pre-existing plan: {path}')
    path.write_text(text, encoding='utf-8', newline='\n')

files = [TREE / name for name in ('transcript_api.py', 'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py')]
files += sorted((TREE / 'tests/golden').rglob('*'))
snapshot = []
for path in files:
    if path.is_file():
        raw = path.read_bytes()
        snapshot.append({'path': str(path.relative_to(TREE)), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
(EVIDENCE / 'before.json').write_text(json.dumps({'tree': str(TREE), 'base_head': 'c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52', 'files': snapshot, 'keys_read': 0}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'plan_written': 3, 'inputs_frozen': len(snapshot), 'product_writes': 0}))
