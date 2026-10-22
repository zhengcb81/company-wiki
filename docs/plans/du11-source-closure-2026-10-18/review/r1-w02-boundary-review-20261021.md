# R1 W02 FF/RF 边界独立审查

**结论：PASS_ENGINEERING_BOUNDARY_ONLY。** 非作者 `/root/r1_w04_summary_runtime` 独立审查；最终固定 **35 PASS，0 FAIL，0 SKIP，9.62 秒**。测试开始 `2026-10-21T22:59:55.9797206Z`，结束 `2026-10-21T23:00:06.9047804Z`，退出码 0。本结论仅接收 W02 工程边界；不表示真实公司 RF、正式摘要、安装或整个 R1 已通过。

## 版本和职责

| 部分 | 最终产品 commit | 审查范围 |
|---|---|---|
| filing-fetch | `cf15aeaa90667a8b8aeac01af713dd984f057fe5` | 相对施工基线 `e8740748` 的 6 个 runtime 文件 |
| revenue-forecast | `768b6dd392d98df67d8eeb1d7ce428ef014cca7c` | 相对施工基线 `9669c4d7` 的 4 个 runtime 文件 |
| 离线 CWP producer | `3b80e0ec9d35db7777d00f419dfe9d5072306f8a` | W04 隔离工区；source_catalog 保持 `0622f242` 基线，176 个 Python 文件字节绑定 |

作者两个工区运行前后 tracked clean；全部 10 个改动 runtime 文件、176 个 CWP producer 文件及独立测试源码 SHA 在运行前后不变。完整路径、SHA 和命令见 [机器报告](r1-w02-boundary-review-20261021.json) 与 [证据包](r1-w02-boundary-review-20261021/README.md)。独立测试源码 SHA 为 `22d9e75660a506300e014962dae7308cf8df6a3a9a5e6731aa1a5b8aeb83626b`。

审查人只读产品，未替作者改代码；发现先交作者修复，再复跑相同反例。未碰 ROOT 正在施工的 W01 source_catalog、生产配置、原件、密钥、安装副本或历史费用账。作者后续仅更新交接文档时，产品 byte binding 仍以上述源码 SHA 为准。

## 独立发现和根因修复

| 编号 | 级别 | 初始缺陷与根因 | 作者修复、最终结果 |
|---|---|---|---|
| RV-W02-01 | P2 | FF 已接受合法 `company_ir` provider 意图，RF 却只接受 `fmp`，把尚未派发的意图及完整 sidecar 一起丢弃。两个边界重复维护不同 provider 词表。 | RF 使用 FF 公布的 provider token 语法保留意图，不声明该 provider 具备下载能力；原反例 PASS。 |
| RV-W02-02 | P2 | RF 将正常 GAP 当成 exception envelope，强求原生正常 GAP 没有的 `retryable`，丢掉完整 FF 结果。 | 分别验证现有正常 GAP 和 exception 两种封闭形状。实际 FF serializer → RF 投影及真实 RF CLI 均 PASS；不放行任意字段或物理路径。 |
| RV-W02-03 | P2 | 非零退出业务 failure 中 `download_events=False` 或 `outcome=downloaded_new` 仍被当成可靠的本地阻断，错误证明 provider 为 0。 | 既有边界要求整数 0 且 outcome 为 null；矛盾结果归 `invalid_producer_schema`，provider/usage 保持未知。两个真实 child 反例 PASS。 |

首次独立运行 **18 PASS / 3 FAIL，7.40 秒**，明确复现前两类缺陷；后补费用一致性控制 **2 FAIL / 28 deselected，3.56 秒**，复现第三类。作者修复后本次同一固定套件全绿。RED 日志/XML 保留，未删除旧断言或用已通过的作者套件代替独立复核。

