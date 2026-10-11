"""Fresh installed FF process, synthetic child response, no host keys/config."""
import json
from pathlib import Path
import sys
import tempfile
import time

root = Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/'scripts'))
import transcript_tool_transport as transport
import et_v2_contract as contract
assert Path(transport.__file__).resolve() == root/'scripts/transcript_tool_transport.py'
assert Path(contract.__file__).resolve() == root/'scripts/et_v2_contract.py'
request = {'request_id':'root-w07','security_id':'MSFT','exchange':'NASDAQ',
           'fiscal_year':2026,'fiscal_quarter':4,'as_of_date':'2026-10-08'}
limits = {'timeout_seconds':10,'max_bytes':1000000,'max_cost_usd':'0.00'}
usage = {'schema_version':'earnings-retrieval-usage/1','request_id':'root-w07',
         'usage_complete':True,'usage':{'requests_used':1,'response_bytes_used':987}}
count = 0
with tempfile.TemporaryDirectory(prefix='root-w07-install-') as scratch:
    wiki = Path(scratch)
    tool = wiki/'synthetic.py'
    tool.write_text('# fixture only',encoding='utf-8')
    for cause in ['call_after_as_of','publication_after_as_of']:
        result = {'schema_version':'earnings-transcript-result/2','request_id':'root-w07',
                  'provider':'fmp','status':'not_found','fiscal_period':'2026-Q4',
                  'candidate_count':0,'error_code':cause}
        assert contract._not_found_result(result,{**request,'provider':'fmp'})['reason'] == cause
        instance = transport.EarningsTranscriptsTransport(wiki_root=wiki,transcript_tool=tool,
                                                         deadline=time.monotonic()+30)
        instance._et_environment = lambda: ({},None)
        transport._run_bounded_json = lambda *a,**k: (json.dumps(result).encode(),json.dumps(usage).encode(),0)
        public = instance._et_result(request=request,limits=limits)
        assert public['status']=='not_found' and public['reason']==cause
        assert public['provider_requests']==1 and public['provider_response_bytes']==987
        count += 1
    for raw in [b'{broken-json',b'[]',b'null']:
        instance = transport.EarningsTranscriptsTransport(wiki_root=wiki,transcript_tool=tool,
                                                         deadline=time.monotonic()+30)
        instance._et_environment = lambda: ({},None)
        transport._run_bounded_json = lambda *a,**k: (raw,json.dumps(usage).encode(),0)
        public = instance._et_result(request=request,limits=limits)
        assert public['status']=='provider_unavailable' and public['reason']=='provider_result_invalid'
        assert public['provider_requests']==1 and public['provider_response_bytes']==987
        assert public['provider_usage_complete'] is True and public['retryable'] is False
        count += 1
print(json.dumps({'physical_install':str(root),'synthetic_checks':count,'passed':True}))
