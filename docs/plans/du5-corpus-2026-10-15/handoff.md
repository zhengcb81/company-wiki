# DU5-CORPUS handoff

2026-10-15。分支 `codex/du5-corpus-20261015`，基线 `8c027011037dc8c8659235fb65f529028dcd15ca`。
机器可读伴件：`handoff.json`（du5-handoff/1）。本卡生产写入 0、供应商/模型调用 0；
原件、生产配置、sentinel 全部恢复留证。**交付后 STOP，等 ROOT 统一接收；不并主线。**

## 交付了什么

1. **9 份冻结金标（du5-gold/1）**：7 公司、CN/HK/US、9 形态（A股半年、经营季报、
   稀疏纯财务季报、增发、港股中期、港股季报公告、8-K 容器、业务 exhibit、原语言
   电话会转写）。冻结记录 `du5_manifest.json`：gold SHA、support_set_digest、冻结
   时间、已读/未读页域、来源侧业务目标、prior use。指定陷阱两组：珀莱雅
   期间/单位表、吉比特 否定/计划/问答。全部锚点在冻结前经独立提取逐条验证。
2. **coverage 五轴**（`coverage_matrix.SAMPLE_AXES`）：original/gold/readable/
   selected/summary_reviewed 分轴显式声明，修掉“一个 REAL 塌缩五轴”的共同根因；
   hk_quarterly 与 sec_8k_6k_exhibit 依新原件转 real（REQ-3 生产验收保持 open），
   us_s1_f1/amended_filing 如实保持 missing。
3. **锚点完整性机制**：`tests/anchor_verify.py` + `test_gold_anchor_integrity.py`。
   旧 317 锚点实测：309 命中、3 个错页（cn-equity p62→61；cn-q-sparse p2→1）以
   `gold_corrections.json` 提案更正（旧 gold 字节不动、旧值可回放），4 个不可独立
   验证锚点（扫描/CID乱码/字形/XBRL边界）显式记录。
4. **独审 v2 更正**：C 节点独立 reviewer（只看原件+金标）复核 2 组新目标，
   22 事实全 RESOLVED；其判定的 4 条真命题负例与 1 条 modality 误标按
   “改错金标需单独更正记录和版本”应用（old/new 逐字段记录，锚点/重要性/分母未动）。
5. **机制正控**（真实 du5 gold 上）：可读替代 support 组不被不透明组拖累；
   错页引文永不召回；重复 sample_id 拒载；旧 20 gold 文件字节锁（blob 身份哈希）。

## 实测收据

| 项 | 结果 | 收据 |
|---|---|---|
| 离线集中回归 | 236 passed / 9 skipped（基线 217 全数保持） | receipts/B-central-pytest-offline-final.txt |
| real_data 集中回归 | 245 passed | receipts/B-central-pytest-realdata.txt |
| Ruff 本包 | 0 errors | receipts/B-ruff.txt |
| native CLI E2E ×2（复跑一致） | 9/9 可读；新集 critical 12/37=0.324（8 FAIL/1 PARTIAL） | receipts/native-run-final/native/summary.json |
| 恢复 | raw/config unchanged、sentinel restored、raw_copies=0、model/paid/network=0 | 同上 restoration 节 |
| Git 字节链 | add→blob→fresh-checkout 全一致，fresh-checkout SHA=冻结 manifest | receipts/git-blob-roundtrip.txt |
| 原件前后 SHA | 9/9 UNCHANGED | receipts/originals-sha-before/after |

native FAIL/PARTIAL 是待修生产质量缺口（召回 0.324），按卡不修源码洗绿；
分母真实（critical_fact_unavailable=0）。旧集结果不并入：旧基线表保留在包
README（旧/新分开），本卡只重测新集。

## 真实 RED 留证

- `receipts/RED-coverage-axes.txt`：coverage 五轴塌缩（真实数据 3 failed → B 转绿）。
- `receipts/RED-gold-anchors.txt`：错页行 + du5 未建（real_data 2 failed → 转绿）。

## 已知限制（详见 handoff.json known_limits）

- 3 个旧错页锚点为 **proposed** 更正，ROOT 决定是否发布 applied 版本。
- du5-us-msft-* 只填形态缺口（公司非 fresh）；us_10q/us_20f 仍 name-only。
- 独审建议的增补事实因已过冻结点未采纳，列为后续候选（不换金标洗绿）。
- 2 个读取子代理请求被平台过滤拒绝（负例措辞触发），澄清措辞后重发成功，如实记录。

## ROOT 接入步骤（handoff.json root_integration_steps）

合回 CWP → 正式候选走同 CLI/du-observed → 与冻结目标原样比较 → 一旦 du5 样本
参与规则修改即标 regression → 裁决旧金标错页更正版本 → REQ-1..5 采集请求照旧开放。
