# DU5-AUDIT-SUMMARY：摘要双向独立审查与同分母比较

状态 READY。工作目录 `C:/Users/郑曾波/Projects/revenue-forecast-audit-du5-summary`；分支 `codex/du5-audit-summary-20261015`；源码基线 `e5189a0614477d4d84c9cd4e0237f9b2a64a059a`。PWF `docs/plans/du5-summary-2026-10-15/`。本卡是 audit 项目施工，不能在 CWP/原 audit 主目录施工。

## 真实缺口与已有能力

`skills/revenue-forecast-audit/references/review-storage.md` 的 S06/S08/S13/S14/S18 已要求读业务、核摘要与遗漏、保留限定和正确召回分母，但缺少可复用的“来源侧目标先冻结→输出侧每条claim复核→同目标版本比较”流程。`authoring_provenance.py`只核已给片段，不检查未选内容的重要遗漏。W08 的 EvidenceReader/reconcile 能实读引用与核记录，却不证明自由文本语义；CWP 已有 quote oracle，不能复制一份冒充新能力。

当前真实摘要旧20条8PASS/6WARN/6FAIL和PD5/Matrix等遗漏仍开放。本包不改这些原始结论，而是让今后每轮审查确切说明哪条有自身支撑、哪些重要内容没留下。

## 固定可写清单

- `skills/revenue-forecast-audit/scripts/summary_review_packet.py`
- `skills/revenue-forecast-audit/scripts/summary_review_contracts.py`（仅确有必要时）
- `skills/revenue-forecast-audit/references/summary-semantic-review.md`
- `skills/revenue-forecast-audit/references/review-storage.md`（只接入上述方法）
- `tests/test_du5_summary_review_packet.py`、`tests/fixtures/du5_summary_review/**`
- `tools/run_summary_review_e2e.py`
- `docs/plans/du5-summary-2026-10-15/**`

复用 audit_contracts、EvidenceReader、review_protocol 现接口，以上以外只读。既有 pool/audit_run/review_evidence/reconcile、安装工具、技能 SKILL 主文件、CWP/FF/RF/生产配置/旧报告不改。若确实需要改别的接口，交 ROOT 具体证据，不发明运行时旁路或新数据库。独立审查的输入不足时用 unknown，不新加身份/缺hash许可。

## 目标接口和执行流

新增 `summary-review-map/1` 是审查工具输入映射，不是生产摘要协议。包含 run_id、attempt_id、document_kind、observed_versions；source_fragments（fragment_id、真实source_ref、artifact/locator）；selection（真实选中声明及证据）；claims（原claim_id、text定位、support/context各自fragment引用）；targets/reviews（实际独立报告定位）。原ID不重写，不解析私有物理目录猜出处。

公开 CLI 采用 `summary_review_packet.py prepare|attach-review|compare` 三子命令，具体参数在 A 节冻结并写 --help：

1. **prepare 来源包**：只呈原语言来源与真实定位、文档类型、已读/未读范围。不给候选摘要、旧评分和选取理由。reviewer 实际阅读后写 targets：target_id、命题、重要性理由、subject/object/stage/modality及来源定位，未知明确 unknown。
2. **prepare 输出包**：在目标冻结后呈各 claim 原文和其自身确切 support/context。缺引用不能从全 selected/其他claim借事实，也不自动补邻居。引用打开状态与语义状态分开。
3. **attach-review**：保存独立 reviewer 的真实声明及其审查对象版本/范围，逐项记主体、对象、阶段/否定/条件、数字/期间/单位与引用充分性。程序负责组织/比对，不模拟 reviewer 自动发语义 PASS；缺审、重复/冲突审查、旧attempt/旧字节错配必须可见。
4. **compare**：同一冻结 target 集比较 source→selected、selected→summary、summary→support；保留原 target/claim 分母，新增目标单列，删除失败claim单列，unknown/不可比明确，不算一个遮蔽重要遗漏的总分。输出 summary-review-comparison/1 与 Markdown。

无hash可以由既有 reader 实读记录 observed SHA；已有hash与实读冲突就是材料变化，不能还按旧报告判通过。没有 PDF/page/native locator 能力时明确 unresolved，不把 JSON Pointer 的打开成功说成原PDF真值通过。原件、CWP excerpt、人工审查分别列来源层级。

## A：先做行为 RED

读现 review-storage、authoring_provenance、review_evidence、review_evidence_reconcile、对应 W08 测试和交接。本包不是重做这些模块。

TDD 覆盖：盲包不泄露候选/旧评分；目标冻结后不能被 compare 偷换；正确数字但错对象的 reviewer FAIL 保留；合法support但语义FAIL不被resolved覆盖；actual/planned/否定/条件/相对主体；question context不能改成answer support；表头单位/期间与正文限定；selected命中但summary遗漏；换分母/只删失败claim/旧attempt套新输出；定位失败/读取额度耗尽/未读范围unknown。测试验证机制保真，不声称单测证明自然语言蕴含。

来源只用最小必要真实摘录与明确synthetic；旧20条真实记录如未能取得完整原始审查则报 NOT_RETAINED，不凭概要造旧20条gold。A/B/C仅各一次集中报告，无逐条人工签收。

## B：实现和集中回归

`python -B -m unittest discover -s tests -p test_du5_summary_review_packet.py -v`，随后本仓现有完整 unittest suite 一次。沿仓现静态检查，不额外建立CI门。无网络/无模型/不安装技能，依赖仅现环境可用标准库与已有audit工具。输出只写调用方owned新目录，旧结果不覆盖；错误输入/写入失败/重跑恢复都不损坏旧材料。

## C：实际 CLI 与独立使用者验收

实现 `python -B tools/run_summary_review_e2e.py --owned-root <新临时绝对目录> --receipt <绝对路径>`。真实启动三个CLI、实际读取源/输出/报告、比较两个版本，不能 mock CLI。

至少 A/H/US、两种来源形态，含问答和期间/单位。使用已保存最小真实材料；不足报告具体 NOT_RUN，不捏造“真实”。另取未参与编码调试的一组片段+候选，先做来源盲审冻结，再由实际独立 reviewer 读输出包给报告；不得预设所有结论为 PASS。只在本 C 大节点做独立试用。不能用人造 all-entailed JSON 冒充独审。

验收工具必须展示遗漏、错引用、unknown与改善并存，保持旧分母与旧失败。原件/配置/原报告/sentinel不变，临时目录恢复。交付CLI用法、真实/合成边界、独审报告、集中测试、清理收据和PWF handoff。正常提交后STOP，ROOT后续仅在现有质量大节点使用；本包不修生产摘要、不等待 CORPUS/v4、不增加发版许可。
