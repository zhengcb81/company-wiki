# DU5-CORPUS 独立施工计划

状态：READY；2026-10-15。工作目录 `C:/Users/郑曾波/Projects/company-wiki-du5-corpus`。

分支 `codex/du5-corpus-20261015`；源码基线 `8c027011037dc8c8659235fb65f529028dcd15ca`；仅自己的文档seed额外提交。

先读 [施工卡](construction_card.md)、[接口与交接](INTERFACES.md)；两者给出完整范围、禁止重叠路径和验收。

## A：实际问题、接口和TDD

**Status:** pending

读实际源码/PWF，核对旧已完成能力；固定自己的精确改动清单、输入/输出及兼容边界；先写真实行为RED。不得把import错误当唯一RED。

## B：共同根因实现与集中回归

**Status:** pending

在卡内范围实施通用方案，跑本包与直接相关集中测试，记录真实失败/通过及未测。只更新自己的PWF。

## C：公开入口E2E、恢复与交付

**Status:** pending

运行卡内实际CLI/独立质量检查，保护原件/配置/sentinel并恢复测试目录；正常commit，写handoff.md/json，STOP等ROOT接收。不要并主线或安装技能。

## Next Step

从A开始；本卡可独立运行，不等待兄弟DU5或ROOT新协议。只有A/B/C大节点，不增加小节点审批。
