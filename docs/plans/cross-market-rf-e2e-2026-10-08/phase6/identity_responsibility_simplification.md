# MAIN：身份核验责任收敛与入库解耦

状态：2026-10-08 入库与元数据/读取/恢复两个责任节点已集中验收；后续跨run内容复用与外包接线进行中。用户再次明确要求系统性减少冗余身份核验；本项提升为 MAIN 当前最高优先级，三张已分派卡的写范围维持不变。

## 已证实的重复机制

| 当前环节 | 已见问题 | 统一责任方向 |
|---|---|---|
| resolver / DB-only reader | 都先按公司归属筛选，又按 market/security_id 核对；resolver 还为缺失身份加载额外 assertion 并在得到原文后再次拒绝 | 公司归属和明确的市场/代码冲突由共用筛选规则负责。已归属公司的原件缺少辅助身份字段只记诊断，不要求补签收才能复用 |
| acquisition → canonical writer | coordinator 校验候选与回执，writer 重复比较同一批字符串；写入之后又重新进行完整语义选择 | 候选选择负责请求范围；下载回执负责实际响应与候选绑定；writer 负责原子保存、字节与索引引用。直接 writer 入口仍须能够拒绝错误归属，不能依靠调用者总是正确 |
| writer post-scan / source_ref_for_import | 用历史请求重新查已提交原件，未知日期触发特殊的 company/security/market/provider/title 签收；宽期间请求可能选中较旧年报 | 已提交来源的引用直接按内容寻址 ID 与 SHA 查询，不再通过历史选择器重新证明公司身份。未知、未来、缺期间不应使原文保存失败 |
| ensure finalization | writer 完成后第三次语义 resolve，再要求结果可用于历史请求才认为保存成功 | 入库与历史适用性分开输出，复用 writer 结果和已提交引用；确实发生的下载必须记账。历史不适用只影响历史结果，不抹掉入库成果 |
| SourceRef / Worker / narrative read | source/hash/bundle 绑定与证券身份经常都被称为 identity；因此容易一概增加重复检查 | 后续层使用 SourceRef 和已解析描述。保留文件损坏、混错摘要和并发变更的责任检查，不再要求下游重新识别证券或人工签收 |

## 目标规则

1. 公司选择是检索输入，不是访问权限。明确 company/entity 归属后，缺 market/security_id/完整 capture 只作诊断；明确的错公司、错市场、错证券代码仍不能作为该请求的结果。
2. SourceRef 是内容版本引用，不是身份许可证。导入刚提交的 SHA 应直接得到该版本；不重跑证券识别、发布日期和期间筛选。
3. 保存原件、选取业务资料、历史信息日、解析质量分别由自己的层负责。缺公开日的原件可以保存、预览和当前处理，指定历史 as-of 的结果明确标出未知日。
4. 不增人工审查、receipt、TTL、policy hash 或新的状态库。沿用现有 catalog / AUTO / 预算账。
5. 并发锁中的一次本地重查用于防止真实重复下载；实际字节 SHA、响应绑定、路径和预算检查用于保护原件及资源。需在调查报告说明用途与调用次数，不把每层都做全量核验当成可靠性。

## 施工顺序与验收

1. 只读盘点主线检查点/调用方，区分字符串重复、必要的请求范围比较、实际字节验证和并发状态检查；记录相应代码位置及旧测试的原要求。
2. 先写 RED：已归属公司但缺 market/security 的真实原件仍可复用；明确冲突仍拒绝；unknown/future/坏日期只影响历史查询；导入引用不调用语义 resolver，也不要求旧 acquisition metadata 完整；宽期间导入引用不能误选较旧年报。
3. 在共用层收敛身份筛选，消除 writer 的日期专用验身份分支及 ensure 的重复 final resolve。旧测试若要求缺字段阻断，依据本文件的新产品要求改成合法正例，同时保留真实错归属/错字节/错期间负例，不能仅删失败断言。
4. 一次集中节点：单元/契约/真实 ensure 与 CLI/Worker 责任集成，再提交冻结版本后跑原三公司 full replay / compare。该节点没有逐小项人工门。
5. 清理本次 owned 测试根、记录释放字节；原件与生产 source_catalog 配置改动 0。更新 PWF、commit/push 后继续 Worker 接线与外包集成。

