# W03 末尾公共 CLI 大节点：只读设计

日期：2026-10-11。调查基线 HEAD：`236fca0850800445bc5d89948049c38e7c80c2fb`。

**本文件是测试方案，不是已执行验收。** 调查仅读实际源码、现有测试、fixture 与归档证据；测试执行、供应商/LLM 调用、源码/tests/配置/输出/安装/Git 写入均为 0。只新增本文件。W04 工程已闭环，不再重跑它。

ROOT 独占新 `tests/integration/test_w03_selector_public_node.py`；`p7_rf_acceptance_review` 独占 W03 共享源码/helper/责任测试；默认从 0.6.0 升至 0.7.0 仍由 ROOT 后续处理。本文件不改默认，不要求增加小节点签收。

## 1. 已有可复用入口与真实覆盖

| 实际文件 / 入口 | 已有内容 | 末尾节点的使用方式 |
|---|---|---|
| `tests/support/official_json_batch_fixture.py::official_batch_state(tmp_path)` | 真 owned SourceCatalog / 原件 scan+import / projection persist；**一个 raw TXT** `call-en.txt` + 两个 issuer 的双页 native JSON；并非 raw PDF；finally 校验原件/配置并恢复 owned 目录 | 复用其隔离、scan/import、投影与 state 字段约定；要证明新业务语义，则在唯一新测试文件建立同结构的短新语义原件 fixture，不改公共 helper |
| 同文件 `official_json_loopback_model` / `model_draft(data)` | 真实生产子进程 HTTP POST 到 loopback；真实 system/user 提示；按真实 evidence id/role 构造一条短 draft；供应商替身，不是财务结论 oracle | 直接复用，保留响应/模型上限；只补对实际收到的业务片段/角色的断言 |
| 同文件 `request_for(state, endpoint, run_id, *, refresh=False, items=None)` | 公共 request2，items 指向原件/投影，真正 request validation；profile P2，model output 400 | 新语义第一轮、同 run resume、同默认新 run reuse 均用实际 helper |
| 同文件 `invoke_batch(state, request_path, run_id)` | `python -B -m company_wiki.automation.narrative_batch_cli`；fresh 进程、真实 compute/model workers；真实 AUTO/预算/发布 | 复用真实公开命令；旧版本首轮需新文件内最小工程 bootstrap，后续使用未 patch 的 fresh CLI |
| 同文件 `invoke_read(state, reference, *, issuer=None)` | 对投影先 public reference2 精确 subject+generation discovery，然后 public read；断言 stdout 真 SHA/byte_size 与 replay receipt | 每个最终 pin 真实读回，比较业务内容与实际 selector version；不得只读 metadata |
| `tests/integration/test_official_json_batch_e2e.py::test_public_mixed_batch_has_real_three_job_flow_resume_reuse_refresh_and_restores_originals` | 3 POST 首轮 / 同 run 0新增 / reuse 0新增 / refresh 3新增；每 item 真 select/summary/verify；compact terminal / 原件恢复 | 借用流程与断言 helper；**不再另跑此整条 case**，新节点去掉无关 refresh 重跑 |
| 同文件 `assert_terminal_jobs` / `items_by_key` / `assert_paid` | 真 job/attempt/terminal 结构、精确 92 tokens/111 microUSD 每 POST、三 job/项与 artifact pin | 新 mixed 直接复用，历史首轮 snapshot 后应原样保留 attempt/ledger，不重新生成 |
| `tests/integration/test_narrative_legacy_effort_history.py::test_completed_real_legacy_binding_reads_without_resigning_or_model[1/2]` | 真原 batch→worker→loopback→publish / fresh CLI readonly resume；全 SQLite dump/原件不变；但只模拟 gen1 缺 effort，首轮依当时默认 | 仅借用 `_database_dump` / `_invoke` 的做法。**不能**在 flip 后再运行它并声称产生了真实 0.6 history |
| `tests/unit/test_narrative_business_recall.py::package_fingerprint` | 完整 ordered spans + status/count/coverage/selection_limit fingerprint | 新 file 可复用同序列化；每次将 source 原 SHA 与 package fingerprint 分开记录 |
| 同文件 `test_explicit_legacy_fingerprint_survives_new_global_default` / `test_default_old_selector_keeps_entire_ordered_fingerprint` | 真 MSFT 全 TXT、旧0.6全 fingerprint；前者 monkeypatch 单模块默认，后者比较 default 与导入的当前常量 | 借用完整 fingerprint；最终必须断言实际 fresh default **0.7.0** 及具体 new anchors，不能只证明“默认=导入的默认” |
| `tests/integration/test_narrative_business_recall.py::test_full_msft_true_business_anchors_qualifiers_roles_and_replay` | 全文489 parser0.3.1 units、九个具体管理层 anchors、96限额、所有真 span 重放；显式0.6与0.7 | 新第三项复用真实原件、anchor集合与 replay；不单独重复此旧 case |
| `tests/integration/test_s5_narrative_evidence_view.py::test_real_transcript_search_lookup_and_directory_restoration` / `support.narrative_transport_fixture.published_fixture` | 真 select/summary/verify handler DAG+projector 发布；内存 `ReplayNarrativeModel`，非外部 HTTP；public evidence-search / evidence-lookup 子进程及原件/目录恢复 | 新第三项复用 `published_fixture` / `_cli` / `_request` / `_success`，搜索一个**0.7独有**业务 anchor；明确本项不是全 AUTO loopback 测试（第一项承担该证明） |

