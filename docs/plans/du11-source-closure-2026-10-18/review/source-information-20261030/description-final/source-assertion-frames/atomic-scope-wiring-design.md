# 新scoped recipe、原子限定提示与历史回放：只读接线设计

2026-10-30。依据canonical `M4_ADOPTION_AND_ATOMIC_SCOPE.md`及现有源码；使用CodeGraph context/explore（项目允许的两次explore），再定点读取相关owner。只写本报告，不改产品、不运行模型/下载/原PDF解析或benchmark，不把正在独立开发的assertion framing当已正确/已接线。

## 核心结论

现有`narrative_summary_protocols.py`已经是合理的窄owner起点，但还不是完整有限registry：仅列`LEGACY_SCOPED`和`FIDELITY_SCOPED`，多个下游仍直接判断`FIDELITY_SCOPED.projection/prompt`。`summary_bundle_format(prompt)`更把一切非4.2的prompt退回legacy格式。未来新行为必须新增完整recipe并按显式recipe分派，不能在`FIDELITY_INSTRUCTION`、当前framing/assessment函数或旧/6物料上静改。

`/5`是source-extractive family（模型只作有限排序、正文由source cards形成），不是scoped改写的第三个prompt；不能为了registry把/5改成/4或/6那样的paraphrase decoder。`/4`、`/5`、已付费/归档`/6`和旧assessment1.0.0均保留历史解释。

建议一个CWP有限recipe catalog＋现有family dispatch；RF只维护公开wire兼容catalog，不导入CWP实现或复制source/framing/准入算法。registry不是第二引擎、任意插件loader、可执行配置或新的权限流程。

## 当前协议矩阵（冻结现有值）

| projection | family | prompt | request | decoder | source task plan cap | artifact |
|---|---|---|---|---|---:|---|
| reading-model-input/4 | scoped | reading-source-scoped/4.1.0 | narrative-model-request/5 | reading-scoped-task-decoder/4 | 20 | legacy raw2.0/projected3.0, producer1.0.0 |
| reading-model-input/5 | extractive | reading-source-extractive/5.0.0 | narrative-model-request/6 | reading-source-extractive-decoder/5 | 既有extractive策略 | source-extractive execution/1，legacy bundle格式 |
| reading-model-input/6 | scoped assessed | reading-source-scoped/4.2.0 | narrative-model-request/7 | reading-scoped-task-decoder/6 | 40 | raw2.1/projected3.1, producer1.1.0；assessment wire1、validator1.0.0 |

注意历史task-plan cap与最终输出cap不是同一字段：`narrative_model_scoped`的`MAX_SUMMARY_CLAIMS=40`、decoder编译及旧/4 build的20 marker存在历史差别。迁移registry时须逐项描述真实现状，不能顺便“统一成40”而改变/4输入。旧None、/1-/3继续由既有legacy dispatcher处理，本次不重构。

新recipe ID/版本须由实现时显式分配（本文不预占/7或4.3）。同一scoped engine可接新描述；至少需要新的projection、prompt、request/decoder边界身份或明确版本组合，以区分新物料/指令/解码语义。若canonical bundle字段形状不变，可以复用assessed bundle格式并登记新的精确prompt/producer/assessor组合；若增加bundle/report字段，才按现有合同显式演进格式，不能放宽旧exact-field检查。

**近期最小范围明确收窄**：不改变旧task/admission/view.to_binding/claim binding和现有prose_diagnostics v1语义；新frame提示只在新request的material按独立profile附加。新增诊断用新assessor版本并按声明版本选择，原v1函数路径保留。近期不复制legacy engine或其几千行依赖；只有将来实际修改共同算法，才对那个owner做必要版本化/迁移。

## 有限registry应拥有的接口

扩展现有纯协议owner，保留旧常量为兼容alias。建议概念接口（签名由TDD冻结）：

```python
recipe_for_projection(version: str) -> SummaryRecipe
recipe_for_prompt(prompt: str) -> SummaryRecipe
supported_batch_projections() -> tuple[str, ...]
recipe_for_assessment(prompt: str, validator_version: str) -> SummaryRecipe
```

`SummaryRecipe`为frozen、有限描述，包含：projection、family、prompt、request_schema、decoder ID、source_plan_policy/cap、output_plan_policy、material_view_version、instruction ID、frame_hint_version（旧为None）、assessor_version（旧/4、/5无assessment）、bundle raw/projected schema、producer、internal wrapper、paid-response durability、subset/target-override能力。不要继续用单一`assess_fidelity`布尔值同时选择prompt、输出预算、物料和所有未来诊断。

