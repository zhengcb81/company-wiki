# QA 几何发现及物理容器分层独审：PASS

独审绑定的四个文件 raw/LF SHA 在 review.json，最终短测与探针前后相同。此 PASS 仅覆盖本节点工程，不代签整个 C、真实摘要或 RF 采用。

- 单列 Q/A 的首行缩进使用当前实测 bbox 高度和 80% 重叠共同约束；12-point 高度时 24/24.1/24.24 允许，24.25/36/80 不允许。此处仅发现候选，不产生角色或经营资格；零额度保持 partial/no candidate。没有公司、页码或文案定制分支。
- 已由结构 owner 识别的 qa_exchange 不再被 PDF table_index 混成经营数据表。下一阶段仍按答案自己的 source-use 判定；中性财务、套话、未知回答不能借问题的业务词入选。英语否认控制保留实际回答 support，问题仅作 context；原 locator 不改。
- 独审发现并由 ROOT 修复 P2：结构显式 partial 的自足孤立答案原来在 PDF/JSON 都变 selected+coverage true。修后保留答案可读与支持能力，同时沿既有 deferred/coverage 通道呈现 QA_CONTEXT_PARTIAL、status partial、coverage false。不新增拒绝原文或人工许可门；无锚问题保持原 ANSWER_MISSING，旧缺字段输入不猜 partial。
- 最终两个受影响测试文件独立 **25 passed / 4.59 秒**，diff check 通过。另有 6 个几何边界、零工作量、3 个跨语言正反 QA、2 个格式的孤立答案探针（有重叠，不与 pytest 计数累加）。宿主测试目录已 removed=true，自有 requested tmp 不存在。
- 仅检查保存的 v4 selection：10 spans、partial、coverage false，问题 ID 不在 support 中。没有重新解析 PDF、运行 SDK、下载或调用模型。关键 VC 否认等源归属闭环仍由 ROOT 后续处理，不能把 spans 增加当金标/正式摘要已通过。

OPEN（本四文件工程范围）=0。原件、配置、W21 保留文件及作者工区未读写；reviewer 未改产品或测试，只写自有检查收据。ROOT 继续最终受影响域测试、正常提交推送和精确 CI 观察。