现有 `test_official_json_canonical_cli_e2e.py` 主要证实 **projection producer1.0.2** 及 page-order / issuer / replay / reuse，和 W03 selector0.7 是两个独立版本轴；不把其通过或其 parser tag 当成新业务策略生效。既有 P7 canonical producer 测试不在本节点重复。

## 2. 当前 tag 与实际政策的缺口

当前 mixed case 已断言 schema、subject/issuer、语言、management/question role、translation 排除、parent 来源集合、public replay、收费、终态压缩与复用。它**没有**断言 selected/new-policy-specific 业务内容，也没有断言 generation/bundle/实际 prompt 的 selector 一致；fixture 的“launched/qualification/shipments”旧0.6就能选中。仅把 `bundle.versions.selector` 改为0.7，即使 worker仍按0.6处理，此 case 仍可能绿。

`test_default_old_selector_keeps_entire_ordered_fingerprint` 虽然名称含 old，实际 first assertion 是 default==导入的当前常量；两者一起误设成0.6依然绿。必须增加明确未来default=0.7、default完整结果=explicit0.7、new锚点存在、explicit0.6完整旧fingerprint保持。不要为了过测试删减全文/改变预期覆盖。

旧 effort history 首轮是实际运行，但“真实”不等于“版本已固定0.6”。默认 flip 后再生成的首轮就是0.7；只删 effort 或改 DTO selector tag 不是旧政策历史。

## 3. 同一大节点仅三项

统一新文件，建议冻结如下三个 test 名称；没有共享 tests 写入，也没有新增生产许可：

### A. `test_default_07_mixed_business_content_public_flow_resume_reuse`

1. 在 owned TEMP 建立与原 helper 相同的三个 work items（raw English TXT / issuer1 Chinese JSON / issuer2 English JSON，投影共享两真 parent）。原件首次 scan/import 前即包含新语义，入库后不改写字节，也不篡改结果。
2. 短原件各保留一个经典 old-policy 业务 seed，让旧0.6也能完成摘要；另放一个新0.7 meaning 与必需限定：
   - TXT 可用 `Our service uses model routing to reduce token cost.`，跟 `But availability depends on the provider and workload mix.`；真实管理层段落、同 QA/speaker 边界。
   - Chinese native whole field 可用已正控的 `公司的产品分为控制器与执行器，控制器通过直销供给设备厂，执行器由海外渠道销售；关键部件须完成客户验证。`。
   - English native field 可用已正控的 `We serve equipment makers through direct sales while overseas distributors handle local service and qualification.`；不同 issuer 各自独立。
   - 一条 analyst/investor question 只做问题；财务-only/行政套话和 provider translation 为负控。官方 field 不伪切片、跨 record 不拼接；不能靠换公司名触发规则。
