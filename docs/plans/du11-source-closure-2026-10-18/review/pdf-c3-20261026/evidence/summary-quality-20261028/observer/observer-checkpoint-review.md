# Observer selection checkpoint 独立审查

**PASS；open=[]。** 仅审查test-harness新增诊断留存，不改变前次真实0POST阻断或内容审查PARTIAL，也不修改原工程final19报告。

新增helper只把已验证typed selection的`to_dict()`规范JSON保存为确定性gzip；event携带未压缩内容SHA和字节数。调用位于gold准入拒绝前，故可保留`layout_coverage.reading_execution`等实际诊断，无需再次解析PDF猜原因。没有读取原PDF、模型响应、provider凭证或环境配置；不影响source判定、任务准入或费用预留。

独立运行当前`test_phase_c_observer.py`的7项及6项中性反控，**13 PASS / 5.20秒**。验证真实typed诊断完整往返、规范SHA、mtime=0压缩、重复零改写、仅诊断改变也拒绝覆盖、父级/嵌套/绝对路径拒绝，以及损坏旧gzip不被替换。Conda -B，timeout插件显式启用；仅1个已知asyncio_mode警告。

相对原final19，仅observer文件变化。将新增helper、调用与event字段在内存逆去后，LF SHA精确还原原`4d7da391…a4e525`；其余18项SHA不变。新增observer测试形成当前20文件范围，见`observer-final20-scope.json`及本报告JSON的files；原final19 JSON SHA仍为`31f455dd…558c83`。

| 工具delta | 当前LF SHA-256 |
| --- | --- |
| `tools/document_understanding_benchmark/phase_c_observer.py` | `06d29f8ccd9bb46f249598d9af301296ea9180891df02cc6af8229e8bec4610c` |
| `tests/unit/test_phase_c_observer.py` | `024e5124ed6b7b691b3f5c9d1eaf85d6950ca96bf00c7cc916644691ce073b2c` |

自有`.oqir28`已按绝对工作区边界核验删除，全部同步测试结束；无新PDF、网络、HTTP、收费API、生产/PWF/原件写入。真实捕获接缝尚未通过新PDF执行观察，本次只签代码路径与中性合同，不复写既有attempt结果。
