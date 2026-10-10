# 独立跨卡审查

2026-10-10 p7_leaf_card_discovery 独立只读复核结论：三卡源码写集彼此及MAIN AUTO不交叉、物理目录不同，保持旧projection默认1.0.1/new1.0.2 opt-in，RF诊断可选，audit采用既有上游接口，无须互等。现有capture支持freeze-input/freeze-arg-index与env继承，离线fake-child可成立。

初次复核发现准备中的schema/example与本卡PWF尚未配齐，MAIN已补齐并逐SHA核对；RF M3已补准确现成测试函数参考；audit旧兼容测试可写名单与机器manifest已统一。

随后集中实查54项通过（verification.json/log），包含三目录branch/HEAD/base祖先/clean、源码无变更、中央与副本同SHA、PowerShell7实际PWF解析、写集隔离/无接口依赖和格式正负控，owned TEMP已恢复。旧PowerShell5.1缺.NET方法的实际失败及修订保留startup_fix.json。

这是施工包准备审查，不是产品源码RED/GREEN、真实供应商结果或公司研究质量验收。三个harness尚未启动源码实现。
