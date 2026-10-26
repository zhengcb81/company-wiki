# 选型后的单层实施细则

2026-10-26当前覆盖说明：C1/C2主体及Linux兼容已发布，旧“下一步C2”只表示当时快照；当前执行[C3工程/真实内容验收](../pdf-c3-20261026/README.md)，以下C1–C3细则继续有效，不能把工程通过代签内容。

状态：**PDF-C1源码已实施并独立终审0OPEN，已发布且精确CI通过；PDF-C2/C3仍待实施验收。** 真实收据见[c1-acceptance](c1-acceptance.md)，以下保留施工细则，不是全计划验收收据。 研究决定见decision.md；实际分层泄漏L1–L8与源码定位见layer-boundary-review.md。此节点不碰W18/W19作者工区，不改Dayu/IQS、RF运行WIP或原件。A股三表仍由新浪W19提供。

## 一、唯一职责层与对外契约

保留原select→summarize→verify三阶段DAG及AUTO任务/lease/outbox/累计预算，不新建常驻服务或第二状态库。在已有文档阅读职责内组织小facade和内部backend，复用DocumentStructure/NarrativeUnit、DU/family策略、summary_input与现有模型端口；**不是把全部功能堆成一个大类，也不是把PDF伪装成现有只支持HTML/DOCX/PPTX的NormalizedDocument。**

上层只能传逻辑SourceRef/已验证字节、标题/文种/语言/阅读意图、资源账户和deadline；只能接收统一证据/摘要/覆盖/质量结果与不透明producer描述。底层存储负责原件、当前版本/根/配置及字节验真，不决定阅读引擎。AUTO负责调度持久化和通用资源执行，不判定PyMuPDF/Docling或按其工具名修改prompt。RF/FF/StockWiki不得import具体PDF SDK或读取目录挑后端。

建议接口（名称可随既有代码一致，但责任不可漏）：

- `describe_recipe(request)`：在执行前返回pathless阅读配方/能力描述，供既有generation冻结；包括显式启用且可能参与的backend/SDK/options/模型revision及自有算法版本。这是计划依赖，不是实际调用证明。`actual_producer(result)`在执行后只记录真实参与的组件/页与fallback原因，用现有选择依赖和收据留证；不得回写冻结manifest。
- `select(verified_bytes, request, resources)`：同一账户下读取、按页分诊、结构/策略/选材与材料核对；返回实际producer、现有package及partial诊断。内部backend必须成套提供read/identity/material_validation/replay，不再任意独立拼parser与replayer。
- `summary_request/validate_summary`：复用当前公共摘要协议和数字/引用校验；引擎私有对象及prompt分支不穿出阅读层，不建另一模型客户端。
- `replay`：按记录producer恢复旧版本行为与精确成员坐标，验证同源/同页/原序/字符范围；不靠全PDF字符串搜索证明引用。
- `close`：释放借用的worker/模型资源。有限批次可复用热实例；不启动无限watch。

## 二、PDF-C1：先以测试封住当前真实分层缺陷

1. 写RED：使用另一个完整backend，和默认backend收到同一WorkBudget、PdfReadingContext及deadline；调度层不通过函数对象`is`判断能力。零预算在任何原生读取/推理前停止，回退不另开账户。
2. 建完整backend/facade契约，移走`automation/narrative_select.py`里的PDF版本/全表重读策略及函数identity分支。旧callable测试端口要显式迁入阅读层兼容adapter或改成整套backend测试替身，不能静默剥掉预算/context。任何兼容失败明确报契约不支持，不重复尝试猜参数。
3. source格式router只转交阅读层；PDF parser_component、select结果真实identity、verify当前支持判断、原文replay共用一owner。新backend名称/版本未支持时不能沿用旧PyMuPDF标签伪装成功。
4. generation/cache接受owner给出的不透明recipe fingerprint；修PDF忽略parser_components的实际路径，同一运行composition向select/verify/freeze提供同一owner。缓存层只规范化/hash/storage，不再枚举PDF工具。改变显式启用配方里的模型/第三方版本/options必须失效；仅移动宿主/模型目录不失效。完全禁用Docling的纯native配方不引用其已安装版本；启用按需分支时可保守绑定可能用到的依赖，即使该文档最终没用也允许额外cache miss，不能漏失效。实际参与列表只在select后的现有依赖/收据记录。
5. 摘要模块在同一逻辑阅读职责内复用当前代码；transport/费用执行仍是通用基础设施。先保留阶段边界，不顺便搬整个仓目录或改wire契约。

