# Progress — M3-USAGE lane

## Session 2026-10-10 (harness takeover)

接管事实：前内置 agent terminal errored，无源码修改。三仓工作树复用，未新建克隆。

三仓初始状态（接管时实测）：
- CWP  HEAD=3c791e3c2a16c12627cc25d0bd8681cc9458e48b branch=codex/m3-acquisition-usage-20261010
  status: ?? docs/plans/cross-market-rf-e2e-2026-10-08/phase6/m3_root_implementation_2026-10-10/（W06 前期骨架 docs，非本线改动，保留不动）
- FF   HEAD=41ba0150c9c634f6021c9346744cada391ec2c4c 同 branch，clean。
- RF   HEAD=0c248d9a07a2dd7a2c756946d88507479d5e9d15 同 branch，clean。

主 RF assurance/output 与主 FF FMP key 未提交内容：不在本工作树范围内（worktree clean），未触碰。

PWF 建立：CWP 本目录（seed 来自 W06 骨架三文件，骨架无实质内容）；FF/RF 各自 .planning/m3-acquisition-usage-20261010/ 已建。

Phase 1 开始：CodeGraph consumer map + 源码定位。

Phase 1 完成：三 Explore agent 消费方映射 + 本人精读 CWP(acquisition_service/download_budget/source_operation/operation_projection/operation_contract/acquisition_failure/bounded_http/adapter_process/dayu_sdk_cli/error_taxonomy/cli 关键段)、FF(ff_v2_envelope/fetch_filing 关键段)、RF(三仓E2E模板)。要点已入 findings.md。
Phase 2 完成：INTERFACE_CHANGE.md 已冻结（acquisition-observation/1 sibling；wire/entity 分键；cost null=未知；MAIN patch=error_taxonomy 3行；cli.py 无需改）。
关键接缝确认：FF _validated_operation 是子集校验(925行 set(payload) <= FIELDS)——新键向后兼容；CWP conftest 只封 connect/create_connection，loopback server bind 可行；provider 客户端在真实子进程无封锁；FF e2e_support.isolated_wiki 是三仓 E2E 脚手架（PRODUCTION_WIKI 可 monkeypatch 指向本工作树）。

Phase 3 完成（RED→GREEN）：
- RED：git stash src 全部 producer 改动，在 base 上跑 tests/integration/test_m3_acquisition_usage_cwp.py，9/9 因 KeyError acquisition_observation 失败（产品原因）；日志 red_cwp_integration.log。中途夹具三修（HK/US 槽须 dayu 接口、runner 容忍模块缺失、.bin→.txt 扩展名、launch-fail 用缺失可执行）。
- GREEN：producer 全量实现（新 acquisition_observation.py + 7 文件接线）。绿后 10 集成 + 39 单元全过。
- 责任回归 146/146 绿（8 个既有套件+2 新套件）；日志 cwp_responsibility_regression.log。

关键契约修正（既有 pin 胜过我的假设）：
1. test_no_target_execution_evidence_stays_unknown_not_zero[oserror-None]：裸 OSError 可能是执行后清理，必须保持 provider_started=None/usage=None；已回退我的 OSError synthetic-zero 分支。typed never-started 零证明唯一来源=cause.provider_started=False（run_json_process 预检超时/进程树建立失败）。
2. cost_reported 语义：provider 费用回执才标记费用已观察；synthetic zero（CWP 自证未启动）只证字节计数，不标记/不清除费用回执（cost_observed 参数）。
3. 计数总是发布观察值，完整性由 *_complete 承载（false=下界，null=不可测）；legacy 回执无交换数→complete=None 而非编造。
4. 无效 cost 字符串整体拒绝 DTO（fail-closed），只有显式 null=未知。

Phase 4-8 完成：
- FF GREEN：4 文件（ff_provider_cause 校验器+4tuple诊断、filing_contracts 错误属性、ff_v2_envelope 顶层 sibling、fetch_filing 接线）；21 新测试 + 167 回归绿。
- RF GREEN：3 文件（filing_upstream_cause 投影、filing_fetch_client、source_preparation）；19 新测试 + 187 回归绿。
- 公共 E2E 2/2：真实子进程 source_preparation→filing_fetch_client→fetch_filing→CWP CLI→loopback provider。us_download（3 exchanges/wire 191<entity 4553/cost 0.0009）、us_reuse（0 body GET）、cn_download（第二市场）、us_missing（RF exit 3 携带完整观察）。argv/stdout/stderr/exit 全存 e2e_logs/。
- 控制矩阵落点：第二市场（E2E CN + CWP integration market-cn）；reuse 0GET（CWP+E2E）；pre-launch（CWP 单元 typed zero + integration missing-exe 未知 + 预算门 0 交换）；mid-body 截断/timeout（CWP integration）；未知费用（CWP integration/unit cap0≠fee0）；metadata 错误（CWP integration 500）；cleanup secondary（既有 pinned 回归绿）。
- RED 证据：red_cwp_integration.log（9 失败 KeyError）、red_ff_projection.log（21 失败）、red_rf_projection.log（15 失败）。
- 恢复：restore_receipt.json（生产 config 双树同 SHA 3d159a4e…、三仓 status 逐项解释、TEMP 全部 TemporaryDirectory 收敛）。

设计定稿（E2E 教训）：acquisition_observation 放 v2 envelope 顶层（与 calls/downloads 同为 operation 级账目），
filing 保持闭合形状——RF company_wiki_source_v2 严格 8 键 source_candidate 合同零改动通过。

MAIN 接线清单（不混入本线 commit）：
1. CWP error_taxonomy.structured_error 3 行（发布异常 acquisition_observation 到 stderr）。
2. FF tools/ci_tests.py CI_TESTS 加 tests/test_m3_acquisition_usage_ff.py。
3. source_catalog/cli.py 总入口无需改动（观察经 to_dict+facade 随 --source-ref-v2 出口）。
