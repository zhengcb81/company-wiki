# CI 上下文缓存边界独审：PASS

本次只审 CI40974928800 暴露的工作预算/私有证明缓存，不代签整体 A/B、真实摘要或 RF 验收。审核绑定的两文件实际 raw/LF SHA 见 review.json。

- 原 CI 零额度反例的根因已关闭：先付 target 工作，再按索引逐项付费验证 context；不在额度检查前完整复制源容器。
- 独审发现并关闭额外 P2：tuple hash 不缓存，仅复用 tuple 仍会在每个 set.add 重新遍历全部上下文。当前只在首个 bound 对象事件登记一次，复制/字典 hash/集合 hash 都有收费。
- 新增两条获 ROOT 授权的长期中性回归：100 个上下文的 1/20 个事件 hash 工作量相同；target 已准备但只剩 2 work 时，10000 个上下文只读两个索引即 partial，不触碰尾部。没有按机器耗时设阈值。
- 本文件独立测试 28 passed / 3.61 秒。另做 6 个额度的真实 owner 探针，partial 时已确定的 2/17 条关系分别保留 2/17 个对齐 proof，complete_assertion 仍 False。无截断洗成 absence/complete。
- 顺序身份、缺失 context 的原诊断、公开 wire 和 source locator 处理未变；真实文档/模型/SDK没有运行。恢复测试目录已由宿主给出 removed=true，自有 requested tmp 不存在。

OPEN=0。独审只新增两条测试函数；没有改产品实现、原件、配置、W21 作者工区或外来 hook mode。ROOT 应继续相关域短测、正常提交推送和精确 CI 观察，旧 e920b09d 失败不能改成成功。
