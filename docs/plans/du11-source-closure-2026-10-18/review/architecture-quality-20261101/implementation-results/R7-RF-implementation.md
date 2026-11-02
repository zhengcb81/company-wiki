# R7 RF：表示门禁、诊断许可与重复验真整改

状态：作者代码冻结，等待独立审查；不是全仓 CI 或真实公司 RF 验收通过。

RF 工作区为 `C:/Users/郑曾波/Projects/revenue-forecast`，main/HEAD `957c6283d3381d23c39515afd3a09147d8201c7b`。本节点修改 18 个 runtime Python、8 个测试文件和 3 份技能说明，共 29 文件；精确 SHA 在同名 JSON 的 `delivery_files_sha256`。未 commit、push、安装或写 Git index。四份既有 assurance WIP 前后 SHA 完全相同，既有 Dashboard/output/.planning 目录未动。

## 共用根因与实现

1. RF01：把来源资料表示大小误当成有效性判定。移除 body/receipt/request、reading、policy、proof 的重复固定字节/数量/深度门。`company_wiki_narrative_contracts.py` 继续负责唯一身份、实际字节 SHA、引用归属和 JSON/版本语义。`company_wiki_narrative_process.py` 与 POSIX 路径同步支持无默认表示额度；显式数值额度仍在读取期间执行，未截断 JSON 后冒成功。`company_wiki_narrative_reader.read_narrative_context` 以已绑定 `narrative_ref.byte_size` 限 stdout，并接受实际调用方的 `max_response_bytes/max_receipt_bytes`，仍有 timeout/进程树回收。CLI 可传同一资源参数，无第二套 cap。
2. RF02：摘录 10–500 字、proof 128KB、采用理由 2048 字不能证明证据质量。改为非空真实引用及完整来源/上下文/公式绑定。合法短句、完整长句与长采用理由均可用；空摘录、foreign text、丢失 context、无真实参数公式仍拒绝。没有通过裁切内容或抬高阈值换绿。
3. RF03：review、producer recipe 与 selection trace 是观察，不是材料许可证。新增纯 `contracts/source_diagnostics.py`，坏/未知/异源 review 投影为 `unavailable/not_reviewed`；未知模型或 assessment 不升级为通过。新算法版本/依赖/规则可保留为数据；不再要求 RF 内置另一套 producer 配方白名单。可选诊断的缺项、损坏、错误 JSON 类型均不阻断实际已验来源；缺项明确 `absent`，坏项 `unavailable`。真实 group/support/context/source proof 与 deferred count/limited 合同保留。
4. RF04：全局历史索引不是当前结果的真实性来源。`publication_registry` 以每行自含哈希追加，不再全历史预读或 chmod；索引损坏/不可写只记录 diagnostic，当前结果仍能通过自己的 input/result/receipt 校验。新增显式 `rebuild_publications`，由已验证的保存结果重建索引；坏输入不会覆盖已有重建目标。旧 lookup/audit 仍可报告旧链损坏，不能成为正常预测的前置许可。现有真实签名验证保留，无签名合法结果不冒称 `host_signed`。
5. RF05：同一次读取后层层再验证、哈希同一 source body。唯一 `verify_original_read` 返回 `VerifiedOriginalRead`（bytes 与 canonical metadata 不可变），reader → preparation → record composer 复用该值；历史 tuple 解包仍兼容，注入裸 tuple/dict 仍走 public 验证。`NarrativeContext` 同样只由实际 wire validator 组成，`to_dict()` 返回副本。没有 secret、nonce、手工签收、skip flag，也不把 Python 类型当不可伪造的权限。实际 wire validator 捕获 claim binding，修复可选 assessment 失效后 summary 事后篡改可能漏过的真实回归。

`SKILL.md`、`references/compliance-contract.md`、`references/data-governance.md` 已更新相应旧 registry/signer/诊断许可说明。FF 本轮只读审计没有找出同类当前人工许可，不凑修改。

## RED/GREEN 与必要边界

