# Transcript Provider Rights Contract v1（已退役）

> **状态：本合同整体退役，不可按其原条款实施。** 2026-09-28 用户确认个人项目不需要逐文件人工审查与审批。当前规则以跨仓总计划 §2.1/S4b 及自动化验收规则为准。

旧版本增加的多阶段 discovery/fetch 权限收据、DownloadAuthorization、provider rights JSON、reviewer/有效期/hash pin、取前取后双重政策复核、Motley Fool/FMP 逐动作人工 gate 均不再是 company-wiki 产品要求。不要恢复这些门槛，也不要为当前来源重建 provider_use_policy.json。

当前实现遵循以下简单规则：

- 对用户请求的准确公司与期次，调用现有可用工具；已存在就按来源 hash 复用，不重复下载。
- 不猜公司身份或期次；无法唯一确定时自动返回 not_requested/ambiguous，不发错误请求。
- 使用原工具/API 暴露的能力与凭证，尊重其直接技术拒绝、速率和费用上限；这不需要额外的人工作业授权或逐来源 reviewer。
- 原始 transcript 保留一次，不翻译；TXT/摘要作为可重建派生，摘要引用和定位由自动校验器检查。
- fake-provider E2E 覆盖成功、复用、歧义、身份漂移、坏 payload/超限、财报成功而 transcript 失败及测试根恢复。真实 provider 不可用时报告清楚，不阻塞其余本地流程。

历史设计过程见 progress.md 与 findings.md；本页仅用于防止旧门槛被误读为当前指令。
