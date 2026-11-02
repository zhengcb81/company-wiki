# 当前状态 — 解耦复核发现六项遗漏，先收口D4

唯一入口本页/[机器状态](CURRENT_STATUS.json)，交接[HANDOFF](HANDOFF.md)，主计划[task_plan](task_plan.md)。

**不能再称全面解耦已完成。** 2026-11-02全面复核确认1项P1、5项P2：[报告与实施顺序](review/decoupling-recheck-20261102/README.md)。原D3已发布的接口/测试成果继续有效，但选定组件通过没有覆盖所有业务入口。本轮完成核查和计划校正，产品修复尚未实施。

## 已完成且继续有效

- RF原文/准备端口、StockWiki可选raw/narrative reader可替换；FF六操作统一连接；ET获取和CWP原件存储边界正确。
- D3实际39项组合、安装入口和真实原件只读通过；正常推送及CI版本见[历史发布记录](review/decoupling-20261102/release.md)。不据此宣称全部仓库/业务路径独立。
- 原件SHA、身份/期次/as-of和实际资源约束保留；旧JSON排版阻断和重复原文预算帽已修。

## 当前未完：D4集中补齐

1. StockWiki正常公司流程仍扫描/解析物理doc_root，新reader未成为默认业务来源。
2. RF实际采用摘要的consume和两工具未继承可替换端点。
3. CWP纯解析/共享引擎经DTO及包初始化反向加载catalog运行时。
4. CWP电话会import公共wire仍由内部dataclass字段反射决定。
5. FF固定stderr大小仍能把已有合法成功结果翻成upstream_error。
6. AUDIT两项真实CWP测试未归ROOT组合；本次2P证明当前功能可用，不代表覆盖已归位。

## 唯一下一步

ROOT按[D4](review/decoupling-recheck-20261102/README.md)先冻结上述真实入口的失败测试，再按责任层修复并集中组合/独审。**RF/AUDIT业务模块改回DEFERRED_UNTIL_D4_CLOSURE，尚未派发。** 这是修正解耦完成度，不是新增人工许可。D4关闭后恢复T4父链、SEM-QUAL-01、新版真实摘要、缓存恢复、RF实际采用与既有公司循环。

三表输出容量、local_prepare扩展兼容、Sina provider泛化和组合CI触发范围另列能力限制，不冒真实生产故障，也不扩成额外阻塞。原件/生产配置/DB/封存与已有WIP保留；Dayu/IQS/Dashboard不动。只在大节点独审，不重复超时全量测试。
