# R6 来源观察器 R2 增量独审

结论：**NEEDS_ROOT_FIX_CONTEXT_PROOF_ROLE_ERASURE**。首次发布竞态已经修好；本轮发现新增结构投影把语义上下文与纯物理证明的角色抹平，须在同一观察器 owner 修复后再做窄复验。不是来源引擎或原文发生变化，也不新增人工许可。

审查绑定 `R6-source-observer-r2-freeze.json` 的七文件 SHA；测试前后七项完全一致，runner 为 `633b326665e9a37a026da28ce472dfbd2aac085366e8f39f0c24f32b0662fc58`。来源运行时代码仍为 `fa8ef38ee0e6e0cd659ad602df5844cc9571ebb9`。逐项身份、完整探针、双输入输出、JUnit 和控制台嵌入同名 JSON。

## 实际执行

宿主 Python，仅 ROOT 自有 `tmp/v2` 合成夹具与一个真实新子进程“缺失合成配置”控制：**10 例，9P/1F，pytest 4.62 秒**。无真实原文、来源重放、模型、下载或配置写入；没有重跑原 29 例和 H1。

- 原 R1 的首次发布竞态反例原样通过：在 pending fsync 时由另一 writer 生成目标，原子 link 拒绝覆盖，foreign 字节保留。
- 已有 owned checkpoint 在 fsync 窗口被更换时也拒绝覆盖，pending 清理正常。
- 缺失父节点、循环、重复 section ID、深度上限四项明确保留不完整状态，没有 actor 自动通过。
- 未 selected target 仍能保留完整原始父标题与限定全文；输入结构不被修改。
- 必需结构信息超上限时仍为 `OBSERVATION_INCOMPLETE`，保留来源状态、真实 False integrity 标志及明确缺失字段。
- 新进程使用当前 ROOT canonical 三工具身份，仅因缺失合成配置退出，没有读取真实来源。

## P2：语义依赖和物理证明在观察结果中不可区分

位置：`tools/source_case_runner.py:165` 和 `:203`，`structure_context_checkpoints`。

`NativeSourceDependencies` 的既有合同（`structure/contract.py:33`）明确区分：`required_context_by_unit_id` 的 introduction/meaning 进入语义引用；只作 list-edge endpoint/furniture 的 `required_source_unit_ids_by_unit_id` 是物理证明，不属于模型材料，也不能替代真实限定依赖。

当前投影把这两个 map 放入同一 set，再生成 `declared_context_unit_ids`，并对同一个 union 计算 `forbidden_context_ids_observed`。独立反例只改变 target→previous 这条引用的角色：一份为 meaning dependency，另一份仅为 physical proof，所有 section 和原始 ID 相同。**两份观察输出完全一致，且都将 previous 列为 forbidden context**。

因此真正的前文主体误继承与合法的物理邻接端点，在交接材料中无法区分。`REQUIRES_SEMANTIC_REVIEW` 保留是正确的，但它不能补回已丢失的角色证据。这不是要求观察器自行判断主体，而是保留所属层已有的证据。

最小修法：投影保留每个 target 的 meaning/context 与 physical-proof 引用角色，forbidden meaning 检查使用对应角色；原文 excerpt 可以继续取两者 union，不裁引用、不重新解析、不引入分类器或新门禁。复验同一角色变形及原原子写控制即可。

复现：`tmp/v2/test_review.py::test_meaning_context_and_physical_proof_role_are_not_erased_in_receipt`；双输入输出为 `tmp/v2/role-observation.json`。两者全文与 hash 已嵌入同名独审 JSON，可独立重建。

## 验证范围与交接

ROOT 的 11P 记录绑定 runner `24e13f1c…`，最终冻结的 `633b3266…` 另外将捕获提前到 `_candidates` 返回时。本轮实际检查最终字节的投影、原子写与新进程入口，并静读该捕获位置；不宣称完整 11 例已在最终版重新运行。

ROOT 已确认复现并授权清理。临时目录初始 absent，完成绝对路径包含和无 reparse 检查后已恢复 absent；清理 10 文件、23,816 逻辑字节。全部必要复现与输出保存在 JSON。R1 的失败及旧 H1 v3 无完整收据的历史保持不变。本次不签真实 H1、正式摘要、缓存恢复、RF 经济采用或全项目完成。

报告后 STOP；ROOT 同 owner 修复并冻结后再增量复验。

ROOT 随后收到用户新要求：取消任意 observer 输出、checkpoint 及 ancestry 截断阈值；本报告的旧 cap 控制只记录 R2 历史行为，不构成下一版政策。后续复审按 ROOT 新冻结范围执行，本轮不继续按旧限额扩测。
