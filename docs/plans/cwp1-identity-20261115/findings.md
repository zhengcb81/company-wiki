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
