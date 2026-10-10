# M3-JSON progress

2026-10-10（W02 seed，保留）：已创建专属 worktree，HEAD=3c791e3c2a16c12627cc25d0bd8681cc9458e48b，branch=codex/m3-official-json-20261010。已读冻结 W02/INTERFACES/task_plan/DATA_CONTRACT 与证据索引。

2026-10-10 接管会话（外部 harness）：

1. 建立本 PWF（seed 复制自工作树内 untracked W02 目录；主项目路径不存在该目录——已记录）。PLAN_ID=m3-official-json-20261010，active plan 已设置。
2. 核验 DATA_CONTRACT/JSON_EVIDENCE_INDEX SHA 与卡一致；sealed run 135 文件只读确认；读取三流代表页字段（envelope success/message/code/datas；datas[0]{records,total,size,current,pages}；记录 ID 字段 `id`）。
3. Consumer map 完成（findings.md）：SourceRef2.0/SourceVersionReader/SourceRequest/CanonicalSourceWriter/official_source_flow/CLI/manifest1/EvidenceSpan/export v1+v2/compatibility/transcript 单 content 合同；实体行来自 scanner `_infer_company`（路径推断）+security_master issuer index（catalog_dir/security_master/{cn,hk,us}.json，canonical_name/aliases/ticker）→ 共享页放 company_root 下非公司命名目录不会获得实体行，投影用 security_master 做 issuer 证明。
4. 基线 SHA：config/source_catalog.yaml、config.yaml → baseline_shas.txt。
5. 阶段2 RED：tests/unit/test_m3_official_json_parser.py 57 项（ModuleNotFoundError 收集失败=新模块诚实 RED）→ logs/red_unit_parser.log（sha 83691c53…）。公共 CLI RED：sealed latest-01 经现行 import → exit 2 `invalid_text_original` → logs/red_public_cli_import.log（sha 2697daca…），argv 完整保存。
6. 实现 src/company_wiki/source_catalog/official_json_structure.py（递归下降、BOM/UTF-8、duplicate key 解码判重、NaN/±Infinity/1e999、lone surrogate、控制符、escape、depth/node/string/source/deadline 限额、RFC6901 pointer、token/body 双区间、双 SHA、locator cwp-json-pointer/1、decoded_slice）。
7. 阶段2 GREEN：57 passed（1.33s）→ logs/green_unit_parser.log（sha d7657fb7…）。冻结锚点（latest-01/18、questions-01、precollect-10 的 token/body 区间与 SHA、answer 先于 question 字节序）全部按证据索引复现；两处测试常数为本人转录笔误已按证据文件 grep 修正（d87c…6569a6cec…、e19d…0addb7…）。
8. 阶段1+2 完成。下一步：阶段3 布局注册 + source subject + projection DTO 的 contract RED。

2026-10-10 接管会话（续，阶段3-7）：

9. 阶段3 RED：tests/contract/test_m3_official_json_contract.py 26 项（ModuleNotFoundError RED → logs/red_contract_layout.log sha e120f637…）。实现 official_json_layout.py（声明式布局注册 paged-qa + flat-list、classify_record、envelope/pagination/issuer/text/time/state 观测、fingerprint）、official_json_subject.py（source_subject/import-request/2 校验）、official_json_projection.py（build/projection_from_dict/canonical hash）、source_manifest.py 增 SourceSubjectManifest 2.0.0。GREEN 26 passed → logs/green_contract_layout.log sha c8f699b5…。
10. 阶段4-6 RED：tests/integration/test_m3_official_json_projection.py（9 failed 1 passed→ logs/red_integration_chain.log）。实现：canonical_writer.py 增 _SharedOriginal/_SharedImportIntent/import_shared_original_staged/共享 _destination/provenance 无 owner 分支；official_json_import.py（/2 入库+retain 失败+recover+error envelope 拒业务）；official_source_flow.py（_journal 容缺 source、_load_retained/_import_retained /2 分发、_persist_completed/_replay_completed /2 附件）；official_json_projection.py 增 build_projection_from_refs/persist/load/replay/export/evidence_span_for_field；official_source_cli.py 增 import /2 分发 + project/read/replay/export 操作。修复：cleanup_staged 双删、layout parse_status 键名、error 字段类型化判定、request_list 破损态守卫、CLI read bytes 直写。GREEN 10→11 passed（含多页 pagination partial 诚实）→ logs/green_integration_chain.log。
11. 冻结页只读验证 tests/contract/test_m3_official_json_frozen_pages.py：86 页全部 parse+layout、总字节 668,749、三流 65/11/10 页 195/33/29 记录、target 24/other 231/unattributed 2（与 JSON_EVIDENCE_INDEX 独立复算一致）、4 代表页 SHA、3 个 500 control response_is_error、36395 答复/时间、latest-01 records/2=2508409 清溢定位反例。
12. 兼容回归：test_official_capture_recovery + test_official_source_flow + test_source_manifest_contract + test_official_transcript_layouts + test_source_version_reader + test_source_export_v2 = 173 passed → logs/green_regression_related.log（期间发现并修复 request_list 回归）。
13. 静态：ruff（src 全部 + 4 测试文件）0 error（auto-fix 6 处 unused import）；mypy 新模块+CLI+manifest 7 文件 0 error（official_source_flow/canonical_writer 基线本就有 mypy 错误，非本线引入，未追改）→ logs/static_ruff_changed.log、static_mypy_changed.log。
14. 最终责任命令：tests/unit/test_m3_official_json_parser.py + tests/contract/test_m3_official_json_contract.py + tests/contract/test_m3_official_json_frozen_pages.py + tests/integration/test_m3_official_json_projection.py = 107 passed → logs/green_final_all.log。
15. INTERFACE_CHANGE.md 写就（§1 新公开接口、§2 MAIN 接线包+重跑命令、§3 未定决策、§4 文件清单）。
16. 隔离：所有测试夹具用 pytest tmp_path/TemporaryDirectory 自动清理；手工 RED 脚本用 TemporaryDirectory；封存 run 全程只读；生产 config 未动（baseline_shas.txt 可对）。新增 provider/model/token/cost = 0。

2026-10-10 收尾：

17. 提交 A=8abfad074057ff8d5c89e01aea8f87a73be5405f（运行时+测试+PWF），push exit 0（pre-push 门 2637 passed，logs/normal-push.log）。FC-1307-a host assumption guard 曾拦 4 个测试文件的宿主机绝对路径，改为 Path.home() 拼接 + M3_SEALED_RUN 环境变量覆盖后 new=0。
18. handoff.json 按 handoff.schema.json 通过 jsonschema 校验（lane M3-JSON、package_status=complete、main_integration=pending、usage 全 0）；HANDOFF.md 按 HANDOFF_TEMPLATE 七节成文。INTERFACE_CHANGE.md 为 MAIN 接线包。
19. 提交 B=3a5087696d29c8dbaca2232738c62a1d6e0ee9eb（HANDOFF.md/handoff.json/build_handoff.py/normal-push.log），push exit 0（pre-push 门 2637 passed）。分支 remote head=3a5087696d29c8dbaca2232738c62a1d6e0ee9eb；交接的运行时代码头=8abfad07（handoff 文件无法内含其载体提交的 SHA，此为自引用边界，以本条为准）。
20. CI：ci.yml 只在 master push/PR 触发，codex/* 分支推送无 workflow——精确 CI 记录 not_available（触发证据+GitHub API 观测在 handoff.json repos[0].ci），MAIN 经 PR 上线时观测。