PDF-C1集中验收：上述RED转绿＋完整`tests/unit/du11_production`包（包括work-policy/cache，不只挑PDF同名文件）＋既有格式/verify/generation/cache的定向回归＋独立架构审查。职责迁移用CodeGraph调用者/覆写者及测试源码核全部旧接缝；本轮CI两项旧观察钩子遗漏见[c1-ci-followup](c1-ci-followup.md)。不是每个文件人工签收，不给每次commit加全量。保留旧replay兼容；不重放旧付费请求。

## 三、PDF-C2：实现按需Docling结构增强

1. 保持既有时序：owner先描述recipe并冻结generation，随后在select中原生读取一次，由有业务价值的未闭句/未解结构依赖/局部组完整性诊断决定需求页；执行后记录actual组件和fallback，不改历史generation。不要为了describe先全文预检、在select再扫一遍，也不加第二planner/store。配方中可能参与但未执行的依赖只证明计划，不充当实际调用证据。路由不用公司名、证券代码或此次gold字符串；普通已闭合页不触发模型。若当前诊断不能识别实际缺口，先补通用诊断RED；不得硬塞p13/p114作为生产规则。
2. 在当前有限worker生命周期内懒加载Docling。部署解释器/SDK/模型参数由阅读层配置解释，不由RF/AUTO每次拼命令；本机Conda路径不能写进业务源码。能力缺失或模型版本不符如实诊断，不隐式联网、下载或换身份。CWP venv目前没有完整Docling，不将本机试验成功伪装成所有部署可用。
3. 显式限定页、线程、冷启/总deadline、RSS/临时字节；当前原生细捕获15秒上限不自动变成重模型启动额度，更不能移动计时起点掩盖84秒导入。按现有任务/批次资源策略分配启动与热推理，余量不足就保留partial/原生回退；不先跑超时再无界重试。首次冷启与有限批次复用、故障结束和清理都需实测。
4. backend只返回阅读层自有paragraph/list观察DTO；不得把DoclingDocument或其私有坐标交给下游。在本机受界隔离子进程中推理，原件内存/受控pipe传递，验输入SHA/响应边界，不复制原始PDF或落全文MD/JSON/图像。
5. 原型中心点落框只可产生候选成员，不能直接作为生产证明。真实准入必须校验source_id/SHA/page/frame、原序连续性、bbox有效与容差界、成员唯一性、覆盖率、精确native字符来源及完整文字等价；NFKC/空白/显式bullet比较只能辅助对齐，canonical text与offset永不改写。多页/旋转/多栏/重复文字/部分重叠/表格、跨父子及邻近业务串线各有否定测试。
6. 61项原型中29个未对齐保持未采用；特别是私用字形和引号替换两整段，不增加特判硬修文字。允许规范变换的类别由通用字符视图契约明示，模糊匹配/编辑距离不能用来补数字、主体或缺失词。输出使用原有native member IDs/locators，不能把Docling charspan当DICT offset。
7. 只增强原文证实的paragraph membership/闭包；不得让字体或模型布局自动变成投资论断/业务因果。经营表仍保留其现有按需原生路径，不能拼成同段就声称row/cell关系已证明。八个目标段落和第九经营关系都按各自契约验。

## 四、PDF-C3：大节点验收和发布