family实现仍是现有scoped/extractive/legacy函数；descriptor只选择受控实现，不在registry复制任务生成、模型调用、业务规则或收入算法。未知新source-owned recipe明确报unsupported；已有legacy delegation保留已知旧行为，不让未注册新prompt默默获得legacy bundle。新recipe只有显式请求才能启用，生产默认不随注册改变。

## source-frame hints的最小接口与成本边界

当前原型`document_understanding/assertion_frames.py::SourceAssertionFrame`包含`matching_text`、reported prefix/inherited、ongoing/future、quantity_basis、project_condition。文件明确声明：matching_text是规范化匹配视图，**没有原文offset/逐字引用含义**。该原型仍由benchmark reviewer独占和验证，本报告不认可其继承/阶段规则已正确。

建议先在source-owned framing owner形成可独立核对的有限观察，再加一个纯物料投影适配：

```python
frame_hints_for_source_parts(known_spans, source_keys, *, framing_version, limits)
    -> CompactFrameHints
```

它接已有唯一fragment身份、task-local parts映射；不重读文件、不下载，不重新计算required support/context、不创建新source事实。按每个唯一source fragment计算一次，再以`source_key`和确定的matching-clause ordinal引用有限hints；不要把normalized ordinal包装成`loc:v1/chars`。若需要精确source范围，由原owner另提供经过核实的mapping，不能由wrapper猜offset。

模型物料优先独立紧凑hint表，例如`source_key → clause ordinal → {reported/ongoing/future/stage/condition-present/qualifier-ref}`，task仅指向既有`pN`或shared_ref。field名字/枚举先与framing owner约定，不把本文示例当已发布schema。reporting prefix/condition尽量引用同一原文fragment的有限clause标识；无法安全引用时保留unknown或简短有限flag，不复制每条`matching_text`、reporting_prefix全文、condition全文。模型已收到的原始fragment正文仍只出现一次。

所有hints都须明确“程序的有限source-scope观察，不是业务事实，不替代原文，不证明该改写正确”。未知语法保持unknown；不能靠提示将别的主体、独立回答或另一项目的限定借给本条。ongoing是当前进行，允许现有`actual`模态配合“正在/持续”等准确正文，不新增一个模型随意输出的业务状态，也不将actual误定义为已完成。project capacity、commissioned capacity、output/sales仍分开；模型不能从hint制造数量/收入。

只有新recipe启用独立frame profile和单条限定/ongoing instruction。`ScopedModelView.to_model_dict()/to_binding()`、task plan和claim binding近期都不改；新request的有限material renderer先取得同一基础material，再对新profile附加紧凑hint表。profile/投影版本与hint数据被实际request data_json/input hash绑定，相关formatter/framing/assessor身份进入新recipe的boundary/generation。无需为此提前新增canonical view schema或改source_plan_sha。共享support/context只消费现有plan/parts；不创建第二套admission或citation closure。

成本验收应实测同一输入的fragment正文出现次数、hint bytes、实际HTTP bytes/tokens、原文chars/char ledger与有界复杂度。当前8tasks原文约1128chars而请求29.6KB/6226tokens，不能再用“每条frame重复全文”付代价。新增hints的字节/条数/每fragment工作预算纳入现有request上限与WorkBudget；超预算留bounded omission/unknown并报告，不静默扩token、费用或输出上限。

## 必须接线的owner清单

