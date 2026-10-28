# C3 闭合组中文数量边界观察器修复交接

状态：**IMPLEMENTED_FOCUSED_GREEN_PENDING_ROOT_REVIEW**。作者 `/root/c3_cache_independent_review`；ROOT 负责独立审查及提交发布，本作者不自签独审通过。

## 根因与实现范围

真实连续原片段 `1,245.4 | 百萬元增加7.6%` 已属于同一个生产闭合组，但旧 benchmark `_join` 只允许中文/中文或中文标点边界无分隔，人工插入一个空格后导致冻结 gold 的完整同比句不匹配。原人工报告 `industry-cloud-source-readiness.md` 的 4/4 是物理闭合材料核对，**并非旧 oracle 评分已通过，也不是实际摘要通过**；该历史报告保留，此处补足工具边界与修复证据。

只修改两个仓内文件：

- `tools/document_understanding_benchmark/closed_group_support.py`：仅 `_join` 允许已验证连续边界的 CJK↔ASCII 数字自然连接。
- `tests/unit/test_closed_group_numeric_boundary.py`：新增 27 个中性正反例，不改已有测试或 gold。

`_locations`、`_native_body`、`_edge` 以及 `_fold/_range_fold` 均不变。数字↔数字、小数点/千分逗号边界、英文↔英文继续保留分隔；不删除原片段内部空白。跨页、跨来源、跨角色、表格行、原段序不连续、普通组跨 block、同 block 字符不连续、不同主体所属的不同真实组都不能借此拼接。工具仍只消费生产已验证的闭合组，不新增第二份主体识别规则或来源许可。

## TDD 与复验

- 首次 `red.xml`：8 个预期失败，另有 1 个不合法的表格夹具同时填了 paragraph/table 坐标。只修该测试载体，保留首份日志。
- 有效基线 `red-v2.xml`：**8 failed / 19 passed，1.31 秒**，当时尚未修改工具。
- 修后 `green.xml`：**132 passed，7.37 秒**。包含全部 27 新例、原 closed-group、attributed-context、reading-display、claim-grounding、source-summary-task 与 phase-C observer 消费者短测；未跑重集成。
- `ruff.log`：PASS。
- `final-scope.json`：原工具 AST 除 `_join` 外与 HEAD 完全相同。

## 冻结真实缓存复评

可复核脚本 `rescore.py` 与 `cached-gold-rescore.json` 使用原 `hk-v2-source-check/diagnosis.json.gz`、冻结 `hk-development-gold.json`，通过 `EvidenceSpan.from_dict` 恢复同一来源材料，执行真实 `compile_scoped_model_view(max_claims=20)`。为了与另一作者正在升级的 observer 隔离，固定使用 HEAD `0c988e8d70e22a436126e6ae31ad4fa8172a4222` 的完整 `gold_observation`，前后仅测试级切换旧/新 `_join`，最后恢复当前函数；没有替换来源证明、编译器或断言。

- `hk-industry-cloud-closure`：**false → true**。
- `hk-rd-period-scope`、`hk-outlook-not-actual`：仍 false；旧缓存没有本次另线语义修复后的材料，未改 gold 或借用其他运行补齐。
- 原诊断 SHA `2670e6fa24291059ccccbf1b98ce109c2f4135c070bdba0d13edc7a45e93e351`、gold SHA `2d6391a1f3f6d0c6e9bc7629e327f54c5bb4d2c651b202d38dd4f4364dbba568` 均保持不变。
- 本收据是缓存编译/观察，**不声称已真实发送模型、正式摘要或新 observer 的 sent-task 范围通过**；新 observer 属另一独立 owner，由 ROOT 汇总验收。

另一个 owner 冻结 observer 后，追加 `combined-observer-rescore.json`：实际调用该最终 observer（LF `8f2c44ef2b63b5a434c3789111388edb8a3e3f3065a5b3ce17fbe7243ca46930`）与本工具最终 SHA。结果行业云在 `full_selection` 和编译请求的 `sent_tasks` 均 supported，实际支持任务 `t35`；其他两项仍缺，`summary_claim_coverage=not_evaluated`。这是组合后的缓存任务材料验证，尚无真实发送/摘要结果，不能据此跳过剩余大节点。

## 最终冻结与清理

| 文件 | 最终 LF SHA-256 |
|---|---|
| closed_group_support.py | `06698b1eacf9c384581f0f960e31d754d7701333b9a24c8fc9c848a41c206403` |
| test_closed_group_numeric_boundary.py | `179cf4a9efa7d84272aa5e00b3fbad301afcee6e2a3248bfcebe5e722583dc30` |

工具最终 raw SHA 为 `c6b3197218424fc64be20ade7cef6576cfdad7eef0e8be89388abde1e0e16940`。测试/缓存复评后仅追加两行边界解释注释；复评运行时 raw SHA `ff9e2d01b527ebc5119a094741414ab008ec58f92223ad08da8febae0d8a7b50` 与最终可执行 AST 一致，差异在 `handoff.json` 留证，不把注释前 SHA 冒充最终文件。

`cleanup.json`：独有 `C:/Temp/c3numeric-boundary-20261027` 已核验绝对路径并清理，无所属 Python 遗留；模型/下载/PDF 解析均 0。没有改生产源码、真实原件、冻结 gold 或其他作者文件，没有 commit/push。下一步 ROOT 独审本窄修；语义 v2 另做最终独审，本轮不启动新的正式摘要。
