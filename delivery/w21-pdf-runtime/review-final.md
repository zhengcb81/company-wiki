# W21-PDF-RUNTIME 终审独立审查报告（review-final）

- 终审员：第二次独立审查 agent（不属于实现团队，与初审者相互独立；未修改任何代码/测试/收据，仅执行只读核查、测试复跑与本机只读对照实验，并落盘本报告）
- 审查时间：2026-10-30（本地，00:55 GMT 起）
- 被审 commit：`eab239d93560efe6f1eb974b547be0bd9e93b3e7`（分支 `codex/w21-pdf-runtime-20261029`，基线 `bb5d09c056ca36bba8061d761b5469d87aa6e5e0`）
- 契约：工区 `docs/plans/w21-pdf-runtime-2026-10-29/construction_card.md`
- 方法概述：以初审报告的 6 条 INFO 为整改清单逐条实证；对照卡"输出接口与交接"逐字段核查 handoff.md/json；实跑 4 个关键测试文件与 checkpoint 全文件；逐字节重算证据 SHA；对根因 #5 的 fopen 机制做终审员自己的独立复现实验（非复用作者工件）；用 Windows 原生命令核对 %TEMP%/junction/icacls/ACP；复查 git 边界与工作区状态。

---

## 1. 初审 6 条 INFO 落实 — PASS

| 初审 INFO | 终审核查 | 结果 |
|---|---|---|
| ① 改动范围 30文件/+794 → 33文件/+930/−7 | handoff.md 第 18 行写"33 文件，+930/−7"；终审实测 `git diff --shortstat bb5d09c0..5a33d923` = `33 files changed, 930 insertions(+), 7 deletions(-)`，逐位一致 | ✓ |
| ② 缓存 95MB → ~160MB | handoff.md 第 59 行"apparent ~160MB / 分配~180MB"；终审实测 `du -s --apparent-size __pycache__/pdf-paragraph` = 163440 KB（≈159.6MB）、分配 183372 KB（≈179MB） | ✓ |
| ③ "~3.10GiB"无出处 → 3.03GiB | handoff.md 第 55 行"3,250,298,880B（3.03GiB，4GiB界内）"；3250298880/2^30 = 3.027 GiB，舍入 3.03GiB 正确；`grep "3\.10"` 在 handoff.md/json/evidence-integrity.json 均无命中，无出处比照已删除 | ✓ |
| ④ 新测试计数 → 20 例 | handoff.md 第 65 行"新测试20例（launch 5 + guard 15）"；终审复跑 launch `.....`（5）+ guard `...............`（15）= 20 | ✓ |
| ⑤ checkpoint 53例 → 80 例 | handoff.md 第 30 行"80例"；终审实跑 `test_pdf_page_checkpoints.py`：**80 passed**（4.39s） | ✓ |
| ⑥ handoff.json 落盘 + icacls 证据固化 | `handoff.json`、`evidence-integrity.json` 均在 eab239d9 落盘且 JSON 可解析；evidence-integrity.json 三条 icacls（env python.exe `(I)(NW)`、ROOT 仓根 `(OI)(CI)(NW)`、W21 工区根 `(I)(OI)(CI)(NW)`）；终审直跑 `icacls` 复核 env python.exe = `Mandatory Label\Low Mandatory Level:(I)(NW)`、工区根 = `(I)(OI)(CI)(NW)`，与固化值一致 | ✓ |

第 6 条 INFO 关联的两项证据补存（初审第 10 节建议）同步落实：
- `receipts/canonical-stderr-diagnosis.txt` SHA256 = `678766800e1155133bfbadce84d36db2239ccf14ab4f841a689f5708e70ad2c0`，与 handoff.json root_causes#5 及 evidence-integrity.json 记录**逐字节一致**（终审重算）。
- `receipts/canonical-fopen-comparison.txt` SHA256 = `4e778225c4c57c0e735a22fc0816d57dce459717a99ae038b6692de6f1f3e404`，与 evidence-integrity.json 一致（终审重算）。
- `%TEMP%\cw-paragraph-diag`：`cmd /c if exist %TEMP%\cw-paragraph-diag` → ABSENT（Windows 原生语义，非 Git Bash 映射路径）。
- progress.md 措辞：第 44 行有 2026-10-30 措辞更正记录，声明 replay 表述收敛为"0 spans 时平凡通过；replay不重启模型的证明由既有 integration 测试（mock runner，9例）承载"——append-only 日志以更正记录收敛，符合 PWF 惯例。