3. 先 pure explicit0.6/0.7 对同原件短语验证“0.7独有 positive”真实成立；若选定 contrast 已被0.6收录，换成已有纯责任正控的准确文本并记录原因，不能仅根据 tag 推定。
4. 用现有 `request_for` 和 `invoke_batch` 正式 fresh CLI，未来源码实际默认已为0.7，不给 request 塞不存在的 `selector_version` 字段，不在新 run 改 DTO。3真实 local POST，9成功 job，attempt一次 / compact terminal `<16384`，每项正确 raw1/projection2 pin。
5. 实际 `server.requests` 的 user evidence 必须含 new业务meaning与应保留的条件/否定，角色正确；不同 issuer / translations / question不变成company facts。全部相关 evidence IDs 与最终 bundle真实 spans对应，draft claims引用最终证据；不用 stub第一条 claim 的截断文字证明它理解了整个条件组。
6. 每一项 `invoke_read` 真公共读回：`NarrativeBundle.from_dict(wire)` 的 `versions.selector=="0.7.0"`、evidence原文/new selection reason、真 locator / parent hash / role / language保持；条件组完整、不凭coverage_complete掩盖 omission。
7. 真 `NarrativeRunStore(...).get_run(run_id).binding_json` 的 execution_versions.selector 与 thaw 后每个 generation manifest selector 也是0.7，projection `generation_sha256` 与真实元数据 manifest canonical SHA一致。metadata/tag/prompt/业务内容四处一致才能通过。
8. 同 run fresh CLI resume 后 items/budget/pins 不变、0新增 POST；另一个相同默认的 run 复用三个 pin且 run.job_ids为空、收费0。无须本节点再 refresh 全部模型来加时长；跨版本新 generation 已由B证明。
9. 原件/配置 bytes保持，owned目录恢复。loopback server errors为空。

### B. `test_completed_real_06_history_survives_fresh_07_cli_and_new_generation_does_not_reuse_it`

**首轮真实旧 producer，后续新进程真实新默认；不能事后手写 binding/job/result/ledger/visible artifact 来造历史。**

1. Owned raw TXT request2 单项，原件同时有 old seed和上面0.7-only mechanism。首旧 CLI 实际 selected0.6应排除mechanism，随后全三 job、真local POST / publish完成。记录当时 source HEAD、原件完整 SHA、actual frozen binding、generation manifest、完整 ordered old selected fingerprint、public artifact bytes/pin。
2. 首旧子进程最小 engineering bootstrap（只在 owned TEMP；不是产品新配置）：先 import `company_wiki.source_catalog.narrative_evidence as ne` 设置其实际 `NARRATIVE_SELECTOR_VERSION="0.6.0"`；再 import `company_wiki.automation.narrative_batch_request as br` 设置br的实际常量0.6；最后 `runpy.run_module("company_wiki.automation.narrative_batch_cli", run_name="__main__")` 使用原公开CLI参数。这固定**实际build-in策略及新run manifest版本**，不是只给结果retag。spawned子worker必须按保存的 frozen execution selector0.6运行，这是正在实施的 source wiring 的验收点。
3. 在首旧run结束前断言实际 old bundle `versions.selector==0.6`、old-only完整内容指纹、new mechanism不在prompt/final；freeze manifests selector0.6。全部 jobs终态/attempt已finish、对应 publication visible / outbox delivered后，读取AUTO和Catalog全SQLite dump、artifact和原件bytes/完整fee。只接受已完成历史，不以此授权 unfinished旧任务执行。
4. 然后**未patch** fresh公共CLI+fresh子进程实际新default0.7，对同old run请求resume。要求返还原items、原pin、原budget、原0.6bundle；0新增POST；原SQLite dump、binding_json、attempt、visibleartifact、费用完全相同。允许现有控制锁文件的合法生成，不误把它描述成原资料/DB变更；但不允许改old数据或伪终态。
5. 旧 pin 经未patch public `invoke_read` 仍完整重放0.6政策，并排除新mechanism。这同时证明 resolver按recorded版，不是“支持旧tag但暗用当前策略”。
6. 同原件起一个新run（真实0.7default）应生成新的0.7 generation，不能命中旧0.6 pin；真实新增1 local POST，机制进入实际 prompt/final，新pin不同；old pin继续可读。新0.7相同run再复用则0新增POST。仅比较tag/hash变化不够，两版业务差异也必须成立。
7. 不修改已归档 old history logs；不在 first manifest人造hash/旧版本field/人工许可。没有 public selector参数，bootstrap仅工程测试；原调用意图与费用预算保持。