| owner | 当前耦合 | 最小变化与保留边界 |
|---|---|---|
| `automation/narrative_summary_protocols.py` | 两条scoped tuple；4.2才assessed；非4.2全legacy | 单一有限描述/索引，legacy aliases冻结；new recipe显式分配，不改旧值 |
| `document_understanding/assertion_frames.py`及其tests | 原型framing独占开发，尚无生产接线 | 先中英/繁体/跨主体/项目作用域正确性与有限成本验证；只提供source hints，不负责模型或RF |
| `automation/narrative_model_scoped.py` | `FIDELITY_INSTRUCTION if assess_fidelity`；view无framing；全局40/历史20差异 | 新recipe选择新instruction和独立material hint profile；共用既有request/HTTP/decoder核心，旧task/admission/to_binding/claim binding不改；不要覆盖老指令常量 |
| `automation/narrative_model_runtime.py` | /6特判4处；durable集合硬列4/5/6 | 从registry取family/descriptor，列举现有adapter函数；durable能力从有限描述导出；不改变/5 advisory路径 |
| `automation/narrative_summarize.py` | 仅projection==FIDELITY才做assess/downgrade/wrap | 根据recipe的明确assessor调用；原AUTO run/lease/outbox、paid ledger与预算保持一套 |
| `automation/narrative_summary_execution.py` | assessed wrapper仅允许4.2；parse/raw拒绝列表硬含FIDELITY；extract terminal report走当前wire checker | 以recipe+declared assessor选择wire/material/quality校验；wrapper形状不变时复用/2；bare/legacy-wrapper不能接收新assessed prompt；compact terminal仅shape，不重算语义 |
| `automation/narrative_verify.py::_bundle` | /6决定skip prompt；plan_max硬FIDELITY；直接assess_summary | 从所请求/summary声明recipe取prompt、格式、assessor/cap；raw/projected/skip都正确，输出assessment版本明确 |
| `automation/narrative_contracts.py::NarrativeBundle._validate` | 当前bundle_format只区分4.2；assessed重验硬用FIDELITY cap和今日assessor | recipe/assessor双重明确匹配；历史版本走冻结解释，未知tuple拒绝；stage/semantic not_evaluated不洗白 |
| `automation/narrative_summary_assessment.py`及一个必要新assessor owner | 单一1.0.0＋今日compiler/prose_diagnostics；expected.validator被换回历史记录 | 保留v1原算法和共同task/admission/view不改；新frame诊断走明确新版本dispatch，新recipe选新assessor；不复制整套legacy engine |
| `automation/narrative_batch_request.py` | projection白名单4/5/6 | 列表来自有限catalog；selector0.9.0等现有能力约束由descriptor/现有边界保留，不自动启新默认 |
| `automation/narrative_batch.py::_paid_summary_recovery_candidates` | projection→prompt硬dict | registry导出durable精确配对；原request/model/paid bytes/hash核对继续，错recipe绝不拿旧response冒新生成 |
| `automation/narrative_generation.py` | boundary identity、prompt选择及bundle schema/producer参与generation；`_bind_summary_bundle_format`单4.2 | 同一recipe的material/instruction/framing/assessor/output-policy因果身份全入generation；历史pinned manifest解释保持，不能重写历史 |
| `tools/document_understanding_benchmark/phase_c_runner.py` | argparse choices4/5/6、reading_projection_for、fidelity观察判断单/6 | 使用catalog公开choices/recipe能力，旧默认/4、历史pair保留；新recipe单独显式运行；不借runner改生产body或掩盖费用 |
| `tools/document_understanding_benchmark/phase_c_observer.py` | request5/6/7硬列、仅request7 cap40/禁止subset | 根据request对应recipe精确编译物料/hints、比实际HTTP material；旧subset策略与新all-admitted策略分别声明；observer不重建source规则 |
| RF `scripts/narrative_summary_observations.py` | 2.1/3.1⇔单prompt4.2，producer1.1、cap40、validator1.0/7deps/固定rules | RF本地有限**公开wire兼容**catalog按prompt/producer/bundle/validator选严格shape；旧矩阵不放宽，不导入CWP或重算framing |
| RF `scripts/company_wiki_narrative_contracts.py`及source context receipt | 当前assessed schema集合推导required字段 | 如格式复用，按明确tuple验证；如新字段才显式新schema；context/receipt可继续可选观察字段，partial/needs_review/assessment留原值 |

补充：`tools/.../holdout_acceptance.py`、`tools/holdout_replay/worker.py`内/4是已命名历史运行的固定协议，不应因加新recipe全局替换。只有新增明确holdout方案才改其可选支持；旧holdout声明/gold不重标。`source_narrative_context.py`的未来summary-use lineage另属M4采用节点，不为framing接线提前改研究参数/公式。

## 旧assessor解释与因果hash：必须分开

当前`validate_assessment_material`使用今日`compile_scoped_material_view`和`assess_summary_material`重算，再将expected.validator替换为报告中recorded validator。因此仅允许历史implementation hash不同，不能保证历史算法语义。新framing/ongoing诊断不能覆盖这些1.0.0函数后继续用同名版本读旧/6。

近期最小处理是**不修改**现有v1的matching/task plan/admission/scoped view/claim role/prose诊断语义，保留原1.0.0路径；在一个必要的纯新assessor中使用相同现有source plan/binding并增加新frame-aware观察，按recipe/记录中的明确版本分派。无需提前复制共同算法或整套legacy engine。若以后确实改变某共同owner的行为，再只对那个语义变化做版本化和兼容迁移。assessment wire仍为1且字段不变时，可以在公开catalog明确登记新validator版本/规则词表及依赖键集；新增不兼容字段时升wire schema。旧1.0.0报告继续原exact规则，new recipe不能接受旧算法冒名report。

