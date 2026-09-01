# Source Catalog Worker — 证据、需求、测试、Gate 与风险追踪

> 本文件是 v4 规范性映射，不是动态完成台账。同一 plan revision 内保持冻结；实际状态、
> evidence path/hash、review payload、authorization 与 execution finding 只追加到经 validator
> 接受的 `gate_ledger.jsonl`/`progress.md`。稳定测试 ID 的唯一来源是
> `test_id_registry.v4.json`；唯一 Gate 前驱与 reviewer 数量来自 `gate_dag.v4.json`。

## 1. 来源证据

| Evidence | 已证实事实/审查反例 | 原始位置 |
|---|---|---|
| E01 | 8/12提交引入相关`EXISTS`队列SQL | 调查报告§7、normalizer基线 |
| E02 | plan为documents scan+correlated status-index scan+temp sort | 调查报告§8 |
| E03 | 真实queue select>902s；非相关等价查询约0.231s | 调查报告§§8–9 |
| E04 | runtime停在selecting next document，parser PID/path为空 | 调查报告§§9、13.1 |
| E05 | SQL内无heartbeat，watchdog 900s | 调查报告§12.1 |
| E06 | scan checkpoint只在完整cycle末落盘 | 调查报告§12.2 |
| E07 | uptime≥900s清failure，5s restart并重复startup delay | 调查报告§§12.3–12.4 |
| E08 | 当日44次scan/2.54h；现场一次427s | 调查报告§11 |
| E09 | 46,600 seen、46,599 reused、0 hashed | 调查报告§11 |
| E10 | 单核约96.8%，内存约91MiB，物理盘低 | 调查报告§9 |
| E11 | LLM约42s/summary，normalize:LLM batch=3:1 | 调查报告§13 |
| E12 | normalize eligible≈12,202；LLM pending122；permanent650 | 调查报告§13 |
| E13 | worker主要读源，但最多约120k字符可外发 | 调查报告§14 |
| E14 | catalog≈46.22GiB、备份≈45.93GiB、总计≈92.16GiB | 调查报告§15.1 |
| E15 | retention `_project_root`/`project_root`属性错误 | 调查报告§15.3 |
| E16 | power gate位于scan后 | 调查报告§14 |
| E17 | worker从活动worktree加载，restart可读并行任务半成品 | 调查报告§15.4 |
| E18 | worker已persistent pause，进程0，HKCU Run移除 | 调查报告§§3、17 |
| E19 | status/control wrapper可写diagnostic log | `findings.md`发现12 |
| E20 | 8/12曾有重复supervisor/实例锁噪声，但非SQL主因 | 调查报告§6.5 |
| E21 | v3三路review逐项hash MATCH，但三份verdict均FAIL | `plan_review_findings.md`§6 |
| E22 | v3 schema接受review FAIL/open P1的伪PASSED、BF00和伪分支 | PR-056、reviewer反例 |
| E23 | 02B分支测试在ADR前；D11M-L存在过早生产边 | PR-054、PR-055 |
| E24 | 当前parser路由含TXT/MD/CSV、HTML/HTM、MHT双路、PDF双路、DOCX/DOC、XLSX/XLS、PPTX、JSON、XML/XSD | `findings.md`发现26 |
| E25 | Canary B/12A缺逐run/cycle exact write/precommit合同 | PR-057 |
| E26 | registry CAS至最终登录批准间存在意外登录启动窗口 | PR-058 |
| E27 | production reset在DAG外；POST与最终激活语义冲突 | PR-059、PR-060 |
| E28 | SQLite progress callback是approximate proxy，不是exact VM step interval | PR-063 |
| E29 | v4草稿预审证明任意N/A、无OP合同、伪review确认与隐式12B/12C rollback都可能形成机器控制缺口 | v4 lifecycle/test precheck；`plan_review_findings.md`待冻结处置 |
| E30 | 当前ZR1002/ZR1003 tmp reader-first测试依赖missing DB触发CatalogStore eager init；verify-only reader会暴露fixture假设 | 2026-08-31 drift recheck；`tests/contract/test_zr1002_reader_first.py`、`test_zr1003_shadow_assertions.py` |

