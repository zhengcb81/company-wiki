# 调查结果

- 三包均有实际独立 worktree；分支、commit 和 FF 代码依赖见 prepared-roots.json。
- RF 已有单模型、期间、校准测试；新包只补原生 draft 引擎的组合反例和可复用报告，不修改 core。
- Audit 已有 W06 数字度量审查；新包只补 A02/A05/A06/A08/A10/A13/A17/A18 的可观察风险诊断，不重复算术、来源身份验证或预测。
- FF 旧 41 为 40PASS/1FAIL、164.62 秒；修 cutoff 后两次结果分别 2PASS/31PARTIAL/8NOT_RUN、182.86 秒和 1PASS/27PARTIAL/13NOT_RUN、184.54 秒。底层 cutoff/usage 的最终集中复验 7PASS；当前阻碍是批次准备/进程/最终证明共同超时，不是 31 个产品缺陷。
- FF 以 2d380a05 为基线，ET d0ac42c6/CWP d75f0d42 的 code-only 快照已准备；这些来源修复尚未因此发布到主线。
- 详细只读候选复核在 candidate-review.md。当前范围不需要真实金融数据或 LLM；不能据此认证经济结论。
