# MAIN共同接口冻结：真实来源与同一AUTO身份

## 范围和当前进展

这是实现依据，不是新许可或逐节点签收。基础节点已164 PASS/41.39秒、changed Ruff与neutralcore mypy通过，独立只读9探针通过。只覆盖public official入口和compact identity；AUTO尚未贯通。三个P7外包已由用户发出，各自源码写集继续排他。原157问题及旧研究封存不改。

## 统一身份与来源责任

中立`company_wiki.narrative_subject.NarrativeSubject`归MAIN，不import automation。raw item_key=document_id、subjectSHA=原件SHA；official_json item_key=projection_id、subjectSHA=投影SHA。to_dict仅kind/item_key/subjectSHA/realparents，以及投影issuer/as-of/adapter/coverage，不含records。缓存标量、nested input/output隔离。它只表达内部身份，不证明当前来源真实。实际原件SourceRef2.0不改变。

当前source-projection-ref/1是严格**9键全量DTO**，并非compact指针。保留原义，事件/request不用这个名字冒充compact引用。SourceProjection构造默认1.0.1先接；P7-CWP最终提供opt-in1.0.2及旧回放，MAIN不改叶文件。

VerifiedProjectionView由MAIN automation/narrative_official_json.py组合load_projection+build_projection_export。后一调用已验全部母页并重建语义，不能再串replay双重解析。每次source操作使用同一深隔离view；后续publish/publicread在自己的source边界重新验当前页集合，早期view不是永久许可。无原语言可用字段时language=None、模型0调用，不能猜默认语言。

原source span保真实parentSHA/sourceID/pointer/token locator；薄adapter逐field增source_role/language/group，originalrole保留。translation不进入独立原语言证据；question不能支持公司陈述；unknown speaker不捏造姓名。group=(projectionID,parentSHA,recordpointer)，不按邻接把问答当连续单角色quote。coverage按pagination_complete/page_envelope_complete真实值，不借DocumentStructure默认linecount伪完整。

## 存储、复用和版本

同一catalog narrative_artifact_versions表复用；anchor只是真实首parent外键。metadata.subject_binding保存compact身份，所有旧rawlatest/current/generation查询排除official_json，防止共享母页A/B污染旧结果。new exact subject+SHA+generation查找；source store校验全部parents的currentactiveprimary关系和catalogSHA，实际字节/投影语义归sourceport，不重复全文件解析。不新增库/表/授权JSON。

投影event/select/summary/bundle显式3.0，generation/2，runbinding/4，publicref/read/receipt及finalpin采用显式新投影语义；raw旧严格版本及旧target解释不变。helper不各自再建协议。模型新subjectheader、prompt从真实request绑定；旧rawprompt1.4和历史generation不重新计费。

projection generation保存subjectbinding、language/profile、sourceadapter真实parser/layout、narrativeadapter/selector、executionversions、model/endpoint/生效参数、prompt与bundleproducer，不嵌records/密钥/位置/预算授权。精确匹配坏artifact仍typed损坏error，不能当cachemiss再收费。

## MAIN内部施工写集（不追加外包卡）

- MAIN root：neutral subject、source_catalog thin CLI、batch/event/select/summary/bundle/contracts、Worker/transport/terminal/pin/context、共同PWF归总。
- 内部source适配agent：仅new narrative_official_json.py与其两个新tests、evidence/source-adapter-02。
- 内部store agent：仅existing source_catalog/narrative_artifact_store.py与new test_official_json_subject_artifacts.py、evidence/subject-store-02。
- 内部generation agent：仅narrative_generation.py的投影manifest基础、新test_official_json_projection_generation.py、evidence/projection-generation-02；暂不实现尚未冻结的transport reuse。

三个内部agent不commit、不写共享PWF，不碰P7 projection/snapshot、RF、audit；由MAIN集成。先各自RED再实现，共同大节点集中审查/真实离线端到端。不是三个新的用户施工包。

## 验收顺序

1. 先已实现基础身份/publicsourceCLI正常commit，保留RED/GREEN/静态实际输出。
2. 投影batch/request/event/sharedcontext责任RED，串source adapter；根主线负责共同DTO和typederror。
3. select→model→summary→verify、generation→prepare/ACK/activate→pin/terminalreceipt/compaction→publicread/reuse同item。真实母页各自绑定，旧raw路径完整兼容。
4. ownedTEMP公共CLI真实import/project→AUTO→localHTTPstub→publish/read→reopen/reuse，A/B共享母页、第二parent变动、partial、cutoff、坏缓存和ACK恢复一次结算/发布；原件/config SHA及TEMP恢复。stub只签工程，不签真实模型/研究。
5. 一个大节点独立审查、normalcommit/push、exactHEAD CI；最后集成P7交付、定点安装，继续根计划真实三家四审/新三家泛化与loop。预算USD20/2M含旧unknown，不重置。


