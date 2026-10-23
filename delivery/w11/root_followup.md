# ROOT 下一步 — 真实来源恢复 lead（W11 交接）

本线离线工程通过≠取得新 IR/Q&A 原件。以下 lead 可由 ROOT 在统一预算与真实新 attempt 内一次有界恢复执行。

## 1. 486789B IR 索引正文（重新获取）

- **真实意图**：`official-discovery-request/1`，`urls=["https://www.wuxiapptec.cn/investors/announcement/ir-material"]`，`start_date=2026-01-01`、`as_of=2026-10-21`（或恢复当日新 as-of）、`max_items=30`、`max_bytes=1048576`、`max_seconds=20`。
- **已知**：该页 2026-10-22 真实响应 486789 B、SHA `f1e822a8067c0b8eb7fc6376d8e1491acfa1ae3b60ce605db90c06326603396e`、HTTP 200、7.4s 内完成（fetch receipt 已封存）。页面含外部 script（`dynamic_content_unresolved` 为真实观察）。
- **缺什么**：正文 HTML 本身（`body_available=false`，两条已配根内 0 命中，含 sqlite/WAL/objects 逐字节检查）。
- **验证条件**：新 attempt 抓取后，先核大小/SHA 与 receipt 是否一致（站点可能更新，不一致不是失败，如实记录新版本即可）；再核材料锚点是否在静态 HTML 内。**修复后的 discovery 能排除隐私/条款等法律导航，并把真正的业务材料锚（deck/report/transcript/业绩说明会等）作为候选输出；但导航/法律识别是有限启发式（标题词 + nav/header/footer 结构 + section 标签），不是站点结构学习：多链接 Download+View 行、个别 legal 标题仍可能漏/误，需以新抓正文复核。**
- **若材料锚由 JS 动态注入**：静态重抓仍只有导航锚时，这是 external_limit，不是 parser 缺陷；需要 DOM 渲染类采集能力（新工具决策归 ROOT，本线不新增）。

## 2. H1 2026 deck / JPM 演示 / 专门 IR 活动记录

- web_discovery.json 已留查询意图（site:officialsite-static.wuxiapptec.com/upload 2026 interim/presentation 等 8 条）与 native response ID lead（turn438…444）。
- 恢复条件：真实联网搜索/抓取在 ROOT 统一预算内执行；取得原件后走 CWP official capture/import 登记身份/期间/as-of。
- 未取得的影响不可估为 0（FETCH-002 原话）。

## 3. 日期/主体核验注意

- IR 索引页的检索时间≠材料发布日期；`disposition=date_unknown` 的候选在取原件时必须由材料自身内容或 HTTP 头补日期，不得回填。
- discovery 候选 `metadata_only=true`，不能作为已读 Q&A 或 deck 正文；capture/import 后才有原件资格。

## 4. 与其他线的接口建议

- `narrative_routing.classify_document_kind`（共享分类器，本线未改）：英文 report/deck 类 title 兜底为 `investor_relations`。若 ROOT 希望更细（如 `annual_report`/`investor_presentation` 专用 kind），建议在共享分类器加模式（如 `\bannual report\b`/`\binterim report\b`），本线 discovery 侧无需再改——它已正确消费分类器输出。此为接口建议，非本线变更。
