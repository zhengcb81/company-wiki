# DU11 business coverage 独立接收审查

## 结论

**PASS：工程增量可集成；真实 C 仍 OPEN。** 受审的是有界选材策略，不是事实成立或预测正确性的认证器。

## 冻结版本

- `src/company_wiki/source_catalog/narrative_business_policy.py`：`20cb13f7e4259d53e6f418da457efc1b28ae8e78b4fcacd2bcc38f2948e12a0c`
- `tests/unit/du11_production/test_business_coverage_relations.py`：`65925870e6cb25d2eb7324058a66672fba13e1b433847b146b9c980586019a15`
- `tests/unit/document_understanding_selection/test_reading_portfolio_disclosure.py`：`65ff44850f0aa9946daba88015ffe0c9bd5a62aaa57e125d91d8a86a12b15e01`

## 根因与修复

源解析已保留真实连续 carrier；缺口在阅读策略未识别“具体产品/工艺/市场范围＋覆盖谓词＋比例/数量”的关系。修复位于原有 reading business policy，新增 `business_coverage_relation`，保留计划、条件、第三方、否定等原文，不升级为已实现的经营状态。legacy detector 不变。

独审发现的金融混入已闭合：设备贷款/应收/资产余额不能借 equipment、software 成为业务覆盖；收入、销售、利润等普通结果词族的英文单复数及中繁体按局部比例分母排除。判别仍在原有局部关系边界内，因此后接/前置独立金融句不抹除有效覆盖，“sales services 覆盖17个地区”也保留。没有公司、百分比或金标特判。

## 检查与证据

- 实读最终实现、完整新增正反控和版本测试 diff，核对三文件 SHA 与冻结一致。
- 独立 inline Python `-B`，显式 WT/src 优先并核模块路径：14 个有限关系反控＋1 个 legacy 不变反控，**15/15 通过，exit 0**。收据 `business-coverage-final-independent-controls.json`。
- 复用作者最终金融词族的 45 focused PASS/3.34s、先前190项相关回归；没有重复全套、真实 PDF 或模型。
- 旧真实 CN 10/10 仍绑定原 `c0f447...`，没有冒称最终 `20cb13f7...` 实跑过；最终仅金融边界增量保留实际 carrier 的纯函数可选性。

## 架构与兼容

沿用单一阅读策略及现有 clause owner；上下文100/120字符有界，没有新身份库、门禁、缓存、任务库或 PDF 遍历。`reading-business-policy/8` 是语义升级；已有 inventory 读取真实版本用于缓存因果失效。版本测试把硬编码 /7 改为当前模块常量，同时保留 monkeypatch test-next 断言，合理且没有放宽生产行为。原文字节、定位和 source 所属身份层未改变。

## 未决边界

本范围无已确认未修缺陷。工程 PASS 不等于整篇无遗漏、正式摘要事实正确或真实恢复通过；ROOT 必须以最终集成版本完成既定 C 和真实内容检查。没有新增权限或逐小节点签收要求。
