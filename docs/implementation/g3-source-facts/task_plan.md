# G3-SOURCE-FACTS — 任务计划

**卡**：`docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g3_source_metadata_and_raw_space.md`
**Worktree**：`C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki` 分支 `codex/g3-source-facts`
**Base**：`5930a644453ed46494c2c83c5ecfb97767fa9492`
**性质**：只读调查包。生产 0 写、raw 删除 0、无 apply/DELETE/UPDATE。

## Goal

为 PWF R2/R4 供应真实决策依据：
1. 九样本（S01–S09）逐份原文/官方来源/目录事实核实 + retired 追溯 + 小范围可应用 metadata 提案；
2. 仅 company_raw 内部重复的真实上界、有限实读、是否值得进一步对象化的判断。

## 独占写集

- `docs/implementation/g3-source-facts/**`
- `tools/g3_source_facts/**`
- scratch：`.planning/g3-source-facts/scratch`（临时，finally 清理）
- 不改 src、RAW-DUP 工具、总 PWF、仓内 `config/**`、CLI/Store/reader/AUTO、生产 companies、生产 SQLite/sidecar/ET。

## 预算（硬约束）

- 原文读取总预算 512 MiB（metadata SHA + R4 实读合计，重复读计入）
- RAW-DUP 每轮 ≤20 组、≤256 MiB、≤120 s；两轮合计不超总额
- 网络：单页 ≤5 MiB，累计 ≤50 MiB，重试有界，不用 LLM/付费/密钥
- 下一轮 max-read-bytes = min(本卡剩余, 268435456)

## Phases

### Phase 0 — 环境与基线锁定
**Status:** complete
- 建 worktree、锁定 base、记录生产 config/source_catalog.yaml SHA256（`3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`）
- 读 samples.json / golden / README、source_catalog 配置、raw_duplicate_audit CLI、DB 只读入口
- 产出：`findings.md` 基线章节

### Phase 1 — TDD 反例框住提案（先写测试，不改事实）
**Status:** complete
- `tools/g3_source_facts/tests` 反例：filename→公开日 unverified；活动日≠公开日；SHA 不匹配禁 verified；retired 原因未知禁 active；两官方记录冲突→conflict；sample ID≠生产 ID；外根/same-path/hardlink 不计内部多副本；未实读不计 verified 收益；超预算停止而非报完整
- 配套实现：`budget.py`（512MiB/256MiB/20组/120s，超额即停）、`proposals.py`（action/conflict/problem 规则）、`raw_space.py`（company_raw 内部上界与实读收益）、`catalog_probe.py`（mode=ro+query_only 单读事务）、`report.py`（0 apply、拒绝绝对路径、只覆盖自身报告）、`cli.py`（proposals/raw-space 两个只读子命令）
- tmp SQLite 夹具验证 0 writer/0 源目录写、坏 SHA/缺日期、no-op/冲突、报告恢复
- 责任测试：`python -m pytest -q tools/g3_source_facts/tests` → **47 passed**

### Phase 2 — 九样本逐份核实（只读）
**Status:** complete
- 定位九原件、stat/云标记/路径包含、预算内一次 stream hash、抽必要页日期/封面/证券/期次
- 生产只读事实匹配 location→source→document/version/acquisition；S01–S04 retired 追 journal/supersession
- 官方一手来源核公开日/证券代码/accession；S09 从 TXT 正文核 ticker/FY2026Q4/语言/日期
- 产出 `metadata_proposals.json`（action ∈ no_change/update_metadata/register_new/do_not_reactivate/unresolved）

### Phase 3 — 零模型 skip 候选 + SourceRef 建议
**Status:** complete
- 一份元数据可核的有价值 IR 或 TXT 的 pathless 生产 SourceRef 建议（已登记才有 ID）
- 一个已有合适纯流程零模型 skip 候选；无合适候选则明确缺口

### Phase 4 — company_raw 内部空间核实（RAW-DUP 有界）
**Status:** complete
- scratch 生成只含 company_raw、路径显式指回 live companies/DB 的调查配置；`catalog_dir` 绝对定位真实库
- 离线 fixture 确认过滤（未配置外根不 stat/hash）
- `scan/verify --config <自身绝对配置> --project-root <live CWP 绝对根> --output <自身报告> --max-groups 20 --max-read-bytes 268435456 --deadline-seconds 120 --max-detail-rows 100`
- 不用 `--hash-catalog`、不用 `--overwrite`；报告不带本机绝对路径
- 产出 `raw_space_decision.json`

### Phase 5 — 集中验证与恢复
**Status:** complete
- `python -m pytest -q tools/g3_source_facts/tests`
- 校验：未知/冲突不转 ready；sourceIDs 全为生产事实或明确未登记；预算读数字可加和；净释放字段全 0
- 运行前/后核生产 config 字节、样本 SHA、DB 只读关键事实
- finally 恢复 tmp/渲染/新副本；不提交原文 PDF/TXT/整页 HTML/密钥/绝对路径清单

### Phase 6 — 交接产出
**Status:** in_progress
- `HANDOFF.md`、`handoff.json`（g3-handoff/1）、`evidence_index.md`
- 正常 commit 到 `codex/g3-source-facts`，不推 master、不合 master

## Decisions Made

| # | 决策 | 理由 |
|---|------|------|
| D1 | 计划文件与卡交付物同置 `docs/implementation/g3-source-facts/` | 卡第8节明确该目录含 task_plan/findings/progress |
| D2 | scratch 用 `.planning/g3-source-facts/scratch` | 卡第2节指定 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| （暂无） | | |

## Phase 5 实测

- `python -m pytest -q tools/g3_source_facts/tests` → exit 0，55 passed，7.2 s
- 生产 `config/source_catalog.yaml` SHA256 运行前后同为 `3d159a4e…e3f968`
- 9 份原件复核：bytes/SHA 与 `samples.json` 全部一致
- 生产 DB 复核：schema 1.2.0、sources 43112、locations 46606、documents 23530、statuses active 25048/missing 6/quarantined 1/retired 21551、`total_changes=0`、db 222,408,704 B、`-wal` 0 B、`-shm` 32,768 B；8 样本 location/document 状态与开工时一致

## Next Step

Phase 6：写 `HANDOFF.md`/`handoff.json` → 清理 scratch → 分两次 commit（不推 master）。
