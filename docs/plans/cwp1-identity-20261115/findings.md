# findings — CWP1 身份匹配双缺陷修复

## 偏离与决策登记

- 基线偏离: 任务书基线 66c97834d，实际 master HEAD 为 ac8841c55（多出 4 个
  docs(pwf) 文档提交，无 src 改动）。worktree 按任务书给的命令（不带显式 base）建于
  ac8841c55。判定: 安全，src 与任务书诊断一致。
- 红线偏离（唯一，已最小化）: A2 新 reason 字面量触发 FC-1301 分类门禁
  （tests/contract/test_fc1301_reason_taxonomy.py），按该门禁 docstring 的正规流程
  （"a new reason code forces a deliberate registry edit"）在
  src/company_wiki/source_catalog/observability.py 的 REASONS 与 STAGES_BY_REASON
  做了两条纯增量注册（各 1 条，stage=identity）。不做则新 code 成为未注册漂移；
  该门禁在基线本就因既有漂移红（见下），本包未使其变好也未变坏，且自己的新 code
  合规。
- FC-1301 基线既有红: test_every_emitted_reason_is_registered 在基线即失败，
  约 70 个未注册 code（narrative_*、local_reconcile 等，含 security_identity.py
  既有 one_verified_linked_exact_identity / multiple_linked_exact_market_listings）。
  属 master 既有漂移，非本包引入；修复它超出本包范围（会大量触碰无关 src）。
- r8 基线既有红: test_r8_entity_gate_normalization::test_entity_gate_normalizes_trailing_period
  在基线即失败（SourceResolver 缺 catalog 属性的装配缺陷，resolver.py），与本包无关。
- worktree 无 .source_catalog（主仓未跟踪目录）: 只读复制主仓 security_master
  （cn/hk/us.json + issuer_links/）至 worktree .source_catalog/ 供探针使用；
  .gitignore 第 53 行已覆盖该目录，不入库；identify 只读，主仓数据未被改动。

## 实现发现（A1 后缀归一化）

- 首版把后缀当"字符串尾部"匹配（无词边界），全库差分（15825 条记录、59933 个唯一
  canonical/alias/ticker 查询串）抓到两个真实回归: 别名 "VSE" 与查询 "VSA" 都被
  SE/SA 剥离成 "vplc"、"LASE"/"LANV" 都成 "laplc"，使 ticker 查询变歧义。
- 修正为词边界规则: ASCII 法律形式仅在是原文最后一个空格分隔词时归一化
  （"BASF SE"、"Apple, Inc." 命中；"VSE"、"LANV" 这类粘连短 token 不动）；
  中文法律形式无空格，按字符串尾部最长匹配（"股份有限公司" 先于 "有限公司"）且
  要求非空词干。
- 控股是名称本体不是后缀（騰訊控股/阿里巴巴集团控股），类成员只取
  有限公司/股份有限公司/有限责任公司；以 …控股有限公司 结尾的名称经 有限公司
  成员覆盖，控股保留在比较词干中。
- PLC/AG/SE/NV/SA 合并为一个"欧洲公众公司形式"等价类（互相等价、与裸名不等），
  LP/LLP 一类——单独成类等于无操作。
- 词边界修正后全库差分: 唯一行为变化为 "Kemper Corporation" 1→2（KMPR 普通股与
  KMPB 次级债两记录 canonical 同为 "KEMPER Corp"）。这是归一化正确暴露的真实
  多候选，走既有 ambiguous fail-closed（不静默选边），与任务"绝不静默选边"一致，
  登记为已知副作用。基线行为实为"靠 KMPR 独有别名静默选边"。
- 归一化是纯超集扩展（plain 相等 ⇒ suffix 相等），故唯一可能的回归形态是
  1→2+（resolved→ambiguous）；0→1 是改进（阿里探针即此类）。

## 实现发现（A2 具名 reason）

- 新 reason 仅在 exact 候选 ≥2、market 数 >1、且全部共享同一非空 issuer_link_id
  时使用；同市场多候选、跨市场无共享链接（如 "万科"）保持
  multiple_verified_exact_identities。
- src 无任何消费方按 identify reason 字符串分支（grep 核实），值域扩展安全。
- schema 不动: IdentityResult 字段与 IDENTITY_RESULT_SCHEMA_VERSION="1.1" 均未改。

## 验证数字

- 基线（12 文件身份相关集）: 116 passed / 2 failed（均基线既有，见上）/ 2 skipped。
- 改后: 126 passed / 2 failed（与基线完全相同的两个）/ 2 skipped。+10 为本包新增
  测试（A1 族 6 + A2 族 4），全部通过。
- 三探针 + 5 回归探针（真实 CLI，worktree config）: 见 progress.md，8/8 达标，
  回归探针与基线逐字段一致（status/reason/resolved name/market/exchange/ticker/
  match_basis）。

## NOT_RUN / 限制

- 未跑全仓测试套件（数千用例，含 slow/e2e/real_data 标记），只跑了身份相关 12
  文件集与 test_stage_taxonomy；理由: 改动面仅 security_identity.py 的名称比较
  分支 + reason 值域 + observability 纯增量注册，邻接契约已覆盖。NOT_RUN 诚实登记。
