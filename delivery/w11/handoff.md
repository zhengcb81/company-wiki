# W11-CWP-SOURCES 交接 — 官方材料发现的离线分类/覆盖根因修复

一句话：用中性夹具与真实封存结果证实并修复了官方 IR 发现的确定性缺陷（earnings 误标 transcript、法律导航 PDF 混入候选、纯导航词进候选、页面级时间误作发布日期），补齐 lead 提取/通知预算/去重/CLI 校验；486789B 原始正文在授权范围内不可得，作为 external_limit 如实交付，未重抓、未复原、未伪造 replay。

## 边界与版本

- 工区：`C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery`；支线 `codex/r1-w11-source-recovery-20261023`。
- 代码 base：`a2f99db676846b7f475def253c541e12c49ae5fe`；start HEAD：`0d7ada21`。
- 产品修复提交：`2e1dfd04`（前置 `a6d12a53`、`ecc7d622`）；本文件所在提交为仅报告提交，产品文件树不变。
- 0 新互联网请求 / 0 模型调用 / 0 下载 / 0 生产 catalog 或 raw 写入。

## 改了什么（仅本卡写集）

1. `src/company_wiki/source_catalog/official_discovery.py`
   - 法律/导航识别：页级 legal/accessibility/imprint 否决（强线索 + 文档后缀可豁免）；privacy/terms/cookie/使用条款/隐私/媒体简报排除；`nav/header/footer` 内无文档后缀的锚跳过；精确 section 标签（Reports/Results/Annual Reports/News Releases/公告/业绩/报告…）不是材料。
   - 材料线索分强/弱：强线索（earnings/transcript/presentation/deck/report 等具体报告词、AGM/6-K 等、招股/年度报告/电话会/纪要…）直接成立；弱线索（results/report/announcement/公告/业绩…）需文档后缀或带日期的 item block，避免导航误收。
   - lead 文本：anchor 文本 → aria-label/title → img alt → 单链接 item block（表格 Download 行），回补标题截断 120 字符。
   - 日期：只取 anchor `data-date` 或「仅含该一个链接」的 article/li/tr 内 `<time>`；页面级/共享列表时间不再成为材料日期，也不再误排除材料。
   - 去重/自指：去 fragment；同 path 的 query/分页链接跳过；空/#/自指 URL 跳过；坏 href 单条跳过并记 `invalid_anchor_url`。
   - 预算：文档后缀候选优先，其次其他材料，最后 notice；notice 不再抢占 `max_items`；每页 SHA 只算一次，pending 有界。
2. `src/company_wiki/source_catalog/official_source_cli.py`（仅 discover 分支）
   - 校验 entity/date/page row/page URL；坏输入结构化 exit 2（无 KeyError traceback）；limitations 去重。
3. 测试：新增 `tests/integration/test_official_discovery_offline.py`（48 例），强化 `test_official_source_flow.py` 的 excluded 断言。
4. 证据/交付：`delivery/w11/`（本文件、`handoff.json`、`evidence_inventory.json`、`test_results.json`、`cleanup.json`、`root_followup.md`、`probes/`、`review/`）。

## 真实证据与结论

- 真实 discover 结果（faa5bf…/stdout.txt，2839B，SHA `1c33f18b…`）只有 3 个隐私/条款 PDF 候选，`coverage=partial`、`dynamic_content_unresolved`、`no_documents_claimed=false`。修复前这 3 个候选正是缺陷现场；修复后同一最小派生夹具输出 0 候选（非原网页重放）。
- 486789B 正文：两条授权根内（audit run 2052 文件/166,731,220B；holdout 65 文件/17,360,200B）精确大小、400–600KB 带内 89 文件全 SHA、sqlite/WAL needle 全 0 命中 → `body_available=false`。不回填、不复原、不重抓。
- RED 证据：`delivery/w11/probes/red_probe.py` 从 git `0d7ada21` 重建 base 模块（blob SHA `7d8fb129…`），保留 D1/D2/D3 的 base 与修复后对照输出。
- 审查 1（绑定 `ecc7d622`）13 项全部修复；审查 2（绑定 `a6d12a53`）NR-01 等修复；审查 3（绑定 `2e1dfd04`）R3-01 修复；审查 4 见 `review/independent-review-4.*`（绑定 `6b538ca2`）。

## 测试（实际运行）

- 交付矩阵：`pytest tests/integration/test_official_discovery_offline.py tests/integration/test_official_source_flow.py -k '<delivered selection>'` → **55 passed / 0 failed / 29 deselected**，JUnit 与 UTF-8 stdout 见 `test-results.xml`、`test-run-stdout.txt`。
- 全文件：新套件 48 passed；既有 `test_official_source_flow.py` 36 passed（合计 84）。
- ruff 通过；in-session `__file__` 均落本工区 src。
- 清理：受保护输入前后逐字节一致；`companies/`、`.source_catalog/`、`catalog/` 始终不存在；basetemp 清除。

## 已知边界（不声称全对）

- 多链接表格行（Download+View、两个锚指同一文档且无文档后缀）仍可能不产出候选（NR-06，未修）。
- 法律/导航识别是标题词 + nav/header/footer 结构 + section 标签的有限启发式；`header/footer` 内强 CTA 若不带文档后缀会被跳过；个别 legal 标题可能被页级否决。
- 精确 section 标签指向**无文档后缀的文档端点**（如 `/download?id=42`、`/press-release/2026-q3`）仍不产出候选；带文档后缀（.pdf 等）的同一标签是候选。
- nav/header/footer 内的锚若带文档后缀仍视为文档候选；仅无后缀的 chrome/section 链接被跳过。
- 同文档 trailing-slash 形式（`/ir/` vs `/ir`）未按自指处理。
- 超大页面若候选超过 pending 上限（`max_items*10+30`）会提前停止并记 `item_limit_reached`；这是有界性取舍。
- 从 item block 回补的标题截断到 120 字符（超出加省略号）。
- `index_notice` disposition 覆盖事件通知与 notice 词标题；不等同法律通知分类。
- 486789B 正文不可得；页面是否由 JS 动态注入材料无法离线判定；旧 SHA 只作回执引用，不可重放。
- 覆盖状态最多 `checked_index_only`/`partial`，无全站或搜索穷尽声明。
- ET unsupported_exchange / CN wire-fee 不在本线。

## ROOT 下一步

见 `root_followup.md`：一次有界重抓 IR 索引（核实新正文与 SHA）；H1 deck/JPM/IR 活动记录的真实来源恢复；共享分类器是否补 `annual_report`/`investor_presentation` 类目的接口建议。
