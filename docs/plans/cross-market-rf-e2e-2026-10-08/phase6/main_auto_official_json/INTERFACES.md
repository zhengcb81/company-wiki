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