- 未做 FC-1301 既有漂移的修复（超范围，见偏离登记）。
- 未 push、未并入 master（按红线）。

## 勘误（F-01，2026-11-15 复审后补）: "身份相关集"选集未枚举

复审指出前文"12 文件身份相关集 116→126 / 2 skipped"未列文件清单，第三方无法精确
复算（审查者等价选集得 105→115 / 0 skipped）。勘误如下，逐文件枚举本环境实际跑的
选集与两态数字；两口径下 +10 增量与失败同一性一致，差异仅来自选集不同。

实际执行的 12 个测试文件（pytest 位置参数顺序即此）:

1. tests/contract/test_source_catalog_security_identity.py（A1/A2 新测试所在文件）
2. tests/contract/test_security_identity_public_ports.py
3. tests/contract/test_security_identity_sec_listing_evidence.py
4. tests/contract/test_fc1301_reason_taxonomy.py
5. tests/contract/test_source_catalog_resolver.py
6. tests/contract/test_cn_primary_issuer.py
7. tests/contract/test_r8_entity_gate_normalization.py
8. tests/contract/test_source_catalog_quality_boundaries.py
9. tests/contract/test_public_legacy_source_recovery.py
10. tests/contract/test_fc1204_coverage_ratchet.py（2 个 skip 的唯一来源）
11. tests/unit/test_local_source_boundaries.py
12. tests/unit/test_stage_taxonomy.py

本环境（/c/Miniconda/python 3.13.9 + pytest 9.1.1，PYTHONUTF8=1，未设
FC1204_COVERAGE_GATE，零网络零下载零模型）实际数字，2026-11-15 勘误时在
同一 worktree 用 `git switch --detach ac8841c55` 基线态 / lane 分支改后态
同口径复算复核:

- 基线（ac8841c55）: 116 passed / 2 failed / 2 skipped（19.12s）
- 改后（a311c3127）: 126 passed / 2 failed / 2 skipped（18.96s）
- 2 个 skip 两态完全相同: tests/contract/test_fc1204_coverage_ratchet.py:121 的
  2 个参数化用例，skip 原因 "coverage gate runs as a separate step
  (FC1204_COVERAGE_GATE=1)" — 环境变量门控，与本包改动无关。
- 2 个 failed 两态完全相同且与本包无关:（a）test_fc1301_reason_taxonomy.py::
  test_every_emitted_reason_is_registered（master 既有注册漂移，失败清单两态均
  不含本包新 code cross_market_dual_listing_requires_market_selection）;
  （b）test_r8_entity_gate_normalization.py::test_entity_gate_normalizes_trailing_period
  （SourceResolver 装配 AttributeError，master 既有）。
- 审查者 105→115 / 0 skipped 与本勘误 116→126 / 2 skipped 的差异全部来自选集:
  本选集多出的 11 passed 与 2 skipped 来自第 10 项 fc1204（2 skip）及第 12 项
  test_stage_taxonomy（20 passed）等文件的存在与否；两种选集下 +10 增量、
  同两个失败、skip 无状态变化均成立。

## 续作发现（2026-11-15，施工包 §5 验收与 §8 收口）

### F-02: 身份根因确认为「后缀变体 + 无名双上市歧义」，非零候选

基线 master 实测：库中**已有**阿里双上市实体（US BABA / HK 09988，
共享 `issuer_link_id=issuer-link-v1:a651e739…`）。施工包 §1 推测的三种形态中，
"零候选"被排除；实际是两种叠加：
1. `"Alibaba Group Holding Limited"` 与库内 official_name `"Alibaba Group Holding Ltd"`
   的 Ltd/Limited 后缀差异 → 掉进 strong_fuzzy，得 5 候选 →
   `fuzzy_candidates_require_user_selection`（A1 后缀归一化修复）。
2. `"BABA"` 同时命中 HK alias_exact 与 US ticker_exact → 2 个 verified exact，
   旧 reason `multiple_verified_exact_identities` 未说明如何消歧（A2 具名 reason 修复）。

### F-03: 修复不静默选边，具名消歧是刻意保留的 fail-closed 语义

`BABA` 无 market 仍返回 `ambiguous`，这是施工包 §3 允许的"带消歧语义的具名响应"，
不是遗漏。理由：不删除任何既有候选数据；两候选各自携带
market/exchange/ticker/security_id/issuer_link_id；请求可用 `--market`/`--exchange`
显式选定（4 个消歧探针全部 resolved）；下游 FF 在指定市场后立刻 resolve 成功。
若强行选 primary 会改变既有已登记实体的引用语义，违反 §4 红线。

### F-04: FF 联动验收通过且可归因（关键修复效果）

未修复 master 对 "Alibaba 20-F FY2025" reuse_only 请求：
`exit=2 / identity_error / "ambiguous / fuzzy_candidates_require_user_selection"`，
与施工包 §1 的 E12 实测逐字一致。修复后 lane：
`exit=0 / source_candidate / resolution_outcome=reused_existing / download_events=0`，
命中真实原件 sha256 `36daec0c…`。**这是本包唯一可归因的下游解锁**。

