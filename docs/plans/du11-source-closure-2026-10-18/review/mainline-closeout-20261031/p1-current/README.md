# P1 当前真实卡片/排名、恢复与新版 RF 采用

2026-11-01：有界工程节点独审通过；正式公司研究与完整长文覆盖继续 OPEN。不是新外包施工包。

## 共因修复

旧实际 Berkshire 为88源任务/72完整卡/16延期，模型请求却带全部88任务、74249B，预留超过已有50000。后附 native range 的发现顺序还会挤掉 BRK-04/07。现在 source-owned 优先级之后，仅同源已知支持坐标用于分配，未知槽位保留；完整支持/context 一字不截。仅发送 canonical 已准入的卡，原文片段/阅读提示各写一次，未发任务仍明确 unprocessed。模型仅给 advisory 排名，不决定事实去留。其他生成式协议、56/64KiB 上限及累计限额不变。

混合用途另有共享根因：compiler 与 execution 重复判断可生成性，后者误用物理可读，令 context_only/unresolved＋support 的真实 handler 失败。execution 已复用来源 generation-reason owner；非支持原文仍不能伪装 admitted。没有新权限、签收或物理根调用。

## 同一生产边界的真实运行

| 样本 | 实际配置 | 实际 POST / token / 估算费用 | 正式产物 |
|---|---|---|---|
| Berkshire 2008 股东信，非10-K | deepseek-flash | 1 / 10464 / $0.004611 | 88任务、73完整卡、15延期；10所需业务原子保全 |
| 华利2023-05 IR，新产物 | mimo-v2.6-flash | 1 / 3630 / $0.000660 | 15完整卡、12所需业务原子保全 |

实际请求分别39520B/12849B，单次预留47840/21169，未加额度。body SHA分别 `66c264bacdc562038fdfe15f2c9a8076d84b71cd694e37b7413be1feb05f234c` / `a466262de5251f0b4e2619eb88f1ba90e8188f5070bb1ea9881a7d5be08b3a45`。两次激活前中断→恢复、完成后同run/跨run均0重复POST，同一body/费用未重复；真实RF来源/叙述读取通过。旧华利精确body `ec1831...` 在新代码仍0POST读取。必要来源 locator 回放确实发生，不能写零解析。

这两次均为 reading-model-input/5 的完整原文摘录卡＋排名，**不是生成式自然语言概述**。Berkshire有15条 unprocessed、模型 RANK_INCOMPLETE、全文 partial；10检查点是已曝光开发样本，不是盲测。模型把 t78/t80 评 low/unclear 或 redundant，卡片与原文仍保留，不可据 advisory 排名删事实。华利15任务内完整也不等于全文完全读取。

## 独审、测试及版本增补

独审原文/每卡完整支持与context、实际HTTP、模型响应、native费用、activation/缓存、旧产物兼容，报告原字节在 receipts/independent。其后只改两个验证依赖；独立免费重算证明两份已付费HTTP、draft、每卡及execution逐字相同，原运行签名未重写。context_only/unresolved 真handler正例与伪造 admitted 负例均验证。最后测试仅将不可变DTO的 deepcopy 改为显式 plain 转换；原2F为夹具复制错误，不是产品放过负例。

正确根因 RED5F、hint类型3F、source-use2F均留证；受影响93例先90P/3个旧presentation断言，适配后目标6P；source-use域53P，最终新增两文件23P/3.23s，Ruff绿。日常pre-push/精确CI在总控 CURRENT_STATUS 记录，不能在此预先签绿。

## RF实际采用及材料留存

同一**新版华利** artifact 已0新模型/下载进入 RF v6 正式参数、公式、报告、snapshot/registry，完整 t3五support＋一context、采用理由/时期/主体持久，独立45断言通过。正式投资产物只放 RF `docs/plans/p2-summary-lineage-20261031/review/v6`，CWP仅存技术审计。2023内容不充作2026经营指引，条件情景不充作已接受公司研究。

母账1,849,869tokens / $0.739510，历史unknown全部保留；这是估算计量而非供应商发票。隔离临时湖清除、受保护配置/原件SHA不变。未复制PDF、全库或完整解析数据库。原最终decoded模型文本、native用量、HTTP输入、generation、selection、prepared bundle/capsule归档；完整provider envelope仅有当时pin/hash与实际恢复证据，临时清除后未保留，不声称可重建该原始envelope。

`manifest.json`只绑定 receipts 下不可变gzip原字节，避免平台换行影响prose。每份运行只留一套材料；旧失败/签名不覆盖。免费离线重放：`python -B -X utf8 replay.py`（仓库宿主配置Python）。它验证请求与已付费捕获、完整draft/execution相等，不访问原PDF、不下载、不调用模型、不覆盖原收据。
