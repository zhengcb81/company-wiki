# W15-AUDIT-PORTABLE：采用证据的显式导出与移位回放

**可以立即开工，与W13/W14及ROOT并行。** 独占工作目录 `C:/Users/郑曾波/Projects/revenue-forecast-audit-w15-portable`；分支 `codex/w15-audit-portable-20261024`；源码基线 `af255d4161f9ea19748f35af45447584a0bdbeee`。设置 `PLAN_ID=w15-audit-portable-2026-10-24`、`PWF_PLAN_ROOT=docs/plans`。完整读[共同接口](INTERFACES.md)。仓库目前没有remote；完成后commit并如实交接 `NO_REMOTE_CONFIGURED`，不自行猜地址。

## 问题与职责

CWP PWF R3明确完整live response/consumer/recovery子收据只在本机，未证明fresh clone可复验。Audit `review_evidence.py`约229–292行按execution_root/allowed_roots读取本机路径；`summary_review_import.py`约170–176行局部相对carrier仅覆盖摘要导入。现有W10 `document_status_join.py`已实现采用语义，尚无“显式导出→换绝对目录→屏蔽旧根→公开join CLI重跑→比较语义”的完整工具/测试。

交付一次性工程导出/回放工具，帮助ROOT以后搬迁必要证据。**不修改W10，不另建采用判定、CAS、数据库或生产包schema。** DU6的“不新pack格式/第二oracle/持久证据库”继续适用；工程manifest只记录明确携带的文件和路径映射。ROOT真实矩阵、实际内容审查及公司PASS不属于此卡。

## 独占写范围

允许新增：`tools/audit_adoption_replay.py`、`tools/run_adoption_replay_e2e.py`、`tests/test_adoption_replay.py`、`tests/fixtures/adoption_replay/**`；`docs/plans/w15-audit-portable-2026-10-24/**`、`delivery/w15/**`。工程模块确需拆分，可在新增 `tools/adoption_replay_support/**` 内进行，保持一个公开工具入口。

禁止：现有`skills/revenue-forecast-audit/scripts/**`（尤其EvidenceReader/join/importer）、SKILL/references、同步工具、安装副本、旧fixture/金标、`runs/**`及历史报告/收据、预算/key、CWP/RF/FF/Dayu等其他工区、母PWF。Audit原工区两个untracked预算脚本保留。本包不运行真实公司或模型/供应商/下载。

## 固定输入输出

1. 输入为现有 `audit-status-join/1` JSON，以及显式文件清单：每项artifact token、文件路径、所属只读root。只处理明确声明的 `result.artifact`、`dependencies.prepared/read/use[*].artifact` 及明确列出的引用文件；不得递归猜整个run或扫描磁盘发现“可能有用”资料。
2. `python tools/audit_adoption_replay.py export --input INPUT --files FILES_JSON --out-root NEW_DIRECTORY`：输出普通目录、工程manifest、原input精确字节副本、派生join-input与必要文件。复制的artifact保持逐字节、相同SHA去重一次；不复制原件PDF/整座湖/secret/供应商全集。
3. 派生input仅修改上述声明artifact路径；精确记录JSON pointer及旧/新token。SourceRef、locator（含空JSON根和`/`）、数字、币种、status、unknown、历史结论不能变；不能用全局字符串replace重写公司材料。若引用在本卡支持范围外，如artifact内部必须访问旧绝对根，明确incomplete/unsupported，不偷偷改原artifact字节或回退旧根。
4. `python tools/audit_adoption_replay.py replay --export-root EXPORTED_DIRECTORY --out-root NEW_RESULT_DIRECTORY`：验证导出字节，使用**现有**公开 `skills/revenue-forecast-audit/scripts/document_status_join.py join --input ... --out-root ... --execution-root ...` 执行。不能自制resolver或第二套projector来制造成功。
5. 输出 `replay_status=complete|incomplete|mismatch`、`quality_status=not_evaluated`，实际CLI命令/exit、文件SHA/size、映射、未携带项、明确差异。对源根与移位根比较每material的native outcome、prepared/read/use、source/document/kind/purpose、failed companion、superseded history、call去重费用及unknown。只排除显式列明的环境输出路径/新attempt/PID/时间；不能泛化忽略所有status、路径或数组差异。

`FILES_JSON`固定最小形状如下，仅是本工程工具输入；不提交生产schema、不写新的许可文件：

