# 项目标题遮蔽正文：独立 TDD RED

## 本次直接证据

公共入口 `select_reading_evidence` 在真实 `_understand` → structure.projects → `_prose_reading_packages` → `_candidates` → finalize/context 链路运行。只输入 source-owned neutral IR；没有 monkeypatch、没有注入预制 package。新测试文件 8 FAIL / 1 PASS，1.84 秒。断言同时检查原始 source ID、text、coordinates 和完整 metadata 不变、实际 work 不超 16M、span 不超请求 96 和 48k。模块路径在 pytest 内验证。

三个标题分别为“项目基本情况”“物流中心建设项目”“设备生产线扩建项目”，正文是设备交付和制造基地产能的两条独立完整陈述，末尾是无关办公流程未来句。前两个标题导致零正文事实；第三个标题可被识别为有意义，但完整正文仅变成标题上下文。3 个来源 span 足以容纳两条事实和一个实际共享标题，当前却无法选；2 个来源 span 下也没有单个独立完整事实。字符预算反控通过。直接使用当前公共输出，不借用旧 trace 的排序、offer 或 deferred 理由。

## 根因责任层及建议

1. structure.projects 记录整个项目“容器”与其首标题 anchor 是正确的格式输出；它没有证明所有 prose 都是一条事实。阅读层不能把 `project.member_unit_ids` 一律当成不可分割证据，也不能只用标题判断正文是否可以进入。
2. `_prose_reading_packages` 已经用项目 package ID 写入 continuity 的 section_key，能够阻止跨独立项目拼接；但随后全量跳过项目 native windows，并原样返回首 anchor 与所有成员。这正是正文失去 SourceOperatingSession 审查入口之处。应由现有物理 continuity + statement/source-session owner 对每个真实 prose member 建立实际事实或闭合 native statement；泛标题只做实际 section context。
3. 不可简单把所有 project 都改为 background。表格项目原有 row/项目名称/单位/期间/脚注和明确限定必须保留原结构语义。只对实际独立 prose 做逐事实处理；显式负向/认证/将来前提仍是有证据的局部依赖。共享标题可复用，但不构造另一份 schema、任务库或 WorkBudget。
4. 含有实质经营事实的标题也可独立成为支持，前提仍由现有同一业务语义层判断；不得靠标题中特定词把其所有正文强塞成上下文。无关未来办公流程不应仅凭成员资格成为任何经营事实的 required context。
5. 既有原 ID 和 locator、native 8 units / 4 blocks / 2048 chars、同一 16M WorkBudget 及 96/48k 均保持。新测试的紧限额校验验证真正闭包成本，不要求预留公司/数字/oracle 席位。

## 审查边界

这是公开入口产品 RED，不是实现完成或全年度内容通过。ROOT 实现后仍需复跑这些冻结断言，并独立增加表格项目/同页相邻项目/真实限定的反控；大节点再跑原始 cache migration 和真实年报选材。第一次测试的 mappingproxy 快照错误单独保存 fixture-error.txt/xml，未算产品 RED。未读取任何真实原件，没有模型/网络/API/下载，没有修改生产或 Git。测试临时目录实际被 conftest 重定位后删除，cleanup.json 再次确认不存在。
