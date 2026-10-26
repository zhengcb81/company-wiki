# Legacy physical deployment 修复交接

已按 ROOT 授权只改 `tests/integration/test_reading_parent_cache_migration.py`，**原单例1P /31.69s**，无重跑广包。最终LF SHA `ab9444118640140443a0e92d2825f135e3239a9d55e1c19b26b10f3b57ba840f`，raw SHA `ca8159ae4f35496db9e89842a4fac19f648dcb1ed46a3ce9d117cd6384d80035`。所有原25个Assert AST与HEAD一致，Ruff PASS。

测试仅在 owned root 部署13份真实源码（当前文件合计<199KB），包括真实package init、decision_inventory和structure包；只把物理sections.py替换成历史字节，按正常package spec的deployed/current搜索路径加载，其他模块回落当前。旧代码与库存owner对应同一物理目录；现代阶段保持原canonical launcher。未改生产hash或伪造cache版本。

实际绿色收据 green-public-cache-result-0.json：2个本地fixture POST，old/new business_algorithms 7f85b2…→d35e6a…，material 7c1565…→34741b…，新/旧cross-run cache均0token，旧精确Ref/bundle不变。实际old producer为owned legacy-deployment/…/sections.py，new producer为canonical src/…/sections.py。全部原上下文父子/不同材料/新缓存/旧ref断言通过。

原RED observed-run.json/log/xml保留，反例报告 report.md/json解释exec+伪__file__未代表真实部署。对比RED与GREEN期间另一owner修改了narrative_generation（caf25…→64e9…），各次运行内部源码SHA均稳定；本作者未改/不代签该产品修复。

清理已完成：.c3legir和.c3leggreen均不存在，RED owned PID15556、GREEN owned PID16340当前均不可见；Windows Job先绑定后放行，并在终态关闭全部owned树。只读hash负控overlay同样已删。

本交接为实现者结果，独立验收由c3_cache_independent_review另做；其独立identity-only process probe已验证真实code filename/sourcefile/hash对齐，不冒称来自本作者GREEN的额外runtime hash观察。未commit/push或触及hook mode WIP/配置/原件/其他工区。
