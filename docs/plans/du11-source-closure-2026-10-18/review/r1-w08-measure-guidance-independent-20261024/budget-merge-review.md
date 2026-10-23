# W08 预算合入独立审查

结论：**PASS_BUDGET_MERGE_ONLY**。本次指定边界内没有确定的阻断问题。

作者工区：`C:\Users\郑曾波\Projects\company-wiki-r1-local-observation`。实际 `HEAD=1712ed10ea1e32b3177ce435e2d8b852270fd6ca`，`MERGE_HEAD=ab95027b5b1452c4403db482362b59a9f8976286`；正常 merge 尚未提交，未见 unmerged paths。结论绑定本报告 JSON 所列工作文件字节身份。

- 当前母额度为 10,000,000 token / 20,000,000 micro-USD（20 美元）；公司目标 150,000 token / 1 美元，仍为 soft。既有 totals 测试验证历史 charge、重复 unknown hold 去重和既有 retained hold 保留，当前额度从 policy 读取。
- `narrative_select.py:460` 创建一次文档工量账户并向 parse/select 传递同一实例；本次真实合成 PDF 测试检查同一对象与 parse 后已花余额，scoped 账户测试确认不会重置母账。
- 工量不足时，`narrative_reading.py:1115` 将包标为 partial/needs_review、coverage 不完整，并保留 `document_work` 诊断；`1183` 冻结不完整依赖。span/character 的容量诊断独立，均标明 `external_model_cost=false`。
- inventory 保持 **1.9.0**；HEAD 原有 **20** 个 business owner 全部保留，新增 `narrative_revenue_guidance` 为第 21 个。实际模块字节进入 `business_algorithms`；旧 owner、product_reference 与新 guidance 字节变化会使缓存失效，恢复字节后新 guidance 缓存重新可用。
- 生效 `document_work_limit` 进入身份；现有真实 PDF 测试确认 16M→32M 使旧 complete 缓存失效，工量不变而 token/费用归零仍保留来源解释缓存身份。费用配置不替代来源语义。
- `resource_budget.py`、`resource_budget.yaml`、`narrative_finalize.py` 与 MERGE_HEAD 按 LF 规范化字节相同。`narrative_reading.py` 的 W08 来源处理扩展保留全部预算诊断、partial/cache 和工量身份路径；inventory 扩充 W08 owner closure，并保留预算合入。

验证：**84 passed，0 failed / 0 error / 0 skipped**；控制台耗时 4.14 秒。使用母工区 `.venv`、指定 W08 `src;tests` PYTHONPATH、`PYTHONDONTWRITEBYTECODE=1`，7 个实际导入模块的 `__file__` 均断言来自 W08。选定用例和逐组数量、原始模块路径、测试文件 SHA 见 JSON。唯一警告为关闭插件自动加载后既有 `asyncio_mode` 配置项未知。

本次没有全套测试、真实年报或 guidance/measure 语法签收；没有网络、LLM、下载或 key 操作。没有修改作者产品/测试/Git/index。仅为预算合入的范围结论。

| 文件 | 实际 SHA-256 |
|---|---|
| `src/company_wiki/resource_budget.py` | `8c55fc4e6a0ad7faf0fbdcef1de06d4e709cdf2935db57c24c4e100092dd76a1` |
| `config/resource_budget.yaml` | `148f22816bf0b8935bbb2c1618f3199d46ff52f41377e3e582c26a96ea7be3b5` |
| `src/company_wiki/source_catalog/narrative_reading.py` | `9eac52bdadb103855cb5cb808a2ba9b4e48d60441168faef294a1c04fa2b11fc` |
| `src/company_wiki/source_catalog/narrative_finalize.py` | `1da9c69714ca7e63649a177c8276ddde9630b6cdcc6cd5995a2d2ae593ce22ed` |
| `src/company_wiki/document_understanding/decision_inventory.py` | `e1c81224e45246899ab7df3b372b90d56f9021cf43549007b803807911a16a52` |
| `src/company_wiki/source_catalog/narrative_revenue_guidance.py` | `9d65dc1f7294b6d12f916a258d122766ac4a8e1e558fc9e5c6c70c3c3d027d80` |

清理：独占临时目录 `.planning/w08-budget-merge-independent-20261024` 已删除，已验证不存在；pytest 自己迁移的 run 目录也在该目录内并已报告删除。最终仅保留本 MD 与同名 JSON。

