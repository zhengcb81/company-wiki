# MAIN W04续行：失败final有界持久化

2026-10-11；沿原W04，共用修复只由MAIN内部worker承担，不新增外部施工卡、不关闭真实研究。

## 必须读取

../m3_root_remediation_2026-10-09/work_packages/W04.md 与 evidence/next-root-review/w04-bounded-diagnostic-design.md（SHA312bc35c9096e66b0a57e6cbaa265dd3614ecb9e7654c2408674ee8b80f3638c）。本细则冻结该报告八字段/None-vs-empty、两种SHA、现有结算和真实整条attempt容量；不存在CallOutcome，不另造ledger/schema包。

## 精确排他写集

src/company_wiki/automation/narrative_model.py、narrative_http_model.py、narrative_model_caller.py、narrative_summarize.py、narrative_batch.py；如需只新增一个内聚 failed_final helper。新增tests/unit/test_narrative_failed_final.py、tests/integration/test_narrative_failed_final_cli.py；现有相应HTTP/caller/summary测试只必要定点更新。自动化models/store/compaction只有已证旧路径丢字段才报MAIN，由ROOT串行接线；不要先泛改共享类/数据库。evidence/w04-main-reception/**独占可写。其他源码、rootPWF、W03 narrative_evidence、P7源及RF/audit/config/raw不写；不commit/push/install。

## 一次TDD责任阶段与一次大节点

1. 真HTTPbody decoder951B/explicitempty/None/18000B、body不同final相同、unknownwire/Unicode surrogate负控先RED。八字段同冻结typed scalar对象，完整raw responseSHA与decodedfinalSHA各真实；旧无字段shape不填。
2. HTTP→caller→failure result，原预算settle一次；response_sha256列仍decodedfinal，不塞rawenvelopeSHA；正式output0/None，不生成bundle，不retry。observed=None保持unknown而非0；8194completion及reasoning子集/旧unknown守实数。真实canonical_json(HandlerResult.to_dict()).encode UTF8严格<16384，以整envelope二分prefix、JSON escapes/multibyte对齐；没有reasoning也公开failed_final。诊断构造/写失败不盖主错误或清fee；真实存储settle失败仍原storefailure语义。
3. 集中责任/static后一次ownedTEMP公共CLI真实子进程+loopback length951→persist/publicdiagnostic/terminalcompaction→两次resume，原一次POST与reservation/settle，不收费不正式output。包含empty与None语义对照。最后SHA保护与TEMP恢复；0外部provider/LLM。不要重复已绿全suite，真实工程证据存唯一attempt日志且历史不覆盖。
4. 向ROOT交精确diff、RED/GREEN/static/公共E2E与字段/fee/byte检查点、日志SHA和恢复；ROOT做独立关键复核、合/正常commit/push/CI。现有大节点审查不拆成逐helper人审。W04真实已配置模型复验与W03/W09研究仍未完成。

## 同一公开E2E暴露的blocked-run恢复共因

8194真实completion>8192单请求上限按现有预算正确block_run，非摘要验证jobs仍pending；两次resume并未再次模型调用/收费，但旧batch activate_run反复修改run.updated_at/control generation，不能称只读恢复。修责任在同一narrative_batch.py生命周期：既有run blocked、无当前活跃worker且无pendingoutbox effect时，原只读状态返回budget_exhausted，保留pendingjobs/原账/诊断，不伪terminal、不撤消预算阻断或取消job。真正活跃worker/未交付effect必须保留原恢复处理，避免吞掉工作；用既有store/lease/outbox只读状态，不新permission/registry。immutable绑定与原件验真仍按所属责任边界，不重新模型/结算。先3样本真实DB/账务counter失败固定，再修同一shared文件；旧合法unfinishedrun/waiting-effect/active-worker正负控受改回归，一次公共E2E集中复跑。dump测试SQLite连接显式finally.close保证owned Windows TEMP恢复，不通过忽略updated_at/主数据来掩盖产品写入。ROOT已确认本责任由W04agent在既有独占batch.py继续实施，W03runtime接线等待该文件交回。

## 2026-10-10T23:41:30.739963+00:00 — blocked run 的既有 outbox 读取按实际 FK 隔离

全局outbox非空不能让无活动工作的本run重复activate。以既有outbox.effect_id→effects.job_id关系扩展现有list_outbox_entries的可选allowed_job_ids；None保持旧查询，空tuple返回空，有值JOIN先scope/status再LIMIT，不推测ID/payload、不增表或许可。W04负责该方法及独立只读query测试，其他store源码仍ROOT独占。以真实Store和unrelatedrun正控、scoped pending/leased/failed负控TDD，再一次公开三样本精确SQL恢复验收。既有PAUSED与noactive jobs/no unfinished attempts/no pending effects条件保持，预算耗尽保留待办与真实旧费，不伪终态。
