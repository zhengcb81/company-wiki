# 有界 PDF 按完成页检查点（短计划，待 ROOT 发布后实施）

本节点修复已证架构缺口：worker只在全pages完成后输出，后页超时导致前页完成结果全丢。**没有证明新HK本次阻断的具体超时原因**。既有19份工程源码冻结；ROOT通知恢复前不写tracked源码/测试。

范围：`narrative_pdf_enhancement.py`、`_paragraph_worker.py`，新纯wire helper `narrative_pdf_page_checkpoints.py`，必要PDF层中性测试。基础transport/全局配置/原件/缓存/summary compiler均不改。120秒、4GiB、3pages、2MiB输出、2048items、单hot converter、离线无下载均不升。

1. **有效RED先行**：以现有ParagraphEnhancement API的runner模拟前页完成后ChildTimeout/ChildFailed与尾帧半截，断言前页原生IDs严格对齐、后页缺口仍在、status为partial；旧实现因只认全体单JSON而失败。反控错source/SHA/env/request hash/page顺序、重复、越界、oversized完整帧一律拒绝；无完成页仍native fallback。
2. **显式版本化wire**：request/1和/2环境算法继续兼容，在recipe/request上显式加入page-checkpoint协议，recipe绑定helper SHA。每页完成后输出一个独立换行结尾JSON frame，重复绑定source ID/SHA、模型/config/runtime/env、requested pages、request digest、单converter；sequence严格对应requested page顺序，无重复/未知页，所有item的page provenance必须属于本页。成功最后有完整completion frame；失败可保留此前完整页，不能把prefix当全3页。
3. **纯decoder**：2MiB聚合bytes和2048items先界限再decode，严格UTF-8/JSON/重复key/非有限数/绑定与字段校验。仅ChildTimeout/ChildFailed可忽略最后一个语法上确属JSON前缀的未终止截断帧；任何换行结束的损坏完整帧、错误绑定、越界或输出超限均不能吞。成功退出缺completion拒绝。旧单JSON response/1、/2仅成功且完整绑定时走原兼容校验，不从其失败残片造page checkpoint。
4. **worker**：所有现有环境/模型/离线/OS内存验证保留。单converter遍历原requested page顺序；每页SUCCESS且items检查后才输出并flush该页frame。总items/bytes计数共用，超界不输出该页；没有PDF/MD/image/cache副本，临时运行根继续恢复。
5. **父层**：捕获既有bounded_process的stdout；仅对Timeout/ChildFailed尝试new stream恢复，基础transport不改。严格解码后仅将completed pages交现有proposals/align_paragraphs，原text/ID/locator不改；completed/pending pages、stream complete/truncated、partial status作为source-free reading_execution观察。未完成页保留原生缺口，不给whole-source complete。
6. **验收**：纯wire负例、原严格alignment/runtime/environment/reading integration定向检查；小真实cold helper进程只发中性JSON帧再超时/失败，验证transport现有capture即可，不导入Docling/读PDF。正常Ruff/mypy、短自有TEMP恢复、逐文件SHA冻结handoff-v4，交独审；不自行签独审，也不启动真实Docling或收费模型。

接口草案：new request field `checkpoint_protocol` + `request_sha256`（对有界语义request字段canonical hash）；page frame schema `pdf-paragraph-page-checkpoint/1`、terminal schema `pdf-paragraph-pages-complete/1`；内部decoder返回completed pages/items/complete/truncated/peak观测。最终名称随有效TDD冻结，新增文件清单交ROOT及独审。
