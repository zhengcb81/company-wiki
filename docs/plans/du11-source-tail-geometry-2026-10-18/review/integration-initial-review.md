# 缩进尾部生产接线：待列证据修复

纯 helper 已独立通过，不等于生产接线通过。当前3源码+集成测试静态初审确认：新负 overlap 分支不能把两个缺失 column 标签相等当作同列证据。ROOT 已接受并准备修复，故标 **PENDING_COLUMN_EVIDENCE_FIX**。

认可有界补充：明确非空相同 column；或当前扫描中实际紧邻前/后正文带，用来源原生 bbox 证明 tail 左边界与正文右边界属于同一正文带。锚必须同 source/page/scope/frame/font/role，不能跨 heading/table/QA/不连续 flow，不能使用 pair 自己、任意同页近邻或宽的多栏合并 carrier。记录锚原 unitID/bbox/误差/关联，计工作预算；至多常数邻居，不建第二 parser/store。

锚行高无需满足尾字形行高，但只能作正文列带物理证据，不借其词义、主语或原文去填补另一个断句。无有效锚仍 unknown/defer。当前版本/源码进入 causal identity、source-family shared owner 方向正确。

本轮未运行新的测试、真实 PDF、收费或网络；等列证明修复冻结后做有限 delta 复审。来源语义闭合/正式内容 C 仍 OPEN。
