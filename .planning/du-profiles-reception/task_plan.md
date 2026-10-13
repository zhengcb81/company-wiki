# DU-PROFILES 接收修复

Owner：ROOT/du_profiles_reception_fix；独占 profiles-fix；base f734ef926de9f64f530bc11f5254dd2f51de2665。

目标：修 R01/R07 的共同策略组合、探测饥饿、SEC 用途与附件边界。DU/1必需字段不改；additive modifiers已由ROOT确认。只 profiles 与自身测试/交接，DU2与作者树不触碰。

- A complete：最初20反例18FAIL/2PASS；最终30反例修复前9FAIL/21PASS，均有意义的行为差异。
- B complete：180PASS=150旧+30新；ruff PASS；mypy 9 files PASS；无旧误断言删除或改写。
- C complete：实际 strategy_probe/701单元压力输出已留证，正常 hooks 提交实现 `e033b4bef8a33676e05208843075d4826e1b3525`，handoff含真实SHA。

固定 budgets不增；角色别名稳定规范化合并，后续更具体块显式覆盖priority。封面/分布式heading/body、公平字符前缀、截短来源语义、外层 SEC/内嵌区间与摘要/修订轴一并实现。无审批、公司特判、下载、翻译、模型调用或新依赖。

## Next Step

交 ROOT 接收实现与 receipt commit，集中跨层验证后并线；本worker停止修改。
