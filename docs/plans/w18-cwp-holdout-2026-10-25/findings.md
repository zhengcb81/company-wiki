# W18-CWP-HOLDOUT Findings

ROOT已经按代码基线ba8f8543c0351f6857e1ce24e943ad9da1b664ef准备隔离工区和施工卡，没有启动产品实现或测试。

本卡已知事实、来源和验收要求以construction_card.md为准。原主工区已有WIP由ROOT记录并保留，不属于本卡。禁止复用他人可变工作区、生产目录或收费调用充当合成测试。

## A节点发现（2026-10-25）

- DUB既有能力可复用：du-gold/1 schema+records.validate_gold、observer.observe_native（生产parser/selector只读观察）、holdout_acceptance_contracts.configured_preview（零POST编译scoped model view）、recovery sentinel/cleanup。缺口：无"冻结producer commit验证+显式producer-repo/manifest驱动的单一入口"，需新薄编排tools/holdout_replay，不复制评分/恢复框架。
- SourceRef解析需要catalog DB；自有隔离湖用测试根catalog+register登记8原件（root指向主仓companies/只读），不写生产库。
- H02排除核查完成：8个候选SHA零命中28个DUB gold+du5_manifest+25样本m1清单SHA全集；紫金年报SHA有3处元数据级出现（迁移保留/金丝雀预检/去重核验）→local-unseen，其余fresh。
- 8样本96业务目标冻结；锚点以PDF页级为主（DOCX/HTML用document级），引句全部由构建器从独立提取切片保证逐字。

## 待调查

- 现有实现/测试已满足哪些需求，真正缺口有哪些。
- 中性RED与真实来源/公开产物各自证明的范围。
- 复用owner、兼容与失败恢复；未证实字段保持unknown。
