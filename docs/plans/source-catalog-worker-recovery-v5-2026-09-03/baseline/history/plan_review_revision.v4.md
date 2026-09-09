# Plan Review Revision Manifest

## Revision v1 — 2026-08-22

本 revision 用于本次三路独立计划审查。以下 9 个核心计划文件在审查结论返回前冻结；
`progress.md` 与本 manifest 不属于审查 hash 集，因为它们只记录审查进度。

```text
dc29ae22c35a89bf4ca2cf360b5f8b07b919df64e508fa698462259da1ffbcb9  README.md
1a58d2f08a2ef9050283e7509b024f9093d33ac064ef85ad8f4745e075db95cd  task_plan.md
990fbd340a3d5ac9d05e1eb0dc68249fa1eeba15ea28435dc00b76d3652ef536  findings.md
c33f6b31b16f877156996a68efeb9f1e3e6c230ec2e6281a659ded18e65d0421  execution_playbook.md
a04d4a541685b800d605e70c2088c1448aadf4a277902810747dc765266b6089  test_acceptance_plan.md
1ee6a3998ca987f4ee5a11e1668cd03862a58ca0b032d66aa982dd1e04cc8694  agent_review_gates.md
016fad0aefda25e74a9a80cc9339cfe8068153093f1ba38697b9675b2c9a3d7b  rollout_rollback_runbook.md
e63120270e1572032d98cdc2a3e8ace0a53efb360215386a8520cda38cd1a1a1  traceability_matrix.md
54f077b8ebd98ba94e30bc6df63bcc32512f8099cc1bb857b51633205fc552e5  implementation_agent_prompts.md
```

审查后若修改任一核心文件，v1 verdict 自动失效；必须追加 v2 hash 集并要求受影响领域的
独立 reviewer 复审。历史 revision 不覆盖、不删除。

## Revision v2 — 2026-08-22

v2 接受并处置 `plan_review_findings.md` 的 PR-001–035，新增唯一 Gate DAG、数值阈值合同，
并把该 findings 文件纳入审查集。以下 12 个核心文件冻结；`progress.md` 和本 manifest 仍不
在自校验集合内。

```text
cdf01a958b80714f72bf24b16c124327562f62ca152b0486d947a34dba02ef4f  README.md
7a44ab6ceb9ac2a3925dea88e1897677c52a393d0a6f891fc7985efff4d94226  task_plan.md
690a989d7264b14197c8126184f558a4c32d8be4c83a0123aa3c7592c87265b4  findings.md
e3a10654438bd86c41377420d00505548b3246771554f71e0ecbe39bd321378c  execution_playbook.md
e6e09390b3747871451ecd62eb287fe293ba91d3492342e6ddba562f6a25cad6  test_acceptance_plan.md
c68216854bdc5536b8564fc0d12b1e0bd63e58e3f81e6f4b30faf8f4c2c9a88d  agent_review_gates.md
971875c062e0327d7f9145975ef367aff9e79d732f1db337ddfc2d547878cd1f  gate_state_machine.md
e66adf2e5cee2807d3d48cec05eb6c75f0d4e1af7a91aeb0d2f94e81e9b4bb8b  acceptance_thresholds.md
8291c4e6ba7252ce2d9f1c871d75eedd88013e05715256e7265721b16834d39e  rollout_rollback_runbook.md
42b5ae21a499c43cd35b8b8123bfc605e2a6e95844ab6955eb2a802d4b0a145c  traceability_matrix.md
2f62b99c2545352361646f449ed690716fc7acc37f0f2bec67364ddf61e77cca  implementation_agent_prompts.md
d436e90165795dac448f0cf3696ca41f6e75ebd2588cd2f4c1799b44d1e63057  plan_review_findings.md
```

来源报告 SHA-256：
`8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`。

v2 仍须由原三类 reviewer 分别复审；只有它们明确关闭所有 P0/P1 后，v2 才能作为未来
实施输入。任何 v2 核心文件变化都会自动要求 v3。

## Revision v3 — 2026-08-22

v3处置PR-036–053及仍开放的v1项，新增机器可校验Gate ledger schema、current-source
freshness、三动作circuit、逐阶段A/B canary、外部trust anchor、精确write contract、真实
registry条件并发、stage-bound LLM授权和证据生命周期。

历史machine manifest：`plan_manifest.v3.json`  
manifest文件SHA-256：
`9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc`

Reviewer必须先重算上述manifest文件字节hash，再逐项按其`core_files`核验。为便于人工复核，
13个核心文件hash同步列在这里：

```text
a360bbe723b7561ec944b408a74d79f985f85600d4dd0bce79083d76137b8c1d  README.md
d228803078ba11343ee14feccf017a263f80bfeb0507740f625241fa8bb4d2d1  task_plan.md
3e9a808bfe181cd32b1d517cc315938a91a218c8ec6bfe8290c7f24140607911  findings.md
93098ef834d3d94e9334618aba422f86a901250492af0951fce0cb3f93e98fd7  execution_playbook.md
6762ec2a5ad3892bb17ca7d611536763b6ee3bc532aa36648b98f56538c1a818  test_acceptance_plan.md
6d137f3e0ce159c42c78372d301d0f7ae14a7e37b3ed118309c5d60c1bfe4cb0  agent_review_gates.md
c403970a49b3e5d4a487220e57288ec6b167d6814041b89c5dbda0525c4cef32  gate_state_machine.md
05f758f9e28f4ed0214d711792d839792330626f2d96dfdde22537471ec4054c  acceptance_thresholds.md
6a397e8b6ed29810d7aef8685ba49715b6e6f264d80ce5fac7dfab3184443fb5  rollout_rollback_runbook.md
46997a9279ec5b5cb591b87453f9abcfa91779f216529717d3bd36ee50bb3fbc  traceability_matrix.md
3e2e70231be2aa35c8b233dc793d0c08f08132b2a0f6017a0254ecd777467b35  implementation_agent_prompts.md
4ac22fa52c31a6b627b56527c99ba9e2a6873775cfa39e171ce34c2b9c2fe52c  plan_review_findings.md
b0f672e1e9a12ecd1539b9e9553ea255ba9ac99ce0b6e400fe0d1b5810e3fd26  gate_ledger.schema.json
```