历史validator依赖hash是当次生产软件来源，保持其原值、键集/canonical绑定；它不是“必须等于当前安装文件”的访问许可。读取旧报告时按其明确版本执行冻结规则，不修改旧recorded hash，不用新算法的结果替旧报告背书。新产物则记录真正执行的新assessor/hint依赖与实际hash。

另一个事实是`scoped_boundary_identity`依赖runtime/scoped/protocol等**整模块LF hash**。新增registry/分派代码会自然改变当前安装实现fingerprint，即使旧请求正文不变。不能承诺所有旧current-generation hash仍相同，更不能为命中旧缓存伪写原hash。须分别验：

1. 老/4/5/6的protocol descriptor语义、旧HTTP/request/material/input gold按冻结规则不变；
2. 原不可变generation manifest、paid pin、response bytes及artifact保持原值，用原pinned recipe重放，不以今日全模块hash重写旧manifest；
3. 新recipe产生不同request/input/generation锚，不误用老/6 response；若最新软件下老协议的新run实现fingerprint变化，诚实记录，不能仅为补当前hash而自动重POST。

若未来要避免“新增无关registry条目使所有协议当前实现hash变化”，可以在新的boundary identity版本中按recipe登记受控语义依赖，仍保留原/1解释；这不是当前节点必须重构的缓存系统。优先复用已有pinned-manifest/paid-response恢复路径，拒绝另建缓存/任务库。

## 最小实施与精确测试细则

先完成framing owner离线中性正确性/复杂度独审；在其接口稳定前只保留上述适配设计。随后以“旧protocol gold不变”为RED基线，先加registry descriptor，再加新request material独立profile与新assessor，打通new scoped request→AUTO wrapper/verify/bundle→observer→RF wire；每个消费者只调用同一能力描述。共同task/admission/to_binding/v1诊断保持不动。最后才在真实当前配置/累计预算内显式运行一个有界新recipe，已有paid产物不重发。

| 测试组 | 必须证明 |
|---|---|
| registry闭合 | projection/prompt/request/decoder映射唯一；未知、交叉配对、重复descriptor拒绝；默认仍历史；/5保留extractive family |
| 旧wire与输入gold | /4、/5、/6各自真实已录request/material/response/assessment读取gold；raw/projected/skip；新增entry不向旧物料加hints、不改既有caps/子集行为 |
| hints身份与引用 | 每个hint绑定已存在source_key/part、clause ordinal/version；未知/越界/跨task/context-as-support拒绝或显式unknown；不制造source locator或业务事实 |
| bounded成本 | shared fragment正文仍一次；hints不携matching_text/全文副本；大小/条数/预算超限有界；重复shared引用不触发重复framing；实际HTTP字节/token与ledger可观察 |
| 单条限定与状态 | benchmark中英/繁体，reported延续/另一主体断开，ongoing/已完成/意向/条件未来，设计/已投产能力/销量；每条独立使用仍保必要限定；unknown不是“语义通过” |
| assessor历史 | 固定旧1.0.0输入/report完整gold，在安装新assessor后仍旧结果；新旧算法在同一中性反例确有差异但旧报告不重标；错recipe/assessor/version拒绝；recorded软件hash保持原值 |
| wrapper与quality | 新prompt不能裸summary或塞旧wrapper；缺assessment、claims hash不符、schema降级、skip phantom model、needs_review→verified洗白均拒绝 |
| generation/cache恢复 | 新recipe/hints/instruction/assessor变化改变新锚；旧pinned manifest/paid bytes完整恢复0POST；错request/model/prompt/hash不能回放；resume/restart/crossrun不重复收费 |
| observer真物料 | 使用相同recipe compiler比捕获的真实material和hint表；subset能力按recipe，不把丢task当重试；source support/context owner不被复制 |
| RF跨仓wire | legacy4/5/6 exact旧合同保持；新explicit tuple raw/projected/skip合法；未知tuple和错validator拒绝；context/consumption保留assessment、partial/needs_review、不冒充语义与预测采用 |

这些是未来TDD与大节点验证清单，不是新的人工许可。本文未执行测试、未签framing正确性/新recipe已接通/真实摘要质量或RF采用通过。
