# M3-USAGE 交接（lane_id=M3-USAGE）

> 本文件 + handoff.json + INTERFACE_CHANGE.md + RED/GREEN 原始日志 + restore_receipt.json
> 均在本目录（CWP 工作树 .planning/m3-acquisition-usage-20261010/）。FF/RF 各自
> .planning/m3-acquisition-usage-20261010/ 有独立子仓步骤记录。旧 W06 docs 记录只读保留。

## 1 实际状态

lane_id=M3-USAGE；owner=harness agent（外部接管，前内置 agent terminal errored、无源码修改）；
接管时间 2026-10-10。唯一总执行 PWF=本目录（PLAN_ID=m3-acquisition-usage-20261010）。

| repo | worktree | branch | base | head | push | exactCI |
|---|---|---|---|---|---|---|
| company-wiki | C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/company-wiki | codex/m3-acquisition-usage-20261010 | 3c791e3c2a16c12627cc25d0bd8681cc9458e48b | d65e421cbd48e4f8622b5af19b9239ef0a878d8e | pass | not_available（ci.yml 仅 master 触发，codex/* 无 run）|
| filing-fetch | .../filing-fetch | 同 | 41ba0150c9c634f6021c9346744cada391ec2c4c | f0f4e36319d6b3afc17e896f12a2aa1b183894b0 | pass | pass（quality@exact head success）|
| revenue-forecast | .../revenue-forecast | 同 | 0c248d9a07a2dd7a2c756946d88507479d5e9d15 | 741f7c01fc2e13d42f919aa0fc8053eb8cabfe08 | pass | pass（quality@exact head success）|

git status 逐解释：CWP 仅剩未跟踪 docs/plans/cross-market-rf-e2e-2026-10-08/phase6/
m3_root_implementation_2026-10-10/（接管前即存在的 W06 seed 文档，按卡片只读保留，不入本线 commit）；
FF/RF clean（只含本线 source/tests/.planning 记录）。主 RF assurance/output 与主 FF FMP key
未提交内容不在本工作树范围，未触碰。

状态分列：
- package 工程范围：complete（三仓 RED→GREEN、控制矩阵、E2E、恢复、提交/推送）。
- 共享 MAIN 接线：pending（patch 清单见 §7；未在共享入口/主线执行）。
- 真实公司/研究：not_run（0 公网 provider/模型/费用；真实大节点由 MAIN 核对）。

## 2 需求与根因

冻结卡：m3_parallel_handoff_2026-10-10/acquisition_usage_chain.md；根 R11 / W06。实际反例：
CWP 成功路径完全丢失已观察下载开销（usage 只在失败回执出现）、adapter 回执里的 wire/交换数
在父进程边界被丢弃、FF v2 成功 filing 无任何 usage 字段、RF 成功侧无 acquisition_usage 提取。

改的责任层：CWP producer（operation 范围预算观测）→ FF（保真投影）→ RF（保真传递）。
对另一公司/布局成立的原因：全部经真实 CLI 子进程 + 既有 AcquisitionBudget 累积语义，
loopback 夹具覆盖 US/CN 两市场、gzip wire<entity、多 invocation 累积；与公司身份/布局无关。

旧工程接受有效且未重做：RC14 limited cause/metadata diagnostics、W08 failure usage continuity、
error-taxonomy 1.1、golden 形状。设计偏差（相对初稿）：观察 DTO 从 filing 内改放 v2 envelope
顶层——RF company_wiki_source_v2 的严格 8 键 source_candidate 合同（非本线写集）在 E2E 实测
拒绝 filing 新键；顶层 sibling（与 calls/downloads 同为 operation 级账目）使该合同零改动通过。
INTERFACE_CHANGE.md 已同步。

## 3 源码与接口

新 DTO：acquisition-observation/1（闭合 12 键，usage_scope=operation，详见 INTERFACE_CHANGE.md §1）。
wire_body_bytes=已观察响应正文 wire bytes（transfer-decode 后、content-decode 前，不含头/TCP/TLS）；
entity_body_bytes=已观察解压/实体字节（旧 1.0 response_bytes 语义）；cost_usd=null=未知（无回执），
cap0≠fee0；http_exchanges 计收到响应的交换数；*_complete 三态承载完整性（false=下界，null=不可测）。

changed runtime 文件（runtime=true，供 MAIN 定点安装；byteSHA/blobSHA 见 runtime_file_closure.json）：
- CWP：acquisition_observation.py（新）、acquisition_failure.py、acquisition_service.py、
  adapter_process.py、bounded_http.py、dayu_sdk_cli.py、download_budget.py、source_operation.py
- FF：fetch_filing.py、ff_provider_cause.py、ff_v2_envelope.py、filing_contracts.py
- RF：filing_fetch_client.py、filing_upstream_cause.py、source_preparation.py

测试文件（runtime=false）：CWP tests/unit/test_m3_acquisition_usage_observation.py +
tests/integration/test_m3_acquisition_usage_cwp.py；FF tests/test_m3_acquisition_usage_ff.py；
RF tests/test_m3_acquisition_usage_rf.py + tests/test_m3_acquisition_usage_e2e.py。

消费者路径：CWP SourceEnsureResult.to_dict / operation facade（--source-ref-v2）→ FF
_validated_operation/handle/gap → v2 envelope 顶层 → RF resolve_filing_result 原样 /
failure_observation → _ClientError / FilingSourcePreparationError → 两 CLI stderr 文档。
MAIN 最小 patch 与测试命令：见 INTERFACE_CHANGE.md §6.3。

## 4 测试证据

每行：argv/cwd/exit/日志+SHA 见 handoff.json tests[]（原日志在本目录）。
- CWP RED（base）：9 failed，全部 KeyError 'acquisition_observation'（产品原因：base 无观察通道）。
  期间夹具修复不计入产品 RED：HK/US 槽接口、runner 容忍、扩展名、launch-fail 可执行。
- CWP GREEN：146 passed（20 新 + 126 责任回归）。单元/集成/loopback 协议分开标注；loopback 只绑
  127.0.0.1 且拒绝非本地 peer；provider 是真实子进程，gzip wire 78B < entity 9472B。
- FF RED（base）：21 failed（无 sibling 校验/投影）；GREEN 167 passed（21 新 + 146 回归）。
- RF RED（base）：15 failed / 4 passed（无投影）；GREEN 187 passed（19 新 + 168 回归）。
- 公共 E2E（GREEN，public_cli scope）：2 passed。真实子进程 source_preparation.py →
  filing_fetch_client.py → fetch_filing.py → company_wiki.source_catalog.cli → loopback provider。
  us_download：3 exchanges、wire 191 < entity 4553、cost "0.0009"、download_events 1；
  us_reuse：0 body GET、download_events 0；cn_download（第二市场）同语义；us_missing：RF exit 3
  携带完整观察（2 metadata exchanges、cost "0.0003"）。stdout/argv/exit 全存 e2e_logs/。
- 真实新增 provider/model calls/token/cost：0/0/0/0（工程包默认 0，不从预算 cap 推算）。
  旧 unknown 保持原未知（7 旧未知模型 + 1 旧 FF 未知采集不回填）。

## 5 隔离与恢复

owned TEMP=pytest tmp（TemporaryDirectory 上下文收敛）；loopback server 127.0.0.1 临时端口、
fixture 收尾 shutdown。restore_receipt.json：生产 config/source_catalog.yaml 主/工作树同
SHA-256 3d159a4e…（conftest production_config_integrity 全程断言）；三仓 git status 逐项解释；
companies/raw/key/config 未写入任何测试原件。未恢复项：无。

## 6 提交/推送/安装

- CWP commit d65e421c（正常 hooks 过：ruff/mypy/config-doctor/host-guard）→ push 新分支。
- FF commit f0f4e363（hooks 过）→ push。RF commit 741f7c01（hooks 过）→ push。
- exactCI：FF/RF quality@exact head success；CWP ci.yml 仅 master 触发 → not_available
  （exact_ci_observation.json）。raw 日志/观测在本目录。
- 安装闭包：runtime_file_closure.json（15 个 runtime 文件 byteSHA+git blobSHA）仅供 MAIN
  定点安装；未执行全仓覆盖或拷贝真实材料。是否并主线：false（施工 harness 默认）。
- 本 HANDOFF 记录为 CWP 上述 commit 之后的 docs commit（SHA 见 git log 与会话报告），
  handoff.json 的 repos[].head 为上述代码集成 head。

## 7 剩余与 MAIN 接线

工程未完成：无（工程包 complete）。
外部客观未知：真实 SEC/ET/官方源公网费用与行为（本线 0 公网调用）；旧 7+1 unknown 不核销。
共享 consumer 待接线（MAIN patch，均已列入 INTERFACE_CHANGE.md §6 与 handoff.json remaining）：
1. CWP error_taxonomy.structured_error 3 行（硬失败 stderr 发布观察；否则硬失败通道无观察，
   returned-gap/operation 通道今日已工作）。
2. FF tools/ci_tests.py CI_TESTS 加 tests/test_m3_acquisition_usage_ff.py。
3. source_catalog/cli.py 无需改动。
真实研究待验：真实三公司大节点（MAIN 负责），本线不宣称已运行。

MAIN 大节点必须重跑的确切测试包（INTERFACE_CHANGE.md §6.3）：
- CWP：python -X utf8 -B -m pytest -q tests/unit/test_m3_acquisition_usage*.py
  tests/integration/test_m3_acquisition_usage*.py + 8 受改责任套件
  （test_acquisition_failure_diagnostic / test_acquisition_usage_recovery /
  test_adapter_process_budget / test_acquisition_failure_return_paths /
  test_acquisition_failure_cli_e2e / test_dayu_sdk_fetch / test_bounded_http /
  test_acquisition_budget）。
- FF：python -X utf8 -B -m pytest -q tests/test_m3_acquisition_usage*.py
  tests/test_failure_usage_continuity.py（+ CI_TESTS 既有列表）。
- RF：python -X utf8 -B -m pytest -q tests/test_m3_acquisition_usage*.py
  tests/test_source_failure_observations.py。
- 公共链：FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT 指向集成树后跑
  RF tests/test_m3_acquisition_usage_e2e.py（argv/stdout/exit 自动落 M3_E2E_LOG_ROOT）。
