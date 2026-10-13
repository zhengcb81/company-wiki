# DU2-FAMILIES 交接说明（du2-handoff/1）

分支 `codex/du2-families-20261013`；base `5a297244`；实现提交 `99256072`（deliverables/families 全量数据包）。
机器可读版见同目录 `handoff.json`。

## 改了什么

在 `docs/plans/document-understanding-2026-10-13/review/deliverables/families/` 交付一个可导入的数据包：

1. **24 份阅读策略规格**（du2-family-spec/1）：A股年/半/季、港股年/中、SEC 10-K/10-Q/20-F、
   A/H/US 招股、定增/可转债/可研/募投变更、投资者调研/业绩说明会、财报电话会、业绩新闻稿/投资者演示、
   8-K/6-K 容器与附件、摘要/修订/更正正交修饰、行政负例（制度/通知/确认函）、问询回复/重组收购/重大合同、
   研报/新闻/政策/ESG。每份含识别证据与反例、章节位置与简繁英别名、业务问题、必要上下文、降权例外、fallback。
2. **39 个 case**（du2-reading-case/1）：31 个真实摘录（覆盖全部 20 份开发样本原件，13 份 PDF/HTML/TXT
   逐条短引文，带原 SHA、页/行 quote anchor、支持集、must_preserve/must_not_assert、失败反例 mutation）
   + 8 个合成正反例（缺样形态，明确标 synthetic）。
3. **index.json**（du2-family-index/1）：每形态独立 spec_status/evidence_status/integration_status 与 gaps
   （28 行：24 已实现 + 4 提案）。
4. **tests/**：85 项结构不变量测试 + `_support.py` 校验 helper + `c_node_quote_check.py` 原文对照工具。
5. **coverage_matrix.md / acquisition_requests.json / README.md**：覆盖矩阵、AR-01..AR-12 补采需求、复跑与边界说明。

## 边界（没做什么）

- 不改 router/selector、不接生产、不新建 skill、不动 FACETS/LAYOUT/原 DU 三包/共享接口/config/CI。
- 不是第二套 registry 或 recall 判定器；records 交 ROOT 导入唯一 profiles。
- 语义执行全部 `NOT_RUN_ROOT_INTEGRATION`：本包不声称引擎理解正确、不报引擎召回。
- 不下载新原件、不复制原件、不翻译原文、不把搜索摘要当正文。

## 如何复跑

```powershell
# 1) 数据结构不变量（日常唯一命令）
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests -q
# 2) C 节点原文对照（只读原件；用未提交 bindings.local.json）
python -B -X utf8 docs/plans/document-understanding-2026-10-13/review/deliverables/families/tests/c_node_quote_check.py
```

结果：pytest **85 passed**（3.6s，exit 0）；C 节点 **97 项检查 0 失败**（16s，exit 0）。
A 节点先有 RED 记录（16 failed/14 passed），失败原因与修正记录在 `.planning/du2-families/progress.md`。

## 真实与合成覆盖

- 真实：31 个 case / 13 个形态（A股年/半/季、A股招股、定增、可转债、IR 记录两份、扫描确认函、
  港股年/中/招股、港股新闻稿、港股演示、10-K、10-Q、20-F、美国新闻稿、电话会 TXT）。
  两家不同公司验证可复用规则（A股半导体设备公司 + H股零售公司），美股/港股另证。
- 合成：8 个 case / 8 个形态（US 注册发行、可研、募投变更、8-K 容器、版本对、行政通知、
  问询/合同事件、第三方研报）——全部因缺本地原件，缺口登记在 acquisition_requests。
- 提案无样本：股东信、港股配售/供股、A股摘要件、40-F/6-K 正文（index 中 spec_status=proposed,
  evidence_status=missing）。

## 仍没证明什么

- 引擎（ROOT 共享链）能否按这些规格正确识别、选择与摘要：未测。
- 摘要忠实度、业务 gold 召回、语义蕴含：未测（旧基准问题修复后由 ROOT 重建分母再测）。
- 双栏阅读顺序、跨页断句闭包、图表 OCR：不在本包能力范围。
- 真实缺样形态（AR-01..AR-12）的规格只有设计与合成证据，不算实证。
- 同一事件 release/deck/call 的重复事实去重：留证据层验证。

## 资源与原件保护

- 模型调用 0、付费 0；持久数据 357,012 字节（<512KiB 上限，未删证据凑体积）。
- 20/20 原件只读，结束后复核 SHA 与 sample_manifest 一致；无 scratch 残留。
- `bindings.local.json`（worktree 根）为本机绑定，不提交；hk-release/hk-deck/us-release 原件在临时目录（易失）。