另核对 W01 最终有限 reason 接口：`local_document_kind_unresolved`、`local_original_unreadable`、`primary_issuer_conflict` 和本地 `budget_exceeded` 保留具名原因。`budget_exceeded` 同时仍可作旧 acquisition failure，未被移入 local-only 集合而破坏已有费用观察。未知值继续有限降级为 unknown；没有增加第二轮公司身份、原文 hash 或权限校验。

## 35 项检查点

| 检查点 | 数量 | 独立证据 |
|---|---:|---|
| 真实 child exit 1/2、action/schema/request 绑定和业务原因 | 2 | 实际有界 subprocess，原 exit 单列、不变成成功 |
| 错 schema/request/action、unknown field、物理路径、截断、HTML、数组、异常退出码 | 9 | 均拒绝为 producer contract failure |
| `not_run` / `not_requested` / `period_unresolved` | 1 | 原生 FF serializer 经 RF 保留精确 FY/Q/provider/intent |
| 非 FMP 合法意图 | 1 | 未派发意图与完整 FF sidecar 均保留 |
| 原生正常 GAP 的完整投影及真实 RF CLI | 2 | 两种合法 envelope 形状不混淆 |
| `current_verified_open` 的 future publication、错 SHA、历史 as-of、裸 first_seen、缺 public receipt lineage | 5 | 不借新 basis 绕过既有时间与引用责任；不读取原件重复验身份 |
| 真实 CWP CLI → FF → RF client → source_preparation | 1 | 合成 HK 身份、空公司目录、真实三个代码入口，具名失败、0 provider、companion 不假装已调用 |
| 未知 acquisition usage；包括既有 provider `budget_exceeded` | 2 | provider/usage null 不写成零；仅未派发 companion 记已观测 0 |
| stdout cap、timeout | 2 | 实际 bounded process 触发，未知 provider 保持未知，未用业务 JSON 绕过限额 |
| ET 实际失败独立于 filing 成功 | 1 | filing SourceRef 不回滚；response bytes 未知仍为 null |
| CN/HK/US 请求 fingerprint 与真实 CWP owner 一致 | 3 | 非手抄 hash 或第二身份库 |
| failure 下载计数/结果矛盾 | 2 | 拒绝错误的 provider-zero 证明 |
| W01 最终有限 local reason | 4 | 经 child → FF serializer → RF 完整 sidecar 保留 |

## 复跑、清理和成本

[证据 README](r1-w02-boundary-review-20261021/README.md) 给出环境变量与命令；[final-receipt.json](r1-w02-boundary-review-20261021/final-receipt.json) 保存实际 argv、UTC、退出码、解释器和基线。运行期只有合成离线材料、真实进程与本地临时 catalog；**0 API、0 模型、0 下载、$0**。未访问供应商密钥。

自有 TEMP `.planning/r1w2v` 初始不存在，清理前 10 文件 / 2,673 bytes，已校验解析绝对路径位于唯一自有根后删除，恢复初始不存在；[cleanup.json](r1-w02-boundary-review-20261021/cleanup.json) 留证。峰值未测量，不能据此宣称空间峰值验收通过。保留的只有小型源码测试、SHA 清单和有界日志/XML，无原文、数据库或响应副本。

## 剩余事项及停止点

1. ROOT 负责已经接受工程的并线、现有 CI 显式表接线、定点安装及最终整合；本审查没有代跑安装副本，也没有代签远端 CI。
2. 本次 CWP producer 故意冻结于旧 source_catalog；W01 新 producer 与此边界的整合仍应在 ROOT 的集中节点验证。4 个有限 reason 控制通过不等于 W01 整个真实数据流程已通过。
3. unknown-publication narrative receipt 跨层缺口归后续 W03：不在 W02 加接口或额外修复，不把已知发布日期路径的工程绿扩展成该路径已通过。
4. 真实新公司 holdout、模型摘要/paid-resume/cache 和四路 RF/买方质量重审仍未完成，保留原 PWF 下一步；未开展新的 live 调用。

用户要求收尾后暂停。本独审完成后 **STOP**；上述剩余项仅交接，不恢复施工、不增加小节点许可。
