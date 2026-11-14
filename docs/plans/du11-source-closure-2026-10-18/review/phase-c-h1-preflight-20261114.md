# 真实摘要预检与历史费用恢复

2026-11-14。延续已验收的 [T4/SEM](t4-sem-20261114.md)，用药明康德 2026 半年报完成一次正式新版本摘要、下游采用及缓存验收。

## 正式试跑前

- 原件 SHA-256 `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。同一 `SourceRef` 已走公开来源接口登记进全新隔离目录，原件复制和下载均为零。真实预检的 112 个证据片段进入正式目录结构，已冻结的 12 个业务检查点均可在实际待发送任务中找到。
- 采用现有配置中的 MiMo `mimo-v2.6-flash`，生产 quote-primary `reading-model-input/5`。原文保留，模型对精选材料排序。此次只开一次新付费尝试。离线构造的请求为 32,958 bytes，SHA-256 `ec7666fe0d9a980cf9a9d7048eacef6a7dfd750bfa59143ef1c124c5e415453d`。正式运行另记真实请求哈希。
- 当前 `config/resource_budget.yaml` 的累计上限 10,000,000 tokens 和 $20。母账预检为 1,965,633 tokens 和 $0.762082 估计/保守记账，包含旧 7 个及新 8 个未知记录。仍沿用原批次最多 200,000 tokens、$1 与 300 秒，既有传输限制保持。

## 试跑工具修复

- 历史 3 个隔离 AUTO 数据库已经按测试约定清理。试跑现在用已入账的母收据 SHA、四个累计金额/保留量字段和每个库的 attempt IDs 恢复账户锚点。原库如存在继续从只读 SQLite 核对。实测匹配 4+2+3 笔，包含既有未知占额的母账值一致。输入由当前任务提供并在此记录哈希。
- `partial` 是覆盖记录，来源 owner 已对当前材料确定身份。验收工具在发送前和发布后核对实际材料 SHA，独立观察依赖状态。部分材料可继续做选中范围的验收。
- RED 包含：已清理但收据有效的库、篡改收据、缺失历史 attempt、改动累计数，以及真实部分材料和错误材料哈希反控。85 项组合通过，本次目录清理。独立审查核对实际九笔收据、原母账和值、部分状态未被提升、恢复路径仍禁止重复 POST。新 run 的实跑请求独立记账。

## 冻结凭据

- 本地 `.planning/shared-reading-production/t4-phase-c-20261114/preparation.json` SHA-256 `46f334ac37f019b447f2f502ef38e4a29e627b11de571424625535d6219dd476`。
- 同目录 `h1-gold.json` SHA-256 `7e898c2e6f4ce216031e68823fc2a885ce68a05a0730d9e876c702e081e72ffa`。
- 母收据 SHA-256 `b711ca14414ea7aa1bf5ee93bae14d6a83141e4a95da29f91a28e3051b69b3c0`，原始 Git 收据 `docs/plans/cross-market-rf-e2e-2026-10-08/phase6/post_w03_original_research_2026-10-11/budget-observation-native-20261011T0140.json`。
- 现有使用账起点 SHA-256 `4b3aec7d4535f921b5d7c3d8f4349b9f8265104e1b89f8d2a359d357ae2021e9`。新 native journal 追加到该原账。旧资料与费用证据仅作只读输入。

本记录完成准备时，未发生本轮外部请求。正式响应、付费恢复、内容质量与 RF 采用仍需分别记录结果。
