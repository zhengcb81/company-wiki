> 2026-10-03 当前施工由 [task_plan.md](task_plan.md) 的S0–S6统一定义。本文保留历史技术背景，旧审批/签收、原件处置和逐小步审查要求不再执行；原件全部保留。

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

# 测试与验收计划：叙述性证据流水线

> **2026-09-29 更新：**本文件保留样本/失效断言；当前运行节奏、节点名和权限语义以[门禁清理方案](gate_and_contract_simplification_2026-09-29.md)及[并行总计划](parallel_harness_orchestration_2026-09-29.md)为准。旧 G0–G4 映射到当前 G-0/G-A/G-B/G-C/G-D；下文“人工授权、独立审查、权限拒绝”是历史设计，不得作为新测试的正向前置。开发只跑受影响目标测试，大节点跑对应真实 E2E。测试仅写唯一隔离 run-id 根/临时 SQLite；`config/source_catalog.yaml`、真实 `companies/` 和生产 catalog 不写。结束恢复测试目录原状，新增下载/派生文件清理；崩溃恢复只处理本次核验过的精确路径。样本见[findings.md](findings.md)。

位置透明的通用负例沿用 R4 [L01–L12、P01–P03](../painpoint-outcome-audit-2026-09-05/simplified-test-matrix.md)，本表仅补叙述证据跨根 ID/locator/摘要与真实 consumer 断言；不在每张文档卡重复四根测试。G0 只冻结目标合同；正式 G2 接线须有 R4 B 阶段独立验收。届时 pilot `source_id → raw path` 映射必须退出跨仓 reader，具体见[边界复核](data_lake_boundary_review_2026-09-27.md)。

## A. 测试夹具与真值冻结

1. **探索集**：P01–P10、T01–T02 共 12 个真实原文；C01–C11 是 11 个局部正例，N01–N02 是 2 个整件负例。首次运行核对完整 SHA-256 与文件长度，不匹配即停止并更新真值版本，不能悄悄替换。
2. **标注格式**：每个候选记录 `source_sha256, document_kind, language, published_at, page_or_line_range, raw_text_anchor, content_role, modality, expected_select, expected_topic, required_qualifiers, linked_risk_or_question, annotator, review_status`。探索集可由一人标注并用原文 locator/SHA 自动回放；只对有争议或高影响的样本在 G-C 做集中复核，不要求每段双人签字。锁定 manifest 哈希；探索卡不充当全篇穷尽真值。
3. **留出集**：W0 从探索集之外按年报、半年报、季报、IPO、定增、可转债、投资者关系、英文 TXT、制度/通知 9 层各至少 4 件选取，合计至少 36 件，作为**盲测最低集成样本**，不能凭每层 4 件宣称总体召回率。每层覆盖不同公司，尽可能包含不同时点/修订版本；IR 与招股/再融资层须包含大表格单元、业务表和跨页证据。W0 在看候选结果前按目标误差、文档聚类和稀有正例数量计算每类正式评估所需样本量；报告按文档聚类的置信区间，若下界未达到预注册门槛或样本不足则为 `insufficient_evidence`，继续独立扩样，不能把零错误的 4 件当作放行证明。来源数不足或版权/可用性不足时记 `blocked_decision`，不得用探索集重复凑数。标注全篇候选和应跳过范围，**将整件被跳过文档中的业务事实漏收率单列**；锁定哈希后实现者不得据留出集调参。
   这项是自动叙述质量与默认发布的独立评估，不是 CWP verified reader、FF/ET 精确采集、RF 证据完整性或无关派生清理的全局前置；样本不足只把叙述质量结论标为未证实。
4. **额外对抗夹具**：在临时原文中人工构造：大写扩展名、错 sidecar、坏 SHA、坏 URL、PDF 空白封面、同页财务表+业务段、业务产品表、覆盖整页的 IR 大表格单元、跨页问答、问中错误数字被答复纠正、多说话人同段、网站编辑文本伪装成管理层、原文中嵌入“忽略指令/调用工具/泄露信息”的操作命令、否定词被删除、过去预测与当前事实冲突、源 retired/撤回、公开时间晚于查询时间、TXT CRLF/LF 和 UTF-8 异常。人工构造样本不得冒充真实业务语料分数。
5. **隔离运行记录**：G0 冻结源 manifest、源码/配置和 parser/selector/prompt/model 版本；G1–G4 各保存一次版本、关键命令/退出码、随机种子、临时 catalog 路径和结果摘要。普通目标测试只留失败与退出码；不为每次运行重算所有原文或输出 SHA。时间使用固定时钟。任何测试命令如缺临时路径保护，应先补保护，不能指向生产路径试错。

