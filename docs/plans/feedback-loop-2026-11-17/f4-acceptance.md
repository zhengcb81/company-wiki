# F4 强制终止及真实宿主验收 · 2026-11-18

后续 RF/Audit 的真实宿主、中断恢复和回告见 [F4 RF/Audit 验收](f4-rf-audit-acceptance.md)。

## 1. FF 真进程被杀后的恢复

实际 RC 跑 FF 与 CWP 的公开 CLI。HTTP 提供方仅本机环回，供方模拟收费、实际记录请求次数。取件、原文验真和入库均已由真实 CWP 执行；在该结果送回 FF 前强制终止 FF 进程。仅保留 FF 开始行。两个恢复进程并发、再重投一次，都使用原生 `get_status` 和同一作业的只读 `act reconcile`。

| 请求 | 原作业 | 强杀后恢复 | 新增 |
|---|---|---|---|
| `exact` | `ffjob-be3c9ef3b114` | `succeeded`，原文 SHA 同一，原生尝试 1，run_started 1，reconciled 1 | 作业 0、HTTP 0、下载 0、模拟费用 $0 |
| `latest_as_of` | `ffjob-29589aa13abc` | `succeeded`，原文 SHA 同一，原生尝试 1，run_started 1，reconciled 1 | 作业 0、HTTP 0、下载 0、模拟费用 $0 |

两次原文 SHA 都为 `00d23755dabb6e6b2861f221da9695414db0bf1ee762aea4e2eea023c468bd9d`。每个原作业发生两个元数据 HTTP 请求、一个正文 HTTP 请求和一次入库。供方模拟原读费用为 $0.0009，FF 被杀前未写回终态，原账均保留 `unknown/null`；只读核对的零新增费用不会填回旧账。本地 `latest_as_of` 只证明已入索引的候选，不证明供应商侧最新。临时测试目录由测试夹具清理。

## 2. 真宿主分诊、修复、复验和回告

以现有半年报原件挂载隔离 CWP 目录，在 FF 原版 `a17fc632aebf8b50d9d071e4816cb672f6f5637e` 启动并强杀一笔 `latest_as_of` 作业。用原 FF 公共命令复现对账被正常采集限额拒绝；初始费用错误地显示为 `not_applicable`。分诊只使用该公开错误的脱敏字段，未发送原件或凭据。

