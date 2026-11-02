# T3 备注未证后缀与连续性合同根修

状态：**实现冻结，STOP 待增量独审**。工区 `tmp/w23-r6`，branch `codex/architecture-t3-source-scope-20261102`，HEAD `8782050b`。本作者无 Git/index 操作，不改 ROOT TERM 源码、旧 47 断言、原 R1 独审或旧 CI 失败收据。

## 根因与修复

独审真实 P2：显式 note 达到 24-unit 上限，仅首个越界 target 被标未知，后续同 note 原文被错误释放成无 intro 的独立完整 material。原代码将“停止计算”当成“来源范围结束”。本次修整个资源/能力退出状态，不只补某个 b23 名字。

`structure/source_scopes.py` 现在按同一计费序列线性处理：限制只停止正向证明和 member 扩张，后续仍属该显式 note 的潜在原始条款保持 unknown，直到真实新 marker、heading、source、role/turn 或明确结构 barrier。unit cap 仍 24；page cap/缺 proof 同样保留后缀 unknown。已识别 furniture 不会把未证状态意外清掉。工作预算在观察/输出前扣费，耗尽继续使用既有 WorkBudgetExceeded→未完成结构路径，不发布伪完整范围，不新增预算系统。

每批诊断至多 24 个 exact IDs；semantic partial/material context_blocked 复用已有传播，不更改消费者。健康标题后的独立业务和新 note 仍可用。

额外真实 RED 发现：矛盾 column 会把原始 failed unit 排到另一健康 heading 后；只跟物理排序扫描会把该 unit 遗漏。现在借用已解析的原始 source sequence 仅保守识别潜在未证后缀；正向边仍同时要求 layout 邻接一致，以及既有 member 或 physical owner 的真实证明。原始 ordinal 不独自证明范围，不选择任一顺序必真，不改全局 layout 排序，不按每 note 排序/重扫全文。单次 layout-next lookup 只作冲突拒证，既有充分成员证明仍不要求 bbox。

旧候选 CI `41383874109` 的四失败也在同一 continuity owner 查明：抽共享 helper 时新增 `len(block_identity)==64`，错误收窄旧接口（已解析 native 观察允许本地 opaque block token），使同 block 原始句片段断开，进而破坏完整前缀/未完尾部计数。已移除这一个多余格式门禁；真实 block identity 相等、source/role/order/char-range 等验证保持。canonical SHA 验真仍归 parser/source contract，不在 continuity 重复创造一层许可。

## 实际 TDD

| 运行 | 真实结果 | 范围 |
| --- | --- | --- |
| 新五个行为控制首次 | 3F/2P，1.94s | 27/73 条 cap 泄漏、重排缺 proof 为真实 RED；page-gap 和 budget 控制已 P |
| source scope 根修后 | 5P，1.56s | 同一五项；没有提高 24 或修改旧期待 |
| 旧候选 CI 四项定点复现 | 4F，1.72s | 同 block 字符范围、四 block 计数、完整句前缀 split、未完尾部不可隐藏 |
| block token 合同恢复＋冻结控制增强后 | **9P，1.76s** | 上述旧四＋新五；新增明确诊断分批<=24、exact suffix 集合、预算足够走到首越界项的反控 |

未重复 82/84、整旧 continuity 文件或全仓。Ruff 四个 owned 文件通过，mypy 三个 source 通过。实际命令、四份原始日志、每项 SHA 在同名 JSON；旧 CI 失败不是修复后通过收据。

## 冻结与恢复

本次仅四个文件有增量，实际字节 SHA 在 JSON `owned_files_sha256`：

- `src/company_wiki/document_understanding/structure/source_scopes.py`，内部 feature `/2`。
- `src/company_wiki/document_understanding/structure/sections.py`，传递借用的实际 source observations。
- `src/company_wiki/document_understanding/narrative_continuity.py`，恢复已有 opaque block identity 合同。
- 新 `tests/unit/document_understanding_note_scope/test_scope_failure_tails.py`，五项端到端原始 ID/材料和预算控制。

独占 `tmp/t3nr-a691` 初始不存在，四次 basetemp 均长度 51/未 relocation；核绝对 parent 和全部非 reparse 后仅删除此目录，最终 `exists_after=false`。文件数/字节数与原始日志保存见 JSON。共享候选 worktree 留给 ROOT，没有修改或清理 reviewer/他人目录。

未运行原件、模型、付费 API、真实 H1、正式摘要、cache/RF 或完整 CI；无配置/原件写入。后续由 ROOT/独审绑定四份最终源码增量，验收后正常提交发布。本作者 **STOP**。
