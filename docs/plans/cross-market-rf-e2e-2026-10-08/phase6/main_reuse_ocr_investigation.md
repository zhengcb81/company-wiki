# MAIN：跨 run 派生复用与全图 PPTX 识读调查

2026-10-09。状态：调查完成，功能未实施、主线产品未完成。只写本报告；共享 PWF、代码、配置、安装副本、生产 DB 和原件未修改。主线 PWF 及两组三市场验收完成前不启动公司池新抽样。

已读 task_plan、r6_handoff_intake、root_cause_remediation、R6-FORMAT 责任卡及 r6_format_integration；也已读实际 `revenue-forecast-audit/runs/pool-20261009-001-us-nvda/remediation/work_packages/W03.md`。该卡明确跨 run cache 属 Phase6 owner，现 W03 已并主线 f788a07a；后续 ownership 归 MAIN 分派。结构先 CodeGraph（972 文件，21,262 nodes），再读已定位文件；CWP HEAD 查询时为 f788a07aa7a6e12b8cc2228c44931ca2df1e68ed，以下结论绑定读到的实现。canonical_writer、official_source_flow、narrative_formats、narrative_batch 本调查零写入。audit forward_test 中另一张 W03 明标 TEST FIXTURE ONLY，与实际来源 W03 不同，未作为生产施工依据。

## 1. 跨 run 重复 POST 的已证实机制

| 层 | 当前身份及行为 | 结果 |
|---|---|---|
| NarrativeBatchRequest | to_dict 包含 run_id、全部 sources、profile、预算、transport/model/pricing；request_sha256 和 input_hash 基于该 dict，input_hash 另含 prompt/parser/selector/normalization 版本 | 换 run_id 或仅预算即换输入身份；同一文档随批次其他成员改变也换身份 |
| narrative_batch._events_from_sources | 批次 input_hash 绑定 source payload；event_id 含该 hash；policy_version=`narrative-batch/1:<batch input hash>` | 即使 source payload.input_hash 相同，每 run 仍生成不同 event/policy |
| models.make_job_key | hash(job_type, subject_type, subject_id, input_hash, policy_version, handler_version) | 不同 policy 产生不同 select/summarize/verify 三任务 |
| NarrativeRunStore | narrative_run_jobs.job_id UNIQUE；create_run 拒绝任务已经属于另一预算 run；reservation 绑定 run/job/attempt/lease/generation | 任务与收费账不能直接借给另一个 run |
| NarrativeSummarizeHandler | 从选片构造 request 后直接调用 budgeted caller，未查可复用派生 | 新 summarize job 又 POST |
| NarrativeArtifactStore | objects/sha256/<响应 bundle hash>.json 仅在输出产生后去重；work_key/2 含 publication_effect_key，effect 又含 verification_job_id | 相同响应可共享字节，却已有第二次 POST/费用；不同 run 保留不同发布版本 |

只读最小复现调用现有 unit fixture 的 _request/Reader 与 build_batch_events：sources 完全相同，run_id 从 batch-a 改 batch-b 时 request_sha256、event_id、policy_version 全变；仅 max_tokens=100000→99999 也改 event。POST=0、DB 写=0。本次没有运行真实收费请求。

现有 tests/integration/test_narrative_batch_cross_run_e2e.py 明确断言三 run 各 POST 一次、各收费 92 tokens/111 micro-USD；A/B 同响应仅共享 object_key，三组 artifact/effect/work_key 不同。同一 run 恢复才零新增 POST。因此当前测试验证发布幂等和物理字节去重，漏掉了用户要求的跨 run 默认计算复用。

## 2. 最小可实施复用接口

保留现有 job/run/effect 身份及 immutable 费用账，在 batch 的新 run 准备入口增加一次“按文档派生身份查可见版本”的规划；不要直接删 job_key 的 run 影响，不把旧任务移到新 run，也不重写 work_key/2。

