# R7 跨仓过度门禁只读审计：FF / RF

状态：**只读调查完成，待 ROOT 实施；不是整改通过收据**。范围仅 `filing-fetch` 与 `revenue-forecast` 的当前运行入口。未 fetch/checkout/改索引/清理，未读 API key 文件、配置值、环境变量值、签名 key 文件、原件或模型；未运行应用、测试、下载或收费调用。源码与工作树快照、实际 AST caller 和四份 RF WIP 的只读 SHA 在同名 JSON。Dayu、IQS、Dashboard 不在本次范围。

## 结论与优先顺序

**仍有与“300KB”同根的门禁，主要在 RF，而非 FF 的新采集流程。** 不是把每个出现 receipt/gate/limit 的名字都删掉：已授权下载意图、真正字节完整性、公司/期间/as-of、引用支撑与币种单位正确性仍有明确责任。本次应先移除“附带策略/诊断有多大、写了哪个审查状态、整份历史登记簿是否可写”对当前有效材料的反向否决，再合并同一事务里的重复检查。

| 优先级/项 | 当前真实阻断 | 最小收敛 |
| --- | --- | --- |
| P1 RF-01 | 叙述完整响应 1,310,720B 内，reading_context 另限 192KiB、通用树/字符串/数组计数；质量诊断另限 64KiB，任一超限整体拒绝引用 | 一个实际传输资源预算；核心引用结构严格，附带 policy/trace/diagnostic 由生产 owner 有界采样/摘要并保 count/limited，不用其体积否决已有引用 |
| P1 RF-02 | 精确已采用 summary proof 另限 128KiB；另一公开绑定路径将完整原始 span 硬截为 10–500 字符合同 | 复用同一已验源引用与完整局部 closure；按真实输入资源预算，不另设证明大小许可。展示短摘录与完整定位分开，不能截原文凑 500 |
| P1 RF-03 | 明确称为 diagnostic 的 prompt-review/assessment，其形状、状态或新诊断规则不合旧枚举，仍使原文或 narrative 读取 fatal；还在多个 owner 重复实现 | 同一 RF wire 诊断投影 owner；未知/损坏/来源不符注记作为不可依赖诊断或丢弃该注记，保留已实读字节和引用。不能把注记当已审查许可 |
| P1/P2 RF-04 | 每次正式预测必须先成功写全局 publication registry；任意历史行损坏/目录不可写会否决本次已正确算完的结果；每次还反复切换只读位 | 自足报告/输入/结果 hash 与实际写入是正式产物依据；版本发现索引由发布 owner 维护，可重建且故障诊断，不成为算法使用许可；取消索引 chmod 开关 |
| P2 RF-05 | 同一调用内 reader、builder、持久 DTO 多套 receipt/manifest/review 规则、两次相同原文 SHA；CLI 又重复强校验已校验结果 | 不删必要信任边界：跨进程接收验一次；直接公开 builder 入参验一次；内部已验 immutable read/verification result复用；冻结输入重新载入仍校验 |

以上不代表每个阈值已经造成当前现场失败。本轮仅静态审计，实际调用条件已证；本机是否已有大于阈值的具体合法材料、registry 是否正故障均未运行/读取生产产物核实。不要据此声称整个 RF 主线现在不可用。

## 现场基线与调查方式

- FF：`main`，HEAD `5ec54e02b8db69d0f38adfd0d7cee58f04f3a2b8`。未跟踪：`.planning/du11-empty-placeholder-original.py`、`config/FMP_API_KEY.txt`、三个 `pytest-of-ff-*` 目录。只记录 Git 路径；key 文件没有打开或哈希，也不清理任何路径。
- RF：`main`，HEAD `957c6283d3381d23c39515afd3a09147d8201c7b`。四个既有 assurance WIP 和 `.planning/m8-native-adoption-20261031/`、`.planning/source-quote-adoption-20261030/`、`delivery/dashboard-b34-wuxi-20261101/`、`output/` 保持原样；没有进入这些运行产物目录审内容。
- 先用 CodeGraph context/files；FF 索引仅列 2 个 script、RF 仅列 32 个且 run_forecast 位置落后。实际当前分别 18/79 个 runtime Python。没有初始化索引；对当前 scripts 的 AST 作只读 caller 检索，以真实文件/行号补足，不据旧索引断言“无当前消费者”。
- 普通沙箱对兄弟路径读 Git 被环境拒绝；正常获准 host 只读成功。此为运行环境边界，不是项目许可控制；没有改 ACL 或转用另一通道绕过拒绝，没有重复问用户。

## RF-01：多层固定大小把诊断/配置变成引用许可

