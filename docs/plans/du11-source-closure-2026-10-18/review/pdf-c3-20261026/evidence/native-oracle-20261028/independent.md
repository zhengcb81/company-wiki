# Native-range oracle 独立审查

FINAL — PASS。绑定作者最终两文件raw/LF SHA，测试前后相同；无open实现发现。

独立定向 **66 PASS / 4.51秒**：自有16、作者中性45、旧claim-grounding5。未重跑156项矩阵或SDK。

NV5-IR-01闭合：先观察单个真实换行，再做通用空白折叠；native range与已证明fragment边界复用同一CJK条件。1245.4与百万元的显示换行可识别，source/gold/ID/locator均不改。内联空格、空行、英文字片、数字相邻、小数/逗号/指数/符号边界未被拼接；来源/页/role/parser/reference及support/context分区保持。

独立重读同一v5 typed selection + exact prepared HTTP body + gold，full selected与准备task支持均3/3，行业云确为t33，输入字节不变；篡改t33准备正文被compiler等价断言拒绝。phase_c_observer字节未变，两个观测路径调用同一oracle。

旧20-claim保存响应解码结果不变，6个已复核错误claims仍全不受支持；部分引用及期间/货币/否定反控通过。source3/3不等于摘要3/3，sent_tasks只是observer对准备任务scope的字段名，本次离线检查未发送HTTP。v5历史0POST阻断收据未改写。

自有.c3ori已按绝对路径检查删除，父环境未变，无后台进程。无源码/作者测试/gold/observer/PWF/原件/配置编辑，无PDF/Docling/模型、网络或下载。Docling启动问题和真实新摘要/生命周期验收是后续独立节点。

| 文件 | LF SHA-256 |
| --- | --- |
| `tools/document_understanding_benchmark/closed_group_support.py` | `4f0b7127384339bebaba1d7150436d01ebfa08ecce4e4a70dbac2f042c336af9` |
| `tools/document_understanding_benchmark/tests/test_native_range_quote_boundaries.py` | `590835cf5a5b4c00a4ebf6ae08c12068fd46d7c670af60efe1b88b4fd8089bab` |