建议派生身份单独命名 schema，按每个 source 计算，不绑定 run_id、其他批次成员、token/cost/time/storage 预算。明确冻结：SourceRef 的 document/source/hash/size/MIME、实际 source_class/language、parser/normalization/selector、handler/bundle producer、model request schema、prompt、adapter、模型名/endpoint 和影响生成的参数，以及 profile。profile 当前只决定 worker slots，仍在 manifest 保存；为最小兼容可保守纳入匹配。价格版本与预算留在原 run binding/账内，不作为已有内容重新 POST 的理由。api_key_env 的名字和任何凭证不是模型内容身份。

注意：当前 NarrativeModelRequest.from_selection 实际把 title/document_kind/language 放进模型 envelope。最小安全实现应将这些实际输入纳入 generation manifest；若希望标题元数据修正也默认复用，须由 ROOT 明确去掉 prompt 对标题的依赖并升级 prompt/schema，不能一边保持模型输入、一边在 cache identity 假装它不存在。元数据作为处理输入不等于恢复旧人工许可或身份门。

generation manifest 可写入现有 narrative_artifact_versions.metadata_json（现仅 bundle_schema/summary_status），无须第二 DB。Reader 增加受限候选查询：按 source identity 查所有 visible 候选，再精确比较 manifest；只查 latest 会漏掉“较新版本不兼容、旧版本兼容”的情况。命中后 read_exact 验 SHA/size/current source，并用现有 bundle/replay 检查保留质量与 locator；无法证明版本兼容的 legacy 记录不猜为命中。损坏或被 quarantine 的记录具名拒绝/失效，不拿它冒充成功，也不默默扣新费用修复。

当前公共读取有可复用的完整路径：NarrativeTransportReader._read 的 current_ref→artifact.read_exact→SourceVersionReader.open_described_version(current,purpose=source_export)→current manifest/as-of 检查→一次 replay_narrative_evidence。read receipt 报当前 read-policy/facts；bundle 保留旧 generation facts/pin，不把旧 policy hash 当当前许可，也不把旧 bundle 重写为新 metadata。复用不能将 as-of unknown/late 改为可用；历史资料资格仍由消费时当前来源事实处理。当前 _replay_normalized 只认可当前 parser_component 的版本，因此“保留旧 pin”不自动等于“旧版本仍能当前回放”；升级须版本分派或诚实具名不可回放，不可只读 artifact bytes 就记已验证。

新的 run binding_json 保存每文档的 generation identity 与 reused exact artifact pin；miss 才创建三任务并进入本 run 费用 scope。create_run 已有空 tuple scope 支路可供全命中 run 使用，但 _resume_binding 目前强制 len(jobs)=sources×3，_final_documents 强制每 event 有 verify；必须一次调整为“reused pins + 新 jobs 覆盖全部请求文档”，以新 binding schema 兼容旧 binding/1、/2。不要只加 early return 而让恢复后再次 POST。全命中不激活 worker/generation、不复制旧 reservation；新 run 实际新增费用为 0，原 run 的 known/unknown/未结账不变。混合批次仅 miss 收费。现有 db batch-owner mutex、runtime gate 和 source current 检查继续负责并发。

显式 refresh 可作为可选请求字段（默认 reuse），进入本 run request_sha256；使用新 run_id 强制新派生/发布版本。相同 refresh run 重试恢复原 pin，不因同 flag 再次 POST。旧 run 同 ID 改 refresh 应按现有 exact intent 冲突拒绝。refresh 与现有 runtime control_generation 不同：前者要求新内容计算，后者隔离过期 attempt/lease。响应相同仍允许新 artifact version 共用对象字节，响应不同发布新 object；旧 pin/事件/费用留存。

### Inflight 同派生与失联恢复

