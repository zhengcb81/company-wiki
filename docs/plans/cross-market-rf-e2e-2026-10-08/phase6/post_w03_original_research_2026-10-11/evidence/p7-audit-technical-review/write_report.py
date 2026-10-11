import datetime as dt
import hashlib
import json
from pathlib import Path
OUT = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\p7\audit")
BASE = "78c2b1089200937a9371548f3f8a212c501fdfcd"
DELIVERY = "18a52f16e605e2ca33bcf5dff5b7d4176077aa1c"
DOCS = "40b38103f4b96860617e9bae98ec5b4ea8ee08d5"
probes = json.loads((OUT/'probe-results.json').read_text(encoding='utf-8'))
scripts = SOURCE/'skills'/'revenue-forecast-audit'/'scripts'
refs = SOURCE/'skills'/'revenue-forecast-audit'/'references'
def ref(path,line,detail):
    return {'artifact':str(path),'line':line,'detail':detail}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
findings = [
{'issue_id':'TECH-P7-001','severity':'P1','category':'code','root_cause_id':'P7-REQUEST-DOMAIN',
 'summary':'Audit money-cap domain rejects explicit zero, incompatible with native free acquisition budgets.',
 'actual':'P01 rejects max_cost_usd=0.00 before request construction; CWP native budget constructor accepts 0.00 without provider invocation. P02/P03 reject negative and NaN in both.',
 'owner':'P7 execution_request.cap_value; FF/CWP remain owners of their native request validity and live cost enforcement.',
 'references':[ref(scripts/'execution_request.py',36,'money cap parser'),ref(scripts/'execution_request.py',44,'finite and number<=0 rejection'),ref(Path(r'C:\Users\郑曾波\Projects\company-wiki\src\company_wiki\source_catalog\download_budget.py'),15,'native finite nonnegative Decimal helper'),ref(Path(r'C:\Users\郑曾波\Projects\filing-fetch\scripts\filing_contracts.py'),319,'native acquisition_limits fee syntax permits 0 and 0.00')],
 'evidence':{'artifact':str(OUT/'probe-results.json'),'locator':'probes[P01..P03]'},
 'minimum_correction':'For max_cost_usd only, permit finite nonnegative values (number < 0 rejected). Preserve bool rejection, non-finite rejection, positive integer byte/token/time rules, and min(scope,deploy). Use native accepted money syntax in the native owner adapter; do not coerce unknown/null into zero.',
 'tdd':['RED: explicit scope/deploy/template 0.00 free request currently rejected; GREEN must preserve exact zero in effective scope.','Negative and NaN remain rejected; native pure constructor round-trip confirms compatibility. No provider claim.']},
{'issue_id':'TECH-P7-002','severity':'P1','category':'observability','root_cause_id':'P7-REQUEST-BINDING',
 'summary':'The helper checks outer metadata but independently serializes native JSON, so effective_scope can describe a different request.',
 'actual':'P04 accepts outer profile P1 / max_response_bytes=100 / max_tokens=100 / cost=1.00 while request bytes contain P2 / 1000 / 1000 / 10.00; diagnostics=[]; P05 faithfully carries those bytes to local fake child with three equal SHAs.',
 'owner':'Native request producer/integration adapter plus P7 build_execution_request binding. Native FF/CWP retain provider, identity, byte/time/fee enforcement responsibility.',
 'references':[ref(scripts/'execution_request.py',152,'outer effective scope'),ref(scripts/'execution_request.py',157,'only template.limits is checked'),ref(scripts/'execution_request.py',170,'independent template.request business object'),ref(scripts/'execution_request.py',190,'recorded effective_scope'),ref(refs/'workflow.md',51,'scope-to-real-request binding claim')],
 'evidence':{'artifact':str(OUT/'probe-results.json'),'locator':'probes[P04,P05]'},
 'minimum_correction':'Bind only resource/profile fields that the actual named native contract owns. Produce them once in the native request/config/argv producer; derive the audit observation from those actual values, compare against min(scope,deploy), and name discrepancies. For FF map acquisition_limits.max_bytes/timeout_seconds/max_cost_usd through existing contracts; do not recursively interpret arbitrary RF JSON numbers as controls. For a JSON contract with no resource controls, record declared versus observed/unknown binding scope without claiming native enforcement. Preserve supplied business fields and current opt-in diagnostics.',
 'tdd':['RED: actual owner-shaped native request/config/argv contradicts outer limits or profile; record must expose/reject local binding invalidity under the existing contract rather than silently claim binding.','GREEN: zero-fee FF shape and cap-at/below-boundary match recorded actual controls, and ordinary RF forecast JSON lacking such controls remains compatible.','Generic P2 field in this probe is not evidence that any deployed native endpoint accepts it; a native owner adapter fixture is required for production integration.']},
{'issue_id':'TECH-P7-003','severity':'P2','category':'observability','root_cause_id':'P7-REQUEST-BINDING',
 'summary':'P7 composition does not pass the builder digest into prelaunch freeze, so the documented build==capture identity is an assumption.',
 'actual':'P06 changes only the reviewer-owned generated request after build. Capture freezes changed current bytes and child consumes them, with input_complete/output_complete=true and exit 0; builder SHA differs from frozen==child SHA. Existing W11 behavior is internally correct for freezing current inputs.',
 'owner':'P7 builder→capture integration composer. W11 owns current-byte history and consumed-copy integrity, not a builder digest it never receives.',
 'references':[ref(scripts/'execution_request.py',189,'positions recorded but no digest handoff argument'),ref(scripts/'audit_run.py',461,'freeze function has no expected digest input'),ref(scripts/'audit_run.py',513,'hash of current source bytes'),ref(scripts/'audit_run.py',598,'capture invokes current-input freeze'),ref(scripts/'audit_run.py',618,'child launch after freeze'),ref(refs/'executor.md',45,'documented same-SHA requirement')],
 'evidence':{'artifact':str(OUT/'probe-results.json'),'locator':'probes[P06]'},
 'minimum_correction':'In the opt-in P7 composition path carry the builder expected digest to the frozen-byte comparison before child launch. Compare the exact retained snapshot SHA, rather than adding a separate pre-read with a race. An optional expected-digest parameter/hook on the existing freeze boundary is one small compatible implementation; legacy capture with no expectation keeps current semantics. Digest mismatch is local invalid input with a concrete record, not a human signature or global publication gate. Keep post-call consumed integrity and original failure precedence.',
 'tdd':['RED/GREEN: builder artifact mutation before capture gives a named mismatch and child_started=false in the P7 opt-in path.','Unchanged file produces builder==frozen==consumed SHA; legacy capture without a builder record still freezes current bytes; 59 old assertions remain unchanged.']}
]
report = {
'schema_version':'p7-audit-technical-reception/1','observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),
'kind':'independent engineering read-only reception; not company four-role review',
'identity':{'worktree':str(SOURCE),'base_head':BASE,'delivery_head':DELIVERY,'docs_head':DOCS,
'handoff_sha256':sha(SOURCE/'.planning'/'p7-audit-execution-review'/'HANDOFF.md'),
'canonical_install_state':'Assigned canonical audit remains base; no install/runtime switch performed.'},
'acceptance':{'state':'accept_foundation_with_material_request_binding_defects',
'accepted':['Opt-in five-helper/nine-reference engineering closure, bounded new attempt outputs and diagnostic/non-evaluated APIs.','Existing W11 audit_run/numeric_audit and all old test modules/fixtures are byte-compatible by clean worktree plus base diff.','Supplied 96-test log and supplied synthetic E2E log are hash-verified historical evidence; unchanged local chain independently confirmed frozen==consumed identity.'],
'not_accepted':['An unconditional claim that effective_scope describes actual native request controls.','A claim that capture enforces builder identity across pre-capture modification without expected SHA handoff.','A positive-only fee cap as compatible with native free acquisition budgets.'],
'not_claimed':['Live native/provider/model budget enforcement, provider overspend, real company RF completion, investment quality, CI success.']},
'materials':{'read':['HANDOFF.md','handoff.json','task_plan.md','findings.md','progress.md',
'scripts/audit_contracts.py','scripts/execution_request.py','scripts/document_status_join.py',
'scripts/authoring_provenance.py','scripts/review_protocol.py',
'references/workflow.md','references/executor.md','references/artifact-contract.md','references/remediation.md',
'references/rf-checkpoints.md','references/review-storage.md','references/review-fetch.md',
'references/review-process.md','references/review-analyst.md','tests/test_scope_request_binding.py',
'supplied fake_native_child.py','supplied E2E driver','supplied 96-test log','ROOT request-contract-diagnostics.json'],
'codegraph':'Uninitialized on assigned audit worktree; no init under read-only scope. Main CWP/FF native contract context used.',
'git':'Default sandbox status emitted must be run in a work tree. Authorized require_escalated read-only Git status clean, no config/environment alteration.',
'old_surface':{'audit_run_and_numeric_audit_base_diff':'empty','old_tests_base_diff':'empty',
'old_test_modules':['test_audit_run.py','test_legacy_native_events.py','test_numeric_audit.py','test_precall_input_history.py','test_sync_skill.py'],
'old_test_count':59,'full_suite_rerun':False},
'logs':[{'artifact':str(SOURCE/'.planning'/'p7-audit-execution-review'/'evidence'/'m3-final-20261010T234447Z-c1b05984'/'green.log'),'sha256':'3a88257e4669c90601bc368972d7d01fe7ef336a44a602da468df98c165cfeb0','observed_tail':'Ran 96 tests in 37.167s; OK; SUITE_EXIT=0'},
{'artifact':str(SOURCE/'.planning'/'p7-audit-execution-review'/'evidence'/'m3-e2e-20261010T221838Z-cc073b16'/'e2e.log'),'sha256':'26bc6547eff65072fe065cdff98c967721b428b29787541af695b2939ffa5e50'}]},
'public_interfaces':[{'helper':'audit_contracts','api':['new_attempt_dir','write_attempt','cli_main'],'contract':'fresh bounded evidence attempts; W11 redactor reused'},
{'helper':'execution_request','api':['build_execution_request -> bytes,record','build CLI'],'contract':'outer min scope/deploy and byte/hash/argv record; defects above'},
{'helper':'document_status_join','api':['join_status_index','join CLI'],'contract':'transport/business distinct; each result located; once-per-call costs; unknown null; diagnostic index'},
{'helper':'authoring_provenance','api':['check_provenance','check CLI'],'contract':'consumed fragment comparison; quote/actor/date/period diagnostics; not upstream truth'},
{'helper':'review_protocol','api':['aggregate_findings','check_coverage','coverage CLI'],'contract':'4-tuple issue keys; numeric/crosscheck/scope gaps; not_evaluated; v1/old runs read-only'}],
'probe_results':{'artifact':str(OUT/'probe-results.json'),'sha256':sha(OUT/'probe-results.json'),
'count':6,'cases':[{'id':r['probe_id'],'name':r['name']} for r in probes['probes']],
'native_executed':'CWP pure budget constructor only; supplied local fake child only; no native acquisition',
'first_attempt_failure':'Windows path length at deep assigned evidence root; first failed driver/local attempt preserved; same semantic cases retried using extended-length paths.'},
'findings':findings,
'expert_disposition':'TECH-P7-001/002/003 and handoff W01–W08 are inputs to the current root-cause expert adjudication. Reconcile existing owner plans and overlap before any implementation. No second remediation workflow created. RC-08 diagnostic/global-gate tension does not justify a new gate.',
'compatibility_and_boundaries':['Keep diagnostic not_evaluated status, SourceRef/acquisition-observation ownership, v1/old reports, old assertions and existing unknown/null semantics.','Zero fee is a configured resource cap; it does not authorize paid work. Native owners remain responsible for real pre/while-read caps and cost evidence.','No per-document permission JSON, human signature, new provider/source inventory, duplicate identity verification, cross-repository file writes or blanket JSON permission schema.','Do not install/switch during current company four-role review. Later integration belongs to MAIN and its existing owner plan.'],
'remote':'no_remote','ci':'not_triggered','costs':{'get_calls':0,'provider_calls':0,'project_model_calls':0,'new_cost_usd':'0.00'},
'changes':{'source':False,'original_tests':False,'installation':False,'production_config':False,'sealed_company_run':False,'output_scope':str(OUT)},
'stop':'Review completed; report is not implementation authorization or quality approval.'}
(OUT/'technical-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md = r'''# P7-AUDIT 独立技术只读接收

可接收工程基础闭包；交付中的请求绑定合同仍有三处材料缺陷，暂不能据此声称“真实请求符合 effective_scope，且 child 必然消费 builder 记录的同 SHA”。本次不是公司四审，不作投资研究质量判断。

交付身份已核对：docs HEAD `40b38103f4b96860617e9bae98ec5b4ea8ee08d5`，source `18a52f16e605e2ca33bcf5dff5b7d4176077aa1c`，base `78c2b1089200937a9371548f3f8a212c501fdfcd`。HANDOFF SHA 为 `946afe381eced7697e849ee535480017c48d791b68bce58fa9d1fa1aaaa12f2d`。

亲核 Git 工作树 clean；`audit_run.py`、`numeric_audit.py`、五份旧测试模块（59 tests）及旧 fixtures 与 base 无差异。已读 HANDOFF/json/PWF、五个 helpers、九个 references、原 E2E driver/fixture 与 ROOT 两项诊断。原 96-test 完整通过日志 SHA `3a88257e4669c90601bc368972d7d01fe7ef336a44a602da468df98c165cfeb0` 与 E2E 日志 SHA `26bc6547eff65072fe065cdff98c967721b428b29787541af695b2939ffa5e50` 一致，本次未重跑整 suite。CodeGraph 在 audit 工作树未初始化；只读范围内未 init。默认沙箱 Git status 的“must be run in a work tree”由已授权 escalated 只读命令解决，未改 Git 配置或其他 owner 环境。

六个真实微型 probe 的完整命令、exit、stdout/stderr、SHA 与产物在 [probe-results.json](probe-results.json)，计划先存于 [probe-plan.md](probe-plan.md)。前三个仅调用 pure helper 与 native CWP 纯 budget 构造；后三个是 pure 序列化与本地 supplied fake child，不调用 native acquisition。

| Probe | 实际观察 | 能证明的范围 |
|---|---|---|
| P01 零费用 | helper 拒绝 `0.00`；CWP budget 构造接受 | 零费用资源合同不兼容，未执行 provider |
| P02 负数 | helper 与 native 构造都拒绝 `-0.01` | 负数拒绝正确 |
| P03 NaN | helper 与 native 构造都拒绝 `NaN` | 非有限费用拒绝正确 |
| P04 外层/正文 | 外层 P1/100/1.00，正文 P2/1000/10.00，accepted、diagnostics=[] | helper 记录与请求正文能错绑 |
| P05 未改请求 | builder=frozen=child，SHA `ee373648…`，正文仍矛盾 | 真实本地冻结链忠实传递错绑字节；不能证明 provider 超支 |
| P06 build 后改自有请求 | builder `ee373648…`，frozen=child `fcb8c8f3…`；input/output complete=true，exit0 | P7 composition 未传 builder expected SHA；W11 对当前字节的冻结记录本身正确 |

首轮 P05 在极深证据路径遇 Windows 路径长度错误；失败 driver 与自有 attempt 留存，改用 Windows 扩展路径表示重试相同六个语义案例，未追加其他 probe。

## 缺陷与最小责任修正

**TECH-P7-001 / P1：费用域不兼容。** `execution_request.py:36,44` 对 money 使用 `number <= 0`。CWP `src/company_wiki/source_catalog/download_budget.py:15–24` 的域为 finite nonnegative；FF `scripts/filing_contracts.py:319–323` 允许 `0`/`0.00`。责任在 P7 cap parser。仅 money 改为有限且非负，负/NaN/bool仍拒绝，byte/token/time正整数规则与 min(scope,deploy)保持。未知/null不转零。零 cap 与免费 native 操作兼容，不证明 native 已执行或已证明费用。

**TECH-P7-002 / P1：外层元数据未与 native 请求绑定。** `execution_request.py:152–168` 校验外层 profile/limits，`:170–174` 独立序列化 `template.request`，`:190–194` 却记录前者。P04/P05 确认这两部分可矛盾。责任是 native 请求生产者/接线 adapter 与 P7 builder 的合同衔接，真实资源 enforcement 继续属于 FF/CWP/native owner。最小修正是由实际 native 合同生成一次控制字段，再从真正送出的 request/config/argv 取得观察值并比较边界。例如 FF 明确映射现有 `acquisition_limits.max_bytes/timeout_seconds/max_cost_usd`，不能递归扫所有 RF JSON 把业务数值当资源字段。没有资源控制字段的 native JSON 记录 declared 与 observed/unknown，不虚称已绑定/已执行 enforcement。这里的 generic P2 字段没有证明任何实际 provider endpoint 会接受它。

**TECH-P7-003 / P2：builder 身份没有进入 prelaunch freeze。** `audit_run.py:461` 和 `:598` 无 expected digest 输入；`:513` hash 当前输入，`:618` 启动 child。这符合 W11 原“冻结当前输入”的语义，缺口在 P7 composition 对 `executor.md:45` / `workflow.md:51` 的同 SHA 保证。修正应在 P7 opt-in 接线携带 builder expected digest，并在 child 启动前比较已冻结的 exact bytes SHA；单独先读一次 hash 会留下竞态。可给现有冻结边界一个可选 expected-digest 参数/hook，旧 capture 不传时语义保持。局部输入不一致记具名失败和 child_started=false；这是本调用输入合同，不能变成人签或全局发布门。

## 可以接收的基础闭包与验证建议

五 helpers 的 API 清楚：fresh attempt/脱敏公共辅助、`build_execution_request`、`join_status_index`、`check_provenance`、`aggregate_findings/check_coverage`；join/provenance/coverage仍是小索引与诊断，quality_status=`not_evaluated`。transport/business 分列、call费用一次计数、unknown/null、原片段quote/actor/date诊断、四元组 issue key、旧 report v1/旧 runs 只读兼容可作为工程基础接收。详列接口与引用在 [technical-review.json](technical-review.json)。

现有测试覆盖外层放大、负控与未改请求的正向 SHA 链，但没有封住这次发现的三个合同缺口。接入当前 expert 根因裁决时，先补有意义 RED：零费用自由操作、实际 native owner 形状的正文/外层矛盾、build 后修改导致 prelaunch mismatch；GREEN 验证对齐/小于边界、负/NaN、旧无期待 digest 的 capture、无控制字段的正常 RF JSON兼容。保留59旧断言，不新增全部JSON许可schema，不把 helper 测试通过写成 live cap enforcement。

W01–W08 与这三项发现交本次根因 expert 合并已有 owner 计划裁决，不另起第二整改流程。RC-08 的“诊断/阻断”张力不构成新增全局门依据。native owner继续负责一次身份解析、来源/原件与真实资源上限；本次没有二次身份或跨仓文件写入。当前公司四审期间未切安装 runtime，canonical audit仍沿既定 base。

状态如实为 `no_remote` / `not_triggered`；本次 GET=0、provider=0、project model=0、新增费用=0.00。source、原测试、配置、安装、sealed company run与共享PWF未修改。只写本接收证据目录。接收已完成，停止在报告交付。
'''
(OUT/'TECHNICAL_REVIEW.md').write_text(md+'\n',encoding='utf-8')
for filename in ['technical-review.json','TECHNICAL_REVIEW.md']:
    print(filename+' SHA256 '+sha(OUT/filename))