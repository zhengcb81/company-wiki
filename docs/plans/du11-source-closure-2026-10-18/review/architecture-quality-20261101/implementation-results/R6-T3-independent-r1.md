# T3 关键节点独立审查

结论：**NEEDS_ROOT_FIX_T3_SCOPE_LIMIT_SUFFIX**。独立新样例 **7 项：1 failed /6 passed，1.73 秒**。存在一个需 ROOT 同 owner 修复的 P2，当前不能签 T3 工程发布。原 82P 是同 SHA 下的真实合组结果，保持历史；没有重跑 82/整仓/原件/模型。

审查绑定正常提交 **`8782050bcee8a5d41f571306eef6fd166d0ff5ad`**，工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6`，分支 `codex/architecture-t3-source-scope-20261102`。20 份冻结文件的实际 raw SHA 与 manifest 全匹配，Git LF blob 全匹配；原 6 份 tests-first 还与原 `tmp/architecture-r2` 的冻结字节相同。精确 manifest SHA、每文件 SHA、完整复现和观测保存在同名 JSON。

## P2 — 成员上限仅阻断第一个超限成员，未观测尾部重新进入材料

位置：`document_understanding/structure/source_scopes.py` 的 `build_source_marked_scopes`，`cursor - index >= bound` 分支。

最小样例在真实合成 native 同一 block 内构造一个 `備註三十一：…` 引介和 27 个连续编号完整句，之后放真正的新标题和独立健康正文。每个原始 unit、block SHA、character range 都由既有 fixture/producer 构造，没有伪造 membership dict、heading hint 或替换 validation。原始来源快照仍保持。

实际结果：

| 成员 | context_blocked | 实际 material anchor | semantic completeness |
|---|---|---|---|
| b22（边界内） | False | True | unknown |
| b23（第一个超限） | True | False | partial |
| b24、b25、b26（仍在同一备注内） | **False** | **True** | unknown |
| 真正新标题后的 healthy_body | False | True | unknown |

原逻辑只把当前超限 unit 加入 unresolved 后 `break`。同一备注内尚未遇到任何新 source boundary 的剩余单位未进入 `member_ids`，也未进入 `unresolved_scope_unit_ids`。sections 恢复外层 frame；materials 又只消费诊断的 exact IDs，因此后续 b24–b26 丢失必需引介并重新成为可用 anchor。

这里不夸大为已验证“最终模型发布了完整错误结论”：本次只到真实 `prepare_native_materials`，释放单位的 semantic completeness 实际为 unknown。但“限额内没来得及证明的同备注尾部，绕过 exact missing-context 阻断”已经是来源 closure 责任缺口，global coverage=False 不能替代目标级传播。

建议同 owner 保留“尚未观测的备注后缀”，直到原始 marker、真实 heading、source/role 等边界；可利用已预扣的有序流，或向消费者表达明确 deferred range。不能加大 cap、把整个文档拦住，也不能把预算边界当作新的独立来源引介。修复应保留真正新标题后的健康 scope。

独立 RED：`test_note_limit_cannot_release_unexamined_suffix_as_complete_material`；完整脚本及原始 ID、diagnostics、semantic_units、anchors 已嵌入 JSON，可在新 owned tmp 重放，不依赖此次已清理目录。

## 通过及静态审查范围

- 四个新的终结符/闭引号/后续实质文字反控通过，末尾观察不改原文。
- 新的同 actor、重复备注号场景保留正确外层标题和本备注 intro，排除旧备注 intro/tail；不是只删错边。
- 同 block 的真实 character member proof 在无 geometry 时仍有效；`LAYOUT_GEOMETRY_UNAVAILABLE` 和不完整 geometry coverage 保持，没有把本地 scope proof 冒称整个 pipeline 完成。
- 纯 stdlib `text_boundaries` 只观察末尾，adapter/layout/layout_hints 三 producer 委托，原显式 native/HTML heading 和冒号语义仍分清；sections 唯一维护父树，source_scopes 只发原始 IDs/局部 frame。
- member helper 保持 source/page/ordinal/role/turn 和真实 membership/非重叠字符范围约束；geometry 是后备，跨页仍走原物理 coverage/列/页眉证明。没有 actor/company 词库、原文删除补丁或跨层研究逻辑。
- 新观察走原 WorkBudget 和逐 unit/字符收费；未提高全局上限、增许可或第二任务库。问题出在 limit 的未观测范围表达及后续传播，不是要取消预算。

本次未再跑所有旧 proof/预算矩阵或 cache mutation；新模块已有显式正向 imports 进入原 recipe/structure package 闭包，不据此代签真实 cache 恢复。

## 处置与清理

已向 ROOT 和 source 作者发送最小 RED/共因；只读源码，不改产品或旧 oracle，不 commit、不建 CodeGraph 索引、不改主 PWF。唯一自有短目录 `C:/Users/郑曾波/Projects/company-wiki/tmp/t5` 初态 absent。ROOT 明确要求先保全原 7 项 probe 和实际 RED；修复作者已确认读取。完整源码及 SHA、原始观测留在 JSON，随后核准确绝对路径和无任何 reparse，仅清理该 owned 根，最终恢复 absent。原件、配置、生产 DB、外来 hook mode 未动。

ROOT 已确认 P2 并交同 owner 根修。本版结论只绑定实际审查窗口的 `8782050b`/20 个 seal，后续修复不沿用此版本的通过检查。本报告另存 `R6-T3-independent-r1.md/json` 作为失败历史，不回写成新版通过。

本报告完成 **STOP**。待 ROOT 修复并冻结新版本后，定点复验此 scope-limit 后缀和健康 scope 边界；当前不签完整 CI、真实 H1/摘要/cache/RF 或整个目标。
