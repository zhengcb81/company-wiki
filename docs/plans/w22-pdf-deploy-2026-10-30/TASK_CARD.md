# W22-PDF-DEPLOY：正式可复现的离线 PDF 增强部署

状态：READY_TO_DISPATCH。可与 W22-ATOMIC 和 ROOT M8 同时开始；本包独占真实增强 SDK 实测，ROOT 不同时启动 SDK。

## 立即启动的信息

- 仓库：company-wiki。
- **工作目录：`C:/Users/郑曾波/Projects/company-wiki-w22-pdf-deploy`**。
- 分支：`codex/w22-pdf-deploy-20261030`；基线 `662f821e`，精确 SHA 见工区/ROOT setup。
- `PLAN_ID=w22-pdf-deploy-2026-10-30`，`PWF_PLAN_ROOT=docs/plans`。
- 本地唯一计划：`docs/plans/w22-pdf-deploy-2026-10-30/`；先读 TASK_CARD/task_plan/progress/findings。
- 交付：`delivery/w22-pdf-deploy/handoff.md` 与 `handoff.json`。
- 本包无收费 API、LLM token、新下载额度；只用现存 SDK/模型和自己生成的小合成 PDF。

## 已知事实与应读证据

W21 工程已合并，不能重做其 child -I/allowlist/检查点。ROOT 接收目录：
`C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/review/w21-root-reception-20261030/`。

其真实结果：no-document SDK constructor 16.22秒/30秒通过；**配置中的中文路径 env 在 PAGE_1 ChildFailed/native_fallback**；同 env 临时 ASCII alias 能完成2页但 accepted0/rejected2，属于 unaligned_native_fallback，不能算正式增强或内容召回通过。原 stdout/stderr/fopen 对照支持 docling-parse6.2.0 非 ASCII 资源路径与 Windows ACP936 的兼容问题；部署方案仍未完成。先读这些收据，不重复旧失败来猜。

已有隔离环境只读：`C:/Users/郑曾波/Projects/company-wiki/.planning/c3-20261028/pdf-sdk-isolated/`。先读 handoff.md/json、runtime-isolated.json、selected-manifest.json、deployment.json。它从426可见分发中选104个，36,121 hardlink，共享逻辑1,233,549,343B；原 scaffold517,241B。模型/依赖/配置 SHA 都以这些实际文件为准。别重造1.23GB包副本、别把共享逻辑字节当新增磁盘。历史4B/5B INSTALLER provenance 差异是诊断，不得重建许可门。

W21作者工区只读：`C:/Users/郑曾波/Projects/company-wiki-w21-pdf-runtime`，其 delivery/真实E2E收据按接收 review 引用定位。不要运行其旧有 one-use probe，不删 marker，不改历史失败为成功。

## 所有层的责任

部署工具只负责：显式选择现有依赖、构建普通隔离解释器/资源树、生成符合既有 ParagraphRuntimeConfig 的本地配置、验证实际生产入口。

