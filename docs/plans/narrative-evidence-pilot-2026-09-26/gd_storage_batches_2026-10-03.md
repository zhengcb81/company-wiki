# G-D：当前空间与分批实施

## 当前盘点（2026-10-03，只读）

仅遍历本项目 `.source_catalog/`、`source_manifests/`、`companies/`，不跟随 reparse；访问错误与 reparse 均为 0。合计 **45,748,203,875 B / 42.606 GiB**，不能再使用 9/27 的 39.744 GiB 快照。历史 F0–F5 已净释放 37.630 GiB，不重复计作收益。

| 类别 | 实际 B | 本批动作 |
|---|---:|---|
| companies 原文、sidecar、legacy wiki | 25,198,502,813 | 整体保留，原文不进入删除清单 |
| 当前 catalog.sqlite3 | 3,055,800,320 | 保留来源/版本事实，不直接删除 |
| catalog.sqlite3.bak-r6-20260927-061319 | 3,055,796,224 | 首批精确冗余快照候选 |
| derived | 2,826,010,634 | 后批按共享路径和实际引用判定 |
| index（8 个投影） | 45,052,670 | 后批核调用者与重建入口 |
| retirement 完整旧 SQLite zstd | 6,198,704,362 | 保留至历史 ID/回滚策略单独收口 |
| retired-evidence gzip | 5,207,478,767 | 派生证据归档，不能直接宣称与 zstd 完全重复 |

两个大归档都不是下载 PDF/TXT 原件备份。当前没有覆盖全部 raw 的可读 SHA manifest，旧盘点还记有三条 missing raw、一条 span source 缺 location；不得宣称全库都能重建，也不把这几项变成无关批次的全局前置。

## B1：立即可实施的重复 active 快照

候选完整 SHA `63c359aa4b09545a540a05f8d32d66ac3c9dbd4ccf696470d55cb38a31f6dcfc`，与 `.source_catalog/retirement/20260926T170825Z-4a9c67e1/prepared.json` 的 shadow SHA、两次 smoke 与 `retired.json` 的 production SHA 一致。当前表无 raw BLOB；未发现该 bak 精确文件名或 bak-r6 的 runtime/config 引用。首批只删除此精确副本，保留当前 DB、完整 zstd、退休收据和原件，不等待无关的 G-C。

1. 先写窄 snapshot 清理器的 RED：合法副本、坏 hash/size、当前 DB、非 snapshot/原文、reparse、basis 漂移、重复 apply/中断恢复。目录参数属于存储维护层，不进入上层业务 DTO。
2. 工具只允许 catalog 目录直接子文件 `catalog.sqlite3.bak-*`，SQLite header，绑定已完成的 prepared/retired 机器收据和保留 archive 的 hash/size；不支持通配符或递归删除。默认 dry-run，显式 apply 复用 CatalogOperationLock，落小型 intent/receipt，失败具名。
3. 一个节点包：小型真实 catalog/raw→复制 SQLite snapshot→dry-run→apply→重复 apply，现有来源读取/原文 hash、主库字节不变，测试根恢复。无需每个 helper 审查或完整备份恢复。
4. 节点绿后执行生产 B1，记录精确删除 B、同卷 free 前后（其他进程变化不能硬归因）、主库 SHA/mtime 与保留 archive 身份、原件零改动。预期逻辑释放 2.846 GiB；实际收据决定是否完成。

## B2：derived/index

注册的 6,714 个唯一路径共 2,794,944,096 B（normalized 3,507 / 2,748,603,555 B，sections 238 / 36,598,946 B，summary 2,969 / 9,741,595 B）；另有 390 个未登记文件 / 31,066,538 B。663 个注册唯一路径有历史 size/SHA 冲突，不能按 artifact 行逐条 unlink。CWP `llm_summarizer` 与 legacy RF 来源准备仍有 normalized 调用者。

先形成按真实路径去重的 plan（文件 SHA/size、所有 artifact ID/source ID、实际消费者引用）；仅该批 consumer 切换后删除。缺引用信息或漂移只 hold 该候选。scratch 删→从 raw 重建→reader/export/query 对照→生产精确批次 receipt。现有 Git deletion_manifest、DB retired-span prune、raw duplicate/focus cleanup 均不替代这个文件清理器。bak + 全 derived/index **理论上限 5.520 GiB**，不能提前承诺全可删。

## B3：旧派生归档

独立决定 deprecated evidence ID 的行为和来源事实保留形式；验证运行时没有 cold reader，再提取必要的小型 metadata/ID tombstone（不是保留全部 retired span 正文）。只读 stream/list/hash 足够的地方不落盘全恢复。不得同时盲删 zstd/gzip；先明确历史元数据/当前回滚保留范围和实际空间收益，再按精确单批执行。

## 后续运行入口缺口

E-B 的 Supervisor/Store/handler/projector 已完成，但当前产品 `automation.cli` 的 status/doctor 仍是固定 not_configured/AUTO-7，已观察到的 runtime factory/真实模型返回实例均在测试辅助。G-C 证明 consumer 能读持久包，不自动证明生产 batch/daemon 可运行。完成 G-C 后须先核已有入口，再补一个薄的生产 composition/bounded batch 施工细则与 TDD；不能把 replay 测试模型接入生产或直接启动旧 Worker。