## B. 13 张探索卡的最低断言

| 卡 | 输入 | 自动断言与人工复核重点 |
|---|---|---|
| C01 | P01 | 多产品分别标阶段；重复订单、客户端量产验证、拟议收购不混为“已量产/已收购”；可回查第 40 页。 |
| C02 | P02 | 5–10 年愿景及“超过60%的设备市场”均保留 `planned`；原 PDF 将“超 / 过60%”拆在相邻 locator，选择预算必须成组保留两段，锚点须精确命中数字片段；不写既成覆盖，公开时点与后续年报分开。 |
| C03 | P03 | 第 3 页四款新品运营描述入选，“部分”保留；同页财务表不物化业务证据。 |
| C04 | P04 | 第 114 页业务产品历史基线入选；83 页旧章不能以一个最终 evidence 代替；招股时状态不变成 2026 年状态。 |
| C05 | P05 | 可转债类别正确；项目必要性与第 13–14 页执行风险成组；预测与已完成分开。 |
| C06 | P06 | 定增注册稿类别和版本正确；第 3 页认证风险与第 101 页项目逻辑配对；例外条件限定到原有锻件。 |
| C07 | P07 | 问 16 和回答完整，预计建成日期有披露时点；不推断后续实际建成。 |
| C08 | P07 | 问 15 跨页不断裂，估值比较标 analyst/investor premise，不作为公司事实。 |
| C09 | P08 | 第 2 页问题 3 的“小于 5%”是被纠正前提，回答“超过 25%”的实体范围保持准确；合作意向不等于收入。 |
| C10 | T01 | 第 124 行起为 transcript，第 1–123 行为编辑材料、第 334 行起为尾注；摘要英文，角色与行定位可回原 TXT。 |
| C11 | T02 | 第 20 行准备发言、第 178 行问答、第 598 行尾注；两个子问题/多个回答不合并错配；`too early to speculate` 保留。 |
| C12 | 版本化 filing-fetch companion-transcript × earnings-transcripts adapter/provider fixture | 新版本 financial filing 请求按合同默认伴随至多一份匹配 transcript；复用命中 provider 调用 0 次；无明确公司/期次采集请求时零 provider/网络调用与零写入；有明确请求时传入已验证证券映射、精确 fiscal period 与 as-of 限制。canonical TXT 字节只含合同定义的未翻译正文，正文不变；分别核对 provider payload hash 与 canonical file hash，sidecar 必须有真实 HTTPS URL/provider/time/SHA；second call 幂等；not-found/unsupported/ambiguous/timeout 只改变 transcript 子结果，不抹掉 filing 成功。旧 filing-fetch schema 仍只产生旧行为。 |
| N01 | P09 | 原文可登记/检索；零 `SelectedEvidence` 和零业务摘要；终态 `skipped_no_narrative`。 |
| N02 | P10 | 不从会议通知生成电话会议回答；零业务证据；终态 `skipped_event_notice`。 |

G1 集成运行统一断言：选中来源身份可信、locator 回读一致、角色/语言/时点齐备、摘要每条事实的 evidence ID 可解析。日常修改只跑受影响样例；探索卡通过只表明已覆盖已知失效模式，不代表总体质量。

## C. 分层测试矩阵

