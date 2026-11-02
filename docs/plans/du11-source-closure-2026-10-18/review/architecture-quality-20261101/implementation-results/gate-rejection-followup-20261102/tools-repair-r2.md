# 工具收口R2：内容身份、观察与样本资格分离

**最终作者冻结，待ROOT同一大节点独立审查与发布。** 不追改原audit与tools-repair历史；本manifest包含初版4文件和本轮必要caller闭包共11文件。

## 根因与收敛

- 指纹保留SHA、bytes、mtime原始观察；内容身份只用实际SHA+bytes，缺字段不等价。准备/母native库、执行后protected/sentinel、母usage内容检查统一同owner，mtime-only变化列before/after不拒；真实字节/累计usage变化仍拒，不恢复时间戳藏证。
- 未冻结、development、未知prior-use均可测量；纯资格owner明确eligible=false/0，fresh/local-unseen且明确freezeTrue才具声明资格。它不是质量通过、独立性证书或loop停止统计，不用generic overall=ok计clean。
- 资格传播至attempt、sample row、独立worker结果、verify/bootstrap/run CLI与bootstrap.json；不只修loader。旧ROOT角色措辞删除，RF实际采用仍not_consumed。
- 真实source/gold SHA和指定实际producer版本不一致仍拒；无全树clean、旧commit许可或人工签收。原日志/回执进程隔离根修保持。

## TDD与实际联调

New12 8F4P -> with10 existing manifest controls22P/27.48s (one actual native worker). New optional-prior3F1P ->4P/1.52s; final outward CLI/qualification/content6P/1.53s. Original first-stage process/observer22+delta evidence is referenced, not rerun or double-counted.

真实自建HTML通过public run_replay与native worker：overall=ok/worker exit0，同时所有回执qualification=false、eligible0。原文/gold运行后字节未变；随后故意改自建原文得到unavailable、改自建gold得到hash拒绝。0模型/0网络。完整worker输出单份gzip-base64留在JSON，不重复膨胀正文。

Ruff 11文件绿，manifest mypy绿。bootstrap/run CLI额外测试是明确synthetic child/summary seam，不冒实际注册成功；实际worker的质量evaluation未伪装PASS。

## 最终交付SHA

- `src/company_wiki/_bounded_process.py`：`0fe1ec07503055932ba9f6b05fa4143b56aaf8ce9861fac914bd581873f241f4`
- `tools/document_understanding_benchmark/holdout_acceptance.py`：`ec69dd77cb61034546261b9deab40c5df76c2da8e5e3e031efb9d2e0b64eaea4`
- `tools/document_understanding_benchmark/holdout_acceptance_observer.py`：`98c1070c8ebacd456d577d24f2470672973602941f48ffd14671d9dfd22f3fc7`
- `tests/unit/test_holdout_observation_isolation.py`：`a24103a2c4a4f13d1b6ecfad1a457cd4d11b673f6412a444c9886eef7e8876b3`
- `tools/document_understanding_benchmark/phase_c_runner.py`：`429bd2e6d4885770d16624d82dfb5c079eb4dfd1fec39178639f28a415e537e6`
- `tools/holdout_replay/manifest.py`：`f2411482c566867ae522b4c3f39ab0f2e69e55e5b85d661a2193e536e6b92380`
- `tools/holdout_replay/runner.py`：`859a2f96bcbe6bb3add1abe3c9d7bcf8112665dee497adb78514dd1677ba0d22`
- `tools/holdout_replay/worker.py`：`8e88073a8d6425e8cf5da6fb4199d99b1fe83d56fefd631157d39482154ae5ab`
- `tools/holdout_replay/__main__.py`：`06a7c82c22371d00c4cfad7a12c8c1f4ac4ca069087fc8101e9d9c4cc6b411a0`
- `tests/unit/test_holdout_qualification_and_metadata.py`：`16c90e160851b6f7f3e815a5fb9c73c1f93500f48d1249829d2b249330c0354d`
- `tests/holdout/w18/test_manifest_freeze.py`：`cd43d83507e1a3afef6d1af9f17db5c4769f43460b2bba67f2f5f7fe8318926c`

## 原审计各项最终去向

- **T-NEW-LOG**：ENGINEERING_IMPLEMENTED: complete native protocol + stderr-only display retention; existing process lifetime owner; no post-exit size permission.
- **T-NEW-EVENT**：ENGINEERING_IMPLEMENTED: full event facts once, I/O/format observation incomplete separate from native; no resend/latch/paid-state weakening.
- **T-PREP-MTIME**：ENGINEERING_IMPLEMENTED: SHA+actual byte size define content identity; mtime remains full before/after observation and no longer admission. Missing SHA/bytes is not equality. Source/native-history/usage actual content changes still fail their owners.
- **T-FROZEN-FLAG**：ENGINEERING_IMPLEMENTED: nonfrozen/development/unknown prior-use permitted to execute; declared qualification false/0 eligible. Do not infer clean/quality/loop-stop from generic ok.
- **T-COMMIT-PIN**：KEPT_BY_REASON: mismatching explicitly requested actual producer version still rejects; unrelated dirty worktree diagnostic; no fixed old commit permission. Help no longer calls a revision allowed.
- **T-REVIEW**：KEPT_BY_REASON: missing semantic evidence remains NOT_EVALUATED/PARTIAL, no raw/source/runtime permission.
- **T-ROOT-TEXT**：ENGINEERING_IMPLEMENTED: text now actual RF use unobserved; status remains not_consumed, not fictitious completed.
- **T-NATIVE-BOUNDARY**：KEPT_BY_REASON: real budget/source SHA/pin/unknown usage/second POST/actual fault contracts unchanged.

## 真实边界与清理

- No real company source/original read, no paid API/LLM, no downloads, no new summary/cache/actual RF adoption acceptance.
- Actual public tiny HTML replay proves execution plus declared nonclean scope, not business extraction or expert quality PASS. Evaluation result is retained and not promoted.
- One actual worker replay only; later pure CLI bootstrap test uses an explicit synthetic registration-child seam and run-summary seam, not fictitious real registration or model work.
- Same-content mtime drift is accepted; true native-history/usage content drift is not erased or silently reconciled outside its cumulative-budget owner.
- No all-Unit/CI rerun, no Git/index/hooks/main-PWF/production config/global installation writes. Final independent review and normal publication remain ROOT responsibility.

自有tmp/tq7初态不存在；先留证再精确清理所有新建夹具/输出/类型缓存。最终清理收据仅补本报告，历史审计保持原失败和当时状态。

最终清理：已核绝对父目录与非reparse，自有 263 文件／8556888 bytes 删除，tmp/tq7恢复初始不存在。所有原测试目录/原件/配置未手工删除；共享pytest缓存元数据未测量恢复，不把默认缓存当原件或宣称整台机器无变化。