- 初始 12 真 RED（5.85s）→ 表示/诊断阶段 9P3F（3.92s）→ 索引和 immutable source 完成后 12P（2.11s）。
- 一次受影响域调查 224P44F（18.80s）：43 项旧门禁 oracle、1 项真实 post-read claim mutation 回归。保留原变形，迁移应接受的表示/未知诊断断言，并根修真实内容篡改；只重跑对应失败与新增控制，61P（5.95s），没有反复跑 268。
- 来源 reader、实际超量流/timeout 子进程清理、receipt 形状、readability 与伪造 context 等必要边界 40P（7.71s）。该次完整 argv 未单独保存，原 stdout 已保存在 JSON，不冒称独立重放或最终全仓收据。
- 收尾类型控制：完整 review 的 list/dict status 4 真 RED；trace fixture 首次缺字段及一次 reason 断言错误已如实保留，修正后 admission 非标量引发真正 wire refusal RED。仅 optional 观察捕获错误，5P（0.75s）。
- 采用理由：首 fixture 有 trailing space，未单独归因为 length；去掉该干扰后 >2048 理由仍真 RED。移除两个同类长度门，长理由及原 unknown claim/empty reason/真实 formula dependency 控制 12P（1.58s）。
- 旧 v3 混合测试独立核查 6P6F：六项旧 oracle 把坏诊断当来源不可用。另有缺 trace/diagnostics 2 真 RED。拆分可选诊断与实际 source proof，原实际 proof/page/identity 负控继续拒；新缺项控制和旧混合场景 14P（0.71s）。
- 最终 26 Python 文件 Ruff 与 AST parse 通过。所有测试使用正常宿主 `C:/Miniconda/python.exe`、独立 basetemp，禁外部 attestation provider/dotenv。每一阶段是增量收据，不合称同次“全部绿”。同名 JSON 保存 raw logs、argv（有记录的部分）、阶段与 SHA；新文件共 24 case，最终没有为了凑总数整文件重跑。

可复验的最小命令（RF 目录，测试者先为 `--basetemp` 选择明确初始 absent 的独立目录）：

```powershell
$env:REVENUE_ATTESTATION_PROVIDER=''
$env:PYTHON_DOTENV_DISABLED='1'
C:/Miniconda/python.exe -B -X utf8 -m pytest -q tests/test_r7_representation_and_index.py --basetemp <owned-temp>
```

精确的诊断/理由/缺项小组命令见 JSON `commands`，61 项历史实际 argv 见 `raw_evidence.exact-rerun-argv.json`。新 oracle 不放松 source bytes、币种/期间/as-of、原文 locator、support/context 分区、foreign text、已声明的签名真实性或真实资源限额。

## 跨仓边界与剩余

invest-core 的默认 registry/host_signed 许可由 ROOT 在 canonical `invest-skills` 独占改造；本作者仅只读检查，没有跨仓改消费者。ROOT 已分别记录 adapter/three-hop 24P1skip 及独立 fast gate 21P1skip+Ruff；那是各自的联调收据，不是本作者的全 RF 独审。RF 已冻结，下一步由独立作者按本 JSON 的 29 文件 SHA 审查；之后 ROOT 集中发布。

未运行全 RF/远端 CI、未读取原件、未下载/调用模型、未做真实公司分析，也未安装全局技能。明确保留的是 public 原始数据反序列化和事实正确性的唯一责任层；同事务 immutable 值不重复走相同 byte SHA。不要把此节点工具/合同绿写成摘要质量、完整 RF 真实采用或全主线完成。

## 独立测试目录恢复

Owned root：`C:/Users/郑曾波/Projects/company-wiki/tmp/r7rf-a1`。创建前已断言不存在；首命令只有创建后的 isolation JSON 序列化因未 import json 失败，随后如实记录，不掩盖或删除既有数据。所有 raw logs 在同名 JSON 留证后，校验绝对 parent containment、root/后代无 reparse，仅删除该确认目录。实际 32 文件 / 167,132 字节，`exists_after=false`，恢复初始 absent；收据在 JSON `cleanup`。未清理不归属的 RF 历史目录，也未声称 pytest tmp_path 会自动删除。