## 2. handoff.md/json 与工区实际状态一致性 — PASS

- **git log**：`e173c977`（A seed+调查）→ `cf888f0d`（B 隔离launch+guard）→ `5a33d923`（C 完整性标签+E2E+rev2-5）→ `eab239d9`（独立初审+更正+证据），四提交存在、顺序与 handoff 的 implementation_commits 及审查路径一致。
- **git diff bb5d09c0..HEAD --name-status**：共 **40 文件** = 初审时点 33 件（生产1+探针3+新测试2+PWF4+收据23）+ eab239d9 新增 7 件（delivery 4：handoff.md/json/evidence-integrity.json/review-initial.md；receipts 3：canonical-stderr-diagnosis.txt/canonical-fopen-comparison.txt/full-unit-summary-current.txt）+ progress.md 修改。`git show eab239d9 --stat` 确认该提交**只触及 delivery/、receipts/、progress.md**，与卡的改动边界（生产 owner、探针、W21 测试、本卡 PWF/delivery）一致，无越界。
- **git status**：终审测试复跑后复查 `git status --porcelain` **零输出**（完全干净，无未解释变更；初审时存在的未跟踪 full-unit-summary-current.txt 已随 eab239d9 入库）。
- **pushed_to_remote=false 如实**：origin 已配置（github.com/zhengcb81/company-wiki.git），`git ls-remote --heads origin` 无 w21-pdf-runtime 分支——json 标注与远端实况一致。

## 3. 关键测试复跑 — PASS

命令：`PYTHONPATH=src python -m pytest tests/unit/test_w21_pdf_runtime_launch.py tests/unit/test_w21_pdf_runtime_probe_guard.py tests/unit/test_pdf_paragraph_runtime.py tests/unit/test_pdf_runtime_environment.py -q`

结果：**48 passed, 0 failed**（2.97s）。分文件：launch 5、probe_guard 15、pdf_paragraph_runtime 10、pdf_runtime_environment 18——与初审/手off 的分文件计数逐项一致。

补充复跑：`tests/unit/test_pdf_page_checkpoints.py` → **80 passed**（4.39s）。

## 4. 收据最终抽查 — PASS

- **cold-rev5.json**：`done_no_document=true`、`guard_rejections=0`、`seconds=16.222824`<30（`deadline_seconds=30` 为卡定界未抬）、BOOT flags `isolated/safe_path/utf8=true`、`prefix_name=env`、终态事件 `DONE_NO_DOCUMENT`、`peak_job_commit_bytes=615,989,248`（616.0MB 与 handoff 一致）、`scratch_restored_absent=true`、launch_command 含 `-I -X utf8 -X pycache_prefix=<repo>\__pycache__\pdf-paragraph`、`profile_sha256=bcc42711…`。
- **synthetic-e2e-ascii-alias.json**：`status=unaligned_native_fallback`、`completed_pages=[1,2]`、`stream_complete=true`、`seconds=43.16`（诊断段 42.3866s）、`peak_job_commit_bytes=3,250,298,880`、`cleanup` 三项 true、`python_origin=ascii_alias_diagnostic`、`actual_engine=docling/2.96.0`、`model_sha256=00333a43…`、`converter_instances=1`、`rejected_groups=2`、`alignment_scope=no_aligned_groups_documented_honestly`、`enhanced_claim_valid=false`、`replay_verified=0`。
- **synthetic-e2e.json（canonical）**：`status=native_fallback`、`last_stage=PAGE_1`、`worker_returncode=1`、`completed_pages=[]`、`environment_sha256=c84a984c…`、`cleanup`/`source_preserved=true`/`enhanced_claim_valid=false`——与 handoff"真实入口的观测、fallback与诊断契约在阻点面前行为正确"表述逐条一致。
- **canonical-stderr-diagnosis.txt**：阶段序列 `CWP_PARAGRAPH_STAGE=INPUT→IDENTITY→IMPORT→CONVERTER_READY→PAGE_1`，随后 `RuntimeError: filename does not exists: C:\Users\郑曾波\...\docling_parse\pdf_resources/glyphs//standard/additional.dat`、`CWP_CONVERSION_STATUS=ConversionStatus.FAILURE`、`ValueError: paragraph conversion incomplete`——与 handoff 根因#5 的机理描述（C++ 窄串按 GBK 解析 UTF-8 路径字节 → docling-parse 资源打不开 → 转换失败）**逐行吻合**。
- **ROOT 无损抽验（终审独立重算）**：`runtime-isolated.json` SHA256 = `bcc4271149…` ✓、`cold_probe.py` SHA256 = `bb67326ad9…` ✓，与 handoff.json/evidence-integrity.json/rev5 收据同值。

