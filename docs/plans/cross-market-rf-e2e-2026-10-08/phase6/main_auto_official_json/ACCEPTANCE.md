# MAIN AUTO official JSON 与 P7-CWP 集中验收

## 结论

**PASS_ENGINEERING / published。** 官方逻辑subject与原PDF/TXT共用同一有限AUTO，P7-CWP已正常合主线；canonical/remote accdeccc737ccaf27d1698238a31af022960a3fa、精确CI38094790883 success（发布证据见evidence/root-final-07）。后续W04/pure W03正常提交236fca08，共享版本接线及其新HEAD发布尚待，不用旧CI替代。原三家研究、四审、新三家/loop不据此签完成。

## 真实证据索引（重复case不相加）

| 节点 | 实际结果 | 证据 |
|---|---|---|
| P7 source独立接收 | 166PASS，35.46s；两布局E2E/旧blob字节同 | evidence/p7-cwp-reception/readonly-reception.md |
| 最终mixed/empty/history | 9PASS，80.38s | evidence/integration-04/final-mixed-empty-history-receipt.json |
| Public canonical跨边界 | 3PASS，46.79s | evidence/transport-subject-03/canonical-cli-handoff.json |
| Public参数shape负控 | 仅新增3PASS，8.76s | 同上；原RED保留 |
| TXT版本/真实MSFT | 57PASS，9.28s；51/51selected回放 | evidence/transcript-boundary-05/HANDOFF.md |
| ROOT集中责任组 | 239PASS/1FAIL（P7冻结源赋值）；定点该1PASS | evidence/root-final-06/responsibility-tests-01.json、specific-fixes-02.json |
| 静态责任 | changed Ruff PASS，最终4模块mypy PASS；先前28唯一注解失败定点PASS | evidence/root-final-06/static-final-03.json、static-01.json、specific-fixes-02.json |
| 独立共因/历史复核 | 101责任PASS；最终history并入上面9case | evidence/integration-04/readonly-review.md |

## 共用根因与处理

1. run单prompt假设导致官方项预留误拒：不可变binding内job_prompt_versions由batch冻结，通用ledger与terminal用同一个pure accessor，错误不再冒称预算不足。
2. generation没绑定明确reasoning_effort及误拒adaptive：绑定实际HTTP语义；缺省/null旧wire不变，历史已完成只读恢复窄兼容，新缓存不假复用。
3. batch schema被误作source kind：工厂按真实manifest要求版本；raw-only request2成立，投影缺/wrong版本仍拒绝。
4. TXT roster误作正文/inline speaker漏END：parser0.3.1修真正边界；0.3.0旧解释保持。真实fixture脱离邻仓目录，CI离线可复现。
5. official CLI忽略显式版本/非字符串裸异常：薄入口透传及shape诊断，P7 source owner保留producer职责。
6. 空字段误报语言失败：完整无叙述直接零调用skip；partial/有内容未知语言不猜。

## 质量、预算与恢复

所有真实parent各自SHA/locator与issuer/as-of绑定；角色和原语言保留，不翻译，原件不可变。同catalog/AutomationStore、lease/generation/outbox恢复、正确逐次结算，没有新库/签收/许可。完整复用新增模型0，refresh真实重处理，部分命中仅缺项。终态小pin每attempt<16KiB，不保留重复正文。旧raw DTO/FK公开语义未伪造成投影；公开ref/read2有完整parents与generation。

本节点外部provider/model请求与费用0；loopback账本数字是synthetic工程测试。USD20/2M累计及unknown沿用。owned TEMP全部恢复，无完整资料湖恢复。P7叶源码原交付不改，RF/AUDIT排他写集、Dayu及邻仓owner WIP不动。完整被测源码SHA与文件体积由evidence/root-final-06/candidate-inventory.json记录。

## 下一步

本包原M1–M3工程已正常主线发布、精确CI通过。P7-RF也已独立接收、发布、安装验证，见P7_RF_ACCEPTANCE.md；P7-AUDIT尚未交付。当前继续W03共享版本接线/公共大节点，再正常发布最新HEAD，随后W05/W08/W09与真实研究。已完成W04和纯W03节点见236fca08；旧157问题/研究封存保持，不重写下面的历史过程记录。

## 原始证据归档字节

发布前cached whitespace检查误把Windows原生CR/CRLF日志及原件fixture作为可格式化源文件。保留其SHA/字节而不重写日志，Git属性仅对plan原始.log、evidence中原始JSON/Markdown等回执和真实TXT fixture按byte处理；源码/Markdown仍正常差异检查和hooks。原失败检查保留摘要，不重复输出全日志。归档后从暂存Git blob逐份验证与原始文件SHA相同；不凭working tree相同冒称仓库中相同。

## 正常hook收尾与P7-RF接收（2026-10-10T23:03:31.329644+00:00）

正常pre-commit首次真实阻提交：mypy在raw source guard发现persisted lineage参数新DTO可空而旧函数注解str；函数实际上只做byte/identity检验、该参数不承担二次许可，因此将注解准确改str|None，不新增阻断。host规则还误把两处JSON Pointer当文件路径，另外4处纯负控使用硬编码示例物理路径；正在按AST字段语义修classifier，4类路径负控改跨平台PurePath/stdlib构造、实际未知path键用tmp_path，10个原拒绝断言全部PASS。没有绕过hook、基线许可或删除断言。原第一次commit失败stdout/metadata保留独立attempt，之后正常重试。

归档时Git自动换行使原生CR/CRLF日志和审查Markdown的已记录SHA变化，已按evidence角色设置-text/-diff，原始内容零修改；暂存280份原始回执/fixture逐byte相同，源码/PWF whitespace检查绿。仅保存必要失败记录，本次候选源码/测试/PWF/证据约2.5MB，未产生全湖/完整备份。

用户已交P7-RF，独立只读接收验收启动；P7-AUDIT仍未收到完成通知，各卡写集继续隔离。CWP主线提交待hook收尾，不将前面工程绿冒称已远端发布。goal active、0外部供应商/模型费用、原件/config/Dayu及邻仓WIP不动。
