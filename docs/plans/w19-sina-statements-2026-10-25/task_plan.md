# W19 执行计划

状态：IN_PROGRESS（A节点）。唯一入口START_HERE.md，细则inputs/construction_card.md，勘察结论findings.md。

| 节点 | 任务 | 状态 |
|---|---|---|
| A | 两仓基线/接口/真实响应核对、中性与真实夹具RED、BJ能力小样本 | in_progress |
| B | provider/normalize、CWP原件/两表/公共query、FF CLI/SKILL | pending |
| C | 迁移/离线及真实E2E、官方逐值对照、空间/清理、独立终审全修复、交接 | pending |

## A 细化（TDD冻结）

- [x] 双仓基线/branch/tracked-clean 核对（CWP a3083502/243993d2、FF c8b0e40/e0d9642，均 clean）
- [x] AGENTS/START_HERE/施工卡/研究材料/CMMON 阅读
- [x] 18份夹具解压SHA与observations.json逐条核对（18/18 OK）
- [x] CWP接缝勘察（store迁移/canonical_writer/识别/budget/bounded_http/SourceRef/测试先例）
- [x] FF接缝勘察（fetch_filing流程/config/transport/envelope/测试先例/SKILL结构）
- [ ] RED-1 normalize 纯函数（真实夹具：Decimal/null/空串/分组行/ps4/EPS/period_kind/consolidation/pointer/hash；负例：非法数值保留raw、缺report_list、report_count不一致）
- [ ] RED-2 provider 分页（max_pages/重复页/无进展/count变化/403/429/预算中停/HTTP200无data=null 区分 not_found vs 终点）
- [ ] RED-3 repo 幂等/迁移（fresh/1.0/1.1/1.2→1.3、旧数据保留、未知版本fail-closed、并发双初始化、故障rollback、只读查询不建库）
- [ ] RED-4 FF→CWP 契约（请求schema校验/intent/limits互斥/all_history、响应schema、fake CWP子进程）
- [ ] RED-5 canonical_writer 第三方数据集入口（多期间、provider≠official、dedup、provenance）
- [ ] BJ 有界真实样本（1请求）或 named capability gap
- [ ] 记录真实RED输出（fixture坏不能冒充RED）

## B 细化（唯一owner实施）

顺序：contracts/normalize → sina_provider → schema/store迁移+writer入口 → repository/service → cli → FF fetch_statements+SKILL。
- [ ] CWP `source_catalog/financial_statements/{__init__,contracts,normalize,sina_provider,schema,repository,service,cli}.py`
- [ ] store.py/models.py 1.3.0迁移（两表DDL+索引+upgradeable加1.2.0）
- [ ] canonical_writer.import_third_party_dataset_staged + document_kinds 登记 + _destination_subdirectory
- [ ] FF `scripts/fetch_statements.py` + `ff_financial_statements.py`（复用 ff_configuration/ff_process_transport）
- [ ] FF SKILL.md 路由（要三表数值→fetch_statements；原件→fetch_filing）
- [ ] 单公司lookup一次/第二请求0HTTP/原件移根复用集成例

## C 细化（集中验证+终审）

- [ ] 单元：数字/单位/空值/三表科目/期间/PIT/Pointer/同键修订/分页异常/预算/响应过大
- [ ] 集成：迁移矩阵/并发/rollback/双根SourceRef/字节损坏/缺表0写/重放0网络/同内容不重复/不同内容保留版本/不进叙述worker
- [ ] 离线E2E：真CLI进程 FF→CWP→冻结响应→canonical→两表→query→FF JSON；中微36/33/36+9729源行对照；重复请求0HTTP；一表失败两表可读partial；范围/行过滤/continuation；严格过去as_of拒绝PIT
- [ ] 真实有界E2E：中微+非工业主体（可小范围）+另一SZ/BJ泛化；≤50请求/20MB/300s；官方原件逐值对照三表各≥2项（expected/actual/locator）
- [ ] 空间测量：全历史原件+SQLite增量≤16MiB；重复请求零增长；fixture≤2MiB/日志≤5MiB
- [ ] 环境恢复收据；Ruff/mypy/hooks
- [ ] 独立agent终审（真实运行链路+反例突变），全部finding根修复审
- [ ] delivery/w19/handoff.md+json（按模板），commit/push作者分支

## Next Step

写 RED-1..5 测试文件（CWP tests/financial_statements/、FF tests/financial_statements/），跑出真实RED并记录。