## 2. Requirement → 稳定 Test ID → 负责 Gate

表内只列主要阻断测试；完整逐ID introduced/variant/red/green/revalidate Gate、条件模板和样本数必须再由
`test_id_registry.v4.json`机械展开。不得用编号范围、自然语言别名或未注册 ID 替代。

| Req | 必须实现/证明 | 来源 | WP | 主要测试 | 负责节点 |
|---|---|---|---|---|---|
| RQ-001 | queue不再近似二次扫描 | E01–03,E10 | 01,02A | Q-P02,Q-P03,Q-P04,Q-S14 | D01,G01,D02A,G02A |
| RQ-002 | eligibility/order/force/retry/terminal/current-source正确 | E01,E03,E21 | 01,02A | Q-S02,Q-S03,Q-S11,Q-S12,Q-S14,Q-S15,Q-S16,Q-S17 | D02A,G02A |
| RQ-003 | 不依赖ANALYZE、偶然stats或单SQLite版本 | E02 | 01,02A | Q-P01,Q-P02,Q-P03 | G01,G02A,G10C |
| RQ-004 | ordinary open exact schema零DDL；missing/old fail closed；ZR tmp fixture显式初始化 | E14,E21,E23,E30 | 0,02B | M-COM-S01,M-COM-S02,M-COM-S03,M-COM-S04,M-COM-S05,M-COM-S06 | G00,G02B-ADR,D02B-NI,D02B-IDX,G02B-NI,G02B-IDX |
| RQ-005 | explicit init/upgrade有幂等、crash、ENOSPC合同 | E14,E23 | 02B | M-COM-F01,M-COM-F02,M-IDX-F01,M-IDX-F03 | G02B-NI,G02B-IDX |
| RQ-006 | ADR-02后只创建一个分支的T/D/I/G | E23 | 02B | GL-F06,M-NI-S01或M-IDX-S01 | G02B-ADR,G02B-NI或G02B-IDX |
| RQ-007 | SQL work计量模式、metadata、N/2N与绝对SLO可复现 | E02,E03,E28 | 01,02A | Q-P01,Q-P03,Q-P04,Q-P05,Q-P06,Q-P07 | D01,G01,G02A,G10C |
| RQ-008 | checkpoint按per-root outcome/fingerprint推进 | E06,E08,E09 | 03 | C-S01,C-S02,C-S11,C-S12,C-S13,C-S14 | D03,G03 |
| RQ-009 | 真正未完成scan重试，已提交scan不重做 | E06 | 03 | C-S03,C-S04,C-S05,C-S06 | G03 |
| RQ-010 | 长SQL可heartbeat/pause/stop/deadline | E05 | 04 | O-S01,O-S02,O-S03,O-S04,O-S05,O-S06,O-S10 | D04,G04 |
| RQ-011 | liveness/VM activity不冒充business success | E05,E07 | 04,05 | O-S07,O-S08,O-S11,S-S03 | G04,G05 |
| RQ-012 | uptime不再是成功里程碑 | E07 | 05 | S-S02,S-S04 | D05,G05 |
| RQ-013 | per-signature/global/no-success circuit持久 | E07 | 05 | S-S01,S-S05,S-S14,S-S18 | D05,G05 |
| RQ-014 | backoff/startup-delay中的pause有界 | E07 | 05 | S-S06,S-S07,S-S13 | G05 |
| RQ-015 | 单实例、PID identity、Job Object无orphan | E18,E20 | 05 | S-S08,S-S10,S-S12,S-S16,S-S17 | G05 |
| RQ-016 | production reset有唯一D/OP/G且不授予resume | E07,E18,E27 | 05,09,12 | RST-S01,RST-S03,RST-S05,RST-S06,RST-S08,RST-S09 | D05Rnn,G05Rnn |
| RQ-017 | scanner每root/phase可profile且不以漏扫换速度 | E08,E09 | 06 | SC-P01,SC-P02,SC-P03,SC-P04,SC-S01,SC-S09 | D06,G06,G10R |
| RQ-018 | scan cache/rehash/offline/path语义不回归 | E09 | 06 | SC-S02,SC-S03,SC-S04,SC-S05,SC-S06,SC-S07,SC-S08,SC-S10 | D06,G06 |
| RQ-019 | battery gate在昂贵enumeration前 | E16 | 06 | SC-S11,SC-S12,SC-S13 | G06 |
| RQ-020 | 每条启用parser route都有size/error/pause合同 | E04,E24 | 06P | P-FMT00-ROUTE,P-FMT01-S,P-FMT02-S,P-FMT03H-S,P-FMT03T-S,P-FMT04P-S,P-FMT04D-S,P-FMT05-S,P-FMT06-S,P-FMT07-S,P-FMT08-S,P-FMT09-S,P-FMT10J-S,P-FMT10X-S,P-FMT99-U | D06P,G06P,G10R |
| RQ-021 | parser medium启用或禁用均有显式证据，oversize/error/cleanup按模板展开 | E24 | 06P | P-FMT01-M,P-FMT02-M,P-FMT03H-M,P-FMT03T-M,P-FMT04P-M,P-FMT04D-M,P-FMT05-M,P-FMT06-M,P-FMT07-M,P-FMT08-M,P-FMT09-M,P-FMT10J-M,P-FMT10X-M | D06P,G06P |
| RQ-022 | LLM queue/backlog满足drain SLO且保持单线程安全 | E11,E12 | 07E | L-S04,L-S05,L-S07,L-S10,L-S11,L-S12,L-S16 | D07E,G07E,G10R |
| RQ-023 | cache/batch逐document并绑定current source/artifact | E11,E13,E21 | 07E | L-S01,L-S02,L-S03,L-S13,L-S14,L-S18 | G07E,G09,G11A |
| RQ-024 | provider crash使用OUTCOME_UNKNOWN，零自动重发 | E11 | 07E | L-S06,L-S20,L-S21 | D07E,G07E,G09 |
| RQ-025 | LLM_OFF/ENABLED由独立ADR-11 exactly-one决定 | E13,E21 | 07 | L-S17,PX-S19,GL-F06 | G07-ADR,G07O或G07E |
| RQ-026 | 主/备provider逐stage独立授权，off路径全provider deny | E13 | 07,11B,12 | L-S09,L-S15,L-S17,L-S19,PX-S07,PX-S18 | G07E/G07O、各BP/BF、G12A、G12B-PRE |
| RQ-027 | retention bug有tmp回归且默认production delete=0 | E15 | 08 | R-S01,R-S02,R-S03,R-S04,R-S05,R-S06,R-S07,R-S08 | D08,G08 |
| RQ-028 | 无自动backup删除/VACUUM/destructive cleanup | E14,E15 | 08,11 | R-S10,R-S11,R-S12,R-S14 | G08、每个生产G |
| RQ-029 | secret永不采集；获批raw evidence有ACL/加密/TTL | E13,E17 | 08,09P,production | SAFE-S09,EV-S01,EV-S02,EV-S03,O-S09,L-S08,PX-S10 | D08,G08,D09P,G09P、每个生产G |
| RQ-030 | 所有自动测试、scratch与生产操作路径隔离 | E18,AGENTS | 全部 | SAFE-S01,SAFE-S02,SAFE-S03,SAFE-S04,SAFE-S08 | 每个D/G |
| RQ-031 | config/session override不写生产配置 | AGENTS | 09P | SAFE-S01,PX-S02 | D09P,G09P |
| RQ-032 | 外部trust anchor+不可写完整release，拒绝TOCTOU | E17 | 09P,12B | PX-S03,PX-S14,PX-S15 | D09P,G09P,G10C,G10R,G12B-PRE |
| RQ-033 | restricted canary是真one-shot并在OP后pause | E07,E18 | 09P,11B | PX-S01,SAFE-S04,CAN-A1-S01,CAN-A2-S01,CAN-A3-S01 | G09P、各G11B-A |
| RQ-034 | canary exact operation/PK/column/path在commit前拒绝越界 | E14,E18,E25 | 09P,11B | SAFE-S07,PX-S05,PX-S12,PX-S13,CAN-A1-S02,CAN-A2-S02,CAN-A3-S02 | G09P、各G11B-A/B |
| RQ-035 | 每个BP/BF拥有不可复用write contract并覆盖所有内部写 | E25 | 11B | CAN-BP-W01,CAN-BF-W01,CAN-B-W02,WRITE-F01,WRITE-F02,WRITE-F03,WRITE-F04 | 各D11B-BP/BF与G11B-BP/BF |
| RQ-036 | migration有峰值空间/中断/ENOSPC预算 | E14,E23 | 02B,11M | M-IDX-F01,M-IDX-F03,M-IDX-P01,M-IDX-P02,PX-S11 | D11M,G11M |
| RQ-037 | request-ledger migration仅A3+G07E后的ADR-13条件边 | E23 | 07E,11M-L | M-L-EDGE-S01,M-L-EDGE-S02,M-L-EDGE-S03,M-L-S01,M-L-S02,M-L-F01 | G11M-L-ADR,D11M-L,G11M-L |
| RQ-038 | control缺失/损坏fail-closed，旧heartbeat不串台 | E07,E18 | 05 | S-S11,S-S15,S-S16 | G05 |
| RQ-039 | 120s delay每login/supervisor session只支付一次 | E07 | 05 | S-S13 | G05 |
| RQ-040 | 观察≥2h且连续5成功，失败清窗口 | E07 | 12A | OBS-S01,OBS-S02,OBS-S03,OBS-S04,OBS-S05,OBS-S06 | D12A,G12A |
| RQ-041 | 12A每cycle先密封exact write contract；新文档延后 | E25 | 12A | OBS-W01,OBS-W02,OBS-W03,WRITE-F01,WRITE-F02,WRITE-F03,WRITE-F04 | D12A,G12A |
| RQ-042 | 12B使用全新stage-bound operation/provider/data/cap授权；LLM-off也不是整OP N/A | E13,E21,E29 | 12B | L-S19,PX-S18,GL-F09 | G12B-PRE,D12B-ARM,G12B-ARM,G12B-POST |
| RQ-043 | registry是真atomic create-if-absent与exact conditional delete；ARM前先审补偿，跨资源intent/journal恢复，补偿仅显式OP执行 | E18,E26,E29 | 09P,12B | PX-S09,PX-S16,PX-S17,START-S03,START-S08,START-S09,START-S10 | G09P,D12B-ARM,D12B-RB,G12B-ARM,D12B-CAS,G12B-CAS,G12B-RB |
| RQ-044 | CAS后dormant；ARM/lease分层，无LOGIN_COMMITTED时任何登录零child/egress/write | E26,E29 | 12B | START-S01,START-S02,START-S03,START-S04,START-S05,START-S10 | G12B-CAS,D12B-LOGIN,G12B-RB |
| RQ-045 | login token single-use，取消/崩溃/竞态fail closed | E26 | 12B | START-S04,START-S06,START-S07,START-S08 | D12B-LOGIN,G12B-POST |
| RQ-046 | G12B-POST只到LOGIN_VALIDATED_PAUSED/ON且process0 | E27 | 12B | START-S05,START-S07,ACT-S01 | G12B-POST |
| RQ-047 | D12C先冻结action intent、用户再授权该hash、三人pre/post审；token/control journal恢复，当前session idle，失败显式补偿且保留第三方Run | E27,E29 | 12C | ACT-S01,ACT-S02,ACT-S03,ACT-S04,ACT-S05,ACT-S06,ACT-S07 | D12C,G12C-PRE,G12C,G12C-RB |
| RQ-048 | 每个关键D/G有exact人数/角色/disjoint、机器payload与detached confirmation | 用户澄清,E21,E22,E29 | 全部 | GL-S02,GL-F01,GL-F03,GL-F10,SAFE-S06 | 每个D/G；exact规则见DAG |
| RQ-049 | ledger/schema拒绝伪status/verdict/findings/evidence/node/review | E22,E29 | 00L | GL-S01,GL-S03,GL-F01,GL-F02,GL-F04,GL-F05,GL-F10 | D00L,G00L |
| RQ-050 | validator校验hash-chain/head/DAG/branch/auth/OP/state/rollback/等待 | E22,E23,E29 | 00L | GL-S04,GL-S05,GL-S06,GL-F06,GL-F07,GL-F08,GL-F09,GL-F11,GL-F12 | D00L,G00L |
| RQ-051 | validator在正式ledger前bootstrap并自测；失败不可手改台账 | E22,E29 | 00L | GL-S05,GL-F10,GL-F11,TESTID-S01 | D00L,G00L,D00 |
| RQ-052 | G10C/G10R各有SQL/control/testops三份无未来依赖prompt | E21 | 10 | G10-PROMPT-S01,SAFE-S06 | G10C,G10R |
| RQ-053 | 核心文档/release/authorization漂移使下游失效而非沿用签字 | E17,E21,E22 | 全部 | GL-S06,GL-F10,GL-F11,PX-S04,PX-S14 | 每个G、G10C、G10R |
| RQ-054 | DAG/vectors/registry/catalog是data且各有专用严格instance schema | E22,E29 | 00L | GL-F04,TESTID-S01 | D00L,G00L |
| RQ-055 | 每个OP唯一匹配静态catalog并绑定sealed动态contract与合法授权 | E25,E29 | 09P,production | GL-S04,GL-F09,GL-F12,PX-S05,SAFE-S07 | D09P,G09P、每个生产D/G |
| RQ-056 | 首写前protected journal可恢复、ordinary open零DDL | E25,E29 | 09P,11J | M-COM-S01,M-COM-S06,WRITE-F01,WRITE-F02 | D11J,G11J,G10R |
| RQ-057 | INDEX分支G11A可受界INDEX_REQUIRED但不算性能PASS；G11M后必须恢复正常10秒门 | E02,E03,E14,E23 | 11A,11M | Q-P02,Q-P04,M-IDX-P02 | G11A,D11M,G11M |
| RQ-058 | G12C后每个cycle有新runtime contract并重验auth/cap/journal/write/egress | E13,E25,E29 | 12C,runtime | ACT-S08,ACT-S09,ACT-S10,WRITE-F01,WRITE-F02,WRITE-F03,WRITE-F04 | G12C及每个runtime cycle audit |
| RQ-059 | reviewer独立性严格等于DAG role/cardinality/disjoint，不用自然语言“全新”扩大或缩小 | E21,E22,E29 | 全部 | GL-S02,GL-F03,GL-F10,SAFE-S06 | 每个D/G |
| RQ-060 | ZR1002/ZR1003 baseline保留，但fixture改显式init/upgrade且产品reader零DDL | E30 | 0,02B | M-COM-S05,M-COM-S06 | G00,D02B-NI或D02B-IDX,G02B-NI或G02B-IDX |

