# DU11 fine/coarse budget 测试调整独审

**PASS：责任层断言修正，无生产行为放宽。**

受审文件 `tests/unit/test_shared_reading_pdf_layout.py`，SHA `f2b488b383976e3e111e662f2849ede1bad8aecfd2ac0c0f90690b691030cd76`。

旧断言把细几何因 max_pages=1 而未处理的page2，等同于完全不能有reading_layout；这与已审native prose复用原DICT的粗bbox/font观察冲突。粗观察不应消耗或重置WORDS/cells预算，也不能伪报fine。

新测试保留partial、processed_page_count=1、page2原文仍在，额外追踪真实 `fitz.TextPage.extractWORDS` 文档全局仅1次，确认page1实际words；page2逐unit无words/cells，且明确granularity=block。相比只检查layout有无，这直接守住产生细几何成本的操作和结果边界。若逐页预算重启则会读第2次WORDS，若伪造fine则会在page2断言失败。没有删除测试、改生产源或扩大时间/预算。

已实读 ROOT XML：46 tests、0 failures/errors/skips、4.307s，包含受改单例及native prose10例。本独审仅diff/源码/XML，未重跑46项或全套，未读PDF/网络/模型。该文本夹具不单独证明table finder次数，邻接现有表格/细元素/共享deadline测试继续覆盖其职责，不借此宣称远端CI或真实C完成。