| 层级 | 具体断言 | 建议现有测试入口/新增位置 | 放行条件 |
|---|---|---|---|
| G1–G4 历史端到端生命周期 | G1 raw→source record→outline/selected evidence/summary→package→locator 回读；G2 export→consumer readonly contract；G3 enqueue→worker subprocess→artifact/export 与暂停、崩溃恢复；当前 G-D 只演练**可重建派生**的 scratch 删除/重建/恢复，不删除唯一原文。所有输出都限制在唯一 run-id 根目录；结束后测试树恢复到运行前清单 | 当前映射见[并行总计划](parallel_harness_orchestration_2026-09-29.md)：G-0/G-A/G-B/G2b/G-C/G-D 集中运行，复用本表具体断言；临时目录 snapshot/cleanup harness | 树基线逐项一致、无进程和产物遗留、无外部写入；G-D 逐批按实际消费者与自动清单放行，无人工批次许可。当前 P06/T02 CLI smoke 不是完整跨仓门 |
| 分类和写入 | sidecar 优先于文件名；`.pdf/.PDF` 等价；P05/P06 不换 source ID；TXT 原字节与 HTTPS provenance；旧 US filing 路由无回归 | `tests/unit/test_source_catalog_scanner_direct.py`；`tests/contract/test_source_catalog_canonical_writer.py`、`test_source_catalog_acquisition.py` | 无来源重建、无越权下载、无翻译 |
| filing-fetch transcript acquisition | resolver 复用优先；一次明确的公司/证券+FY/Q 采集请求；adapter 只在隔离 staging 调用；保存到 company-wiki 原文目录并核验 raw-byte SHA/sidecar；复用幂等；transcript 错误与 filing 子结果隔离；测试禁止真实网络、共享生产 cache/config/log/lock 写入 | 新增 `tests/contract/test_filing_fetch_transcript_adapter.py`，使用 fake adapter/provider 与 tmp_path；G-A 再用只读真实 TXT fixture 核对解析输出 | C12 全通过；未请求或歧义期次零调用/零写入；不下载翻译副本；真实 provider 能力/条款/权益不明时只禁用该 provider，离线测试继续 |
| filing-fetch × earnings-transcripts acquisition-to-summary E2E | 从新版 filing-fetch public orchestration 请求 financial filing + related transcript；fake provider 替代正式 exact-period adapter；经隔离 staging 和 canonical writer 保存至 scratch company-wiki raw，核验双 SHA、HTTPS sidecar；继续解析、选择、英文摘要、source locator 回读；同 run 覆盖 transcript reuse、无明确请求时零网络和 transcript 失败但 filing 成功 | `tests/e2e/test_filing_fetch_transcript_pipeline.py`，唯一 run-id 根目录与目录基线恢复 harness；必须经过生产同一 orchestration/adapter seam；fake provider 不联网，current shared-config CLI 不直接启动 | ET/FF/CWP 真实 producer 合同冻结后实现和执行；不依赖 RF 下游 G0。四条结果路径通过、无越界写入/翻译副本、清理后目录快照一致；可选 live canary 受 provider 能力和费用预算约束，不需逐次人工授权 |
| 解析/定位 | PDF 页文本/表格双视图与锚点覆盖，P08 第 2 页 29/30 块相交仍拆多问答，P04 第 114 页业务表不丢；跨页多原子锚；`sort=True` 页偏移不可混旧规范化游标；TXT 行/字节偏移与编辑边界 | `test_source_catalog_section_extractor.py`、`test_source_catalog_evidence_query.py`；新增双视图/多锚/TXT fixture | 选中 evidence 的每个原子锚 100% 回读同一 raw SHA；未知精度显式标记；解析版本变更触发重验 |
| 选择性物化 | P04 长篇 PDF、P09 制度 PDF 和 T01 英文 TXT 走新 DAG 前后比对：旧 `normalized.md` 与旧 `evidence_spans` 零增量；只计选中证据与小型覆盖账本；skip 包可见后才放行后继 | 新增 outline/selector 隔离集成测试；同时测试不存在旧 normalized 的冷启动路径 | 新 DAG 无隐式 `source.normalize`/`normalize_catalog`；selected locator 可从 raw 回读，负例无业务切片 |
| 选择与摘要 | 13 张卡、hard negatives、错前提/否定/阶段/风险、无来源句和原文内操作指令拒收；抽检被 skip 的整件文档与未选页；注入不可读候选页/OCR 失败/不透明表格 | 新增 selector/summary contract tests；探索样本只读回归 | 全部 13 卡通过；无无引用事实、角色错置、负例误收或执行原文指令；skip 漏收率单列并满足 W0 门槛；覆盖不完整不得输出整件 skip 或假称完整摘要 |
| artifact/DAG/export | 输入 hash/producer/schema/role 绑定；未知 role 拒绝；旧 v1 可读；新包 ID/哈希、撤回、增量重放 | `test_source_catalog_artifact_handle.py`、`test_source_catalog_source_bundle.py`、`test_source_catalog_artifact_reconciliation.py`、`test_source_catalog_export_index.py` | 旧合同不破，新合同不误用 invalid/retired/未来来源 |
| 全文检索/回源 | 中文三字词、两字词、英文词、精确短语、OCR 页、来源/历史时点过滤；命中后从 raw 重新定位；比较轻量索引与查询时解析。当前 prototype 对选中 evidence groups 做内存 BM25；pilot resolver 已从调用方 raw-path 映射按 hash/parser/selector 回放并在 12 样本 E2E 中核验，但不连接 catalog 或正式 source service；canonical `EvidenceQueryService.lookup` 仍只读旧 `evidence_spans` | 临时库 benchmark 与新搜索合同测试；`unicode61`/trigram 两个失败夹具；`tests/unit/test_narrative_retrieval.py` 覆盖中英短词、短语排序、状态、回源重放与篡改失败；`test_narrative_g1_pipeline.py` 验证两样本检索与 12 样本所有选中组回源 | “硫化锂”“中试线”“出海”按冻结查询合同检出；两字词不因 tokenizer 静默漏掉；返回 source ID/locator 后必须能按同一 SHA 从原文回读；索引+缓存字节和 p95 不越 W0 门槛。pilot resolver 不代表正式 G2，通过仍需冻结 package schema/version、来源授权、生产 API 与 consumer 合同 |
| Worker | 先修 `automation` 单执行者事务，再受控多文档并发；白名单、暂停代际、双库 saga、20 类故障、共享限流 | `tests/unit/test_automation_{store,worker,migrations}.py` 与既有 source-catalog worker/lock/控制合同测试；新增 F01–F20；完整协议见 [并发实施手册](worker_parallel_execution_plan.md) | 所有中断点可恢复或失败关闭；同 job key 至多一个 accepted artifact；prepared 不外露；下游等前置 visible 才 READY；暂停后无新 claim/网络/产物激活 |
| 叙述证据包消费合同（G2a） | StockWiki 与 revenue-forecast 分别以真实 reader/adapter 消费 CWP 版本化来源/选择证据；覆盖旧/新/未知版、retired、撤回、历史时点、`partial`/`needs_review`。同 SHA 跨 company/dayu/Dropbox、副本失踪、priority 置换与目录移动不改变证据 ID/locator/摘要引用；不同 SHA 不能换版，来源身份或原文字节错误不能换 root 绕过。旧 pilot `narrative-evidence-selection-bundle/0.2.0` 不得冒充正式 `/2.0`。 | 复用 R4 L01–L12/P01–P03；StockWiki/RF 各自的薄 v2 reader 通过 CWP 真实 producer golden；外仓测试由各 owner 运行，本仓提供版本化只读夹具与原文 SHA | 两边 reader/adapter 均通过自动合同和真实 locator 回放；正式 reader 零 root/path 业务分支且不接收 pilot raw-path map；不跨仓写库，不把来源摘要当已接受投资命题。 |
| 可选身份互操作（G2b） | StockWiki 身份库/serializer 生产真实 identity snapshot；IQS 2.2 schema/公开 JSON 校验 CLI 验 issuer/security/listing。新的 mapping DTO 四态：`mapped` 唯一、`unknown` 已查无结果、`ambiguous` 多候选、JSON `null` 未尝试；不输入叙述证据包/文档正文 | StockWiki 本仓 DB→serializer golden 与 IQS CLI 正反例，均在各自 owner 测试根；总指挥在独立 G2b 根做只读跨仓核对 | 缺少可选映射仍能运行；歧义不可自动合并；身份功能单独放行，不是无关派生清理或叙述消费的全局前置。 |
| 性能/空间 | 同一 12+留出集在相同机器/版本对比现行/新流程，分别计 CPU/墙钟、LLM token/调用、SQLite/WAL/衍生文件、p95 查询 | 隔离 benchmark 脚本，记录命令、硬件和结果文件哈希 | W0 签门槛全部达成；空间按全量占用比较，非只报 DB 主文件 |
| 旧主库提前退役 F0–F5 | 17 张非 span 表与 active 旧 span 的全量主键/digest 差分；旧库/压缩包 SHA、`zstd -t`、完整解压流 SHA/长度逐字节相同；原库和影子库 `quick_check`；active `evidence`、目录/resolve/filing-fetch、retired 旧证据明确归档提示；三方当前合同；切换中断与切回 | [本轮运行卡](implementation_run_2026-09-26.md)的版本化复制脚本、双读夹具、流式备份校验、空间峰值与 review receipt；**不做完整落盘恢复** | 原文和来源历史、active 证据不丢；retired 旧 locator 不伪报无记录；Worker 保持 paused；压缩流与原库完全相同；F4/F5 逐项门禁通过；净本机释放达到预注册门槛 |
| 低价值原文处置 D0–D5（历史、暂停） | `skipped_*` 只表示不生成叙述摘要；当前唯一 raw 全部保留，不进入 G-D 删除清单。旧 OCR/附件缺口与来源引用继续作为诊断背景 | [原文处置卡](raw_disposition_plan.md)只读历史研究；当前 G-D 仅测可重建派生 | 不因低价值/重复或人工复审状态删除唯一原文；原文缺失报事故，派生净字节按同卷结算 |
| 旧库迁移（F0–F5 已完成） | 历史副本、行数/哈希/外键、引用差分与故障注入收据只读保留 | [已完成运行卡](implementation_run_2026-09-26.md) | 按用户要求没有做完整备份落盘恢复演练；此行不是未来 G-D 的重复门 |

