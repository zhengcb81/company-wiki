# 施工卡 SR-CWP · 增量发现与有限阅读

**工作目录** `C:/Users/郑曾波/Projects/company-wiki`

**起点参考** `master@de136b99a` 或最新无冲突主线。现有 `source_catalog/read_budget.py` 属并行工作，开工先读状态和 diff。需要隔离时用任务自有短路径 worktree，保持主工区。

**第一步** 读 [共同接口](../interfaces.md) 第 2、3、5 节和 [调查结果](../findings.md)。用本仓包含的 loopback 夹具在独立短路径重现 `tests/integration/test_narrative_batch_cli_e2e.py::test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes`。该测试两次失败。单跑诊断中一份为 `PARSER_INCOMPLETE`，其余文档成功。记录具体原件、parser、页/段覆盖、工作进程收据和返回状态，判断是运行依赖、共享解析/质量逻辑还是夹具与真实契约不一致。先写能覆盖新样本的失败用例，按根因修复，再验证原基线。

## 写入范围

- CWP 来源发现、现有源目录查询/精确引用，以及有限文档阅读的公开接线。优先在 `src/company_wiki/source_catalog/`、`src/company_wiki/automation/`、相关 CLI 与定向测试中改最少的所属代码。共享 engine 和 profiles 继续处理格式、文种、选择及来源定位。
- 本仓隔离测试和本卡 handoff。生产 `config/source_catalog.yaml` 与 `config/source_acquisition.yaml` 只读；用临时配置模拟范围、根和 provider。W12 主线的计划与并行 `read_budget.py` 不属于本卡。FF 的调度、OS 任务、Dashboard、ET/SID/Dayu 实现由原属主维护。

## 实施步骤

1. 扩展来源 owner 的公开有界元数据枚举。复用既有 `acquisition_service/adapter_process` 和市场路由。保留每条 candidate 的真实 provider/accession、生效日期、来源市场、身份和期次证明。用同一 fixture 返回同日多个文档、跨页、真实空、截断及更正版。真实情况还不能枚举完整时得出可继续处理的部分状态。正文仍从现有 FF → CWP ensure 接口按精确候选入库。
2. 以同一 SourceRef 和阅读档位对接当前共享引擎。实现有界本地业务读取和正式摘要两条路径。验证本地档位模型请求为 0；正式档位沿 `scripts/narrative_batch_configured.py` 与 CWP 现行配置。局部增加公开组合入口时使用现有 AUTO、工件存储和预算。到期传入的是精确引用，不触发旧 worker、文件夹扫描或全量转换。
3. 给 FF 输出可读回的处理状态和紧凑 `result_ref`。已入库未读部分通过分页目录/owner 派生查询给出精确 refs。新申请先复用已有有效工件。固定 `run_id` 绑原请求及 owner 收据，运行失败后按原作业与费用状态恢复。
4. 对样本验证 PDF、原生 TXT、一个带业务内容的 IR/再融资或招股候选、一个纯模板。内容检查能对回原定位并保留主体、时间、条件。TXT 不启 PDF/OCR。先用已保存真实来源与回环模型验证，不在本卡调用真实收费 API。

## 验收和交接

- 一次大节点独审。验证 CWP 自己认领源身份、SHA、页/段与解析质量，FF 不需要读取 CWP 内部文件布局。找到确实误拒的诊断或非必要检查时，先按 F4 审视门禁并从责任层修复，加正反例。
- 隔离测试应包括 A1/A2/A3 的 CWP 部分和 A4。用两个执行进程验证同一 SourceRef、同一运行的命中零重复模型；强退和未知用量只查原记录。新增测试需同时有新资料进入与同一资料复用的观测。移除本卡生成的临时目录。
- 交回本仓 `docs/handoffs/scheduled-refresh-2026-11-21/sr-cwp.md` 和机器可读同名 JSON。列基线/交付 commit、实际公开命令和 schema、固定样本/用量、初始失败根因、定向测试和独审 commit/未决项、清理收据、FF 接线摘要。请使用 [共同回执模板](../handoff_format.md)。
- 提交本卡文件。交付前独立 agent 核对代码与证据，发现问题修复并在最终版本重验。总控协调 CWP、FF、Dashboard 组合和启用，本卡交付不会启动本机任务。
