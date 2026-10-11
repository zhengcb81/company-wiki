"""Record actual publication and a discovered code-snapshot metadata edge."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
dpath = HERE / 'dispatch-record.json'
d = json.loads(dpath.read_text(encoding='utf-8'))
central = Path(d['central_root'])
old = 'gitless依赖HEAD可能unknown，报告用manifest固定commit和实测module SHA，不伪造git证据。'
new = 'ROOT已实测：这两个code-only目录位于FF worktree内部，现有git -C会向上找到FF HEAD（2d380a05），不能把它误报为ET/CWP提交。工具依赖记录须区分实际git归属与manifest固定来源commit：只在toplevel等于传入root时用git HEAD，否则git_head为unknown/null，来源commit从本包dependency-manifest读取并与现有实际module绑定分开表示。此处是报告真实性，不增加身份许可或新门禁；集中快测加一个嵌套gitless快照反例。'
card = central / 'cards/W07-FF-PERF.md'
text = card.read_text(encoding='utf-8')
assert text.count(old) == 1
card.write_bytes(text.replace(old, new).encode('utf-8'))
generator = HERE / 'prepare_packets.py'
raw = generator.read_bytes()
assert raw.count(old.encode()) == 1
generator.write_bytes(raw.replace(old.encode(), new.encode(), 1))
ff = next(r for r in d['lanes'] if r['lane'] == 'W07-FF-PERF')
Path(ff['start_here']).write_bytes(card.read_bytes())
ff['card_sha256'] = hashlib.sha256(card.read_bytes()).hexdigest()
dpath.write_bytes((json.dumps(d, ensure_ascii=False, indent=2)+'\n').encode())
public = json.loads((central / 'dispatch.json').read_text(encoding='utf-8'))
public['lanes'] = d['lanes']
(central / 'dispatch.json').write_bytes((json.dumps(public, ensure_ascii=False, indent=2)+'\n').encode())

proof = {'schema':'w07-root-preparation-publication/1',
         'checkpoint_commit':'8e7027b898aa2a443bf042ba724a84dba7350f35',
         'remote_confirmed_by_push': True, 'normal_precommit':True,
         'pre_push':{'passed':148,'seconds':19.41,'behavior_paths':0},
         'worker_state':'READY_NOT_STARTED','real_provider_llm_calls':0,
         'followup':'FF card documents verified parent-Git metadata edge; no runtime implementation',
         'cards':[{k:r[k] for k in ('lane','card','workdir','card_sha256')} for r in d['lanes']]}
(central / 'preparation-publication.json').write_bytes((json.dumps(proof, ensure_ascii=False, indent=2)+'\n').encode())
for p in (HERE / 'verification.json', central / 'preparation-verification.json'):
    value = json.loads(p.read_text(encoding='utf-8'))
    value['ff_card_parent_git_edge_documented'] = True
    p.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())
p = HERE / 'task_plan.md'
s = p.read_text(encoding='utf-8').replace('3. 进行中：', '3. 已完成：')
s = s.replace('准备与边界核对完成；正常提交推送本批PWF/交接证据，再向用户给出三张卡与工作目录。', '三包可以现在同时开工。ROOT下一步继续W04集成与G2；各包实现尚未开始，交付后按卡集中接收。')
p.write_bytes(s.encode())
for p in (HERE / 'progress.md', central / 'progress.md'):
    with p.open('a', encoding='utf-8', newline='\n') as f:
        f.write('\n- 正常提交/推送8e7027b8，pre-push资料快测148PASS/19.41s（0行为路径），失败记录与三包已上远端。额外只读发现FF内部gitless依赖会拾取父FF HEAD，已在卡明确如实区分来源commit，未实施运行代码。所有worker仍READY_NOT_STARTED。\n')
assert hashlib.sha256(Path(ff['start_here']).read_bytes()).hexdigest() == ff['card_sha256']
print('Preparation complete; three cards ready; existing main goal remains active.')