## 5. 卡 C.5"交接前独立审查"满足度 — PASS

- **初审独立性**：`review-initial.md` 署名独立 agent 并声明未修改代码/测试/收据；内容含大量区别于作者的独立实测（detached worktree 基线对照、icacls 直跑、guard 正反例本机实证、SHA 重算），并给出与作者原稿数字相左的 6 处更正——非"作者换名自签"口吻，可信。
- **修复-复审闭环**：作者以 eab239d9 提交更正与证据（非口头宣布采纳），终审（本报告）为第二次独立复审，报告将保留于 `delivery/w21-pdf-runtime/review-final.md`。
- **作者未自签通过**：handoff.json `review.final.verdict=null`、`generator="W21 implementation lane (author), fields pending final review"`——终审结论由本报告给出，作者未预填。
- 符合卡"保留初审/修复/最终报告，不能作者换名自签或只勾通过；只在这一个大节点审查"。

## 6. handoff 内容字段完整性（卡"输出接口与交接"清单） — PASS（附 2 条 INFO）

对照卡第"输出接口与交接"节逐字段核查 handoff.json（辅以 handoff.md）：

| 卡要求字段 | 状态 | 位置 |
|---|---|---|
| card_id | ✓ | `card_id`/`plan_id` |
| 实际 workdir/branch | ✓ | `workdir`/`branch`（与实况一致） |
| base_commit | ✓ | `base_commit`（bb5d09c0，与卡冻结基线一致） |
| implementation_commits | ✓ | `[e173c977, cf888f0d, 5a33d923]` |
| 最终 tested/reviewed commit 与有关 file SHA | ✓（final 如实 null） | `final_tested_commit=null`、`reviewed_commits.initial_review_target=5a33d923`、`final_review_target=null`；file SHA 固化于 `evidence-integrity.json`（profile/probe/stderr/fopen）与 `cleanup_receipts.root_untouched`（model/config/ROOT 文件 SHA） |
| 逐需求 implemented/tested/PARTIAL | ✓ | `requirements` 10 项，含 `C2-synthetic-e2e-canonical=PARTIAL`、`C2-ascii-alias=DONE-diagnostic` |
| 实际命令/耗时/案例数量/范围 | ✓ | `commands_and_durations`（rev5 16.22s/30s 界、canonical 16.53s、ascii 43.16s）+ `test_counts`（137/237/20/9400+） |
| 冷启动/真SDK与合成入口各证明了什么 | ✓ | handoff.md"冷启动/真SDK/合成入口各证明了什么"三段证明边界 |
| 配置/资源和磁盘共享/新增字节 | ✓ | `resource_config`（界未抬、`limits_raised=false`）+ `disk`（`env_rebuild_or_copy=false`、新增字节 ~160MB git-ignored、ROOT 1,233,549,343 共享字节不变） |
| 故障与清理收据 | ✓ | `root_causes` 1–5 各带 receipt + `cleanup_receipts`（junction/root SHA/env 零写入/incident stash 事故如实） |
| 独立 agent 初审/修复/终审路径及 OPEN | ✓ | `review`（initial 路径+verdict；final 路径）+ `open_items_for_root` 3 项 |
| 兼容局限 | ✓ | `compatibility_limits` 3 条 |
| 是否已推远端 | ✓ | `pushed_to_remote=false`（与 ls-remote 实况一致） |
| 未知 = null/NOT_RUN 不编造 | ✓ | `final_tested_commit/reviewed_commits.final_review_target/review.final.verdict` 均为 null，`pushed_to_remote=false`，generator 注明 pending final review |