### F-05: RF 六路线归因对照 —— 不冒领、不引入回归

六路线在未修复 master 与修复后 lane 下**逐条完全一致**：
route3 两边都 `exit=0 / found_capture_ready`，其余 5 条失败原因逐字相同。
因此：
- route3 满足 §5.3 "至少一条 found+capture_ready"，但**该成功不归因于本包**
  （该路线用 `阿里巴巴－Ｗ` 精确别名 + 元数据完整的 FY2025 原件，从未撞身份歧义）；
- 本包**未引入**任何 RF 回归；
- 剩余 5 条为既有下游缺口，非 fuzzy/ambiguous 复发，符合 §5.3
  "或具名新原因说明剩余缺口"。

### F-06: 剩余缺口具名根因（交 Dashboard / FF owner）

- route1: FF `ff_local_source_prepare.py` 把 `identity_scope="listing"` /
  `issuer_link_id` 塞进 `source_request`，却把 `schema_version` 固定 `"1.0"`；
  CWP `resolver.py:591` 要求 identity scope 字段必须用 schema `1.1`，抛
  `SourceResolutionError`。CWP CLI 归为 `invalid_local_prepare_request`，
  FF 再映射成闭集外 `unknown`。**属 FF↔CWP local_prepare 契约层**，
  不属于身份匹配，也不在本包写域（§4 红线：不改 Dashboard 侧适配器/协议）。
- route2/4/5/6: `company-wiki ensure exited 1` /
  `upstream_cause.code=acquisition_validation_failed`，`provider_started=false`。
  属 ensure/采集校验层，与身份层无关；与 RF INPUT-PREP 记录的
  `local_metadata_incomplete` 同源（CWP-2 / FF1 目录层在途 lane 的范围）。
- 建议交接：Dashboard 侧重跑阿里 FF drill 与 RF 采集路线时，把这 5 条作为
  **下游契约缺口**（非身份缺口）分别派给 FF owner 与 CWP FF1 lane；
  本包不再扩大写域。

### NOT_RUN / 限制（诚实登记）

- 未改、未重跑 A1/A2 既有实现与单测；本轮只做验收与收口。
- 未跑全仓测试套件（沿用节点 5 的既有数字与 F-01 勘误，未重复计分母）。
- 未修复剩余 5 条 RF 缺口的任何下游文件；未 push、未并入 master。
- 后台执行曾被宿主沙箱拒绝一次（shell 初始化文件读取），已改用前台执行同一
  Python 脚本完成，未绕过任何拒绝；原始失败记录保留在 `rf-six-routes-run.log`
  之外的说明中（前台成功日志已落盘）。
- 联动探针使用 tmp 夹具指向修复后 lane 的 `src`；Dashboard/FF/RF 三仓的
  生产配置、`config/source_catalog.yaml`、已登记实体与候选数据均零改动。

### §8-3 明示交接任务（不并线）

主工作区存在在途 WIP（`docs/plans/module-pwf-reconciliation-2026-11-14/` 等），
且 `codex/ff1-catalog-repair-20261115` lane 的 B4 尚未收口。按 §8-3 情形 2
**不强行并线**，改为显式交接：

> `OWNERPKG-CWP-CANDIDATES-01` 分支 `codex/cwp1-identity-suffix-20261115`
> 通过独立重审（`INDEPENDENT_REVIEW.md`，reviewer_status=approved，0 OPEN P1/P2）
> 后，**待主工作区在途 PWF 收口、且 ff1-catalog lane 并入/明确不冲突后，由主线
> 任务执行并线**；触发人：company-wiki 主线 owner（操作者）。
> Dashboard 侧消费以 handoff.json 的 `release_tag_or_commit_for_dashboard`
> 为准（40 位 SHA，可 git rev-parse；不在此处写死以免文档自指）。

### F-08 决策登记: release commit 取 `8de234871` 而非重审时点 HEAD

独立重审 F-R7 建议用重审时点的 HEAD `4b0fc3fe5`。实际 handoff.json 采用
`8de23487113bc8316b45bd5c8ca6a2680be6b333`（重审报告 + F-R5 证据闭环之后的提交）。
理由: 该提交与 `4b0fc3fe5` 的**实现与验收证据逐字节相同**，只多出
`INDEPENDENT_REVIEW.md`、3 个主探针 `.command.txt`、`evidence/replay/` 与 PWF
节点状态，全部为 docs/evidence-only，不改变任何实现语义；Dashboard 按该
commit 消费可一次取到实现、全部证据与独立重审结论。
handoff 文档本身是同分支上更晚的 docs-only 提交（`f927062ef`），
**不写进 release commit 以避免文档自指**（沿 parallel-lanes 惯例：
`result_commit` 指向实际产品/证据提交，元数据提交另行登记）。
两个 SHA 均可 `git rev-parse`，分支 `codex/cwp1-identity-suffix-20261115`。
