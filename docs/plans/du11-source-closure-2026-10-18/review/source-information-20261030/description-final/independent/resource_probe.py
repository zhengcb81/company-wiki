import sys,json
from pathlib import Path
sys.path[:0]=['src','tests']
from company_wiki.document_understanding.operating_states import assertion_roles as roles
from unit.du11_production.test_source_information_binding import session_for,unit_id,observed_use
original=roles._PROCESS_RULE_SUBJECT
class ObservedRule:
    calls=0
    chars=0
    def search(self, value, *args):
        self.calls += 1
        self.chars += len(value)
        return original.search(value,*args)
rows=[]
try:
    for n in (100,200,400):
        counter=ObservedRule()
        roles._PROCESS_RULE_SUBJECT=counter
        text='公司'+('申请中止上市审核 ' * n)+'。'
        session,budget=session_for([text])
        use=observed_use(session,unit_id(0))
        rows.append(dict(steps=n,source_chars=len(text),prefix_search_calls=counter.calls,
            prefix_search_chars=counter.chars,charged_work=budget.used,use=use))
finally:
    roles._PROCESS_RULE_SUBJECT=original
output = sys.argv[1] if len(sys.argv)>1 else 'resource-latest.json'
Path(__file__).with_name(output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=True,indent=2))
