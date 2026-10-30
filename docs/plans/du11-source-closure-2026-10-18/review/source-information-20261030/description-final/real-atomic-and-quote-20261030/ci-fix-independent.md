# CI根因修复独立复验与窄push回归节点

结论：**INDEPENDENT_PASS_EXACT_NEW_CI_PENDING，范围内0 OPEN**。原CI41056460382/bf58769b仍失败留档；新提交远端结果尚不能宣称成功。

按ROOT指派，源码registry owner和新protocol identity单测只读复验，未改这两个路径或旧四参数失败测试。三个lookup先处理非字符串JSON形状，prompt/bundle format按ValueError拒绝，None/known维持原语义；公共runtime对[]/{}继续给ModelResponseError(PROJECTION)，没有改成有效默认协议。新7项与原4参数先独立11P/3.73秒。

评估将这类错误纳入现有短smoke合理，因此仅修改pre_push_gate.py及直接测试。沿CURRENT_CI_REGRESSION_CASES既有模式加**一个node：test_protocol_lookup_does_not_hash_non_string_json**，包含6个坏JSON参数；known/absent语义第7项此次独审运行，不把整模块加到每次push。固定target34→35，同一pytest进程、180秒不变，不增加新的门禁/人审/全量检查。库存约束先1RED，补节点后通过。

最终固定短域 **21P / 0F / 5.64秒**：直接gate与one-dispatch调度测试＋新7项＋旧4参数。此前11P不相加。ruff四路径、diff-check通过。原来合法协议/旧wire语义由ROOT其他受影响域证据覆盖，本节点不代签全仓。

四路径raw/LF SHA见final-seal.json；旧失败测试只读SHA也记录在final-review.json。读过AGENTS/配置，未改生产配置、reader、原件、权限或三个已封工具路径；0模型/下载。ROOT正常提交推送后再看新head精确CI，不能把原失败改绿。