INFO-A（流程性，非缺陷）：json 的 `final_tested_commit`、`reviewed_commits.final_review_target`、`review.final.verdict` 当前为 null、`pushed_to_remote=false`——这是**终审前时点的如实状态**，符合卡"未知就是null"。按预期流程，终审通过后由作者执行：将 final commit（本报告被审 commit `eab239d9` 及推送后的远端 SHA）与 verdict 补入 json，随后推送分支。此为终审后的收尾动作，不构成本次审查的阻塞。

INFO-B（笔误级）：handoff.md 第 18 行改动范围拆分"生产 1 文件；探针/新测试 6 文件；本卡PWF+收据 26 文件"中，中间段件数标签与实测差 1：实测 src+tools+tests = **6 件**（含生产，+765/−7）、docs/plans PWF+收据 = **27 件**（+165）；即正确拆分为"生产+探针+新测试 6 件 / PWF+收据 27 件"。总数 33、+930/−7 及各段字节量均正确，仅件数归类表述失准，不影响任何结论；建议作者补记 json 时顺手更正。

## 7. root_causes#5 与 OPEN 项表述 — PASS

- **诊断性定位如实**：ASCII 别名 E2E 在 handoff.md 中被明确表述为"诊断性验证"、收据标注 `python_origin=ascii_alias_diagnostic`、json 状态 `DONE-diagnostic`；"证明：一旦部署路径满足ASCII要求，配置界内SDK增强可运行"，并重申"未拿engine成功签业务召回；对齐质量验收归ROOT真实文档批次"。canonical E2E 如实标 **PARTIAL**（真实入口的观测/fallback/诊断契约行为正确；SDK转换在本机 canonical 路径不可用）。全篇无把 ASCII 别名宣称为 canonical 验收的表述。
- **根因#5 证据链终审独立复核**：终审员未复用作者工件，自行以 `ctypes.CDLL('msvcrt').fopen` 对同一资源路径复现——`exists=True`；**GBK(mbcs) 字节 fopen → OK，UTF-8 字节 fopen → FAIL**；`ctypes.windll.kernel32.GetACP()` = **936**（`chcp` 亦为 936，即系统 ACP=GBK；终审 shell 中 `locale.getpreferredencoding` 显示 utf-8 系 `PYTHONUTF8=1` 会话变量所致，与系统 ACP 无关，不影响结论）。机制、编码环境与 stderr 收据三方互相印证，根因#5 成立。
- **OPEN 项具体可执行**：OPEN-1（部署路径 ASCII 化）给出三个具体选项——env 重定位/ASCII junction 别名（注明诊断已验证可行、零字节拷贝）或机器级 UTF-8 ACP 或上游修复，并说明满足后即达 ASCII 别名 E2E 实测状态；OPEN-2（首跑字节码冷编译 ~67s 一次性代价）给出 warmup 或首文档 fallback 自愈两个具体处置；OPEN-3 明确对齐/召回验收归 ROOT 真实文档批次，本卡不签业务召回。三项均未伪完成、未把本范围缺陷移到 ROOT。

---

## 结论

**终审通过，可交付/可推送。**

- 7 项必查全部 PASS；阻塞项数量：**0**。
- 初审 6 条 INFO 全部落实且有落盘证据（SHA 逐字节吻合、测试/缓存/残留/措辞均实测复核）。
- 终审后预期收尾（不阻塞）：作者将 final commit 与 verdict 补入 handoff.json（当前 null 为如实状态）、按卡推送 `codex/w21-pdf-runtime-20261029` 分支；推送属作者动作，本报告不代执行。
- 遗留 INFO 两条（均不阻塞）：INFO-A（json 终审字段待作者补记）、INFO-B（handoff.md 第 18 行拆分件数标签差 1，建议顺手更正）。
- OPEN 3 项为交 ROOT 的跨层接口需求，表述如实、具体、可执行。
