# CI工作边界根修（2026-10-29）

当前：原失败及新增四个中性反例RED已重现，根修后234P/9.52秒；396源文件mypy、ruff通过。独审PASS/OPEN=0，独立28P/3.61秒及6档partial probe；见ci-boundary-independent-review.md/json。源码尚待本次正常发布，远端旧failure仍保留。

- 原CI：e920b09d / run40974928800 / job123800497362；Unit tests唯一注解失败 `tests/unit/du4_operating_states/test_root_boundaries.py::test_exhausted_budget_does_not_copy_the_context_tail`。未改变注解或旧历史结果。
- 根因：新私有证明缓存在预算检查前完整复制context；每个bound relation还重复复制。真实代码缺陷，不是平台问题，不删除或放松测试。
- 本地覆盖漏项：原A/B大节点的4目录/1文件不含真正被修改的DU4 owner测试。pre-commit职责是静态检查；pre-push遇wide scope按既有策略只跑fast，不承诺完整unit。无需给每个commit加全量。此次将DU4 owner全目录纳入对应大节点短域。
- 修复：先读取已收费的target，逐索引收费验证context，保留请求原序列；对已验证成员构造/计费一次私有key，事件循环复用。公开wire/来源/单一母预算不变。
- 验证：保留原失败单测，新增零/小预算不访问context、多个事件只验证一次且顺序敏感的测试；跑DU4 owner与来源信息/production适配器相关短域，396源文件mypy；独立agent审查实际SHA再发布。
- W21 author runtime三文件不改；不同时运行SDK，0新供应商POST/下载。原件及外来WIP保持。

独审补漏也已修复：Python tuple hash不缓存，首次complete登记计费并只做一次；1/20条关系、100contexts同2200次ID hash。缓存target后只剩2work只读取2个context，partial不伪完成，关系与proof仍逐项对齐。不新增gate、不修改pre-push策略。

已正常提交推送 `ad34ce6e594ffc50a6936f566264617abb284b6e`；pre-commit全通过，pre-push158P/65.85秒。新精确[CI40977151896](https://github.com/zhengcb81/company-wiki/actions/runs/40977151896)已启动，当前in_progress；旧40974928800继续failure，不重复改历史。

最新已核：40977151896 completed/success，绑定上述完整ad34ce6e SHA。CI根修闭合，继续C，不重新运行旧失败或扩充每次commit门禁。