```json
{
  "roots": {"execution": "C:/owned-test/source"},
  "files": [
    {"artifact": "receipts/native.json", "root_id": "execution", "path": "receipts/native.json"}
  ]
}
```

`artifact`必须精确等于join-input中的原token；`path`是所属显式root下相对文件路径。相同token的完全相同重复项可合并；同token指向不同root/path拒绝并说明。不同token的同SHA字节仅存一次；同basename异字节使用不同内容路径，禁止覆盖。派生映射示例 `/documents/0/result/artifact`、`/documents/0/dependencies/prepared/0/artifact`；以现有真实payload结构为准，未知结构不能盲猜后声称已搬全。

固定进程退出码：复制/回放完整且语义比较相同为0；`incomplete`、输入非法、字节损坏或公开CLI无法运行为2；语义`mismatch`为3。原native结果本来就失败但被精确保留，可以是工程replay完整；收据必须仍保留native失败，`quality_status`始终not_evaluated。不可用native失败被“修好”来通过比较。

这是派生工程材料，原input/artifact不改。工程manifest证明复制完整性，不能把缺来源hash变成人工许可门；输入本身的来源质量失败应在两边保持同样失败，不能因回放语义相同宣称来源有效。缺应携带文件、复制后坏SHA/截断和无法执行公开CLI，均不能记complete。

## 必须完成的测试与反控

| ID | 场景 |
|---|---|
| P01 | 至少一份冻结的非生产W10复杂测试输入，经真实join CLI在源根和两个移位根执行；移位时旧根实际不可用，一个目标含中文/空格，从外部cwd启动 |
| P02 | mother成功/companion失败不互借prepared/read/use；晚peer、superseded discovery保留；同call费用去重一次，unknown不清零 |
| P03 | JSON根空字符串与`/`、行locator、原SourceRef/期间/as-of/币种量级保真；同basename异bytes不能覆盖，相同bytes只保存一次 |
| P04 | 导出后删除源根仍可回放；移动到任意另一个根不依赖导出时绝对路径、环境home或个人安装目录 |
| P05 | 缺artifact、漏列声明依赖、路径逃逸、损坏/截断、复制期间输入变化、现有非空输出和总字节/文件数超限给具体incomplete/失败，不覆盖旧输出。只读root是调用指定范围，不引入private/public权限系统 |
| P06 | 造native evidence冲突时，两地同样保留错误；另造真实搬迁映射/字节错误时replay必须mismatch/非零。证明工具检测到错误，而非导出后将失败改成PASS |
| P07 | 使用显式有界文件数/总字节/执行时间；源文件前后hash相同；成功/失败/timeout均清本次scratch，保留原sentinel与指定delivery证据 |
| P08 | 工具小模块职责明确、无公司/本机根特判，已有join/EvidenceReader是唯一采用语义责任层；全新counterexample由独审者独立编写执行，不只复读实现者报告 |

## A/B/C与实际命令

A读现有W10 join/reader/testfixture合同，冻结源→移位预期和正反例；B实现工程导出和公开CLI回放；C集中做单元、真实移位E2E和全套Audit unittest一次，然后调用独立agent审查全部P01–P08及需求完整度。内部发现全部修复并补审最终代码，才交接；不增加A/B小节点签收。

```powershell
python -B -m unittest discover -s tests -p test_adoption_replay.py -v
python -B tools/run_adoption_replay_e2e.py --owned-root .test-scratch/w15 --receipt delivery/w15/e2e-receipt.json
python -B -m unittest discover -s tests -v
```

E2E工具复用现有 `tools/run_review_evidence_e2e.py` 的owned-root/receipt思路；不要修改该旧入口或复制整套其实现。`--owned-root`是可含原有sentinel的父根，内部独占attempt；清理不是删父根。输出收据路径与scratch分离。新fixture总量目标≤512KiB，不复制中央真实run。

## 交接

`delivery/w15/handoff.md/json`、最小可复现export示例、直接CLI收据/差异、`review.md/json`、清理和空间统计。独审报告绑定最终代码commit及变更文件SHA，实际独立移位重放并修完发现。全部源码/测试commit，仓无remote如实记录；ROOT接收后负责主线并线与新真实矩阵采用。本包COMPLETE不等于ROOT R3所有历史live材料已收齐。