run_batch 当前整个 _run_owned 在同 AUTO DB 的 `.batch-owner.lock` 内，0.2 秒 timeout；进程死亡自动释放 OS lock。B 遇到正在生成的 A 应具名 busy/retry（在请求 deadline 内），不得把 prepared/nonvisible artifact 当完成。A 完成发布后 B 再按 generation 匹配精确 pin。同 DB 当前模型不允许两个 batch owner同跑，不需要为此另建任务库。

A 失联时 lock 释放不意味着可把工作/费用转给 B：enabled runtime generation 仍属于 A，activate_run 要求 recorded run恢复并推进fence；A无provider receipt的finished attempt用 settle_finished_attempt_reservations结为unknown且不退款。B应报告已有inflight owner需恢复/重试，或由现有协调器恢复A后再reuse，不用新run绕过unknown reservation；未发布版本仍不复用。refresh同样遵守该恢复边界。

现锁以 DB 路径为域，**同 catalog / 不同 AUTO DB 并不受它保护**。若多公开入口允许共享catalog但不同AUTO DB，MAIN须用现有 `_file_mutex` 在catalog中按stable generation做跨进程计算锁（获取后再查visible，发布/失败后释放），或让这些入口明确共用同一canonical AUTO。锁文件不是第二调度账，原账仍由原run承担；按请求deadline有界等待，不能无限轮询。不声称现有db mutex已解决全部跨入口并发。

## 3. 真实全图 PPTX 与新发现

只读固定 RF delivery 原件 `objects/c0/c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`，实际 SHA 完全匹配、4,016,522 bytes。当前 normalize_document 1.0.0：0.293 秒，page_count=pages_read=22，0 units、0 parser errors、22 opaque image assets，图片合计 3,954,484 bytes；首三张图片 2560×1440。未写整份 deck/全文/拆页集合。

parse_pptx 的循环使用 `slide_number = slide.slide_id`，实际 opaque_pages/asset.slide_number 为 256..277；这是 OOXML 内部 ID，非第 1..22 页。R6 卡要求 1 起页序，unit.coordinates.page_number 和 locator 也继承错误编号。现有 tests/document_normalization/test_pptx.py 只断言 slide_number 为 int，未断言 ordinal/page_count 范围，故漏检。OCR 施工须一并修正“包内 ID 与展示页序混用”，包 ID 可作为独立 metadata 保留。不能在 parser 1.0.0 下静默改释旧 s=256 locator：新增 parser/locator 版本并保留旧回放分派，或对旧不支持版本具名拒绝；原 artifact/快照绝不改写。

纯 document_normalization 当前声明 no models/no network，只解析 PPTX text/group/table 并携带 OpaqueAsset；normalize、language、select、verify/public read 的路径仍不能把图片产生为正文。_replay_normalized 还要求整个 document.structure.coverage_complete，不能只在 select 拼 OCR 文本而让回放继续纯 parse。

## 4. 本机 OCR 与当前 LLM 配置

只报告配置的非秘密字段，未打印或保存密钥：

| 配置 | model / endpoint | 已观察能力字段 |
|---|---|---|
| config.yaml 主模型 | MiniMax-M3；https://api.minimaxi.com/v1/chat/completions | max_tokens=8192，temperature=1.0，reasoning_split=true；model_options_from_config 为该配置产 max_completion_tokens |
| 配置 fallback | mimo-v2.6-flash；https://token-plan-cn.xiaomimimo.com/v1/chat/completions | enabled=true，usage_scope=general |
| 有限 NarrativeHTTPModel | openai-compatible-http/1 | 仅 system/user 字符串消息与 JSON response_format；无 image payload、vision capability、图像计费字段；明确 no SDK retry/fallback |

不能从 MiniMax/MiMo 名称断言图像支持。当前配置没有 vision/OCR 路由声明；本调查未联网查供应商、未请求远端模型。legacy LLMClient 的 fallback 是主文本请求重试后尝试已配置备用模型，不能推出 canonical AUTO 有 vision 备用；BudgetedNarrativeCaller 的 fallback 参数是 reservation record，不是模型切换。有限 AUTO 若后来采用备用模型，必须显式采用其实际模型/endpoint、单独预算 reservation 和版本身份，不能复用主模型价格或隐藏第二次调用。

