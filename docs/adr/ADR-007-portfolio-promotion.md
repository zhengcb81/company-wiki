# ADR-007：dayu portfolio 提升（promotion）为可复用规范来源

- 状态：accepted
- 日期：2026-08-03
- 背景：`dayu-agent/workspace/portfolio` 已在 `source_catalog.yaml` 配置为 `dayu_portfolio` root 并被扫描索引
  （catalog DB 实测 3,591 locations），但 filing-fetch / revenue-forecast 对其"复用"请求返回
  `no_existing_source_satisfies_request` 并触发重复下载。根因（见
  `docs/plans/portfolio-reuse-fix/findings.md`）：
  1. resolver 复用管线硬过滤 `kind=='company_raw'`，portfolio location 不产 handle；
  2. filing-fetch handle 契约要求 `canonical_path` 在 `companies/` 子树内；
  3. 二者之间没有任何"portfolio → company_raw"桥接。
- 决策：新增**提升（promotion）**能力 —— `import-portfolio` CLI + `portfolio_promoter` 模块：
  把已索引的 portfolio 文档**拷贝**进 `companies/{entity}/raw/{kind}/`（经
  `CanonicalSourceWriter.import_staged` 复用全部受验证逻辑：去重、原子拷贝、不可变 `.source.json`、
  重扫、REUSED_EXACT 断言），携带**规范身份**（先经 `SecurityIdentityResolver` 归一化 security_id，
  如 `3896`→`03896`）。提升后文档拥有 company_raw location，resolver 自然返回 capture_ready handle，
  filing-fetch 零改动复用。
- 配套修复：`canonical_writer._write_provenance` 的 sidecar 增顶层 `market` 字段 —— 使 scanner 的
  prefer-new 元数据合并在提升场景触发（G1），否则新 acquisition 元数据被 dayu_meta 全有或全无合并丢弃。
- 不采用的方案：**只读复用（Strategy B）** —— 放宽 resolver 过滤 + filing-fetch 路径围栏，直接发
  portfolio 路径的 handle。不采用原因：跨两仓改动、削弱路径围栏/篡改证据、portfolio 由 dayu-agent
  可变持有（增删改会导致陈旧 handle），破坏单一写者/不可变不变量。仅在磁盘拷贝成本被证明不可接受时重评。
- 保护的不变量：
  - ADR-005 单一写者：规范写入仍只在 `companies/{entity}/raw/`（提升即拷贝+独立溯源，非软链接）。
  - 不可变溯源 sidecar + 字节 sha256 + companies/ 路径围栏全部保留。
  - 未提升的 portfolio 文档依旧 fail-closed 不可复用（resolver 过滤未改动）。
- 影响范围：新增 `src/company_wiki/source_catalog/portfolio_promoter.py`；`cli.py` 新增 `import-portfolio`；
  `canonical_writer._write_provenance` 增顶层 `market`；测试 `tests/contract/test_portfolio_promoter.py`。
- 迁移策略：按需提升（单条或 `--all`）；已有 portfolio 文档提升一次后即永久可复用。
- 回滚/修订方式：删除 `companies/{entity}/raw/` 下对应 canonical 文件 + `.source.json` + 重扫即可；
  不触及 portfolio 原文件。
- 验证：金山云 FY2022–FY2025 年报/H1/Q1 共 7 份提升后，filing-fetch 只读请求全部 `capture_ready`、
  零下载；幂等 `deduplicated_after_download`；新测试 8 项 + 相关既有测试 39 项全绿。
