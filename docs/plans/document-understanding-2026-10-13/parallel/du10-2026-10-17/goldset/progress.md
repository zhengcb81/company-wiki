## ROOT 最终接收 — 2026-10-17

状态：PASS，作者完整历史 faf5e580 已 merge；ROOT 修正与独立复审以 receipts/root-gold-final-review.json 的 17 项实际文件 SHA 为准。下方旧 schema1、raw bindings 命令、旧 PASS 和原始 handoff SHA 均为历史，不能用于当前 schema2。

### 实际修正

- 语义：Verisk 单一 Insurance segment 的分母（552.1+230.5=782.6 million）不再误罚为非总收入；阿里8.60亿与含蚂蚁9.60亿去重口径分开；东方电缆原文 Q3 总额约30.66亿与类别35.49亿的冲突保持未知，不自创包含其他收入/YTD解释；名创电话会按开场创始人/CEO归因；中微21.81%属于等离子体刻蚀设备，XD RIE与YDRIE时间点分开；宁德772保留报告期内，仅321在建为期末。
- 抽象：source_ref 使用真实公开v2身份，source_binding仅用于测试初次登记；临时 SourceCatalog.register_sources → query_ref → open_version 实读验证SHA。HTML严格绑定 canonical unit_id+source_locator 并批量 replay；PDF只查指定物理页，无全篇回退。生产根/配置不改，不复制原文。
- TDD语义先8FAIL；当前71PASS/2.83秒，含5个真实临时Catalog正反控（错误SHA、大小、页码、quote拒绝）。11/11真实来源回放PASS；独立复算10原件SHA/size/mtime保持，生产config SHA保持，隔离目录和sentinel恢复。
- 最终独立复审8项全部闭环、0未解决。旧独审Verisk数字误读保留为历史，由本ROOT结论覆盖。

### 当前复现命令（从 company-wiki 根运行）

```powershell
python -B -X utf8 -m pytest docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests -q -p no:cacheprovider
python -B -X utf8 docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests/verify_anchors.py --project-root . --output <独立测试收据路径>
```

环境需已安装本项目和catalog/PDF依赖；第二条需要当前source_catalog配置中的原件。只在隔离临时catalog登记少量选定路径，不扫描全湖、不写生产库。回放PASS只证明来源/locator，不证明经济语义或摘要质量；语义另由独立实读审查负责。

**这是已被读取和修正的回归标注集，不是盲holdout，不是正式模型摘要质量验收。** case.prior_use仅描述最初选样时的历史；新holdout必须另选未参与调整的来源。新增股发行等完整文档阅读覆盖仍遵循母计划，不以本11例冒称全覆盖。0收费/下载/翻译，原件无变更。

Next Step：ROOT继续共享引擎PDF生产接线，随后配置供应商真实摘要、缓存恢复与新盲样本验收；此数据包不新增生产门禁。


---

以下为历史记录（状态以顶部 ROOT 更新为准）。

# DU10-CWP-SUMMARY-GOLDSET — 进度（progress）

## 2026-10-17

- [x] worktree 建立：`C:/Users/郑曾波/Projects/company-wiki-du10-summary-goldset`，
  分支 `codex/du10-cwp-summary-goldset`，基线 `900dbf6489f3b995a0bfb7fcbb8a001a68df241d`。
- [x] A 节点：缺口盘点完成（对照 29 个既有 DU-Gold sample、DU2 families/facets 约定、
  摘要合同六类错引）。冻结 11 个 case / 10 份唯一原件，全部本地存在、文本可提取、
  SHA 已算。收据 `receipts/node_a_freeze.json`；缺口矩阵 `findings.md` §1。
  先用（prior-use）逐公司核查完成（fresh×2、元数据-only×2、同公司不同原件×7）。
- [x] B 节点：`cases/`（11 case + index，schema `du10-summary-goldset-case/1`）、
  `tests/`（结构校验 58 项 pytest + 只读锚点核对工具）完成。
  - 结构测试 58 passed（0.95→2.6s，离线，0 网络模型）。
  - 锚点核对 11/11 PASS（SHA+mtime+118 anchors 回放）。
  - 施工中修正 3 处（见 `receipts/node_b_tests.json` fixes_during_node_b）。
- [x] C 节点：独立 agent 实读复核。首轮发现 1 阻断（baba must_preserve 口径错配）+ 3 轻微建议；
  全部修复后同一 reviewer 复核 PASS。收据 `receipts/node_c_independent_review.*`、
  `receipts/node_c_repair_review.*`。
- [x] 交接：`handoff.md`、`handoff.json` 完成。状态 COMPLETE。

## 环境与卫生

- 原件只读：全部读取走 PyMuPDF/BeautifulSoup 只读抽取；verify 工具核对 mtime 前后不变。
- 机内 bindings 在 `~/.du10-goldset/bindings.local.json`（两仓之外，不提交）。
- 测试零外部夹具：pytest 收集只读本卡 JSON；无 owned temp 残留待清理（无写测试）。
- `catalog.db` 观察为空库（只读查询零表）；未触碰任何配置/生产目录。