### C. `test_full_txt_ordered_legacy_fingerprint_default_07_business_and_public_resolver`

1. 原fixture `tests/fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt` 全66324bytes，SHA `4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`；parse真实version0.3.1，489units。禁止裁掉正文、抹掉 speaker/role或修改fixture。
2. 沿现有 `package_fingerprint` 完整 serialization，在相同title=fixture.name / existing_kind=investor_call_transcript下：explicit0.6完整 ordered fingerprint为 `11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f`；explicit0.7末次纯策略归档fingerprint `c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478`，103candidate /96selected /7omitted /partial。
3. 明确实际futuredefault为0.7；不指定版的选择与explicit0.7 **完整ordered package**相同。explicit0.6仍旧fingerprint；源SHA与fingerprint不可混用，归档snapshot文件末尾换行SHA也不是packagefingerprint。
4. 复用原 full TXT 九个anchor：`what we launched with Perception`、`50% less cost`、`90% of the tasks`、`if a given model goes away`、`still continue your cyber operations`、`my math has changed`、`price performance on silicon`、`token usage`、`mix of the portfolio`。它们必须在真实management span中；0.6不得突然有new anchor。分组真实role/语言/坐标，全96span真实 `verify_transcript_evidence_spans` 重放，无failed；96上限、8units/1200chars group上限保持，partial/7omitted诚实展示。
5. 用 `published_fixture(tmp_path, source_spec={"data":raw,"title":"MSFT Q4 2026 earnings call","language":"en"})` 走实际 handler三job+projector，以内存ReplayNarrativeModel作纯外部0的运输fixture。其title与纯fingerprint的fixture.name不同，不对这条fixture强套另一个title的完整packagehash；验证新独有内容即可。
6. 真 fresh public `evidence-search` 搜索 `90% of the tasks` 或 `50% less cost`（不是旧版也能找到的Azure），对每个回传 evidence_id调用public `evidence-lookup --span-id`：lookup span与最终payload相等、locator准确、raw角色management；全locator_count/回执replay verified/真实view bytesSHA准确。误用currentpolicy重放旧ref或只支持version tag会在B暴露。
7. 只读repo fixture原SHA前后相等，ownedcopy原SHA相等、临时原件/catalog/payload全部移除，生产根与客户目录不参与。此项外部POST0；实际AUTO HTTP跨进程证明只在A/B，不夸大C为模型供应商测试。

## 4. Source owner 预期接口（已协调，尚待其实现签名冻结）

source owner给出的接线方向：`NarrativeRuntimeDependencies.selector_version: str|None=None`；`NarrativeSelectHandler` / `NarrativeVerifyHandler` 同名kw；单一 narrative_selector_binding helper resolve+partial真实pure selector；`select_verified_projection(..., selector_version=...)`；factory frozen.execution_versions.selector→runtime，resolver recorded.selector→reselect。raw与official共用，不复制两套算法。

这些接口在本设计读查时**尚未交付稳定**；ROOT等它稳定后再按实际签名实现A/B/C，不将本节当作已经存在的公开接口。旧首bootstrap0.6是新file测试工程夹具；public request不扩新许可字段，最终product默认仍ROOT独占。

## 5. 预算、范围与恢复硬约束

