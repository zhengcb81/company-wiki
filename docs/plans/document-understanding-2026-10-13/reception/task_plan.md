# 旧 DU 三包接收与共用根因整合

PLAN_ID: reception
Owner: ROOT
状态：A/B 工程接收完成；C 正常并主线、推送与精确 CI 收尾中。

## 目标与边界

接收 DU-PROFILES / STRUCTURE / BENCH 和原 ROOT 整合，修复共用根因，集中测试后发布。
新 DU2-FAMILIES / FACETS / LAYOUT 已由用户分发、正在排他目录施工，本轮不改它们。
原件、生产配置和邻仓 WIP 保留；模块接收不代表生产摘要切换或真实研究验收完成。

## 阶段

1. [complete] 核最新提交、祖先、范围；主线 review/架构改造保留，旧三包及 ROOT 最新分支已整合。
2. [complete] TDD 修 profile / 子正文绑定、上下文不动点、最终预算裁剪、真实证据评测。独审追加反例修复完成。
3. [complete] 集中 B：491 PASS / 18 real_data deselected，13.76 秒；四份真实原件 11 PASS / 0 FAIL，14.72 秒。追加最终切片→独立 oracle 接口 5 PASS；benchmark 147 PASS / 7 real_data deselected。两轮独立核心审查无剩余阻断。
4. [in_progress] 正常合主线、推远端、精确 CI 留证；更新母计划，回收 ROOT 自有临时接收工作树。

## 统一验收记录

[接收汇总](acceptance.md)、[机器结果](evidence/acceptance.json)、[紧凑测试留证](evidence/test-receipts.zip)。
真实回放使用本机绑定，4 原件及 6 配置 SHA/mtime 不变，预存哨兵不变，自有 tmp 删除；0 模型 / 0 新费用。
旧 benchmark/root 的自证式命中率不再作为当前质量结论。微软独立真实 baseline 关键业务仅 4/8，4 条漏读仍是 FAIL；没有删 gold、降重要性或加付费/切片预算以换绿。

## 后续顺序（不等待小节点签收）

1. DU2 三包交付后 ROOT 一次接收并应用策略数据与布局辅助；R08 布局/来源行坐标、R09 业务价值预算继续开放。
2. 生产摘要仅通过 `build_summary_input` 接既有选择器/AUTO Store/配置模型与预算；旧 `package_units_for_prompt` 不作为模型入口。模型调用消费子策略 focus、来源日期、角色和 deferred，不能只测试组装函数。
3. 同一大节点做真实 source→读策略→选择→配置供应商摘要→locator 回开与独立业务 gold，保留无模型 producer-only 与模型质量的区别。新 Observer 未测整份 CID 乱码，不替代 native observer 该检查；TXT 行范围未提供时保持 unknown。
4. 回到母计划真实 G2/G4 原三家公司/G5 新三家公司及审计循环。以已有预算和请求执行，不新增授权 JSON、canary、人工作业签收。

## 错误与修复

- 首批 8 RED 复现别名/子正文失效、闭包顺序和限制、上下文缺失/误去重、元数据透传等问题；已有 8 反例保留。
- 独审再发现最终 package/char/context 预算截断后断链，先追加 4 RED，再按真实实发全集做不动点反查；独立 7 正反例 PASS。
- 初次 metadata 循环变量遮蔽、全 shadow 状态归因已修。公开 normalizer 回放测试曾遗漏 required limits，并误改 administrative 断言；最终行政 False / unknown None 两者均保留正确语义。
- 本机 bindings 缺少产生的 skip 不当通过；集中真实节点已显式绑定并运行 11 项。
- 外部 worktree Git/ruff cache 的沙箱写入限制用授权的 require_escalated 和 ruff --no-cache 处理，未更改仓库权限或 Git 注册。
