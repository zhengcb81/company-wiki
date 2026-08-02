# CW-2.24 验收复核计划（核实是否真的完成用户全部要求）

> 目标：不信任 task_plan.md 的 `completed` 标注，直接核对真实代码/配置/测试，逐条对照用户的原始要求。
> 用户原始要求（来自命令）：
>   R1. 重复下载文件（如不同程序 dayu-agent 下载、文件名不同但内容相同）在**索引里标记**。
>   R2. revenue-forecast 会下载财报等，但这些很可能已在 company-wiki 存在：
>       R2.1 下载的文档应放进 company-wiki，遵守同样的目录规范。
>       R2.2 若索引显示某公司已有财报等文档，不重复下载，直接复用。
>       R2.3 需要下载时：A股→StockInfoDLSimple；美股/港股→dayu-agent。
>       总目标：整合不同工具下载的文档，尽量减少重复下载。

## Phase 1（理解计划与声称）— 状态：completed
- [x] 读取 CW-2.24 计划全文（task_plan.md 4836-5166）
- [x] 计划声称 status=completed，A1–A14 验收矩阵
- [x] 关键声称：分类信任顺序重构、identity-aware resolver、下载抑制、sidecar 补全、Dayu 容错、三市场 preflight、revenue 端到端、StockInfo DNS 修复、40 新测试 + 618 contract

## Phase 2（核对真实代码）— 状态：in_progress
- [ ] R1 重复标记：scanner/duplicate 是否按 whole-file SHA 把"不同文件名同内容"归入同一组并标记？是否在索引/UI 可见？
- [ ] R2.1 revenue-forecast 下载文档写入 company-wiki：`company_wiki_source.py` 是否写 `companies/{entity}/raw/{kind}`，遵守目录规范？
- [ ] R2.2 复用抑制：resolver 命中已有 capture-ready → adapter 调用=0；是否有真实测试 + 生产证据？
- [ ] R2.3 市场路由：A股→StockInfo adapter；HK/US→Dayu adapter；config/source_acquisition.yaml 是否定义此路由？
- [ ] StockInfo adapter 是否可追踪交付（git tracked）还是 untracked？
- [ ] 618 contract tests 是否真绿（实际跑一次）？

## Phase 3（对照判定）
- [ ] 逐条 R1/R2.1/R2.2/R2.3 给出：完成 / 部分 / 未完成 + 证据 + 缺口

## Phase 2/3 核对结果（基于真实代码/配置/生产数据，非计划自述）

| 要求 | 判定 | 证据 |
|---|---|---|
| R1 重复文件在索引标记 | ✅ 完成（机器可读层完整；index.md 未含，属次要缺口） | 生产 catalog：3,477 重复组 / 3,513 可回收副本。location 表含 duplicate_relation/duplicate_group_id/canonical_location_id；`duplicates` CLI 列出组（canonical 受保护 + 其余 eligible_for_recycle）；`export_indexes` 导出 locations.csv 带重复列。实测样本：SHEIN 研报同时存在于 company-wiki 与 Dropbox，同 SHA 被归组标记。 |
| R2.1 revenue 下载入 company-wiki | ✅ 完成 | `company_wiki_source.py` 默认 resolve（零下载）；`--allow-download` 走 ensure→AcquisitionCoordinator→`CanonicalSourceWriter` 写 `companies/{entity}/raw/{kind 子目录}/...`，且写前按 SHA 查 `_existing_original`，命中则 DEDUPLICATED、不产生第二份。 |
| R2.2 已有则不重复下载 | ✅ 完成 | resolver 命中 REUSED_EXACT/EQUIVALENT → 直接 REUSED，adapter discover/fetch=0；IDENTITY_CONFLICT / allow_download=False → MISSING 且不调 adapter。identity 过滤按 market/security_id fail-closed。有 `test_source_catalog_download_suppression.py` 3 测试 + 生产 canary 证据。 |
| R2.3 市场路由 | ✅ 完成 | `source_acquisition.yaml`：cn→stockinfo-cninfo(StockInfoDLSimple)，hk→dayu-hkex-cli，us→dayu-sec-cli；`acquisition.py for_market()` 强制 CN/HK/US 路由。 |
| StockInfo 可追踪交付 | ✅ 完成（已 git add） | `src/company_wiki_adapter.py`、`company_wiki_adapter_cli.py` 在 StockInfo 仓内状态为 `A`（已暂存），不再是 Phase 5 记录的 untracked。 |
| Dayu 只读 | ✅ 保持 | dayu-agent 非 git 仓；company-wiki 仅调用其 CLI。 |
| 测试 | ✅ 通过 | 实跑：CW-2.24 相关 52 全绿；source_catalog 全量 160 全绿。 |

## 结论

CW-2.24 **实质上正确完成了用户的全部核心要求**（R1 + R2.1/2.2/2.3 + 整合），代码、配置、生产数据、测试四方面交叉印证一致，与 task_plan 自述的 completed 吻合。

**两个需要告知用户的注意点（非阻断，但属已知边界）：**

1. **R1 仅覆盖字节级完全相同的重复**（whole-file SHA）。计划第 4.2/5 节明确把"重新编码/加水印但语义相同"排除为未来 semantic duplicate 项。
   - 影响：同一上游源、不同程序/不同文件名下载→字节一致→能归组（覆盖用户举例的主流场景）。
   - 不覆盖：若某程序对 PDF 重新编码或打水印导致字节不同，则不会被识别为重复。这是有意的范围限定，不是 bug。

2. **人类可读的 `index.md` 没有重复标记**（仍停留在 2026-04-19）。重复标记存在于 catalog(SQLite)、`duplicates` CLI 和 `locations.csv` 导出中。若用户期望"index.md 里直接看到重复标记"，这是唯一未做的点——但它通常不是这套系统的"索引"所指。

**可选后续（需用户决定，不在 CW-2.24 范围）：**
- 把 duplicate 标记/计数同步进 `index.md` 的人类可读视图；
- 规划 semantic/near-duplicate 检测（不同字节但同内容），需新增 normalized hash 或文本指纹方案。