## 3. 风险登记

| Risk | 可执行失败模式 | 预防/检测 | 回退/阻断 | Owner Gate |
|---|---|---|---|---|
| RK-01 | SQL修复改变候选/顺序/source freshness | Q-S02,Q-S11,Q-S14,Q-S17 | revert I02A、保持PAUSED | G02A |
| RK-02 | planner换版本/stats后复发 | Q-P01,Q-P02,Q-P03,Q-P04 | block production | G02A,G10C |
| RK-03 | approximate proxy被冒充exact steps | Q-P05,Q-P06,Q-P07 | evidence无效、重测 | G01,G02A |
| RK-04 | ADR前混入另一分支红测或实现 | GL-F06 | invalid ledger/commit | G02B-ADR |
| RK-05 | ordinary open隐式建库/DDL | M-COM-S01,M-COM-S02,M-COM-S06 | fail closed | G02B-NI,G02B-IDX |
| RK-06 | index/request-ledger migration占满卷 | M-IDX-F03,M-IDX-P01,M-L-F01 | 不执行生产OP、PAUSED | D11M,D11M-L |
| RK-07 | checkpoint误跳过未完成root | C-S01,C-S02,C-S13 | per-root due/reconcile | G03 |
| RK-08 | progress handler重入/泄漏 | O-S04,O-S05,O-S10 | rollback/pause | G04 |
| RK-09 | uptime/heartbeat掩盖无成果 | O-S11,S-S02,S-S03 | circuit | G05 |
| RK-10 | 交替failure绕过同签名budget | S-S05,S-S14 | global latch | G05 |
| RK-11 | reset顺带resume/arm | RST-S01,RST-S05,RST-S09 | reset gate FAIL、保持PAUSED | G05Rnn |
| RK-12 | PID reuse/Job Object退化误杀或orphan | S-S10,S-S17 | identity fail closed | G05 |
| RK-13 | scanner以跳目录换速度 | SC-P04,SC-S01,SC-S09 | invalidate G06 | G06 |
| RK-14 | metadata spoof长期未检 | SC-S03,SC-S04 | 30日rehash | G06 |
| RK-15 | parser route缺样本仍启用 | P-FMT00-ROUTE与对应route ID/template | 禁用route或BLOCKED | G06P |
| RK-16 | antiword/parser child pause后残留 | 对应P-PAUSE模板 | kill job/pause | G06P |
| RK-17 | old source artifact抑制/错绑new source | Q-S17,L-S18 | stale+regenerate | G02A,G07E |
| RK-18 | batch/cache跨document错绑 | L-S03,L-S13,L-S14 | reject batch/cache | G07E |
| RK-19 | crash后外部重复请求/计费未知 | L-S20,L-S21 | OUTCOME_UNKNOWN/manual | G07E |
| RK-20 | fallback绕过授权 | L-S15,L-S19 | provider disabled | 每个BP/BF Gate |
| RK-21 | evidence泄密 | SAFE-S09,EV-S01,EV-S02,EV-S03 | P0隔离/轮换 | G08,G09P |
| RK-22 | same-table wrong-PK或net-zero写污染 | PX-S12,PX-S13,CAN-BP-W01 | precommit rollback | 每个A/B Gate |
| RK-23 | 文件覆盖/DB-file crash窗口或journal半写/lazy-create | WRITE-F01,WRITE-F02,WRITE-F03,WRITE-F04 | protected intent/reconcile/pause | G11J、每个写OP、G12A |
| RK-24 | 12A周期中扩展文档或漏合同 | OBS-W01,OBS-W02,OBS-W03 | 整个G12A FAIL | G12A |
| RK-25 | source只有事后sentinel | SAFE-S02,PX-S06 | 无OS deny则BLOCKED | G09P、A Gates |
| RK-26 | verifier自验/可写或check-load TOCTOU | PX-S03,PX-S14,PX-S15 | immutable trust or BLOCKED | G09P,G12B-PRE |
| RK-27 | registry check-then-set或隐式Gate rollback覆盖第三方值 | PX-S16,PX-S17,START-S09 | atomic conflict/显式OP/不碰第三方 | G12B-CAS,G12B-RB |
| RK-28 | CAS后意外登录绕过最终用户批准 | START-S01,START-S02,START-S04 | dormant零启动、conditional rollback | G12B-CAS,D12B-LOGIN |
| RK-29 | token replay/两进程竞争双启动 | START-S07,START-S08 | single-use atomic consume | G12B-POST |
| RK-30 | 12B复用短期LLM授权跑无限backlog | L-S19,PX-S18 | 新12B manifest | G12B-PRE |
| RK-31 | OP12C顺带启动当前session或G12C暗中写回状态 | ACT-S04,ACT-S05,ACT-S06 | OP12C-RB、G12C FAIL | G12C,G12C-RB |
| RK-32 | ledger伪PASSED开放下一边 | GL-F01,GL-F02,GL-F03,GL-F07 | validator非零、BLOCKED | G00L及每次append |
| RK-33 | authored next/错误前驱/分支被信任 | GL-F06,GL-F07,GL-F08 | 只用validator next | G00L |
| RK-34 | reviewer自审、人数/角色不足、payload/confirmation被改 | GL-F03,GL-F10 | gate不成立 | 每个D/G |
| RK-35 | ledger整链被自洽重写 | GL-S05,GL-F11 | external expected-head mismatch | 每次append/next |
| RK-36 | G10 prompt要求未来节点形成伪循环 | G10-PROMPT-S01 | 六prompt输入集合fail closed | G10C,G10R |
| RK-37 | 核心文档在审后变化 | SAFE-S06,GL-F10,GL-F11 | 新manifest/re-review | 每个G |
| RK-39 | 任意N/A或无sealed contract执行生产OP | GL-F09,GL-F12,PX-S05 | validator拒绝、保持PAUSED | G09P、每个生产D/G |
| RK-40 | 12B/12C失败后没有合法写执行者 | GL-F08,GL-F12,ACT-S06,START-S03 | 显式compensation OP→独立G | G12B-RB,G12C-RB |
| RK-38 | A/B最后集中补签 | CAN-A1-S03,CAN-A2-S03,CAN-A3-S03,CAN-BP-S03,CAN-BF-S03 | 每OP后pause+独立G | 每个A/B Gate |
| RK-41 | ARM/control/token/registry/journal半提交后猜测性恢复或覆盖第三方值 | START-S03,START-S09,START-S10,WRITE-F01,WRITE-F02 | ARM前seal RB；intent/finalize+ownership nonce；REGISTRY_CONFLICT | D12B-RB,G12B-RB |
| RK-42 | INDEX分支在建索引前被10秒门死锁，或INDEX_REQUIRED被伪报性能PASS | Q-P04,M-IDX-P02 | G11A受界诊断；G11M后正常10秒复验 | G11A,G11M |
| RK-43 | G12C后第二周期沿用旧合同、过期授权或超cap继续写/外发 | ACT-S08,ACT-S09,ACT-S10 | 每cycle密封+持久cap；失败circuit+pause | G12C及runtime audit |
| RK-44 | verify-only reader修复导致ZR测试失败后恢复产品eager DDL | M-COM-S05,M-COM-S06 | 迁移tmp fixture，不放宽产品合同 | D02B-NI或D02B-IDX |