**实际入口**：`narrative_source_preparation.main` → `company_wiki_narrative_reader.read_narrative_context:46-57` → `validate_narrative_response` → 普通 `_bundle_contents:1014-1027` 或投影 `_projected_response:1259-1278`。

**条件与代码**：

- `company_wiki_narrative_contracts.py:23` `BODY_LIMIT=1_310_720`，是实际子进程 stdout 收集预算；不是 4MB。
- 同文件 `:521` `READING_CONTEXT_LIMIT=192*1024`，`:895-900` `_reading_context` 无条件先扫 `_reading_json` 后按完整 canonical JSON 大小拒绝 `reading_bytes_limit`。两种当前 bundle 都必经。
- `:533-564` 同一 payload 又单设 visited<=30000、depth<=12、string<=16384、object<=256、array/rows<=4096；后续 policy<=128、facet<=16、group<=512 等。部分是结构/引用分区的已发布合同，不能盲删所有字段验证；但 policy 文本/diagnostic 规模不等于来源真实性。
- `narrative_summary_observations.py:135-151` 把完整 assessment 序列化后 <=65536 作为 `_require`；`_summary_observation` 捕获 ValueError 后改成 blocked/invalid_summary_assessment。不是仅丢弃超长说明。

**共用根因**：多个消费者各自把“有限元数据”解释为固定授权额度。CWP 调整一个上限，RF 仍在更低的另一层否决；策略与诊断随泛化增强增大，反而阻断选中的正确来源。

**具体方案**：由公共 wire 传输 owner 使用既有可配置实际资源上限，已声明 artifact byte_size 与实收 SHA/长度继续绑定；不放任无限 stdout。core SourceRef、EvidenceSpan、group/support/context partition、原始引用仍严格验证。policy/trace/assessment 的明细在所属 producer 采样/摘要并保计数和 limited；如需要完整审计，保 producer artifact 引用，不要求每次 RF 完整搬入。删除内部重复 serialized-size 判决，不用把 192 改成另一个拍脑袋常量。公共 schema/feature 如需调整由双方版本化 wire 同步，RF 不 import CWP 私有实现。

**定点用例**：两个当前 bundle 各一份合法来源，读取上下文略超 192KiB、assessment 略超 64KiB但整体在明确传输预算内，引用与 SHA 不变时可读；坏 span hash、support/context 交叉、错误父来源仍拒。stdout 真超资源预算仍有限停止、回收自有进程。未知诊断不授予 semantic accepted；limited 仍诚实。

## RF-02：本地采用证明和旧短摘录限制

`source_narrative_context.consume_narrative_input:235` 调用 `build_summary_provenance`；`narrative_summary_provenance.py:60-98` 已只复制选中 claim closure，没有复制全 bundle。但 `:30,117-129` 再将**整份 proof**限制在 128KiB，`contracts/document.validate_evidence_claims:760` 在正式输入验收必调。`validate_summary_excerpt_bound:103-111` 又复用 128KiB 对完整 anchor 验长。源/claim/entry/spans/局部 context 中有重复文本与 ID，该大小不是有效引用的事实条件。

另一仍公开的 `research.input_evidence.bind_parameter_evidence` 分支接受 binding.narrative_context，调用 `_bind_narrative_span:289-313`，要求完整 raw_text 10–500 字；`contracts/document.py:645-653` 对未附 summary proof 的 claim 也要求 10–500。它不是新 `consume_narrative_input` 的主要 summary-use 路径，**不能冒称新 summary 都先卡 500**；但它是尚可调用的公开兼容 authoring API，并非仅历史测试。

**方案**：保 exact source/claim/完整 context/formula closure 的单 owner 检查，去 proof 体积许可。对当前 narrative source 使用完整已定位 anchor；只需短展示时另选有正式 locator/offset 的原始子范围，完整 raw span 留在来源层，禁止直接切片字符串再冒原 span ID。普通手填网页 excerpt 是否保持简短是展示/authoring 建议，不能倒逼 source-owned 长单元改写。旧 artifact 原字节与旧 schema replay 不重签。

**定点用例**：原始合法已定位 span >500 字，两公开绑定入口语义一致；完整局部 proof >128KiB但有实际输入资源预算时通过；篡改一个 anchor 字、少一个必需 context、误币种或把 ratio/stock 当收入仍失败。未附合法来源证明的任意长文字不能靠取消长度检查获得真实性。

## RF-03：optional review 的“诊断”仍是硬门

**当前允许的部分也要说清**：None/not_reviewed 已能通过，不存在“每份原文必须人工签收才能读”的常规要求。问题是**可选注记只要存在且不合旧形状，就反向使真实来源不可用**。