## D. 定义指标，W0 锁阈值

- **证据召回率** = 留出集人工标注为必须入选的独立业务事实中，能由正确角色/时点/模态的 selected evidence 完整覆盖的数量 ÷ 必须入选事实总数。分别报各类型与宏平均，不能只报全局平均。
- **证据精确率** = 系统入选且被人工判为真实业务证据的单元数 ÷ 所有入选单元数；同时列负例文件误收数、标准财务表误收数、网站编辑误标数。段落边界不同但事实一致可按 W0 冻结的匹配规则计，不能运行后放宽。
- **locator 成功率** = `source_sha256`、页/行/字符范围均与 raw 回读一致的 evidence 数 ÷ 所有入选 evidence 数。只给页级时若合同要求段级不得当成功。
- **摘要支持率** = 人工复核的原子事实中，引用的 evidence 实际支持相同实体、条件、时间、角色、数值/单位/否定的数量 ÷ 全部原子事实数。无引用句计失败；空摘要不计成功。
- **效率** = 每文档总墙钟与 LLM token，另列最慢长文档；**空间** = raw 保留 + 全文索引/缓存 + 所有 normalized/selected/summary 文件 + SQLite 主库/WAL/索引/必要备份的真实增量；另列 paragraph/table-cell/空 cell 行数与 skip 包大小。只比较同一输入、同一硬件和同等检索能力。
- **原文处置错误率** = 冻结盲测中被判可删除、实则含应保留业务事实或已有有效引用的来源数 ÷ 被判可删除来源数；另报各文档类型、实际误删反例、`blocked` 分母及删除后无法回源件数。D0 测同卷实际字节，`observed_size` 只作定位线索。W0 预注册统计门槛；样本不足不放行唯一原文自动删除。
- **门槛冻结**：探索集 13 卡全部通过、关键语义错置为 0、负例业务切片为 0、选中 locator 100% 可回读、暂停写入为 0，是确定性安全门槛。留出集每类召回/精确率、skip 漏收、p95 延迟、时间/空间收益的数值门槛与样本量/置信区间方法，必须在 W0 **看过现行基线并听取消费者容忍度后**签定、锁 manifest 和评估脚本；此时尚未有这些数值，状态明确为 `UNDECIDED`。未签或置信区间证据不足不得宣称质量或性能达标，不可把“略有下降/降低”自行解释为合格。

## E. 执行与失败规则

1. 开发中运行改动影响范围内的现有测试及必要的新负向测试；G1 跑解析/选择/摘要集成矩阵，G2 跑导出与消费者合同，G3 跑 Worker 故障和吞吐，G4 跑迁移/处置的文件身份与恢复。全套 source-catalog 合同测试仅在广泛改动共享核心或正式生产发布前跑一次。测试命令由实施者在隔离环境记录，不能从本计划把生产路径直接贴进命令。
2. 对抗测试要证明校验器**会拒绝**被篡改的 SHA、定位、来源 URL、摘要否定、角色和时间；不要只检查正常路径。
3. 已知样本中一个严重错误就停止相关模块扩样，保留最小复现、根因和回归测试。留出集失败先核标注，修复后用新的冻结留出集做最终一次盲测；不得反复调参到同一留出集过关。
4. 仅 G 节点产生 scoped acceptance。生产 Worker 解除暂停、在线抓取开放、跨仓消费者切换和物理删除各是独立发布动作，不能由测试通过自动触发。