## 4. 精确 Gate 覆盖

`reviewers`是节点成功时必须恰好存在的独立机器 payload 数；T/I/OP本身不接review verdict。
BF01–BF99与05R01–05R99只实例化实际需要的连续/唯一编号。

| 节点/链 | Requirement重点 | reviewers |
|---|---|---:|
| T00L→D00L→I00L→G00L | RQ-048–056，validator bootstrap | D00L=1，G00L=2 |
| D00→OP00→G00 | RQ-030,048,051,053，正式ledger genesis | D00=1，G00=1 |
| T01→D01→G01 | RQ-001,003,007，baseline-only | D01=1，G01=1 |
| T02A→D02A→I02A→G02A | RQ-001–003,007,023 | D02A=1，G02A=2 |
| G02B-ADR | RQ-004–006，ADR-02 exactly-one | 2 |
| T02B-NI→D02B-NI→I02B-NI→G02B-NI | RQ-004–006 | D=2，G=2 |
| T02B-IDX→D02B-IDX→I02B-IDX→G02B-IDX | RQ-004–006,036 | D=2，G=2 |
| T03→D03→I03→G03 | RQ-008,009 | D=1，G=1 |
| T04→D04→I04→G04 | RQ-010,011 | D=1，G=1 |
| T05→D05→I05→G05 | RQ-011–016,038,039 | D=2，G=2 |
| T06→D06→I06→G06 | RQ-017–019 | D=1，G=1 |
| T06P→D06P→I06P→G06P | RQ-020,021 | D=1，G=1 |
| G07-ADR | RQ-025，ADR-11 exactly-one | 2 |
| T07E→D07E→I07E→G07E | RQ-022–026 | D=1，G=1 |
| T07O→D07O→I07O→G07O | RQ-025,026 | D=1，G=1 |
| T08→D08→I08→G08 | RQ-027–029 | D=1，G=1 |
| T09P→D09P→I09P→G09P | RQ-030–34,38,43,48,54–56 | D=2，G=2 |
| T09→D09→I09→G09 | 所有启用合同E2E与mutants | D=2，G=2 |
| G10C | Core exact join；只授权D11A | 3（SQL/control/testops） |
| D11A→OP11A→G11A | 生产只读对照 | D=2，G=2 |
| D11M→OP11M→G11M | ADR-02=INDEX时的生产索引 | D=2，G=2 |
| D11J→OP11J→G11J | RQ-055,056；首个生产写前journal | D=2，G=2 |
| D11B-A1/A2/A3各自D→OP→G | RQ-030,033,034，逐阶段pause | 每个D=2、G=2 |
| G11M-L-ADR | RQ-037；前驱必须G11B-A3+G07E | 2 |
| D11M-L→OP11M-L→G11M-L | ADR-13=SCHEMA_DELTA时 | D=2，G=2 |
| D11B-BP→OP11B-BP→G11B-BP | RQ-026,034,035 | D=2，G=2 |
| 每个D11B-BFnn→OP11B-BFnn→G11B-BFnn | RQ-026,034,035；nn从01连续 | 每个D=2、G=2 |
| G10R | exact release join显式含still-valid G09P/G09；只授权D12A | 3（SQL/control/testops） |
| D12A→OP12A→G12A | RQ-040,041 | D=2，G=2 |
| G12B-PRE | RQ-032,042；只开放D12B-ARM | 2 |
| D12B-ARM→D12B-RB→OP12B-ARM→G12B-ARM | ARM写前seal补偿；journal intent/finalize；仍PAUSED/OFF | D12B-ARM=2，D12B-RB=2，G=2 |
| OP12B-RB→G12B-RB | ARM后任一失败/lease到期显式回退；G继承OFF或REGISTRY_CONFLICT | G=2 |
| D12B-CAS→OP12B-CAS→G12B-CAS | atomic registry；dormant ARMED_ON_PRELOGIN/ON | D=2，G=2 |
| D12B-LOGIN→OP12B-LOGIN→G12B-POST | fresh用户登录批准；验证后自动pause | D=2，G=2 |
| D12C→用户授权intent hash→G12C-PRE→OP12C→G12C；OP12C-RB→G12C-RB | fresh长期激活、exact pre/post审；失败补偿/冲突终态 | D=2，PRE=3，G=3，RB G=2 |
| G12C后每个runtime cycle | RQ-058；逐cycle contract/auth/cap/journal/write/egress | 依runtime_cycle_policy，不复用G12C报告 |
| 每个D05Rnn→OP05Rnn→G05Rnn | RQ-016；reset-only side lane | 每个D=2，G=2 |

