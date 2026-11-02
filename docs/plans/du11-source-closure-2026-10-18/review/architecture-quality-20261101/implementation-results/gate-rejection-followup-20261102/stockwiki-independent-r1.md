# StockWiki 独立审查：初轮

**NEEDS_ROOT_FIX。** 已核作者13路径SHA前后完全相同，完整阅读源/测试diff与新增未跟踪测试；未修改作者文件/Git/生产状态。此报告保存原失败，后续修复不得倒签。

1. **SK-P2-PROTOCOL-CANDIDATE**：真实公开NarrativeSourceTransport.read收到好receipt和另一个同schema的重复status key或NaN locator_count行，均返回source_and_locators_verified。framing fallback把坏协议当普通日志丢弃，再接受剩余好协议。应仅忽略非协议诊断，保同schema协议的strict/ambiguity拒绝。
2. **SK-P2-FINITE-TIMEOUT**：raw VerifiedOpenTransport.from_config接受NaN和Infinity实际时间预算。应在唯一owner校验有限正数，不恢复300s任意帽；探针没有启动子进程。

其余已读：非canonical JSON接受发生在真实artifact size/SHA之后；source/manifest/asof/引用/partition仍检验，可选review不晋升verified/research状态。actual explicit byte/receipt/time边界与树回收没有被删除。完整源diff、13SHA、四个公开反例与脚本已封存JSON。

实际列出两份现有CWP→Stock E2E文件；等ROOT修复版冻结后只跑synthetic narrative TXT和raw text两条技术链及必要负控，不读P06/真实IR/招股书，不重136/27组。未跑之事没有冒称通过。

0付费、0网络、0原件。tmp/si7仅本审查自有文件，先留证；待修复版最终E2E后精确清理并写后续报告，原FAIL不覆盖。
