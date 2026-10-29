# W20-RF-ADOPTION ROOT 独立验收（2026-10-29）

**结论：CHANGES_REQUESTED，暂不并线。** 不是退回整包；可交原 harness 修以下三个通用问题。原包提供的两份测试已独立复跑 **26 passed / 12.49秒**，作者工区前后 clean。独立反例揭示现有绿测未覆盖的接线断裂及聚合遗漏。

## RF-R1 · P1 · 不相连的身份/哈希被误当完整采用链

`tools/narrative_adoption_audit/audit.py:466–529,831–863` 只分别判断 claim/parameter 存在、给定SHA在任意输入source存在，再按 span_id 拼接。没有验证这些键确实属于同一条来源→片段→claim→参数链。

复现使用真实校验通过的 source-B wire；把合法 source-A 回执里的 span_id 换成 B，保留 A 的 SHA/claim/parameter。报告把 **B片段判 used，且无绑定错误诊断**。把显式 source_id 改为根本不存在的 canonical ID，也仍 used。详见 `rf-evidence/probe-results.json` 的 `foreign_span_with_existing_capture` 与 `wrong_explicit_source_id`。这会直接破坏本卡要提供的“没有偷换资料、模型实际采用”的观察可信度。

返工：在一个共同的 receipt-resolution owner 中验证实际已知的边；canonical parent 与 RF 本地 source_id 应通过既有 SourceRef/capture 映射，不能把两种命名空间直接比较。检查已提供的 hash/source/locator/parser/claim target/material/parameter 关系，记录命名诊断。**继续保持缺hash宽松unknown，不增加许可或人工门禁。** 加两份不同合法来源同时存在、错source/hash、错定位/claim/param和跨run反例。不能只给此例加字符串限制。

## RF-R2 · P2 · 同一片段的多处真实采用只剩第一条

`audit.py:831–863` 使用 first intact dependency。独立探针用真实 consume adapter 把同一片段分别绑定 `first→0_base_2026` 与 `second→0_base_2027`，再真实 run_forecast；最终两处claim都被采用，但 **span.cited_by 只保留2026**。同一回执两条dependency还被写成“多个receipt”。

返工：以 canonical span 为一个item，聚合所有合法依赖路径并去重；保留各错误路径诊断，不吞掉其他有效路径。补同回执/跨回执、跨年度/情景、顺序颠倒结果不丢引用、单span不重复计数测试。完整证据见 `two_valid_bindings`。

## RF-R3 · P2 · gzip绕过输入字节上限

`cli.py:38–47` 只看压缩文件stat，随后无界 `gzip.decompress`。独立小探针：133B压缩文件、上限1024B，函数却返回100000B。此时JSON与items限额尚未执行，不能保护读取阶段。

返工：限制压缩和解压后的读取量，流式最多读取limit+1后抛命名resource_limit；不能先完整解压再检查。补小压缩炸弹、截断/损坏gzip、exit2/不留半份输出。维持既有额度。

## 验收范围与交接

本次实际HEAD `7716c7daefd540a143a282e621e1b53f9c1d9d07`，实施与作者独审绑定 `8b221153`，其后产品源码未变；四份源码/测试实际SHA见 `rf-review.json`。ROOT另核plan/progress两项交接SHA因文档收尾落后，这只是记录同步项，不单独否决产品。作者原独审及26绿测不被改写，新增反例另存。ROOT没有改作者实现、没有merge/commit它的分支、没有模型/网络/下载。

可复验脚本 `rf-evidence/probe.py` 使用本工区已有校验器、真实wire/consume/run_forecast和小合成材料；固定工区路径便于本机重放。修复后由原 harness 先把以上案例转为有意义RED，再修共同owner、跑相关短包，调用真正独立agent复审，交付新的implementation commit、source SHA、测试/清理记录。无需反复全量或新增小节点签收。

26项命令、JUnit、实际根因与完整复验要求在 `rf-review.json`；临时pytest树已验证在ROOT自有scratch内后清理，原作者工区保持clean。**真实公司RF采用与主线循环仍未签收。**