## 5. 机器分支与设计决策

| Decision | 决策节点 | 合法值 | 未选分支处理 | 最迟冻结 |
|---|---|---|---|---|
| ADR-02 | G02B-ADR | NO_INDEX / INDEX | 不创建另一分支任何ledger record | T02B-NI或T02B-IDX前 |
| ADR-11 | G07-ADR | LLM_OFF / LLM_ENABLED | 不创建另一profile链；OFF没有B出边 | T07O或T07E前 |
| ADR-13 | G11M-L-ADR | NO_SCHEMA_DELTA / SCHEMA_DELTA | NO_SCHEMA_DELTA时不创建D11M-L链 | D11M-L或D11B-BP前 |

其他实现选择必须由相应D Gate的evidence manifest冻结，不能另造未登记branch status。

## 6. 维护与机械检查规则

1. 新来源事实若改变计划语义，先建立新plan revision；不要在实施中修改本矩阵。
2. 每个新requirement先分配唯一稳定Test ID或合法template expansion，再为每个ID指定精确
   introduced/variant/red/green/revalidate/condition；禁止group-level笛卡尔推导。
3. `TESTID-S01`必须按冻结active-section extraction grammar拒绝duplicate、undefined、range
   abbreviation、未展开enabled template、禁用ID和历史/示例区误引用。
4. 实际evidence path/hash、review payload、authorization、状态与失效边只进append-only ledger。
5. ledger record不得包含任何authored next字段；只有validator读取DAG后输出临时eligible set。
6. source/config/release/auth/write contract/control generation漂移必须追加INVALIDATED/supersedes，
   不能覆盖旧记录或沿用旧review。
7. 任一P0/P1必须由对应独立reviewer在冻结revision上明确CLOSED；修订者不能自签。
8. prose与DAG/schema/registry不一致时fail closed并创建新revision；弱模型不得自行“择一理解”。
