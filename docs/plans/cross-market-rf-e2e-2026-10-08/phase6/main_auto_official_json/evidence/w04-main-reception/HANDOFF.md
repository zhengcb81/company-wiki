# MAIN W04 实施交接（2026-10-11）

状态：本责任源码稳定；交回 `narrative_batch.py` / `store.py`，不再写源码或测试。未 stage/commit/push/install，canonical、production/config/raw、P7/RF/AUDIT/W03源码均未由本线程修改。ROOT负责集成、PWF归总及真实配置供应商后续验证。本报告不签 W04 全部研究/供应商任务完成。

## 真实写集与接口

- `narrative_model.py`：`FailedFinalDiagnostic` frozen八scalar字段；`FAILED_FINAL_SCHEMA="narrative-failed-final/1"`；`FAILED_FINAL_ATTEMPT_MAX_BYTES=16384`。`from_observation(*, provider_body:bytes|None, content:str|None)`、`to_dict()`、`from_dict(mapping)`。真正raw HTTP entity SHA/bytes与完整decoded final UTF8 SHA/bytes严格区分；没有raw实体则wire SHA/bytes均None；None是未观察final、空string是观察0bytes与e3b0…SHA。原文不strip/NFC/替换surrogate；prefix独立copy，所有DTO字段类型/长度/clipped/完整prefixhash严格校验。
- `narrative_http_model.py`：既有length与empty-content分类保留，异常携带可选typed `failed_final`。完整HTTPbody仅计SHA/长度，不另存完整JSON；只截final正文，不存reasoning、请求、密钥。body构造诊断异常仍保持原主错误与usage。未知final的`content_bytes`真实None；旧直接构造异常默认0维持原兼容。
- `narrative_model_caller.py`：失败保留已知usage或原未知保守reservation，只settle一次，不重试。existing reservation `response_sha256`仍decoded final SHA（未知None），绝不改成wire SHA。失败正式output=0/SHA=None，没有bundle。真正结算存储失败仍`MODEL_BUDGET_STORE_FAILURE`、保守旧fee，不因可选诊断清费。
- 新 `narrative_failed_final.py`：`fit_failed_final_result(base:HandlerResult, diagnostic:FailedFinalDiagnostic)->HandlerResult`，只用于失败。通过实际`canonical_json(HandlerResult.to_dict()).encode('utf-8')`完整envelope测量，在codepoint上二分最大prefix，严格 **<16384 bytes**。JSON转义（C0/引号）、CJK/emoji/组合字符按真字节算；不切JSON字节。如果连空prefix八字段metadata也装不下，保留原error/metrics且不附可选对象。没有新账本/数据库上限/许可协议。
- `narrative_summarize.py`：生产budgeted caller异常→failure HandlerResult附有界诊断；可选fit失败不盖主错误/收费；原成功schema不变。
- `narrative_batch.py`：public `model_diagnostics[].failed_final`从真实attempt读回，即使没有reasoning字段也可展示。历史缺字段仍缺，不回填；破损可选诊断只显示unreadable，不改原job/账务。
- `narrative_batch.py` 生命周期共因：只有既有blocked run、PAUSED栅栏、无LEASED/RUNNING/VERIFYING job、所有scoped attempts已finish、无scoped未完成effect、无scoped pending/leased/failed outbox，才能对仍pending的真实jobs只读返回原budget/storage_exhausted。没有取消jobs、伪终态/成功、重新settle或activate。真实active/未交付保留原恢复路径，原allterminal只读历史兼容不改。账本blocked检查优先于allterminal分类，修复scheduler先终结依赖时初次failed而恢复budget_exhausted的非确定状态；真实storage原因仍storage_exhausted。
- ROOT授权扩展 `store.py` **只** `list_outbox_entries(*,status:str|None=None,limit:int=100,allowed_job_ids:tuple[str,...]|None=None)`。None保持旧查询；()返回()；有scope用真实`outbox.effect_id→effects.job_id` JOIN先过滤再LIMIT。opaque outbox ID/payload无需猜测。未改写库操作、其他store行为、schema或权限。另一run的pending结果不会反复activate本run。

新测试文件三个：`test_narrative_failed_final.py`、`test_automation_outbox_read_scope.py`、`test_narrative_failed_final_cli.py`。既有测试源码未修改。

## RED → GREEN：不累计重复用例

所有日志/回执唯一命名保留；名称含green的候选如果returncode非0，不当GREEN。

