# 0.8 兼容边界只读意见

当前三例失败已由 ROOT 独立复现；本审查额外执行 7 个短 owner 输入并保存在 observations-initial.json，没有修改产品或作者测试。

建议在共享 reading detector 的描述证明投影分支做显式版本隔离：0.8 只让该分支消费独立 True 且 material 的 prepared 描述 proof，不能把新 descriptive_only 或 unknown 直接补成 operating_mechanism；0.9 继续保留静态构成／定义的来源价值。可用结构化 family/mode 接口，不需要旧文本词表或 reason 字符串白名单。

不要把 raw SourceAssertionRoles.material gate 施于整个 reading 或整个 _operating_fact。实测 paid seats 数量变化与 usage-based billing 的 raw role payload 都是 None/materialFalse，但它们已有 _reading_relations 的具体数量／计费证明，完整 prepared assessment 是 payload=True/material。统一压掉会丢失原 0.8 真实披露。old detect_business_fact、既有 milestone/planned/quantity/resource 等独立贡献保持原样。

三例旧静态输入以及具体未知产品构成均 raw payload=True/descriptive_only=True/materialFalse；它们通过新描述 operating_mechanism 分支溢入 0.8。修新捐赠分支即可关闭该因果链，不必重建选择器或把所有 static 文本全局拒绝。

“多类产品和配套解决方案”在 0.9 的独立 True 另属共享 abstract modifier grammar 漏项；通用修饰词处理合理，不能做整句特判。具体未知成员清单和真实软件功能仍要保留。

原 6 文件独审 PASS 是当时工程范围历史，不撤改；它不能代签后来暴露的 0.8 兼容 CI。后续仅对稳定修复字节执行短聚焦复审，单独记录 SHA 和验证范围，不宣称旧精确 CI 已恢复。
