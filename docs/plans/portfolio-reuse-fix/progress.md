# 进度日志 — portfolio 复用修复

## 2026-08-03（Phase 1 Spike 执行 + Phase 2 内核原型）

- **Phase 1 状态**：completed ✅（见 task_plan.md / findings.md 发现 8）。
- **验证结果**：金山云 FY2025（首版 spike）+ FY2024（身份解析版原型）提升均 `reused_exact`、
  `capture_ready=True`；filing-fetch 只读复用两份均成功、`missing_capture_fields=[]`、零下载；幂等 `deduplicated`。
- **生产代码改动（1 处，最小）**：`canonical_writer.py::_write_provenance` 增顶层 `"market": request.market`
  —— 使 scanner 的 prefer-new 元数据合并在提升场景触发（G1）。
- **原型产物**：`spike_promote.py`（FY2025）、`spike_diag.py`、`promote_prototype.py`（Phase 2 内核，身份解析 + dry-run）。

### 遇到并解决的错误
| 错误 | 处理 |
|---|---|
| `KeyError: pdf_sha256` / `source_url=None` | 丰富溯源在 `meta.json`，不在 `.pdf.source.json`（88B 最小标记）→ 改读 meta.json（G3） |
| `CatalogOperationLockedError pid=1676` | worker 持 normalize 锁 → `worker-pause`（设计机制）→ 锁过期为 `import_staged` 回收 → 测试后 `worker-resume` |
| `CanonicalImportError: exact provider identity did not resolve` | G1（sidecar 缺顶层 market → prefer-new 不触发）→ 修 `_write_provenance` 后通过 |
| `identity_conflict / identity_mismatch_market_or_security_id` | G2（"3896" vs 规范 "03896"）→ 原型加 `SecurityIdentityResolver` 归一化后通过 |
| `UnicodeEncodeError: 'gbk'`（emoji 打印） | spike 打印改 ASCII，并给原型加 stdout utf-8 reconfigure |
| 误读文件：把 `.pdf.source.json` 当丰富溯源 | 见上；已在 findings 词汇表标注 |

### 系统操作记录
- worker：`worker-pause`（2026-08-03 09:04 前后）→ spike/原型测试 → `worker-resume`（新 pid 18004，enabled+running）。
- 测试期间从 `companies/金山雲/raw/` 删除过 1 条 FY2025 canonical 副本（重测 import 路径），
  FY2024 首次导入为 `imported_new`，均无残留。

### 当前状态
- Phase 2：in_progress。剩余 = 把 `promote_prototype.py` 正式化为 `portfolio_promoter.py` 模块 +
  `import-portfolio` CLI（--all/--dry-run）+ 批量验证；随后 Phase 3（E2E）→ 4（去重/陈旧）→ 5（测试）→ 6（ADR/文档）。

## 2026-08-03（Phase 2-6 实施完成）

- **Phase 2**：completed。新增 `src/company_wiki/source_catalog/portfolio_promoter.py`
  （`PromotionIdentity`/`promote_from_portfolio`/`promote_all_for_entity`/`find_entity_doc_dirs`）；
  `cli.py` 新增 `import-portfolio` 子命令（--entity/--company-query/--market/--document-id/--document-kind/
  --fiscal-year/--as-of-date/--all/--dry-run）。真实 `--all`：金山云 7 份全部提升成功。
- **Phase 3**：completed。filing-fetch 只读复用 FY2023/2024/2025 全部 `capture_ready`、零下载。
- **Phase 4**：completed。幂等/去重/陈旧语义验证+文档化。
- **Phase 5**：completed。`tests/contract/test_portfolio_promoter.py` 8 项全绿；
  相关既有测试 53 项全绿（合计 61）。fail-closed 护栏未削弱。
- **Phase 6**：completed。`docs/adr/ADR-007-portfolio-promotion.md` + `docs/OPERATIONS.md` 新增一节。
- **Phase 7**（Strategy B 只读复用）：**跳过**（默认不做，ADR 记录理由）。
- **测试过程中的小修复**：`portfolio_promoter.py` 需在 copyfile 前 `staged.parent.mkdir`（测试暴露）；
  测试 fixture 需实体级 `portfolio/<ticker>/meta.json` + 先 mkdir 再写。
- **最终状态**：主方案实施完毕，计划内全部 Phase（0-6）completed。产出 4 个生产文件改动/新增 +
  1 个 ADR + 1 节运维文档 + 8 项新测试。

## 2026-08-03（Phase 1 Spike 执行 + Phase 2 内核原型）

- **背景**：用户本意是用 revenue-forecast 给金山云做营收预测；filing-fetch 触发了对已在
  `dayu-agent/workspace/portfolio` 中的金山云 FY2025 年报的重复下载。用户两次追问根因，随后决定
  **暂停营收预测**，转而用 planning-with-files 把"详细修复方案"落到 company-wiki 目录。

- **根因调查（已完成）**：
  - 更正先前错误结论：portfolio **已**在 `config/source_catalog.yaml` 配置为 root（`kind: dayu_portfolio`），
    且**已扫描入库**（catalog DB：dayu_portfolio 3,591 locations，含金山云 3896 全部 7 份财报）。
  - 真正断点：`resolver.py:405-513` 复用管线硬过滤 `kind=='company_raw'`；`filing-fetch` handle 契约
    要求 `canonical_path` 在 `companies/` 子树内。两道闸把"已索引"挡在"不可复用"外。无桥接命令。
  - 完整根因与代码证据：`findings.md`、以及
    `C:\Users\郑曾波\projects\Research\kingsoft-cloud-revenue\ROOT_CAUSE_portfolio_reuse.md`。

- **代码核查要点（已落 findings.md）**：
  - 规范写入唯一受验证入口 = `CanonicalSourceWriter.import_staged()`（canonical_writer.py:136），
    走 staging_root → 原子拷贝 → `.source.json` 不可变 sidecar → 重扫 → 断言 REUSED_EXACT。
  - `SourceHandle`（resolver.py:208）从 location 的 absolute_path+content_sha256+source_url 构造，
    portfolio location 字段齐全，理论上能造 capture_ready handle，只差放行。
  - 选型：**Strategy A（导入/提升）** 为主方案，全在 company-wiki、filing-fetch 零改、保留全部不变量；
    Strategy B（放宽两闸做只读复用）默认不做，记入 Phase 7。

- **产出（本会话）**：
  - `findings.md` — 根因 + 代码落点 + 选型 + 待复核假设。
  - `task_plan.md` — 7 个 Phase（0 已完成；1 Spike；2 实现；3 端到端；4 去重/陈旧；5 测试；6 文档；
    7 可选 B）、文件变更清单、风险回滚、整体验收。
  - `progress.md` — 本文件。

- **当前状态**：**仅完成方案制定，未动任何代码**。Phase 1（Spike）为下一步起点。

- **未完成 / 下一步**：
  - Phase 1 Spike：先手工提升金山云 FY2025 验证"拷贝即生效"，盘点字段映射与受影响测试。
  - 其后按 Phase 2→6 实施。Phase 7 默认跳过。

- **已验证事实（便于后续会话恢复）**：
  - 金山云 FY2025 年报：document 文件名 `fil_cn_48ec0d41eb244001f0f3795438c351495c196ada.pdf`；
    pdf_sha256 `efe2ccd923b744eb69166aebf5f9b32ab7560efe3f6c44f2c6bcf4672fec1fa8`；
    HKEX source_url `https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0423/2026042301428_c.pdf`；
    filing_date 2026-04-23。
  - catalog 三 root location 计数：company_raw 33,074 / dayu_portfolio 3,591 / dropbox_stock 9,899。