- 现有 request helper **max_output_tokens=400，max_seconds=40，max_tokens=200000，max_cost_usd="2"，timeout_seconds=5** 原样保持；真实 HTTP adapter / caller 不 monkeypatch reservation为更大。短fixture/response可以缩短，不能为过测试提高400、200000或费用。
- 真 caller按 `len(model.request_bytes(request))+128` 预留input，按实际model.max_output_tokens预留output；loopback固定usage73input/19output，92tokens/111microUSD每POST。usage必须不超过原reservation；检查实际run reservations与请求400一致，未知/未settled为0。
- model_draft仍取真实management/company_filing evidence并截<=180，不能为了新的断言构造太长JSON。condition保留证明在真实prompt+最终evidence，别要求旧stub反向造完整财经解释，也别修改产品claim质量cap。
- 三项一次集中执行；完整原责任包、W04public3、168、56、canonicalP7、全repo以及已有原PDF真实页实验都不重复。遇到具体失败只修真正共因和重跑失败范围；驱动错误留原log，不作为产品RED。
- Owned TEMP baseline有预置文件则逐字节保持；原件/config/fixture及SQLite实际dump保护；所有连接/子进程/loopback线程关闭后清理，Windows只读临时物仍先验证绝对 containment再清理。不能删repo或客户目录。
- 外部供应商/模型0，只有127.0.0.1 local模型替身；测试不下载、不翻译、不读密钥，不安装依赖，不写生产state；真实供应商/公司研究验收仍open。

## 6. 可执行命令与唯一建议写集

在source owner稳定、ROOT已正常完成default0.7接线后，ROOT唯一新testfile增加以上三个测试与短private helper；不改 `tests/support/official_json_batch_fixture.py` / 原测试 / 原TXT / 安装目录。

从 isolated CWP MAIN repo执行一次：

```powershell
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/integration/test_w03_selector_public_node.py
```

不是此刻可以称为已存在/已通过的testfile；ROOT创建后这就是唯一终节点3项命令。若ROOT用完整nodeID定点执行，建议名字如A/B/C所示，避免Windows超长paramid。PYTHONDONTWRITEBYTECODE=1，实际子进程用 helper.subprocess_env()固定ROOT src/scripts、strip GIT_、禁dotenv，不让child从安装旧副本漂移。

可选仅责任触及的旧入口（**不在上述3项之外再一起跑**）：full fingerprint unit、fullTXT integration、S5 realTXT、mixed-public original 或legacy-effort历史。它们可在新file设计中复用函数/helpers，不能把以前日志或直接DTO构造当作新增公共CLI验收。

原生receipt建议每test记录runid、actualHEAD、selected/version/fingerprint/anchor、实际POST增量、原binding/manifests/currentgeneration/pins、publicbyteSHA+replayreceipt、actualreservation/fees、protected before/after与TEMP恢复。只在已有ROOT owned证据节点归档一次，原日志不覆盖。不新增人工signoff JSON或小节点gate。

## 7. 调查基线 SHA（只读，不等于测试结果）

- mixed public case：`a65e9adc35178bf3d6847797cb5f2f182916e96220d464be5c03b65055f2f3a3`
- shared official fixture：`ad8ce82d1e590e2037c586983b62a57159c9d6ba5b745110a34c604bbfaf1e89`
- legacy-effort历史：`57828622b410a6e54020027085e9def2b3d61a98a52eaa74a4599e0978283412`
- pure fullTXT integration：`8f0203f0dd85eccc356d5f0098c96f08c85cf6c7fc236bd7bff2158d72a341d5`
- full fingerprint unit：`a64750af0a0c53e45b034ce7cef7054195fb52a764817e27bf3069b3864605c8`
- S5 actual fullTXT resolver test：`4db3147db9c0c3febf260bfd4f7ddd1a3555a9db61305cd2dab2f8b6e1c6e4e8`
- transport true-handler fixture：`6ceb05b743d474a21fe6abb24e58e762dde31fa0282081be7f811bfd043fbf23`

当前读查 global default仍0.6；默认flip /新file实现 /一次真正末尾运行 /正常commit及精确CI由ROOT继续。本线程写完本方案停止，不声称0.7完整主线已验收。
