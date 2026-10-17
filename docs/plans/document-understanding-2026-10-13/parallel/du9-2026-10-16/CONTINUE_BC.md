> 2026-10-17用户最新分工覆盖本历史通用说明：POLICY由ROOT接A并已完成B/C纯组件及独审（6e0edeef），PLANNER仍由原harness完成，ROOT等待；不要求PLANNER或POLICY作者重复施工，原工区只读边界保持。

# DU9两包继续施工说明（沿用原卡，不是新任务包）

ROOT当前在指定目录只找到A阶段成果。若最终实现已在其他目录/分支，请直接给最终handoff路径和commit，不重写已完成代码。若指定目录就是实际交付，则按下列要求继续原卡B/C。

## 范围与所有权

| 包 | 原工作目录 | 原计划 | 必须完成的实现 |
|---|---|---|---|
| POLICY | `C:/Users/郑曾波/Projects/company-wiki-du9-geometry-policy` | `docs/plans/du9-geometry-policy-2026-10-16/` | 唯一catalog的typed geometry意图、原registry解析与因果摘要、`geometry_policy.compile_geometry_policy`、新旧回归 |
| PLANNER | `C:/Users/郑曾波/Projects/company-wiki-du9-geometry-planner` | `docs/plans/du9-geometry-planner-2026-10-16/` | 纯规划/申请/状态恢复入口、共享调用者预算、章节公平/重叠去重、输入边界与所属层端到端 |

完整白名单及验收依据仍是原 `construction_card.md` 和 `INTERFACES.md`。两个工区、源码目录不重叠，可同时继续；无需等待ROOT或兄弟实现。POLICY不做调度，PLANNER不改catalog/匹配器；不修改ROOT的source/parser/automation、其他仓库或生产配置。ROOT已经预先授权卡内完整实现。

## 连续执行，不在A停工

1. 读取自己原PWF与原卡，保留A调查、已有提交和未提交半成品。把状态改成实际进度，继续执行B，再执行C。**A阶段冻结期望不是STOP，也不需要ROOT人工签收、新许可或新接口批准。**
2. 先用原固定接口与自有合成夹具建立实际可复现失败，然后实现。A中作者自己写的假设不能覆盖原接口；若不一致，记录依据并纠正假设，不能为迎合手算假设修改兄弟模块或旧gold。
3. B集中测试：POLICY覆盖不同市场/文种、同role不同规则、行政priority1与fine解耦、混合附注、unknown、实际相关改动的摘要因果及旧wire；PLANNER覆盖零/小额度、重复/嵌套窗口、父文scope、乱序/无导航/未来未知、状态重放与诊断上限。只使用原WorkBudget，不重置15秒/64页/工作额度。
4. C直接从自己公开入口进行所属层E2E与恢复，验证输入不变、临时目录/sentinel/配置恢复、0供应商。组件测试不代替ROOT的真实PDF深页或正式摘要验收。
5. 在C调用另一独立审查agent，审查最终代码、边界、反例、测试及交接真实性；修复其发现，再让该独立agent复核最终SHA。只有C做这次集中审查，不为每个小步骤增添人签。平台不能启动独立agent时如实记录缺失能力和已完成进度，不能谎称全部完成。
6. 正常提交实现/测试/自己的PWF，保留hooks。提供原接口要求的 `handoff.md/json`、独审报告/精确SHA及测试收据。**最终提交和交接之后才STOP**；不自行并主线、推main或改安装技能。

## 交接前自行核对

- POLICY实际文件及专用测试存在；公开模块可import；不是只有findings或未运行的测试设想。
- PLANNER公开包可import并能运行 `plan_geometry_requests` / `admit_geometry_request`；`__init__`不得引用缺失的planner模块。状态JSON重放结果与连续处理一致。
- handoff中的每项PASS有实际退出码和收据；没运行或缺失写明NOT_RUN，不能把A完成、ModuleNotFoundError或未提交DTO称完整交付。
- 用 `git status --short` 解释所有剩余文件；所有卡内完成代码正常commit，不遗留实际实现只在未跟踪目录。

交接格式继续使用原 [INTERFACES.md](INTERFACES.md)。ROOT接收后再统一生产装配/并线，原件不改。无需另立计划目录或新签收系统。