## MAIN集中接线实现冻结补充（2026-10-10）

- request2 `items` 混合 raw/official_json；batch-result/2仅`items`，每项item_key/kind/status/artifact_ref/errors，额外generation_status/model_diagnostics可有；旧request1/result1旧wire保持。
- event3/select3/summary3/bundle3明确`subject_binding`；第一真实parent只作内部数据库FK，不在新协议公开冒充完整来源。ref2直接subject+generation，不带source_ref/effect_id；新2 raw项仍ref1。
- binding4沿原generation_settings+generation_manifests wrapper；各item keyed实际item_key，raw read_policy map只含raw；投影从source port验全部parent，不伪造policy签收。
- 投影manifest2绑定完整subject/sourceadapter/真实source_metadata(含title/kind/language)、实际adapter1.0.1、prompt official-json/1.0.0、model-request2、handlers/selector/profile与实际model语义配置。来源metadata影响prompt，不得漏到复用键之外。
- unknown语言只诊断，无叙述complete-skip可零调用summary_not_needed；completed摘要仍必须真实语言。源字段展示沿EvidenceSpan原NFC契约，decoded_sha绑定原字段；adapter不得额外strip首尾空白。
- verify使用`replay_verified_projection(view, selected)`同一个已验view；publish/reconcile在真实可见切换边界fresh source view一次，ACK不新增许可/重复解析。store各parent current SQL由store责任层负责。
- FinalPin保持旧raw7 positional/wire；投影公开pin为4 artifact字段+subject_binding+generation_sha256，terminal-receipt/2.0，无anchor伪身份；同一AUTO库终态收缩，不保留重复大型正文。
- source-only evidence view2是同一read2的有界展示；检索分别绑定每个真实parent，不能用anchor manifest覆盖整个逻辑subject。

## 逐任务模型提示版本与根因诊断补充（2026-10-10）

`narrative-run-binding/4` 使用 `job_prompt_versions: {job_id: actual_prompt_version}`，只含该run scope的模型summarize jobs；旧binding缺此字段仍执行原run单prompt。映射由batch从已冻结generation组装，账本只管map/scope/lease/预算，不依赖source/parser/batch实现，不重新打开原件、不增加数据库或许可。resume核对已冻结映射，不改写旧记录。错prompt仍拒绝外部调用，但不再冒称超费用。

Caller仅将RunBudgetExceededError报MODEL_BUDGET_DENIED；binding/scope错误分别MODEL_RUN_BINDING_CONFLICT/MODEL_RUN_SCOPE_MISMATCH，存储不可用MODEL_ADMISSION_UNAVAILABLE可重试，其他无效预留MODEL_ADMISSION_INVALID。错误正文/凭证不进入报告。显式reasoning_effort属于真实HTTP生成语义，raw1现在绑定；未提供/null仍旧identity。thinking=adaptive沿真实配置接受。

TXT boundary采用新版本修正roster优先和inline speaker end；旧具体parser可回放。已识别Full heading格式保持既有EOF解析覆盖规则；自然fallback无END仍拒绝，不能仅凭EOF断言整个电话会全文完整。真实END存在时排除后置免责声明。MSFT版本化原件fixture便于离线/CI复现，不依赖相邻项目目录。

## 集中验收后的兼容边界

- request2/binding4是容器版本，不代表含投影。工厂依据真实冻结subject.kind与generation-settings/2才要求projection执行版本；raw-only同版本容器走raw generation1。真实raw-only CLI回归与mixed均PASS。
- 旧generation1未记录reasoning_effort的历史run，只在全部job终态、outbox已交付且产物真实visible时可只读恢复；仅容许该字段缺失的窄历史差异。不重签、不修改账本/manifest，不让新effort配置复用旧缓存；未完成run拒绝并要求新run。
- public official project显式producer版本由source owner解释。缺省1.0.1，1.0.2为opt-in；非字符串参数在CLI typed拒绝，未知字符串由producer拒绝。不全库升级旧sealed投影。
- Complete且native fields全空为skipped_no_narrative/summary_not_needed/unknown语言，零模型调用；partial空记录或有内容但无法判语言不猜测，不借空证据完成摘要。