生产已有 `configured_paragraph_runtime()` 只读 `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 指向的 JSON；`pdf-paragraph-runtime/2` 绑定 `pdf-runtime-closure/2`。`python/artifacts/model_sha256/model_config_sha256/runtime_versions/environment_sha256` 及资源界来自实配。上层 FF/RF/摘要不应知道 Python/SDK路径或模型设置。

因此本包**不修改上层或 W21 运行时来迁就部署**，不做全局 PATH/site 注入或 provider 切换。新配置只在本卡 owned 验收子进程显式启用；不改 ROOT 生产 profile/config/环境变量持久状态。ROOT 接收后统一选定正式配置。

## 独占可写范围

1. 新 `tools/pdf_runtime_deployment/`：小型可重复的 preflight/deploy/verify/CLI、README。优先复用既有标准 venv/环境指纹实现；不要把旧 .planning 某次绝对路径脚本直接硬编码进产品。
2. 新 `tests/unit/test_w22_pdf_deployment_*.py` 和必要小 fixture；新 `tests/integration/test_w22_pdf_deployment_entry.py`（实际SDK用显式 opt-in，日常CI不引入昂贵真实模型任务）。
3. 本卡 PWF 和 `delivery/w22-pdf-deploy/`。
4. 一个新空的、ASCII 路径部署目标。建议候选 `C:/cwp-runtime/w22-pdf-sdk`，**不是已经批准其存在/可写的事实**：A 中先核目标不存在、同盘/可写及已存在相同任务收据；用当前平台支持的宿主权限创建。目标存在且不是本卡产物时不覆盖、不删除，改用另一个明确 owned ASCII目标并写入收据。不要改全局 ACL/MIC。

禁止修改：`_atomic_file.py`/pre_push_gate（归 W22-ATOMIC）、W21三 owner `narrative_pdf_enhancement.py`/`_paragraph_worker.py`/`narrative_pdf_environment.py` 及其 runtime helper；PDF对齐/策略/triage/geometry/parser/recipe/预算/LLM/缓存/QA/source scope；其他仓/原件/数据库/生产config/全局技能/ROOT共享PWF。如果发现公共接口真实缺陷，交最小中性反例和接口需求，不跨界补丁。

## A：根因与部署设计（无需 ROOT 中间签收）

1. 核对工区/base/status/AGENTS及历史证据。区分解释器入口、site-package资源路径、model路径、scratch、源码路径；ASCII Python别名本身不证明实际包资源是ASCII。
2. 选普通隔离 venv 和真实 ASCII 资源树，不把临时 junction/alias 当正式环境；可以使用相同 NTFS volume 的 hardlinks 复用已选依赖和模型。明确 interpreter/scaffold 的允许小复制与包/模型零大复制边界。不升级/装新 SDK，不修改已存在包字节、元数据、模型、权限或系统设置。
3. 冻结所选104依赖/版本/实际 SHA与配置关系，复用既有 dependency resolver，不重新发明一套依赖身份证明。工具参数通用，无用户名/公司/日期/某个模型版本硬编码；缺少明确源配置就报具体错误，不扫描整机自动选新环境。
4. 模型共享路径若原ASCII兼容则直接复用；确需新ASCII资源路径也只在 owned树 hardlink 原有文件，逐项证明对应关系和源未变。link不支持时清楚退出，不隐式大复制。不能对 hardlink 文件就地编辑/chmod。

## B：实现可恢复、幂等的窄部署工具（TDD）

- 普通 venv，无 pip/用户site/全局site；选定依赖复用现有清单，不写自定义全局 import loader。对现有 .pth 等实际行为做字节/解析检查，不能把已知标准 provenance 诊断升级为门禁。
- 目标首次为空；目标已是本工具同源完整部署时复核后零写复用；目标未知/源变更/中途失败分别报告，不能误报“已就绪”。允许在本工具已知 owned incomplete树恢复，保护其他文件。无人工 authorization/receipt放行链。
- 故障注入：link中途失败、源变更、已有目标冲突、配置错误、不可写scratch、重复执行。仅清理/恢复本次 owned新增项，不沿hardlink删除源；不要用整目录复制或备份恢复演练。
- 新解释器实际运行 resolver/production配置加载，环境摘要吻合；父PYTHONPATH/PYTHONHOME污染仍由既有W21 launch owner隔离。配置必须反映实际所选路径与版本，旧artifact/recipe不改写。只因路径变化 metadata-closure SHA相同可能合法，不能虚构全代码身份变化，也不能隐藏实际代码变更。
- 不改封顶：constructor30秒，生产120秒/3页/4GiB committed/CPU4/64MiB input/2MiB output。SDK不就绪先看真实日志，禁止同配方反复超时或抬限额。不要对系统文件缓存做清理，fresh process不叫OS-cold。

## C：真实入口、恢复、独审与清理

1. 先跑轻量部署/冲突/配置/恢复单元测试，确保不import重SDK；再用新revision收据跑一次 no-document constructor（若轻量证据已足以判断启动可用，不机械重复旧观察）。
2. 在独立测试资料根生成**最多两页合成PDF**，含正常正文、分段/换行及至少一处真实可测的增强候选。调用既有 `PdfReading`/configured ParagraphEnhancement → 真实worker → 已配置离线 SDK → 现有对齐入口。不mock converter冒充SDK；不自己构造假bbox/改匹配阈值来造accepted。
3. 分开记录：configured path实读、转换完成页、SDK模型/环境、实际proposal、accepted/rejected及原因、原文text/SHA/locator保持、fallback、时间/峰值。至少正式ASCII资源配置必须不再发生已知中文资源打开失败。
4. **转换通过不等于对齐通过**。期望正对照至少一处真实accepted，负对照仍拒绝错配；若通过正常源布局仍accepted0，先审合成夹具是否根本无增强需求，再给出真实最小对齐反例/输入/结果。不要为交卡改ROOT对齐层。部署工程可单独说明PASS，但整体C2必须PARTIAL，不能以engine成功/0spans签“全部完成”。
5. 同配置第二次轻量复核应零环境写入；checkpoint/恢复优先用现有轻量测试/捕获结果验证，不再启动完整SDK重跑同PDF。真实 paid摘要/模型缓存/RF不在此卡，均 NOT_RUN。
6. 测试目录前后恢复：删除本卡新增PDF、DB、缓存、输出，保留小日志收据；清理自身child/临时alias。**新部署env是显式交付，不是测试垃圾**，保留并列清单/路径/共享逻辑字节/新增scaffold字节，注明NTFS metadata无法精测；不能将其误删后声称可用。旧env/SDK/model/config/原件和已有receipt SHA不变。不提交整个env/per-file大清单/模型；清单只在本地，提交compact摘要与SHA。

测试路径示例：专属 unit 文件与现有 `test_pdf_runtime_environment.py` 的必要节点；新增真实SDK entry使用显式命令单独运行，不塞进每commit/pre-push/全量CI。短自有basetemp，保留RED→GREEN和实际耗时，不反复全仓。

**交接前调用真正独立 agent 全面审查**原卡、实现、实际环境/硬链接源保护、隔离、幂等/中途恢复、真实入口与对齐证明范围、磁盘和清理。审查者补独立反例并绑定最终源码/配置；修完所有范围内缺陷并复审后才交。若外层真实对齐缺陷无法在本范围修，就PARTIAL列清，不能随意扩大到ROOT文件或作者自签。模型/工具不可用则记录独审未完成，不伪造报告。不加A/B小节点签收。

## 输出接口、验收和交接

工具输出配置仍是既有 `pdf-paragraph-runtime/2`，可由 `COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG` 显式选择；上层接口不变。另交compact `deployment.json`：schema_version、输入源/目标路径、依赖/模型SHA、复用方式、scaffold新增字节/共享逻辑字节/未知实际分配、创建/复用/失败恢复、原源保护结果、配置路径与内容SHA、轻量fresh-process验证。不要往新schema放密钥或完整父环境。

`handoff.json` 为 `harness-handoff/1`，包含 card_id、status（READY_FOR_ROOT/PARTIAL）、workdir/branch/base_commit、implementation_commits、tested_commit/reviewed_commit、code_files的raw/LF SHA、逐项requirements、命令/退出码/耗时/日志、deployment/config/SDK-E2E/对齐各自状态、独审报告与OPEN、cleanup、原源未变、剩余接口需求、pushed_to_remote。未知用null/NOT_RUN，不编0。独审后代码若改需更新相关测试/独审绑定，纯文档后缀另列。

正常提交并推本分支，禁止合master/改ROOT生产配置/安装全局技能；完成后STOP等ROOT接收。ROOT负责集成ATOMIC+部署工具、显式配置采用，以及之后真实C2/主线摘要/缓存/RF，公司loop不由本包代签。