- **单元：** backend替换/身份一致；共享预算0/耗尽、deadline；同源/同页/原序/字符范围；兄弟串线、表格误并、旋转/多栏、坏框/重复成员；兼容字符不修改原文；不支持依赖的诊断；原生路径不导入重SDK。
- **集成：** 冻结recipe后动态分支不改历史generation；actual中不出现未执行组件；禁用外部工具的native不受其安装版本影响，启用按需配方的可能依赖变化正常失效。同一owner贯穿select→summary材料→verify；producer/options/runtime变化正确失效cache；旧producer原文重放；模型缺失、timeout、子进程退出、截断/过大响应保留partial并清理；回退及恢复使用同一资源账户。
- **真实E2E：** 重新跑当前三文档五页，对照已有当前共享引擎6/8而非emitter0/8；两个缺组须完整闭合，原六组保持，经营应用关系不退化且typed rows状态如实。验证实际task-local模型输入与配置内正式原语言摘要、数字/单位/期间/否定/前瞻保真、原文精确引用、缓存重启零重复POST、RF实际采用。
- **泛化：** 独立新公司/US PDF及不同文种、真实扫描/复杂版面按实际本地可用来源选择；无样本写缺口，不伪造PDF或把HTML转成PDF冒充。开发五页不是holdout。遵守现有母账与配置，不逐材料询问授权。
- **空间/恢复：** 测试放独占目录，记录初态；结束删除新下载/页图/临时产物、恢复初态。原件不改/不删。不做完整恢复备份演练。只留紧凑失败/质量/费用与来源版本收据，不另存全文多份。
- **独审：** 最终代码/配置/证据绑定SHA，独立agent检查本节点架构及真实质量；发现问题修共用owner，零OPEN后正常commit/push、核精确HEAD CI、更新PWF。日常定向测试，不无变化重跑超时全量。

## 当前下一步（唯一）

PDF-C1正常发布与精确CI已通过；下一步PDF-C2按需结构增强。C1源码/真实接缝独审已通过，C2/C3仍OPEN，不用A/B研究或工程绿代签正式摘要/cache/RF完成。


## 最终独审补正：冻结配方与实际执行分开（2026-10-25）

独审发现初稿将“实际使用依赖”放在原生读取后才能决定，却要在读取前冻结generation，时序冲突。已采用上面的保守recipe机制解决：不新增预检全扫或planning库，不执行后改manifest。初版宁可对显式启用但本次未用的可选模型产生额外cache miss，也不能错误复用；未来有实证再优化。独审早先建议里的“未用不入依赖”只适用于actual列表，不是冻结recipe的绝对要求。


冻结不变量：actual使用的backend/model/options必须属于冻结recipe允许的配置与指纹；版本漂移或临时替换不能当普通fallback。重放按actual的文本/坐标契约派发并核recipe一致；验证canonical原文成员不等于重新推理布局模型，不能为缓存恢复增加不必要的模型调用。无法按原契约重放则如实报告，不冒充新版本可验旧证据。

## C2接线前的源码调查补充（基线87d39bbc；尚未实施）

以下将下一节点约束落到真实调用链，不增加审批或第二计划。调查只读、未运行重模型或产品测试，不能当C2通过。

### 1. 真正到达摘要的最小链路

`PdfReading内部增强器严格对齐 → observation_adapter.build_observation显式generic hint → narrative_continuity._Analysis.edge既有物理边owner → finish / narrative_reading._prose_reading_packages → _candidates / _context → summary_tasks.build_summary_task_plan`。

- 当前`ObservationUnit`没有通用paragraph membership槽，`reading_layout.upstream_hints`也只透传words/cells/font_runs/spans，塞任意metadata不会自动生效。continuity已直接读原始du-input hints，因此本节点不必扩大所有结构类型。
- **只修改structure/paragraphs.py不够。** `_prose_reading_packages`不信任普通容器的atomic性，会再按native continuity拆解；必须在实际模型任务中验证完整成员，而不是只看结构分组数量。
- 摘要继续复用现有citation_views与summary_tasks；不另写Docling summary/prompt/合并器。AUTO、存储、FF、RF不解释新hint或SDK配置。

### 2. 成员提示与原文身份