- `company_wiki_source_reader_v2._validate_success_receipt:341` → `_validate_review:194-209`：形状/旧 status 枚举、review.source_sha、evidence/policy hash、reviewed_at 错误都抛 SourceVersionTransportError；这时原文自身 SourceRef/SHA/manifest 尚有独立验真路径。
- `contracts/company_wiki_original.validate_receipt:183` → 该模块另一份 `_validate_review:218-229` 重复同一规则。随后 `company_wiki_source_v2` builder、`contracts/source_provenance` 的正式输入验证会再调用它。
- `company_wiki_narrative_contracts._diagnostics:507-513` 把 prompt_review 精确五字段和三个旧状态作为整体 bundle 必经校验；普通和 projected 当前响应都调用。
- assessment 同样存在消费者硬编码 `_WIRE_RECIPES`（当前 4.2.0/4.3.0）与诊断 rule/dependency 名单。发布 schema 的核心不兼容当然要报告；但新的 source 诊断代码/assessment 算法版本不应被当成缺人工许可，也不能让 RF 重复实现 CWP 的资料分类/语义判断。

**为何多余**：用户已明确取消逐材料 prompt review 许可，并授权包括审查存储故障在内只作诊断。有效原件的实读、原件 SHA、真实父来源/期间/as-of 与摘录定位不能因为一份旁注坏了而失效。旁注的“来源不符”只能说明这份旁注不可依赖，不证明已实读原件错误；更不能把未能解析旁注伪报 reviewed。

**方案**：在现有 RF versioned wire owner 中统一诊断投影，保“未评估/未知/损坏/其他来源注记”状态；非法或不可理解注记不转成 trusted review，不改变 raw bytes/citation validation。移除三处同义硬阻断/重复枚举，consumer 不为每个新 CWP 诊断加许可。assessment 的数值/引用/覆盖一致性属于公开 core DTO则保留，同一 schema 内新诊断 token 按数据保留，semantic_status 不能凭任何注记升为真实接受。不要简单 `except Exception: pass`，也不要静默制造 not_detected。

**定点用例**：已验证相同 raw/ref，review=None/not_reviewed/storage-error/新诊断 shape/foreign review annotation 都可读并留诚实诊断；原件 SHA、manifest identity/期间/as-of 改错仍拒；annotation 不得让 claim 自动 actual/accepted。真实 CWP handler golden→RF 两种响应/正式 source record 联调一次，防再次仅一边松另一边仍挡。

## RF-04：全局登记簿成为正常预测的许可中心

`revenue_forecast.main` → `prepare_forecast` → `revenue_core.run_forecast:418-486`：正式结果已计算、强验证、生成 receipt/hash 后，仍必须 `register_publication` 成功才返回。注释明确“missing/unwritable registry fails whole publication”。

`publication_registry._append:123-143` 在每次 append 先 `_read_entries:74-100` 读并校验全历史链；一条旧行坏、旧 confidence revision 无法识别或目录不可写会拦住这次新公司的有效输出。`:105-119`、`:136-143` 每次清/设只读位。链式 JSONL 不是原始财报，当前用户已允许中间文件重建；它作为全局权威形成额外 permission/state 依赖。

**收敛**：报告自带冻结 input/source refs、计算验证、结果 hash和实际版本化落盘；原子写入本次产物失败当然不能声称已保存。全局索引只负责版本发现/检索，可从已验证产物重建；索引故障记录具名诊断，不能否决计算或打印/导出。移除索引只读位切换，不改原件保护；旧 ledger 原字节保留给显式 audit，不在本次静默重写。发布 owner 在完成实际产物写入后维护索引，避免“先登记但输出没写成”。

SKILL 还写 invest-* 默认 require_registered_input 与 host_signed；那是本次两仓以外消费者合同，**本轮未进入 invest 仓验证，不声称已清理**。若 ROOT 采用本简化，应同步其“自足验证产物可用，registry/attestation为来源状态”适配并做一份离线互操作；不是再要求用户人工签收。

**定点用例**：旧 registry 故障/不可写但本次输入正确，仍可计算、validate-only、导出实际版本且有索引诊断；本次 output 写失败不能伪报成功。篡改冻结输入/结果仍拒。正常可写索引可记录与重建，重跑同公司版本不覆盖原报告。

## RF-05：责任重复与快路径