本机 C:/Miniconda/python.EXE 已有 rapidocr 3.8.1、onnxruntime 1.26.0、PIL/cv2/pptx；无 tesseract、pytesseract、paddleocr、easyocr、winocr。RapidOCR 三类本地模型可直接指定，不需要安装/下载：

| 已有模型（C:/Miniconda/Lib/site-packages/rapidocr/models/） | bytes | SHA-256 |
|---|---:|---|
| ch_PP-OCRv4_det_mobile.onnx | 4,745,517 | d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9 |
| ch_ppocr_mobile_v2.0_cls_mobile.onnx | 585,532 | e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c |
| ch_PP-OCRv4_rec_mobile.onnx | 10,857,958 | 48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b |

RapidOCR 默认 config 的 model_path=null，OrtInferSession 会进入 DownloadFile.run 路径（本地文件有效时可能跳过，缺失/损坏仍会下载）；必须明确 Det/Cls/Rec.model_path + CPU thread bounds，并对模型 hash/character metadata 检查失败具名报错，禁止靠默认构造自动补下载。

ROOT 追加授权后做了一页离线试验，显式三路径，patch socket connect/create_connection/getaddrinfo、requests/urllib、DownloadFile.run 为拒绝。首张封面 ordinal=1（旧 parser ID=256），PNG SHA `5905a318d9a9450f59bc747fe54b74789331ba9c79f1458ad138ead04c85ea1d`。初始化 0.654 秒、推理 2.737 秒，3 行，平均 confidence=0.993410，最小=0.984260；“Microsoft”“FY27 Segments and Investor Metrics”“September 2026”与实际看图一致。图像底部低对比小字“Classified as Microsoft Confidential”未识出。因此这里只证明本机可离线启动与封面主要文字识别，**不能证明正文/表格或全 22 页完整识读**；置信分数也不能代替召回/阅读顺序验收。网络尝试=0，远端模型=0，费用=0。

唯一持久单页图 64,310 bytes 写独占 `.tmp-cwocr-ds8bldig/page1.png` 供 view_image，随后核目录、文件名及 SHA，unlink/rmdir 恢复不存在，原件删除=0。首次沙箱默认 TEMP 写图 PermissionError 是环境错误（推理已运行但未输出统计）；仅空目录，后按其准确 sandbox UUID 定点检查恢复/不存在。第二次显式 workspace owned temp 成功，报告采用第二次的实际统计。没有安装、下载、配置或生产 DB 写入。

## 5. 最小 OCR 实现与必须保留的缺口

在 CWP 共用格式编排层增加可选本机 OCR adapter，消费 verified OpaqueAsset.original_bytes；pure PPTX package parser 可继续无模型。语言探测、select、verify、公共 read 必须使用同一个配置/版本化编排入口，避免四处各选 engine/model 或只在某一个环节拼字。不借研究侧看图结果制造 canonical EvidenceSpan。

识读版本/manifest 冻结 engine+version、三模型 SHA、CPU runtime 与预处理/阈值配置。使用 source SHA、ordinal slide、shape path、media SHA、图片坐标 box/行序的新版 locator，保留 OCR_USED、LOW_OCR_CONFIDENCE、明确 transform；图内坐标与 slide 坐标含义分明，未知 layout/table 不凭纯 OCR 字符串补成财务 cell。只持久 selected spans/最终小 bundle；整页图及完整 OCR 结果临时内存释放，同媒体在单次文档内可按 SHA 去重复推理，不能每 locator 重跑全文。