- 源owner完成同source/SHA/page/frame/连续原序/唯一覆盖/严格字符等价认证后，才发紧凑generic paragraph proof。可用每unit O(1)的group、position/count、prev/next原unit引用及proof digest，或每组一次有界成员表；不得给每unit复制整段全文/全成员列表造成O(N²)。对外不叫Docling专属业务类型。
- hint是transient，在`NarrativeUnit.to_evidence_span`的既有过滤点剔除，不改原raw_text/unit_id/coordinates/parser，也不随每span持久化大结构。
- `_Analysis.edge`只增加一种物理正证；仍保留source/page/role/原序/章节/profile/project/表格/标题/已知异列等反证。不伪造native字体或font coverage；缺字体而当前observer拒绝时如实not_applied，不假填regular。跨页沿现有原生证明，本节点不凭同paragraph_ref跳页。
- `finish/statement_members`继续把独立完整事实分开，保留条件/否定/计划限定；同段不等于同一事实/因果。当前8unit/4block/2048字符上限不为试点金标提高。原型含10/15成员长段，不能一律强塞完整窗口；须按真实完整句边界保留闭合前缀、延期未闭尾部。
- **采用明确兼容决策：** external-membership-only窗口负责原成员成组，不触发`_candidates`现有`native_range_unit`折叠。这样最终span仍保留原native成员/locator，避免只保留`_carrier_origins`却宣称所有最终ID不变。已有纯native range路径不改，也不生成外部改写文本carrier。

### 3. 分诊与有限运行时

- 在native已经读取页面的snapshot/emit流程记录小型结构缺口需求，后端读完后只处理dedup的受界页，全源DU只跑一次。现有geometry planner以table/QA为主，`tabular_evidence`不能冒充叙述缺口；需要共用时在唯一owner明确扩purpose，不另造planner/store。
- 早期分诊只描述相邻原块的未闭句、金额/单位分裂、悬挂bullet等物理观察，结合已有reading intent，不再写第二套业务词法。仅“无句号”不够，不能触发所有标题/标签。
- 后验`CONTINUITY_OPEN_START/END`等用于核验/下次有理由的回放，不免费启动全源selector→Docling→全源selector。`NEEDS_UPSTREAM_GRANULARITY`当前是表格问题，不能泛化成任意段落问题。
- 如果早期分诊尚无可靠实现，可先用明确受界页请求验功能；这仍是工程试点，不宣传成通用分诊已完成。不得将p13/p114或gold字符串编码成生产规则。
- 重模型解释器/依赖/模型与线程配置只由阅读runtime解释；基于既有有限worker生命周期复用热实例，必须接关闭/异常/父worker终止清理。先核现有受界隔离执行器的资源与子进程清理能力，不先新造常驻服务。冷启、推理、RSS和剩余deadline真实计量，原生15秒fine-capture不是Docling启动额度。

### 4. 本节点集中测试清单

1. 中英文数字→单位/增幅→原因、悬挂列表正例；检查最终summary_task实际成员与原句，而非仅DTO数量。
2. 异源/页/角色、兄弟业务/项目、表格/标题、异列、跳漏/逆序/重复文字、错误frame/字符差异全部拒绝提示；原生材料仍保留。
3. 同段独立事实仍拆分；条件/否定/计划不丢；没有hint时输出逐字段等价，原text/ID/locator及持久span不被提示污染。
4. native读取一次、DU一次、同页需求去重、0需求0重模型调用；低预算/超时保持闭合前缀及真实partial，不新开账户。模型丢失/截断/超大响应/worker退出均有清理收据。
5. recipe绑定显式启用增强器/模型/选项/对齐代码指纹，actual只记真实调用；修改算法使cache正确失效，移动宿主不失效；原spanreplay不重新推理布局。
6. 五页开发金标保留原六组、补两缺组，经营表typed-row状态如实；之后独立新公司/US PDF与真实扫描/复杂页holdout，再正式摘要/缓存/RF。不能用开发五页代签泛化。