一条实际调用：`source_preparation._prepare_source_ref_v2:263` → `open_source_version_v2` → reader 自有 receipt/manifest/review/日期校验＋`:350` 全文 SHA；然后 `:272` → `build_revenue_source_record_from_verified_read` → 另一 `contracts.company_wiki_original` 校验＋`:143-145` 再 hash 同一 immutable bytes；builder末尾又 `validate_source_provenance`。持久输入重新载入的校验必要，但同一未改对象多套定义会漂移（RF-03已经有真实例子）。

另 `revenue_core.run_forecast:452` 已强验证结果，`revenue_forecast.prepare_forecast:48-51` 又 `validate_forecast_output` 重跑强验证；可选 `render_markdown` 入口还验证。公开任意字典入口确实不能盲信 caller，不能统一加 `skip_validation=True` 或按成功布尔跳过。

建议单个 `VerifiedOriginalRead`/已有验证 context owner 传完整不可变结果，内部 compose 复用；公开 raw builder仍完整验证一次、序列化后重新加载仍验。sourceclock、canonical identity、源字节 digest 的规则只定义一次；此为减少重复与漂移，不删除事实核对。预测输出也仅在同一 CLI 事务复用已绑定 exact payload/input hash 的 verification result，公开 render/validator仍验输入。

**定点用例**：同事务读取1次/原文哈希1次且没有二次 identify/download；直接调用公开 builder 的坏 raw input仍拒；冻结结果改1个字段不能复用旧 verification。这里没有测实耗时，不承诺节约秒数。

## FF：查到的控制与应保留的边界

本轮未找到 FF 当前 v2 路径上的 manual receipt/approval/canary/expiry/license 门禁。`fetch_filing._download_intent:1100-1116` 以请求 filing_intent 为唯一意图，旧 `--allow-download` 只是兼容输入；矛盾显式参数报 request_error 是避免同请求两种行为。`filing_contracts:252-280` 旧 authorization 可选、仅 provider/accessions/caps，注释明确 expiry/unsigned policy hash不决定许可。不要因为名字仍叫 authorization 就冒称仍需授权文件。

以下是实际责任，不应取消后改成偷偷无界工作：

- 下载 bytes/time/fee、ET campaign累计/未知消耗、请求 reuse_only 等：请求与所属 resource owner 执行；不重复人工确认。
- `ff_process_transport` 32MiB stdout并发收集上限、共享 deadline、自有进程树回收：这是实际 I/O 工作边界，不是字段大小当材料许可；可用同一任务传输预算收敛，不能变无限缓冲。
- `ff_configuration.read_json_object` 64KiB：AST只找到小连接配置的两个调用（root config与ET launch config），没有用于分析文档/reading policy/公司财报。此次不把它包装成已经发现的分析资料门禁。若将来承载大策略应拆职责，不能复用该 reader限额。
- `ff_local_preparation_observation` 128KiB/计数限制：超限或不合法返回 None，装饰性 observation不会因此成为 source 可用许可；真正 local status/blocks_download 属原始字节验证/既有预算状态，不是它的 JSON 大小。RF本机源SHA校验和FF对跨进程字段绑定保留，别与人工身份审批混为一谈。
- 文件/来源必须与指定公司、文种、期次、as-of匹配；CWP 是身份与原字节 owner，FF是路由/adaptor，不再自己扫描多根、维护第二允许根或全仓 clean/CI 签收。实际 runtime AST未发现正常使用前跑 Git clean/CI 的入口。

## 已退休、仅可选或必要的部分

- RF `processed_artifact_canary.py` 只有自身 main调用，当前预测/source preparation 没有 caller；它是独立只读工程工具，不是当前 canary放行门。`installation_manifest.manifest_sha256` 只在 `--version` 分支用于诊断，不是预测发布许可。不恢复或重复删除历史工程控制。
- RF host签名可选；`run_forecast` 已允许 provider未配置/失败时标 `unattested`，不是RF本身必须签名才能计算。声称 host_signed却签名不符仍应拒绝该真实性声明；不要把伪签名标成有效。不读取环境值、key或trust store，故本轮不知道本机实际是否配置 signer。
- 企业/文档身份、原字节 SHA、原始定位、support/context partition、真实来源期次/信息时点、币种/单位/公式与收入时间口径：保留所在单 owner校验。它们不是人工许可，也不是“所有门禁都删掉”后可以由模型猜的内容。
- 只有资料处理/审查元数据未知，不整文拒读、不禁止原件复用；未知涉及引用所需具体证据则只对相应推断保持 unknown/partial，不能自动补真值。

下一步由 ROOT 合并 CWP 自审发现与本报告，按以上责任节点实施与关键联调。**本作者 STOP**，未新增外包/审批节点、未改主 PWF或两个仓库。
