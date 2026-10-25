# C1 CI 两项失败的独立跟进审查

2026-10-25。结论：**测试夹具迁移审查通过，0 OPEN**；不代签随后远端 CI 或 C2。

## 根因和范围

`87d39bbc5b3bacf59dfc6c3ead11665b7007e83e` 的 CI `40229110372` 两项 unit 失败。公开 annotations 指向 document_work_policy 两测试，ROOT 已本地原样复现 KeyError budget。当前 `_select_pdf` 正确把读取/选材下移到 PdfReading，不再调用旧 handler 私有 `_parse_pdf/_run_selector` 观测点，因此旧 ObservedHandler 没有记录 budget。这个证据支持测试观测点落后于职责迁移；不应仅凭 KeyError 宣称产品预算失效，也不应删除两测试。

本次变更只在 `tests/unit/du11_production/test_document_work_policy.py`。对比 HEAD 的 AST，两个完整 test 函数及 manifest helper 完全相同；没有弱化预算、partial/cache、费用独立性或原件 SHA 断言。所有已独审产品源码 LF SHA 保持不变。

## 新观测器是否真正执行

- ObservedReading 继承实际 PdfReading，read 原样调用 super().read；没有 mock native parser，原三页 PDF 继续实际经过 native 读取/规划/单位校验。
- 记录预算对象与 after_parse 发生在整个阅读 owner read 返回后；因此包含真实读取和边界新增校验的计数，而不是拿预估计数冒充。
- ObservedSelector 只包一层入口断言，实际调用原 bound builtin 0.9 selector，并原样返回 selected；不是自制 package 或空 selector。
- selector 入口必须接收同一 WorkBudget 实例，并与 after_parse 的 used 相等；后续测试继续检查真正的 exhaustion/诊断 used 与 limit、非 complete 依赖与不可复用、增加 work_limit 导致缓存失效、外部 token/费用变化不能污染 source cache。
- 临时 config 仍由 monkeypatch env 指向 tmp_path；socket connect 继续阻断；原件 SHA 检查保留。

这是一处观察器随责任层迁移，不是让实现去迎合旧私有 hook，质量断言和实际执行能力均保留。

## 独立验证与临时目录

第一次独立跑相同两例时，项目长路径策略将 basetemp 重定位到沙箱 Temp；在 fixture setup 创建 numbered directory 阶段出现 2 个 OSError，测试尚未执行，不能记为产品/断言失败或绿。外层自有 scratch 已移除；pytest 当时报告 relocated cleanup removed=false。随后只检查该精确自有重定位路径，已不存在；没有清理通用 Temp 父目录。此失败如实保留在同名 JSON。

改变已证明有问题的路径条件：使用 ROOT 既有受界运行器，把 tmp 基址置于本仓，由它独占建立 48 字 basetemp，不触发重定位。独立执行原两测试：**2 passed / 6.65 秒**，外层 **11.098 秒**，exit=0；临时根恢复 absent，0 付费/下载/重模型。收据 `c1-ci-independent-boundary-receipt.json`，日志同名前缀 `.log`。没有运行全量工程或新增小节点许可。

远端后续精确 HEAD 的 CI 仍由 ROOT 正常提交/推送后核对；本报告只验收这次夹具修复。

## 最终绑定

- `tests/unit/du11_production/test_document_work_policy.py`：6102 bytes，SHA-256 `930d46e53f0dd0bc355395f5d8e454b09b156f14b64bf49cf06fe9c35afb1f94`，LF SHA `930d46e53f0dd0bc355395f5d8e454b09b156f14b64bf49cf06fe9c35afb1f94`。
- 阅读 owner LF SHA：`35c1685105d3196fbc16c6a53300d97eaa77e6e663d883785b7b3b132ff5ad9d`，与此前 C1 最终独审相同。
