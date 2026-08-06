# ADR-008：可复用 root 配置化（Strategy B）——portfolio 等已索引目录直接复用

- 状态：accepted
- 日期：2026-08-04
- 前置：ADR-007（`import-portfolio` 手动提升桥，commit 7ce2774）
- 背景与演进：
  1. ADR-007 交付手动提升（拷贝进 companies/），但无自动调用点 → "已提交但不生效"（三层根因见
     `docs/plans/portfolio-reuse-automatic/findings.md`：孤儿命令 / worker 锁阻塞 / 端到端未接线）。
  2. 初版自动提升方案（ensure 内 `_try_promote_portfolio`）实现并验证后，审查发现其
     **只对 dayu_portfolio 目录结构有效**（硬编码 kind + dayu meta.json 格式），加新目录需每目录
     一套适配代码——违反一般性与 config-driven 原则。决定**弃用自动提升，改行 Strategy B**。
- 决策（Strategy B，config-driven 只读复用）：
  - **resolver**：可复用 root 从硬编码 `{company_raw}` 改为配置项
    `reusable_root_kinds`（`source_catalog.yaml`，默认 `[company_raw]`；生产配置
    `[company_raw, dayu_portfolio]`）。加目录 = 配置加一行，代码零改动。
  - **scanner 元数据富化**（dayu_portfolio 专用路径）：把 filing `meta.json` 的身份与分类字段
    并入文档元数据——`form_type→document_kind`（FY/H1/Q1-Q3 映射）、`fiscal_year`、
    `source_url`、`provider`(source_provider)、`language`、`filing_date`；身份回填：
    `security_id←ticker`、`market←实体级 meta.json`；分类器与 admission 同步 FY/H1 映射
    （繁体标题 年報/中期報告 也纳入 token）。
  - **resolver 身份归一化**：security_id 比较去前导零 + 小写（HKEX "03896"=="3896"）。
  - **filing-fetch 路径围栏配置化**：`config/company_wiki.json` 增 `allowed_handle_roots`
    （默认 `[<wiki_root>/companies]`；生产配置加入 dayu portfolio 目录），`validate_handle`
    按允许根集合校验 canonical_path。
  - **陈旧防护**：`_handle` 构造时校验文件存在性（已存在，覆盖所有 root）。
  - **锁健壮性**：直接 ensure/import-portfolio CLI 对 `CatalogOperationLockedError` 指数退避重试
    （`_retry_on_catalog_lock`）；filing-fetch 路径由 `PausedWorkerScope`（v1.4.0）保护。
- 语义护栏（fail-closed 不削弱）：
  - 只读 resolve 仅放行 `reusable_root_kinds` 中 root 的文档；未列入的 root 照旧不可复用。
  - `filing_date > as_of_date` 不匹配（resolver published 门）；身份未 verified/active 不匹配。
  - handle 必须 capture-ready（https_url/published_date/snapshot/capture_trace + 文件存在 + 哈希一致）。
  - filing-fetch 独立围栏与 company-wiki 配置**双闸同步**（都是配置驱动，非代码硬编码）。
- 不采用的方案：
  - Strategy A 自动提升（ensure 内 `_try_promote_portfolio`）：实现并验证后被弃用——per-目录结构、
    磁盘拷贝、提升状态机，对"已索引即可复用"目标过度工程。`import-portfolio` CLI 保留为
    "固化"批处理工具（ADR-007）。
  - 把复用逻辑放进 filing-fetch：破坏主仓库=company-wiki 原则。
- 保护的不变量：单一写者（只读复用不写盘）、不可变 sidecar、字节哈希校验、路径围栏（配置化）。
- 验证：契约测试（resolver 可复用 root 配置化 / 默认排除 / 陈旧不复用；filing-fetch 围栏
  配置化通过/拒绝/加载）；真实 E2E：安踏体育（2020.HK）FY2023 年报经 filing-fetch 只读请求
  **直接复用 portfolio 文件**（collector=`filesystem-catalog-dayu_portfolio`）、`capture_ready`、
  零下载、https_url/日期/年份齐全。