来源报告SHA-256：
`8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6`。  
计划冻结时Git HEAD（仅作漂移线索，不是未来实施基线）：
`26a6b22f80ae964892d3f3f44fab364e65276583`。

`plan_manifest.v3.json`不可覆盖或追加；`plan_review_revision.md`、`progress.md`、未来动态
`gate_ledger.jsonl`、`evidence/`、`reviews/`、`decisions/`不在核心自校验集合。任何核心字节
变化都会使v3 verdict失效并要求新文件名`plan_manifest.v4.json`与重新独立复审。

v3最终状态：**REVIEW_COMPLETE_FAIL / HISTORICAL_ONLY**。三类reviewer均逐项验证manifest、
13个core hash与来源报告hash后返回FAIL；开放项见`plan_review_findings.md`的PR-054–066。
因此v3永久禁止作为实施授权；其manifest仅供审计，不得覆盖、追加或“修好后复用”。

## Revision v4 — 2026-09-03

v4针对v3三路FAIL与后续草稿反例，新增/重写严格instance schema、唯一机器DAG、逐ID测试
registry、operation policy/dynamic contract、stage-bound authorization、detached review confirmation、
显式12B/12C compensation、write-intent journal迁移、物理state与lifecycle outcome分离、精确reset
返回边，以及只读`plan_consistency_check.py`。

冻结时状态（后续已失效，见本节末记录）：**FROZEN_FOR_INDEPENDENT_REVIEW / NOT_IMPLEMENTATION_AUTHORIZED**。
一次性machine manifest已经生成：`plan_manifest.v4.json`；该文件从生成时起不可覆盖、追加或
“就地修正”。manifest外部字节信息为：

```text
c34b849475f1efeb0a3237af2d4a748a6e36c276f7c91b6ad07cae8ea3004711  plan_manifest.v4.json
size=9598 bytes
```

冻结集合包含48份normative文件；覆盖115个固定DAG节点、29个schema、315个稳定测试ID、
18个vector group（140个case）、60个requirement、44个risk和105个计划审查finding。
来源报告及48份文件的路径、大小和SHA-256逐项保存在manifest内。冻结时Git HEAD仅作漂移线索：
`16ef042f40cc85375d0de5196c654a9c027a6ef2`，不是未来实施基线。

冻结前保存的只读检查输出为`plan_freeze_check.v4.txt`：

```text
ca47be86a15d94c68787c637d08567cdf57b2be51e27ee67f2cdff84b9137af7  plan_freeze_check.v4.txt
PASS: 7696 checks; {"fixed_nodes": 115, "schemas": 29, "tests": 315, "vectors": 18}
READ_ONLY: no production database, registry, process, source, config, or network access
```

manifest生成后已再次运行同一检查器，得到同样的7696项PASS；同时重算历史
`plan_manifest.v3.json`，其SHA-256仍为
`9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc`。

v4计划审查必须由SQL/性能、生命周期/安全、测试/DAG可实施性三类彼此独立的只读agent，
针对上述同一个冻结manifest重新从零完成。草稿预检、作者自检和一致性检查PASS都不能替代
正式verdict。三份正式结论全部PASS且无开放P0/P1前，v4不得作为未来实施输入；任何normative
字节变化都会使v4失效并要求创建不可覆盖的新`plan_manifest.v5.json`。

正式独立审查状态：三路均为**INCOMPLETE_USAGE_LIMIT**，没有可采信的最终verdict。

### v4 后续失效记录 — 2026-09-03 22:17–22:22 UTC

当前有效状态覆盖上方历史冻结时状态：**INVALIDATED_FROZEN_BYTES / HISTORICAL_ONLY /
NOT_IMPLEMENTATION_AUTHORIZED**。manifest本身仍保持上述hash，但重新检查当前工作树得到
`FAIL: 27 error(s) after 7696 checks`，全部为`MANIFEST-BYTES`。27个normative文件的写入时间均
集中于`2026-09-03T21:29:17.252–266Z`。其中16个当前文件在只读内存中CRLF→LF后精确匹配原hash，
另11个不匹配，尚不能证明仅为换行差异。无论语义是否变化，当前字节都不再等于v4冻结输入。

禁止覆盖v4 manifest、按当前字节重算v4 hash或继续声称v4可供正式审查。所有原文件保留；任何
后续修订/重新冻结必须使用新v5 revision，并重新进行三路独立审查。中止的三名agent不算PASS，
也不构成对v4技术内容的FAIL结论；本次失效依据是可复现的字节完整性检查失败。

后续独立forensic预审已完成：`/root/v4_test_dag_review`独立验证同一27项漂移、16项LF等价与
27项patch重建结果，高度支持pre_commit整仓暂存/恢复加autocrlf的因果解释，但不计正式PASS。
详细证据、逐文件原/现hash、不确定性、独立结论与安全续接方案见
`reviews/v4-freeze-integrity-incident-2026-09-03.md`。当前未创建v5，未更改Git属性或任何规范文件。
