# R7 核心 CI 测试迁移独立增量审查

结论：**PASS_ENGINEERING_SELECTED_SCOPE**。这次 5 个测试文件迁移没有发现 P1/P2，没有用放宽来源、绑定或 unknown 规则来掩盖产品退化；可作为本次 CI 修复的独立工程审查依据。

审查基线 `bd911a2bd1125fe46d7c5a0f605fe3b0104f17be`。作者报告 JSON SHA：`668d2c36f758d32de59e3bc2ad442f6a723ee20c351d0919ab104e69a121e442`。5 个测试和 25 个已发布 core 源码，执行前后及清理后逐 SHA 一致；本审查没有修改源码或旧测试。详细 SHA、探针源码和原始日志/XML 完整保存在同名 JSON。

## 旧、新期待与责任边界

| 范围 | 原来的失效期待 | 本次保留的正确约束 | 独立判断 |
|---|---|---|---|
| 默认 draft | 默认必须 ≤56KiB、强制出现 deferred | 无显式容量时完整保留全部可用卡；显式 56KiB 仍按 UTF-8 实际字节整卡分配、保留晚出现的重要卡和全部任务行 | 取消任意默认表示许可；没有取消显式预算 |
| 收据 | 399 行合法收据仅因 >32KiB 被拒 | 原样保留全部行和 False；绑定、类型、任务与 claim 仍受校验 | 大小不是许可；无 selected 的 wrapper 测试不冒充来源绑定验收 |
| rank | 用已取消的隐式额度制造未发送任务 | 改用真正 unresolved 范围；不能对未发送任务排序、不能把已发送子集完成称为全文完成 | 实质负控仍在，不再依赖过期默认额度 |
| post-model | 合法 70,006 字符 ID 触发 RESULT_SIZE | handler 成功后完整 ID、规范化 draft、真实 native usage 和响应 SHA 保留 | 仅退役体积失败；13 类 JSON/语言/身份/引用/闭合/路径失败原样保留 |
| 原文字节 | 上层再次对手造 VerifiedContent 计算 SHA | 上层绑定返回身份/长度；当前 reader 单独负责真正原文 SHA，历史 policy 指纹仅作 lineage | 不把重复 hash 重新变成许可；新 adapter 仍必须遵守 verified reader 合同 |

## 实际执行

仅选 10 例：4 个新独立探针和 6 个必要现有用例。首跑 **9P / 1 审查夹具错误，4.73s**；失败是把 immutable `result.result` 直接传严格 JSON encoder，真实 handler 和 typed selected-bound parse 当时已成功。修为公开 `result.to_dict()['result']`，所有断言保留，仅该例再跑 **1P / 2.98s**。未伪称一次完整 10P，未重跑 113、Unit、167 或全文件。

独立控制包括：

- 带中文、emoji、引号和换行的原文，默认完整保留；显式实际 UTF-8 整卡容量精确满足，没有截断原文。
- `admitted_emission_complete=True` 只表示选中任务的发出；`source_processing_complete=False`、selection partial 和 semantic/subfact not_evaluated 保持，不伪造全文理解。
- 真实公开 handler 处理 176 任务，其中 175 可发、1 unresolved，完整 execution >32KiB，绑定解析成功；修改 task SHA 或将 bool 改成 0 仍拒绝。
- 真实 SourceVersionReader 在成功打开后遇到**等长度的一字节损坏**，仍拒绝 `no_verified_location`，不是只测长度。
- 已迁移默认/显式容量、大收据、未发送 rank、真实大结果 usage/SHA 以及 selected plan SHA 反控通过。

保留作者原 7RED、113 中 112P/1 新夹具错误以及其后 5P 恢复的历史；没有重写历史失败。本人刚修改的 W08 report 测试由其他审查人验收，本报告不自审该文件。

## 清理和限制

专属 `tmp/r7i-b842d1` 初始 absent，完成后验证绝对路径、无重解析点，再恢复 absent；全部复现内容先完整嵌入 JSON。0 真实原件、模型、网络或收费调用，生产配置、Git 和主 PWF 未修改。

本结论只签本次 5 测试迁移的工程范围，不代替完整 CI、新真实摘要、缓存恢复或 RF 经济采用验收。当前没有待根修的实质缺陷。
