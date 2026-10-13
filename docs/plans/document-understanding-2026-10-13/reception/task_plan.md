# 旧DU三包接收与共用根因整合

PLAN_ID: reception
PWF_PLAN_ROOT: C:/Users/郑曾波/Projects/company-wiki/docs/plans/document-understanding-2026-10-13
Owner: ROOT

## 目标与边界

接收DU-PROFILES/STRUCTURE/BENCH及已有ROOT整合成果，按review/root_implementation修复接收阻断，集中测试后并主线、推远端、更新PWF。新DU2-FAMILIES/FACETS/LAYOUT正在施工，独占目录和三个工作树不写。原件/生产配置/邻仓WIP保持；真实模型与完整公司G2/G4/G5仍归母计划。

## 阶段

1. [complete] 最新交付/祖先/范围核对；ROOT接收树以主线5a297244合入旧整合及BENCH最终b891cf74，接收基线f734ef926，最新review及三仓架构改造保留。
2. [in_progress] TDD集中修复：benchmark与profile互斥修复中；ROOT八RED及独审追加四RED已修，39相关PASS，独立七反例复核PASS。收到两叶后集中整合。
3. [pending] 一次集中B测试及代表原件回放，独立审查核心修复；正常提交/合主线/推送，整理重复派生证据与更新总PWF。

## Next Step

接收两个互斥修复叶，合入ROOT核心修复；单次全DU集中测试＋代表原件回放，再正常并主线/推送。生产AUTO摘要接线与DU2布局/业务扩展、真实G2/G4/G5仍需后续大节点，不能把模块接收写成全项目完成。

## 初查

- 三作者树status均空；benchmark又有3e526033后的两个提交，handoff列ad77758d已过时，验收以最新实现与实际测试为准。
- ROOT整合树未包含最新benchmark b891cf74；它已包含profiles和structure；生产尚未启用。
- 原整合包含两个较大native summary和阶段重复记录；合入后集中整理，不删除原始公司资料。

## 错误与修复

- 接收merge只有README/task_plan/progress三文档冲突，保留主线review导航；作者记录仍完整在各自handoff。
- diff --check发现旧STRUCTURE .gitignore EOF空行，接收树修正后正常merge commit。
- 首批八RED全部复现；第一次相关回归暴露metadata参数被循环局部变量遮蔽和纯shadow包状态归因，修正后162PASS/11缺绑定SKIP。
- 独立审查发现预算在materialize阶段再次切断跨包依赖/否定；追加四RED后用共享依赖定义对实发全集反查，39PASS，非必要缺失partial。独审七正反例PASS。
- 外部工作树默认沙箱Git/ruff cache写入拒绝；必要操作用已授权require_escalated，ruff只读检查用--no-cache，未改Git注册或权限配置。