有界处理继续用现有 compute worker/子进程 deadline、page/media/text/unit/pixel 上限与 profile。全 22 页每页识读结果、正文实读对照、阅读顺序/表格和低对比漏字须在集中大节点核实；仅“每图至少1行”不能当作全部正文已读。损坏图片、无文字、低置信/无法识读和缺依赖是具名 incomplete/review 状态；不得变 skipped_no_narrative/PASS。本机 OCR 不额外 POST，远端 vision 目前无可验证配置，仍是未证实选项，不能硬编码供应商、模型或价格。

## 6. ROOT 可实施的 TDD 反例与责任范围

| 反例/正例 | 旧实现应暴露 | 修复后要求 |
|---|---|---|
| 公共 CLI A 完成、B 只换 run_id；本地计数 HTTP server | 两次 POST | 默认一次 POST；B exact pin复用、新增费用0；A费用/unknown账不变 |
| B 改预算、加入另一文档、请求顺序不同 | 重做相同文档 | 按文档复用，miss单独收费，有限预算继续约束新工作 |
| C 显式refresh、C重启resume；响应相同/不同两例 | 无refresh语义 | 只新增一次请求、旧pin仍可读，同字节共享对象且新发布版本独立 |
| parser/prompt/selector/model参数/profile版本变、较新不兼容/较旧兼容 | 只有source latest | 精确版本匹配，未知legacy不猜；旧冻结run不重新签当前版本 |
| reused pin损坏/retired/current source changed；混合批次；pause/kill/restart | early return易漏账/重POST | 具名拒绝或恢复；不借旧reservation，不重新扣历史账，不越scope |
| 两进程同generation；A POST后失联；同catalog不同AUTO DB | DB局部锁/unknown账 | 有界busy/单次生成或既有owner恢复，旧unknown保守计；未visible不返回success；跨DB若在scope内须实际跨进程覆盖 |
| PPTX两页含内部ID256/260及重排 | page_number=内部ID | ordinal1/2；包ID另存；旧locator不默默改释 |
| 文字/图片/混合/group/重复media，OCR缺模型/坏hash/禁网 | 无图片正文 | 明确版本的unit/box/flags；禁下载；重复media一次计算、每页locator仍独立 |
| 实际正文含低对比小字/数字经营表/页脚 | OCR高分仍漏字 | 真图对照、质量gap保留；财务数值不冒充经营证据 |
| select→verify→公共read多span、改mediaSHA/box/版本/文本 | select拼接无法回放 | 同共用入口一次全文解析/OCR，exact identity/tamper拒绝 |

复用责任文件：automation/narrative_batch_request.py、narrative_batch.py（与 W03 owner 协调）、narrative_run_store.py、narrative_projection.py、source_catalog/narrative_artifact_store.py；测试沿现有 batch_cross_run_e2e、budget_and_resume、recovery、upgrade_identity、artifact_store 添加。现有“三次 POST”测试改为显式 refresh 发布测试并另保留默认复用反例，不删发布碰撞/旧pin/字节去重断言。

OCR责任文件：新增受配置约束的本机 adapter、document_normalization 的 PPTX页序/locator/unit/replay版本分派；automation/narrative_formats（W03 overlap）、narrative_select/narrative_replay/worker_factory、source_catalog/narrative_language 接共用编排。测试覆盖 document_normalization、select/verify/transport 和真实22页大节点。模型依赖必须声明/验证当前执行 runtime，不能将开发机已安装外推为 CI或其他安装全部可用。

跨仓：FF 可继续消费原 narrative-batch-result/1 document artifact_ref；可选 refresh需调用方透传，但来源采集 identity 不变。RF仍只读 exact NarrativeRef/SourceRef，既有结果/快照不重新签；真实研究消费由 RF owner负责。StockWiki无写入，Dayu/ET无改动。CWP必要入口/源依赖若进入已安装技能闭包，由 ROOT在合并后定点同步并实查，不由本调查改安装。完成仍须主线原三家、新三家真实研究与独立审查；本调查和封面 OCR 成功都不关闭这些任务。