真实 Codex 已创建 session `01a1f054-2130-7060-bc8e-e84f5c1c3f5e` 后强制终止总控。重启找回同一个 session 的结果。真实 FF owner 命令在隔离副本核对原代码、采用已独审的 Git 修复版 `a9f9d6d1f3af139c08898a296dba14574dbf044d` 并运行定向回归。CWP 发现端校验确实执行该版本，依据原观察再次查同一 FF 作业 `ffjob-4c54cbb8a9c0`，关联未改的原文及 SHA `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。业务结果找回，费用保留未知。

FF 用本仓 `get-report` 读回责任仓完整回告，包含原发现方、版本及复验引用。`observe/triage/repair/replay/report` 各 1 条终态。重复重启回执一致、下载及 FF 作业增加 0，Codex 没有新增会话。最终受控试验只用了一个分诊回合，输入 21,022（缓存 13,056）、输出 324 tokens；无业务模型调用。这是自动执行已独审修复的验收，不代表所有 owner 都已能自主生成、验证和发布任意新修复。[机器收据](f4-host-receipt.json)

最初诊断试跑中 Windows 沙箱在临时目录无法启动读文件工具（267）；Codex 正确返回 `needs_evidence`，没有执行修复。该尝试消耗输入 200,865（缓存 188,416）、输出 1,177 tokens，不算在成功作业的复用计数里。后续将已由 FF CLI 验证的脱敏证据直接附给只读分诊，确定性步骤由 owner 命令执行。两个宿主试跑均未请求供应商和业务模型，Codex 真实账单金额未从 token 估算。成功试验临时目录自动删除；早期试跑的进程锁解除后，其专用临时目录也已清空删除。

## 3. 重跑方法和检查范围

- 装配/强杀：设置 `FEEDBACK_FF_CODE_ROOT` 为兼容 FF 工区，用 `python -B -m pytest -q -s tests/integration/test_feedback_f4_owner_recovery.py`。只有被显式指定时才用相邻仓。保留两类请求、并发对账、一次入库、原文指纹和直接 HTTP 计数断言。
- 真宿主：[指定版本的试验脚本](../../../tests/integration/f4_real_host_probe.py)。在 `PYTHONPATH` 含总控仓根的正常宿主，从仓根运行 `python -B -X utf8 tests/integration/f4_real_host_probe.py --help` 查看参数。用上述 FF 两个版本、已归档的 `t4-phase-c-20261114/preparation.json` 内 `r4-cn-h1-real`、截至日 `2026-11-17`，以及本机已配置 Codex 路径。每次试验单独指定不存在的 `--output`，只在需要新验收时明确运行；正常重启按原 `recover` 继续。
- ROOT 反馈、CLI、Phase C 加跨层合同 114 项通过；历史本机环回 3 项在正常宿主通过；实际 FF/CWP 双强杀 2 项通过。FF 本仓 188 项及 8 子例通过，已推送 `main`。受限沙箱中的三个旧回归在第一个 POST 前失败，同一版本的正常宿主测试全绿，保留原断言。
- 独审覆盖旧费用两种错误形态、合法未启动零证据、原生 attempt 错配、结果及费用分离、实际回告和受控真实链。总控代码核对工作树 SHA-256 前缀：`local_host.py` `c1907cba`、`coordinator.py` `c13ce2d2`、`observations.py` `ad53b0ad`。实际 FF 为上述提交。

本轮验证指定 FF/CWP 组合与通用宿主。其他 owner 的生产接线、不同供应商费用的额外核对以及公司池正式运维继续沿[分工](dispatch.md)与各自 PWF，不能将本轮的隔离验证记作已全量上线。

## 4. 外层 worker 未启动原生命令时的恢复

在 `owner-json` 与 `codex-jsonl` 两条隔离路线上，让真实外层子进程在进入原生执行前 `os._exit(17)`。旧版已写 `running`，重新启动宿主唤醒零条，两条回归均变红。修复将现有 SQLite 领取移到实际执行端。并发执行两次 `recover`，找回同一 action ID，原生命令实际启动一次，重复查询增量为零。模拟 owner 启动器的 `OSError` 时，同一排队动作带具名诊断并可恢复。已领取、缺终态的历史动作继续按原作业核对。

最终定向包覆盖 `tests/unit/test_feedback_local_host.py`、`tests/unit/test_feedback_loop.py`、`tests/integration/test_feedback_loop_cli.py` 和 `tests/integration/test_feedback_f4_owner_recovery.py`，共 27 项通过。用现有 FF 源码跑真实子进程和环回，再执行 `f4_rf_audit_host_probe.py` 的合同模式，恢复期间环回请求、下载、付费调用均为零。这一轮的分诊由离线夹具提供。独审复核并发领取、启动器诊断、旧记录和已启动动作的保护。测试目录由夹具删除。[部署与接续](host-integration.md)

## 5. 责任仓已保存回告时的恢复

此前已有宿主侧回执落盘后退出的恢复。本次两条 RED 命中更早的窗口：真实 FF 写完回告后，宿主原生进程在记录 stdout 前强制退出，原 action 停在 pending；另一个已有 unknown 的本地回执也无法补记。两种情况都有独立 owner 回告。

宿主保留首次登记的查询命令。显式恢复用原 action ID 调只读 `get-report`，以规范化 JSON 的 SHA 核对完整提交请求。确认后在原 SQLite 行登记完成，收据标注 `receipt_source=owner_report`。错版本、缺件、读取报错保留原状态。仅有开始且没有可信回告的动作继续占用原工作区。配置摘要、读取方式和历史兼容见[宿主接口](host-integration.md)。

使用 FF `d5fa32c` 和从 RF 已发布 `e13861db` 只读导出的真实 owner 脚本。分别写入一份合成回告，在宿主写侧车前以 `os._exit(17)` 终止；两次并发恢复都指向原 action，原回告写命令累计一次、文件修改时间一致，后续已排队动作完成。独立复审同时覆盖同 ID 错版本、运行中缺回告、宿主配置更改及晚到回执竞争。

F4 两种回告、原 FF 环回恢复、总控 CLI 和 Phase C 定向共 38 项通过。运行 `tests/integration/test_feedback_f4_owner_recovery.py` 时可显式指定兼容的 `FEEDBACK_FF_CODE_ROOT` 和 `FEEDBACK_RF_CODE_ROOT`。RF/Audit 合同端到端另行通过，恢复期间环回请求、下载和付费调用增加均为零。测试根及 RF 导出副本自动清理。

## 6. F2 FF 短请求进入总控

2026-11-19 验收作者交接 `8d1228d`，最终受审实现 `eb2ee5c`，两者之间只有交接文档改动。定向基线复跑 204 项和 8 子例通过。ROOT 独审发现非法数组、对象会让短请求旁路丢失终态，两例在作者版真实 CLI 复现。FF `95769c0f68dee27c282c99658c18e05cb91a816b` 先辨明意图字段类型，修复后的两个用例保留原 stdout、stderr、退出码及零 connector 调用，并补齐开始/结束配对。独审复验确认付费与持久作业边界。

ROOT 用真实 FF 短 CLI、CWP 公开命令和本地环回 provider 完成首取，再精确复用同 SHA 原件。首次执行实际发出两次元数据、一次正文请求，模拟收费收据与短请求的用量范围一致。复用与随后的重复导入均零新增下载或 provider 请求。组合导入实际侧车和作者 6 份样本；后者有 27 条唯一观察（25 预期、2 未知），无解析诊断和悬空开始。两条未知均保留，只走原观察的只读查证，持久 FF 作业入口调用数为零。

复跑入口为 `tests/integration/test_feedback_f4_short_intake.py`，用 `FEEDBACK_FF_CODE_ROOT` 指向包含本卡样本的 FF 版本。本次 CWP/F4 组合用受控 provider 和只读 ROOT 宿主。RF 正式周跑与 ET 的生产消费轮次继续沿各自运行计划取证。[FF 作者交接](../../../../filing-fetch/docs/plans/f2-ff-short/handoff.md)

最终 FF 定向回归 224 项和 8 子例通过，组合测试 1 项通过。独立复审重跑两类非法请求并检查回放断言，测试根已清理，远端 `refs/heads/main` 已核对为 `95769c0f68dee27c282c99658c18e05cb91a816b`。另用相同隔离环境核对历史配置诊断用例 `test_real_cli_config_error_has_no_upstream_cause`。基线 `d5fa32c` 和最终版均返回 `fatal`，该用例在两版都因期待 `config_error` 失败，另记为 FF 环境诊断待查。

## 7. F2 MC 转录发布反馈进入总控

作者交接 `b1acea5` 的代码经独审覆盖至 `8806ff4`，后续只补交接文档。独立复核原投递样本发现，11 行只保留 5 条观察，三个身份冲突把已完成转录变成额外悬空开始。作者版 MC 全量 297 项通过。ROOT 补充 7 个失败反例及首取、复用、陈旧译文的消费者测试。

MC 的适配器 `meeting-converter-feedback/1.0.2` 为每次真实调用生成独立 step，原侧车重投保留原身份。反馈未启用时不探测文件；启用时在业务计时结束后取指纹，无法读取仅影响证据。目录无法证明旧译文存在。追加前隔开截断尾行，保留旧行诊断和下次开始。详情记录结构化异常类型、阶段和角色，任意异常原文由本仓原日志处理。

使用真实 `core.transcribe_one`、合成音频和离线引擎/翻译桩。验证首次转录完整发布、同音频随后零调用复用、强制转录遇翻译失败时保留旧译文和对照字节、子进程硬退出仅留开始。通过 `details_ref` 定位陈旧结果的结构化错误，消费方能识别原问题。作者路径生成的四份新样例合计 30 条唯一观察（22 预期、4 偏差、4 未知），零解析或身份冲突，只有硬退出的一条开始未配对。真实宿主持久登记同一观察，重复导入的执行和登记增量为零。

最终 MC 全量 302 项、CWP 定向 29 项通过。独立复审另跑 MC 46 项和实际组合 1 项，通过并绑定最终源码和测试内容。复跑入口 `tests/integration/test_feedback_f4_mc_intake.py`，用 `FEEDBACK_MC_CODE_ROOT` 指向包含正式样例的 MC 主线。已清理测试副本及运行目录。远端 `refs/heads/master` 核对为 `1d3fd6c9214495ebef2cb8a4d4014712002eca00`。MC 主工区既有 `.coverage` 字节保持。[MC 本仓进度](../../../../MeetingConverter/docs/plans/f2-mc-output/progress.md)

本次验收覆盖观察、详情定位、陈旧案例消费侧复验以及中断和费用的只读处置。MC 当前的自动分诊、修复与持久回告待 owner 运行端口；用量和缺原生终态继续按 unknown 保存。
