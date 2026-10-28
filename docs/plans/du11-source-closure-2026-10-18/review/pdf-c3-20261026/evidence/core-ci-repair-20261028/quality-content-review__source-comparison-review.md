# Source comparison delta 独立复审

**PASS，open=[]；CMP-IR-01闭合。** 仅接受相对`74d98a57`的当前3文件比较词/口径delta，逐项匹配`source-comparison-freeze.json`，测试前后SHA一致。

同一`_SOURCE_COMPARISONS`词汇派生识别pattern、结果修饰语及规范basis；前指只读取实际方向断言和后句marker，不使用全unit词袋。显式yoy/qoq互斥反例及真实`_candidates`路径现延期；等价yoy、qoq、同比/按年仍unique，无basis前句允许后句clarify。前件其他句或marker外的比较词不捐basis，泛指prior period不编造季度/月度。

最终定向 **32 PASS / 2.62秒**：23个作者/既有比较、主体、方向、未来/否定、多前指、跨scope控制＋9个独立反例/同义/scope控制。原22PASS/3FAIL与CHANGES_REQUESTED报告保留在`source-comparison-tests.log/xml`及`source-comparison-review-red.md/json`，不与最终32相加。Conda -B，timeout插件显式启用；仅已知asyncio_mode警告。

| 文件 | 本轮LF SHA-256 |
| --- | --- |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `57a2a8a74be95833613a78524109e6c82b3cd75649c769c384b17efeac81b235` |
| `src/company_wiki/source_catalog/narrative_operating_relations.py` | `73a14192e9cbeff0f59fae4fb79d526e4241a82f8093a5098f302346e12b70a9` |
| `tests/unit/document_understanding_selection/test_summary_source_admission.py` | `5cb8ed07b3f9443422a6b4e778016f640108fc324997144d008987cc660499ed` |

自有`.scir28`已按绝对工作区边界验证删除；无产品/既有测试/PWF改动，无PDF、模型、网络或后台进程。未重跑已发布20文件全批；CI/PDF其他owner及大节点真实验收仍另行处理，本结论不代签新摘要内容。
