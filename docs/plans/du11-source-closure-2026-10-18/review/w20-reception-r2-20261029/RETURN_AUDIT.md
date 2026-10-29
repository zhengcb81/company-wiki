# W20-AUDIT 第二轮定点补完（2026-10-29）

本文件取代上轮RETURN_AUDIT作为当前返工入口；同一原卡、原工区、原分支继续。只剩原R1一个P2共同根因，原R2已关闭，不重做整包。ROOT未并线/安装，主线公司循环仍暂停。

- 工区：`C:/Users/郑曾波/Projects/revenue-forecast-audit-w20-checkpoints`
- 分支：`codex/w20-audit-checkpoints-20261028`
- 本轮HEAD：`da17f2b5b4404c650e77671601e10553b879d2e7`，代码`4ed94fcce99135d7c45ea1f16b5f0ed013b77313`。
- 原PWF：`docs/plans/w20-audit-checkpoints-2026-10-28/`，PLAN_ID不变。
- 必读：[ROOT报告](audit-review.md)、[机器报告](audit-review.json)、[参数化反例](evidence/audit/test_typed_binding.py)、原卡construction_card.md。

## 已关闭，保留成果

原7条反例全绿；作者35项、numeric7项、11步离线CLI通过。显式unread共享availability已经正确，两入口一致，原R2关闭。比例/金额、负号、日元、H1/H2原例已修。20交接文件SHA匹配；不把已有绿测或旧独审改写成失败。

## 原R1剩余：typed信息必须和同一数值绑定

**不变量一：显式单位不向别的数值借量纲。** claim为收入1000元、增长10%，value=1000、unit=元；原文有1,000元，当前反而anchor_absent。`元`是合法identity scale=1的金额单位，不是“没提供单位”；不能因_scale_tokens返回空就从整段claim借增长率百分比，把金额分类为ratio。参数化正/负数及千分隔都有实证。

**不变量二：候选金额不向同段另一笔金额借币种。** CNY12.5亿的claim遇`USD1,250,000,000；人民币余额2元`，当前scale_equivalent。整段币种集合交集不代表当前value属于该币种。USD/HKD/CNY交换角色均可复现。保持candidate的value/scale/currency局部对应；不能判明时unknown或partial，不能全段捐赠正向标签。无需无限币种词典/FX推断/LLM分类。

修同一typed比较owner，复用已有numeric checker兼容能力；是否调用特定函数本身不是独立门禁。将两条不变量变成参数化测试，含合法混合金额与比例、不同币种多金额、明确单位与未声明单位、正负号、缺少信息等有限对照，避免仅针对这两句文本打补丁。原R2及已有正例保持。

## 收尾

原allowlist/隔离要求继续。先存有效RED、修共同owner，跑W20与受影响numeric短包/一次离线CLI即可，不全仓、不重开已闭合R2、不增加审批/授权文件。测试根恢复初态。

调用真正独立agent审查两条不变量及原卡边界，修复全部本范围问题。保留初审/旧RED，本轮review另存，更新同delivery/handoff.md/json受测/受审源码commit及SHA、实际命令和清理。正常commit本分支；本仓无remote，如实记录，不创建公开remote。不自行并主线或全局安装。完成交ROOT，不需中间小节点签收。
