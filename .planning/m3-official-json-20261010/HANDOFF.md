# M3-JSON 独立施工线交接（HANDOFF.md）

## 1 实际状态

- lane_id：M3-JSON；owner：Hermes Agent（外部 harness 接管）；接管时间：2026-10-10。
- 原内置 agent 已 terminal errored 的事实：实查无源码更改，只留下 `docs/plans/cross-market-rf-e2e-2026-10-08/phase6/m3_root_implementation_2026-10-10/W02/` 的计划（三文件已作为历史 seed 复制并保留，未清理全工作树）。
- 自己的 PWF 路径：`C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki/.planning/m3-official-json-20261010/`（PLAN_ID=m3-official-json-20261010，只维护本 PWF，旧 W02 目录只读）。

Repo（company-wiki，唯一）：

| 项 | 值 |
|---|---|
| worktree | `C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki` |
| branch | `codex/m3-official-json-20261010` |
| base | 3c791e3c2a16c12627cc25d0bd8681cc9458e48b |
| head | 8abfad074057ff8d5c89e01aea8f87a73be5405f |
| remote branch | origin/codex/m3-official-json-20261010（新建） |
| remote head | 8abfad074057ff8d5c89e01aea8f87a73be5405f |
| exactCI | **not_available**：ci.yml 仅 master push/PR 触发，codex/* 分支推送无 workflow（证据：`.github/workflows/ci.yml` 触发集；GitHub commit status API 对 8abfad07 state=pending total=0、check-runs 空）。本地 pre-push 门跑了受影响套件：2637 passed（logs/normal-push.log）。MAIN 大节点经 PR 上主线时再观测精确 CI。 |
| ci_head | null（无 CI run） |

git status 解释：提交 8abfad07 覆盖本卡写集（9 个 runtime 源文件 + 4 个专属测试 + PWF/seed/日志等非 runtime）。提交后仅剩两个未提交证据文件：`logs/normal-commit.log`（空——首次失败尝试的内容被重跑截断覆盖，成功时 pre-commit 钩子静默；该文件在 commit 里的 blob 是失败尝试的钩子输出，故其 worktree byteSHA≠git blobSHA，含义不同）与 `logs/normal-push.log`（push 门输出，随后提交）。生产配置未动（baseline_shas.txt 对照）。

状态分列：

- **package 工程范围：complete**（责任测试 107 全绿、相关回归 173 全绿、ruff/mypy 受改范围 0 error、冻结 86 页锚点复现）。
- **共享 MAIN 接线：pending**（automation/* 为 MAIN 保留文件，本线未触碰；接线包与最小 patch 见 INTERFACE_CHANGE.md §2）。
- **真实公司/研究：not_run**（本卡不跑收入预测/研究模型；三仓真实大节点归 MAIN）。

## 2 需求与根因

冻结卡：`phase6/m3_parallel_handoff_2026-10-10/official_json_projection.md`；根调查：`m3_source_research_2026-10-09/official_json_source_root/DATA_CONTRACT.md`（SHA 2d80afee…）与 `JSON_EVIDENCE_INDEX.json`（SHA 4969a523…），两 SHA 与卡一致，已完整阅读。

实际反例（全部进测试固定）：

1. 封存 run 86 页 668,749 bytes / 257 条记录 / 目标 24 条——原页不是单一公司；旧 importer 按单电话会 content 校验拒绝分页页（RED：`invalid_text_original`，logs/red_public_cli_import.log）。
2. latest-01 `/datas/0/records/2` = 2508409 清溢（activityCompanyId 57808）；2508385 中微在 latest-18 同 pointer——测试 `test_documented_wrong_pointer_stays_the_other_company` 固定此错误定位不被冒充。
3. precollect-10 `/datas/0/records/1` ID36395 answer 非空、无回答人字段——投影中 `answer_first_publication_known=false`、`speaker_known=false`，时间字段（crtTime/updTime）原值分别保留不互换。

改的责任层：MIME admission 的电话会结构条件（新增通用结构 parser + 声明式布局，不按公司/页号硬编码）、单 issuer 存储意图（共享 `_shared` 源导向存储 + typed source subject，不伪造 owner）、以及消费身份分离（投影显式版本，SourceRef2.0 继续绑定整页 raw）。对另一公司/布局的通用性由第二声明布局 `official-flat-list` 的未见夹具测试与 issuer-agnostic 分类规则证明。

哪些旧工程接受有效且未重做：旧单 content JSON transcript 合同（transcript-original-json/1.0.0）、manifest 1.0.0、SourceExport v1/v2.0.0、TXT/FMP 电话会路径全部原样通过（173 回归绿）。

设计偏差（诚实列出）：

- 投影选择层简化：`record_created_date` 取自 `crtTime`（缺则 created_at）；DATA_CONTRACT 要求"不同字段时间含义不混淆"，实现将原字段值全部保留在 `times` 且 `answer_first_publication_known=false`，但 as-of 资格判定目前只用创建时间，未区分 updTime 修订语义——已列 remaining。
- manifest 2.0.0 未注册进 packaged compatibility policy（需要 MAIN 的版本发布动作，见 §7）。
- AUTO 未接线（排他写集外，交 MAIN）。

## 3 源码与接口

全部 changed file 与 byteSHA/git blobSHA/runtime/reason 见 `handoff.json.repos[0].changed_files`。runtime=需要安装的运行时文件共 9 个：

| 文件 | 作用 |
|---|---|
| source_catalog/official_json_structure.py | cwp_json_structure_parser/1.0.0：RFC6901 pointer、token/body 双区间与双 SHA、UTF-8/escape/surrogate/dup-key/finite/depth-node-string-byte-deadline 限额 |
| source_catalog/official_json_layout.py | official-json-layout/1：注册布局 paged-qa/flat-list、envelope/pagination/issuer/text/time/state 观测、classify_record |
| source_catalog/official_json_subject.py | typed source subject + official-source-import-request/2 校验 |
| source_catalog/official_json_import.py | /2 入库（共享 raw、error envelope/语法失败留 capture、恢复入口） |
| source_catalog/official_json_projection.py | source-projection-ref/1：build/persist/load/replay/export、EvidenceSpan 绑定 |
| source_catalog/official_source_cli.py | CLI：import /2 分发 + project/read/replay/export 操作 |
| source_catalog/official_source_flow.py | staging/journal/recovery 的 /2 分发与容缺 |
| source_catalog/canonical_writer.py | _SharedOriginal/_SharedImportIntent/import_shared_original_staged、共享 _destination |
| source_contract/source_manifest.py | SourceSubjectManifest 2.0.0 |

runtime 安装：CWP 代码无需技能整仓复制；消费者仅 export/parser 接口改动文件。新 DTO request/response JSON、版本/兼容/unknown 语义、入口、MAIN 最小 patch 与测试命令全部在 **INTERFACE_CHANGE.md**。

## 4 测试证据

完整 argv/cwd/UTC/exit/collected 结果与日志 SHA 见 `handoff.json.tests`（11 项，RED/GREEN/STATIC/COMPATIBILITY）。要点：

- RED：parser/contract 新模块缺失（诚实产品 RED）；公共 CLI 对 sealed latest-01 exit 2 `invalid_text_original`（与根调查 §6.2 预期一致）；integration 9 failed/1 passed（链未实现，v1 兼容基线已绿）。
- GREEN：57 unit + 26 contract + 13 frozen-page + 11 integration = 107（最终命令与卡一致：`python -X utf8 -B -m pytest -q tests/unit/test_m3_official_json*.py tests/contract/test_m3_official_json*.py tests/integration/test_m3_official_json*.py`）。
- 兼容回归 173 passed（capture recovery / official source flow / manifest contract / transcript layouts / source reader / export v2）。
- 单元（纯 parser）、集成（TEMP catalog 公共链）、公共 CLI（子进程）、冻结真实页（只读）分别标注 scope，未混同；loopback 协议测试未使用（本卡 0 模型）。
- 实际新增 provider/model calls：**0**；token/cost：**0**；不从预算 cap 推算。旧 unknown（provider 时区、answer 首发时刻、companyfilter）保持未知，未补造。

## 5 隔离与恢复

- 所有测试夹具为 pytest tmp_path / tempfile.TemporaryDirectory 独占 TEMP 根，结束自动清理；手工 RED/CLI 脚本同样用临时目录。初始不含的下载/派生文件随根删除；无初始文件被改写。
- 封存 run 全程只读：冻结页测试只读验证 86 页 SHA/字节数（668,749）与锚点；集成测试只经公共 importer 在 TEMP 落 4 页副本，其余 82 页只读，未复制整库。
- 生产配置保护：`config/source_catalog.yaml`、`config.yaml` 前后 SHA 未变（baseline_shas.txt；git status 无 config 变更）。
- 恢复证明：`test_import_v2_failure_retains_capture_and_recovers`（copyfile 故障注入后 recover_official_source 完成 /2 导入）与 `test_invalid_json_is_retained_but_not_indexed`（语法失败留 capture 可查）。空间预算失败不发布半结果由 `_persist_completed` 先于 staging 清理的既有顺序保证（沿用 v1 结构）。

## 6 提交/推送/安装

- normal commit：8abfad074057ff8d5c89e01aea8f87a73be5405f，exit 0；pre-commit 钩子全过（含 FC-1307-a host assumption guard——4 个测试文件的宿主机绝对路径已改为 Path.home() 拼接+M3_SEALED_RUN 环境变量覆盖，guard new=0）。commit 日志见 logs/normal-commit.log（空=钩子静默；见 §1 说明）。
- normal push：exit 0，`* [new branch]` 建立 origin/codex/m3-official-json-20261010；pre-push 门 2637 passed → logs/normal-push.log。
- remote exactSHA=8abfad074057ff8d5c89e01aea8f87a73be5405f=local head。CI 见 §1（not_available by trigger design）。
- 安装：未执行全仓覆盖或拷贝真实材料；MAIN 用 changed runtime 闭包（9 个源文件 + 4 测试）。
- 是否已经并主线：**false**（施工 harness 默认；分支待 MAIN 集成与 PR）。

## 7 剩余与 MAIN 接线

工程未完成：无（本卡范围 complete）。

共享 consumer 待接线（MAIN，INTERFACE_CHANGE.md §2，必须重跑的确切测试包）：

1. `automation/narrative_formats.py` 新增 `official_json` source class；`narrative_select/replay` JSON route（调用 `replay_projection`）；`NarrativeBatchRequest` 去重键 source+projection identity；generation 绑定 parser/adapter/projection/as-of。
2. MAIN 大节点必跑：`python -X utf8 -B -m pytest -q tests/unit/test_m3_official_json*.py tests/contract/test_m3_official_json*.py tests/integration/test_m3_official_json*.py` + `tests/contract/test_official_capture_recovery.py tests/integration/test_official_source_flow.py` + AUTO 各套件 + 三仓真实大节点。
3. packaged compatibility policy 注册决策（manifest 2.0.0 / projection / projection-export）。

外部客观未知（单列，不猜参数发公网）：server companyfilter 存在性/真实字段、provider 时区语义、answer 首次公开时刻与历史修订接口、跨公司 Q/A 真实案例、第二真实官方布局。

真实研究待验：三公司四独立审查、收入预测消费端验证（本卡 0 模型 0 费用）。