## 并行边界

MAIN 只改现有 CWP source_catalog / automation 及相关测试。R6-FORMAT 的新 document_normalization 子目录、R6-RF-INPUT 的 RF 实现、R6-FF-CAUSE 的 FF 诊断实现保持零写；跨仓身份重复若涉及其接口，在最后统一接线，不进入别人当前工作树。

## 当前复现状态

前一来源资格集中测试 231 项中 229 通过，2 个失败为新登记原因码缺 stage 映射；另加宽期间导入引用真实 RED 1 项。尚未发布本次资格代码，不把这些结果记作全绿。用户本次要求触发责任层重构，先完成新 RED 再实施。

## 实施接口与兼容边界

- `CanonicalImportResult` 升为工程结果 schema 2.0：保存 outcome、路径与 SHA，返回已有 `SourceRef`；删除 `resolution`。原始 `.source.json` 保持 schema 1.0，既有原件/capture 不重写。
- `SourceAcquisitionService` 仍在原输出位置提供 `resolution`。writer 不再执行历史/证券选择，service 仅一次查询用于生成消费者所需的历史结果，不把不适用当成保存失败。普通下载完整 resolve 从4次减到3次；未知日从5次加额外验读减到3次；后续独立打开仍验当前字节。
- `candidate_scope_problem` / `receipt_binding_problem` 是纯字段比较；coordinator 和可独立调用的 writer 共用同一规范化规则，保留各自公开入口的错误目标负例。没有“已验身份”许可 DTO 或可绕过的签收标记。
- 已归属公司而缺 market/security 的记录允许复用；明确冲突排除该候选。resolver 返回 MISSING 表示当前没有合适来源，旧 IDENTITY_CONFLICT 枚举仅留输入兼容，不再因为一个坏本地候选禁止整个请求下载。
- 普通 `DownloadCandidate.filing_date` 与 TXT 一样可未知；最新信息日排序仍只排序已知合格公开日，不用 None 或请求日期猜“最新”。
- 旧测试中“坏候选禁止全请求”和私有 `_verify_unknown_date_index` 的完整 metadata 签收要求已被新 RED 反例否定，测试改为候选排除/缺信息合法复用/精确 SourceRef 保持，不删除错字节、错 accession、越界、错公司负例。

责任测试记录：第一轮18项8真实RED/10PASS，11.84秒；补充3项全RED，3.82秒。实现后集中88项86PASS/2FAIL，14.33秒；两失败分别是新测试未使用 exact provider 请求、stage 元组顺序错误，修复测试调用与映射，未放宽断言。完整回归待下一集中节点。

## 连续下一节点：剩余全局身份与元数据门禁

只读审查已证实以下不是猜测；当前入库节点通过后立即按责任层继续处理，不能宣布简化完成：

1. formal envelope 将缺 entity_ids、无明确期次及任意 metadata 冲突整体标 blocked。改为字段级质量诊断；明确请求中的错误归属/期间由唯一选择规则判定，不重复增加形式上的签收。
2. Reader `_describe_version` 因 source_url/title/collector 等任意 provenance 冲突拒绝整个描述、导出和摘要。共用元数据观察须显式列争议字段、不伪造一致性；原文读取只依赖版本和真实字节。历史查询仅受实际使用的公司/期间/公开日争议影响。
3. 现场 runtime_policy 实为 schema2 steady，Reader 却仍自动启用旧schema1许可及坏文件全局阻断，CLI失败时又当None。统一当前配置的steady读职责，旧snapshot仅显式历史compat；不让旧许可文件决定个人项目的访问权。
4. NarrativeTransport 自取当前scoped pin再传给自己验、回放后又全量ref/manifest/policy重复验证。使用一次当前读context/manifest和一次实际字节open；真实source/artifact SHA、locator回放和指定as-of继续保留。
5. latest gap-plan把unknown publication纳入eligible_remote，与最新选择器的已知日规则不一致。统一未知日诊断，允许保存；未知日不冒充历史已公开或证明最新。

下一节点先覆盖争议辅助字段仍可raw/export/current摘要、争议公开日历史不合格、无期次当前可读、显式错误期间不命中、坏旧runtime文件不禁当前根、不同目录同SourceRef、零重复policy自验，再做一次相关责任集成和相同三市场E2E。不得改三个外包独占目录；跨仓消费者需要的调整留MAIN最后统一接线。


