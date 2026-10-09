# W08 独立复审（2026-10-09）

结论：冻结的 W08 工程责任范围通过；原独立 FAIL 和控验记录保留。本报告不代表全部历史错误通道已清理，也不代表整家公司 M3 已通过。

## 版本和证据

- FF 审查时交付 HEAD：`bb0fe920d75781ebf6bc25365c9e190cdd73bb12`；源码提交 `07cd3a2cca3649659c8acfffda0a4e4dc3ef6cc7`，后续只有交接文档变更。
- RF 审查时交付 HEAD：`ef5150007855a74498150f075fe9eb1be0201ad5`，包括首次候选投影修复和 MIME 责任修复。检查时两个工作树已提交；RF clean。实现者后续可添加各仓 PWF docs-only 收尾提交；本报告以本段 commit 和八个实测源文件 SHA 固定审查对象，文档提交不改变该源码结论。
- 最终 reviewed RF source SHA：`filing_fetch_client.py` = `ee8979e4853debf0cd433aae7a3d01219952d0fe0ebbffbabec4c37f8fd252d4`；`filing_upstream_cause.py` = `67be19ef4e903c06abcaa05217d509ac48c4a090d9ebc557128d9a35d224cf27`；`source_preparation.py` = `4038be124d06c9d3b26a5d0490f82f18e03e0dd92fa4a3b1c72625da294c9ebb`。
- 八个责任源文件的全部 SHA、确切 argv、观察字段、测试输出及 TEMP 恢复记录见 `re_review_receipt.json`。原 `independent_review.md` / `independent_review_receipt.json` 和中间 `candidate_recheck_receipt.json` 保留未覆盖。

## 原 R1：公共失败候选泄漏

初审用真实 RF client CLI 及假 FF JSON 响应发现：合法 cause 旁的 `candidates=[{error: 带合成敏感标记的 URL}]` 原样出现在公共 stderr。RF preparation 最终过滤不能撤回中间边界泄漏，因此当时暂不通过。

修后 `_ClientError` 和 `_emit_error` 都使用同一个 `validated_failure_candidates` 投影，只保留类型符合合同的身份字段与 SourceRef。独立 8 控验覆盖 v1/v2、上游 exit 2/0、RF client/preparation：合法四身份字段、security/entity token 和 SourceRef 保留，未知 nested、source URL、error-only、market dict、MIME list 不输出合成标记；实际失败退出码仍是 client=2/preparation=3。原有 lowerbound 36 bytes / $0.03、usage_complete=false、stage/attempts/calls/downloads 保留原值。证据见 `candidate_recheck_receipt.json`。

## 跨层兼容：不重复格式能力门

复审发现首次投影新增的 MIME 六值白名单把 W05 已支持的合法 DOCX SourceRef 删除：独立纯函数控验返回 None。已交实现者从责任层修正，SourceRef 投影只验证有界 MIME type/subtype 形状，格式能力由 CWP parser/reader 决定，不再维护第二份能力清单。

最终独立 12 个真实 RF client CLI 控验覆盖 plain / 官方 DOCX / custom MIME × v1/v2 × 上游 exit 2/0，全部通过。中文公司名、中文配置路径、合法身份和 SourceRef 原样保留；错形 MIME/market、unknown nested 和 URL 敏感标记不外露。未知费用 `acquisition_usage=null`、`usage_complete=null` 保持未知，不补成零。

## 集中责任测试与先前联调

- 最终独立重跑两个直接受影响模块：`test_source_failure_observations.py` 和 `test_source_failure_cause.py`，50 PASS，13.07s。
- 初审已经独立完成 FF 59 PASS / 2.85s、RF 73 PASS / 12.07s；最终复审只重跑修复触及的责任集。
- 初审 5 条实际 CWP → FF → RF client → RF preparation CLI 链覆盖 provider failure、timeout lowerbound、malformed usage、local_metadata_gap 和没有登记原件。两个本地缺口为不同有限 subtype，provider_started=false，不把没有调用 provider 伪装成调用成功。
- 全链证据为真实 CLI 和自建无 HTTP provider，未知/完整/下界 acquisition DTO 逐字段比较；stage/attempts/calls/downloads 保持观察值，未编造自动 retry 或结算信息。最终只修改候选投影和格式形状检查，没有再次跑未触及的 5 条慢链。

## 限制和清理

- 本次只验 W08 新有限 cause、观察字段和 RF 公共错误候选 DTO 边界。历史 FF `_resolution_trace`、复用失败 free-form reason、`missing_capture_fields` 旁路仍属冻结计划已列明的限制，不能据此声称所有旧字段已经全部净化。
- RF 当前 reader+record 复合调用失败统一记作 `source_reader`；这是现有观察精度，不宣称已知道内部哪一步失败。
- 合成响应/无 HTTP provider 不能证明真实供应商能力、套餐权限、整家公司研究质量或 M3。外部 HTTP/付费调用均为 0。
- 本复审未修改任何源码、生产 config/raw、技能安装副本、旧执行或主 PWF。首次 sandbox TEMP 创建受限，在 child 启动前失败；已移除本次空目录，使用正常 OS 的独占 TEMP 重跑。全部最终 TEMP 基线恢复且临时根不存在，八个源码文件审查前后 SHA 一致。