| 证据 | 实际结果 | log SHA256 |
|---|---|---|
| `red-unit-20261010T232338Z-193f4700.log` | 最早夹具误差：长参数ID使Windows PYTEST_CURRENT_TEST环境值>32767；12 ERROR混入，不能当产品RED | 见原.json |
| `red-responsibility-20261010T232426Z-ff2fddca.log` | 修短ID后真实20 FAIL/2 PASS，公开/责任缺诊断字段 | 26c979c608d11ea5b51b80efcb2ccda740d7d24b1182d54bae16e3b66155c74f |
| `green-responsibility-20261010T232844Z-18399ae4.log` | 168 PASS/4.15s，HTTP/caller/usage/summary旧责任与19新责任；后续不重复整包 | 62ed1e0d1ae3bbc53629dcfd2d30ce407634c0862277bd64edff4d715c61d2eb |
| `green-public-cli-20261010T233034Z-4b39580d.log` | **3 FAIL**，diagnostic/fee断言已过；DB恢复写updated_at共因与SQLite fixture未关闭导致Windows清理次级错误 | 02fcd53910eea174992de77725ce3714080efa1249b45e8efc87b4b9276e3159 |
| `red-blocked-history-20261010T233959Z-88282111.log` | 真实Store恢复条件14 FAIL；不是provider问题 | eeeff2cb438ba79f989556cf8f0ba1c9b6fdea9b1c7fa6632027a678543ebd4a |
| `final-public-cli-and-recovery-20261010T234124Z-0e96b324.log` | **2 FAIL/3 PASS**；budget ledger已blocked但allterminal先判failed的实际竞态。既有completed历史/activation恢复两项PASS | b0224c7f586616dd03afd069faf6059f9790e3c63b0e8550c427046ddd3a8fbf |
| `red-outbox-scope-20261010T234251Z-a5d11787.log` | 8 FAIL/6 PASS/11 deselected；缺FK scope、foreign outbox导致误激活、scoped failed被遗漏 | b51ba70c942e7c53808cfde604884854a2af545510dc5f51ba7b00820f829219 |
| `green-final-unit-scope-20261010T234505Z-ef47c6f8.log` | **56 PASS/5.23s**：47诊断/blocked条件（含原19）+9只读query；不与168相加 | 52808abed8a05ce96701b30bb6f183ea7583e8c7ea74e81c7fc50fef5cff67a4 |
| `green-final-public3-20261010T234533Z-743169ad.log` | **3 PASS/22.31s**，最终稳定源码公共CLI 951/empty/None；只这次作为本片最终E2E | 910924bc451d9ff66d7989ebf7d3b9f1f50e2240e6de61d644f3b283cfb1bf51 |
| `static-final-20261010T234557Z-8dcc8d4b-ruff.log` | 7源码+3新测试Ruff PASS | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| `static-final-20261010T234557Z-8dcc8d4b-mypy.log` | 7源码mypy PASS | 050c52a2b0c61e8b681ef5c485e0bc03340b8d55148e0acef27d744c8be42033 |

最后公共3样本只调用自身loopbackHTTP，实际3次初始POST；2次resume/样本，共6次，新增POST=0。各样本保73输入/8194输出、known charge8267 tokens/16461µUSD。8194>配置8192仍真实block；没有提高cap或假装模型成功。verify保真实PLANNED或合法DEPENDENCY_TERMINAL(DEAD_LETTER)，后者必须指出真实summary job=dead_letter；verify无attempt/effect，summary本身MODEL_OUTPUT_TRUNCATED终态。每次resume逐job快照、AUTO与Catalog完整SQLite dump、reservation和budget保持；不是忽略updated_at得到绿。所有HandlerResult保存JSON有效且<16384，无正式artifact/effect/output，hidden reasoning sentinel不进入账本。失败不会调用需成功FinalArtifactPin的终态compaction；有界失败诊断直接留在原attempt。既有成功历史/ACK-activation恢复另已PASS，不用失败body伪造正式pin。

## 原件、恢复、预算与SHA归属

各责任/static/CLI runner自有TemporaryDirectory；回执`owned_temp_restored=true`。测试下载/公司TXT、Catalog、AUTO DB、请求、日志/缓存均不写生产根。CLI测试恢复原文byte+mtime快照且显式finally.close SQLite dump连接，避免Windows句柄阻止清理。协调锁控制文件允许测试期创建，不把它算数据库/原件变更。

外部provider/LLM调用0；实测µUSD是synthetic loopback计量，不消耗项目$20/200万token预算。未查/输出密钥，使用测试synthetic key且断言不能进入stdout/stderr。

`FINAL_SHA_RECEIPT.json`固定254文件基线：251未变；三delta分属：

1. 本线程 `automation/store.py`：ROOT已明确授权读取scope扩展（本报告上述唯一method）。
2. `source_catalog/narrative_candidates.py`：ROOT确认另行W03独占并发工作，本线程未写。
3. `source_catalog/narrative_evidence.py`：ROOT确认另行W03独占并发工作，本线程未写。

生产配置保护hash均不变。不能宣称254全部未变，也不能回退合法W03改动。`OWNED_DIFF.txt`包含6既有源差异+1helper+3新测试全文，SHA5c8f131b411091545c0ecb77a337d0c17f15aa38a130335722b39c30f14cbe3d；最终每个源码/测试SHA在`FINAL_SHA_RECEIPT.json`和static最终回执。日志初始长ID夹具错误约1.2MB，仍保历史proof，未覆盖/删除。

## 交接后步骤与实际边界

ROOT可开始W03共享batch接线，并做既定大节点独立复核/正常commit/push。只接本报告精确写集，尤其store只读method范围；不触碰P7-RF/AUDIT排他源码。

本片证明真实公共本地产品链HTTP→decoder→meter→failure attempt→public/resume、字节/费用/恢复不变量。它不证明真实配置MiMo/DeepSeek输出质量或业务research结论；W04真实供应商复验、W03来源recall、W05/P7审查及后续完整RF仍按ROOT原计划继续。没有为green扩大用户配置或加入材料授权/签收。