## 当前施工：元数据 / 读取 / 恢复责任节点

- 共用 `MetadataObservation` 只读投影：保存原有争议记录，争议字段给 None；元数据坏 JSON 只给质量诊断。`metadata_diagnostics(SourceRef)` 提供无路径的字段名/问题，不扩大 SourceExport v2 固定字段，也不新增存储库或签收物。
- 精确原文打开不再检查财年/公开日。查询按所请求字段处理：明确争议财年不能由文件名重新猜回；争议公开日不进入历史 as-of。辅助身份缺失仍可在公司归属后复用，明确错误/争议的请求字段仍排除候选。
- 现代 reader、resolve/ensure CLI 统一 steady，不自动加载旧 runtime_policy 的 rollout 许可。历史快照只能由显式 compatibility 调用者传入；文件无需重写/删除。格式错误的请求仍是错误，旧有效指纹是生成时观察，读取回执报告当前指纹而不冒充旧指纹。
- `open_described_version` 由读取层一次提供当前描述和真实字节；Transport 删除自取 policy 自验与回放后的全量身份/元数据/策略三重检查。原始 SourceRef、artifact SHA、逐locator原文回放、用户明确 expected_source / as-of 仍在各自责任边界验证。
- Worker 取消标题/声明语言变化和策略指纹的准入阻断。解析类型与真实 source/hash/size 绑定继续负责错误输入。已建立事件和账本保持原样，不因元数据修正或可容纳原件的大小限额变化而重跑模型。
- 发现已完成 batch 的恢复仍有旧指纹和全部当前事实等值门；实际 CLI/Worker RED 1项/6.67秒。改为保留 frozen membership / intent / execution / usage 证据与当前原文字节检查，移除对当前元数据/历史policy的等值许可。不会重签旧事件、artifact、usage；新预算/模型请求仍用新run，防止混账。
- GapPlan 统一来源日期分类，unknown / invalid 保留可见库存 `publication_unknown`，不作为历史missing/newer，亦不能证明not_published；保存未知日原件的能力不受影响。字段仅非空时输出，普通历史wire/hash保持原样。

集中验证过程：19真实RED→19GREEN；Worker/Gap补充5真实RED后75PASS/1旧unknown-date要求；相关公开链239项207PASS/31旧门禁要求失败/1缺真实TXT输入skip，119.76秒。旧要求依据此新产品合同调整为观测当前字节和实际选择负例；不删除错SHA、错期次、损坏原文、真实current limit、证据locator或冻结账本篡改断言。最终集中仍在运行，暂不记全绿。


### 随后整体效率施工：跨批次内容复用

当前node的恢复修复不会改变用户明确发起的不同batch。只读发现 `test_narrative_batch_cross_run_e2e.py` 现有合同明确期待3个不同run同一source仍发3次模型，只对相同结果的对象字节去重；`SourceRevisionEventPayload.input_hash` 包含旧指纹和全source_metadata。不能把“相同run零重跑”说成跨run内容缓存完成。

下一责任节点先调查 selector 对title/kind/language的真实使用，TDD覆盖同SourceRef、同解析/选择/模型版本、不同目录/title/url/来源日期修正的默认新batch应复用内容且新增模型费用0；明确refresh/变更生成算法或实际片段才生成新版本。生成身份应由真实源字节、parser/selector版本、selected spans、原语言、prompt/model配置决定，元数据用于当前来源描述和显式选择。沿用AUTO及content-addressed artifacts，不复制原件、不增许可receipt/缓存数据库、不给新run冒认旧费用。旧事件/用量保持原样；先验证默认复用与显式refresh契约，再实施。此项尚未改代码，单列后续，不盲目从旧事件hash删字段造成账本或selector行为漂移。


当前更新：本文件“连续下一节点”五项已实现并通过集中测试与冻结三市场同规格回放，详见metadata_responsibility_acceptance.md。早期RED/施工结果只为历史记录；尚未完成的是跨run内容复用、格式/诊断/RF输入主线接线与两组新研究，不能重新把已关闭门禁列成待做。
