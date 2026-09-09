# revenue-forecast planning 独立只读审计（2026-09-04）

## 边界与完成程度

- 审计基线：`C:/Users/郑曾波/Projects/revenue-forecast`，HEAD `6b4e3cf`。不修改其产品代码、生产配置、catalog、机器状态、receipt、历史包；只写本审计文件。
- 已完整读取 planning-with-files SKILL。当前 GP 活动组 6 份文档已逐份全文读取；历史巨型文件按下表诚实区分全文、片段与盘点，不把 shell 读取但输出截断冒充语义全文阅读。
- 未运行全套测试、网络、provider、LLM、真实扫描、删除、任务注册或任务执行。
- 唯一动态探针为已从完整源码确认停在 argparse 的 `python -B tools/daily_t2_schedule.py --run-daily`；它返回错误 `the following arguments are required: command`，未进入 runner。
- 原工作树有 `.review-zr407-20260818/`、`.tmp-zr408-unit*`、运行证据与三组 audit 历史包等 untracked；不归本审计修改。

## 核心结论

机器 DAG 已记录 `117/117 accepted`、`plan_status=completed`、`implementation_status=completed`、`current_next=CA-201`、`current_phase=J_final_verification`；此为原 DAG 终局，不是当前 GP 部署/自然时间/产品余项全部完成的证明。scenario registry 197 项均为 passed，但其测试层级和生产产物不能互相替代。

### RF-P01：GP-008 注册 action 仍不能被 CLI 解析（代码确定，部署 action 未知）

- 完整源码 `tools/daily_t2_schedule.py`：`cmd_register` 生成 `"<script>" --run-daily`；`build_parser` 仅接受子命令 `run-daily`，没有 `--run-daily` 兼容分支。
- 安全 argparse 探针实测拒绝：`python -B tools/daily_t2_schedule.py --run-daily` → `required: command`。因此 3552795 加默认 catalog/manifest/report-root 并未修复生成 action 与 parser 的不一致。
- `assurance/runs/daily_manifest.json` 仍为 `20260903T211059Z`，started_at `2026-09-03T21:11:04.545939+00:00`，observation_period=1，ok=true；这是手动运行记录，不证明 SYSTEM 任务触发成功。
- `legacy_periods.json` 仅 period=1/status=observing/hits=0；close_allowed=false，completed window=0。
- 定时任务只读查询：沙箱 `schtasks /query /tn revenue_daily_t2 /xml` 与 weekly 同类查询均显示找不到路径；require_escalated 再查两任务均 `Access is denied`。不能判定任务不存在，亦不能声称已取得真实部署 action。
- `tools/weekly_t3_schedule.py` 完整源码使用正确子命令 `run-weekly`，没有同类 action 拼写缺陷；但真实注册/执行状态同样未知。

建议：GP-008 标为 `blocked_code + deployment_unverified`，保留9/3 owner注册声明作为历史证据；删去“代码落盘即生效、已注册任务无需重注册”的无条件结论。下一步是独立授权的 CLI/action 修复和提权只读检查；不得在文档同步中顺便修改任务。禁止再承诺最早9/6门开，改为只有机器 periods 出现两个 completed 且各≥24h、hits=0后才可进入删除审批门。

### RF-P02：GP-006 不是“真实 roots CI 缺口关闭”

- `.github/workflows/quality.yml` 的 `real-roots` job 实际 `windows-latest`、`continue-on-error: true`。
- 注释明确此 job 为依赖 sibling 的临时数据测试；真实 catalog 测试 `zr806/zr1004/fc1001/fc1003/fc1004/fc1105/preparation_e2e/zr709/zr907/ca202` 不包含，需要 self-hosted production catalog。
- 当前9文件清单与原 GP-006 要求的真实 roots 非阻断覆盖不同。

建议：标为 `partial`（Windows sibling CI 接线已实现；真实 roots 阻断式 CI 覆盖未完成/待运行环境决策），不能继续写 D-3 closed。不能因为其他 CI green 推断这个 non-blocking job 证明完成。

### RF-P03：GP-010 顶部待批准、末尾待批准与批准记录冲突；部分验收未完成

- `gp010_cohort_cutover_request.md` 已有9/3 owner批准记录，却仍顶部“待批准”、末尾“等待KD-08批准后执行”。
- 同文件实际执行：normalized 7/7、review receipt 7/7、summary 6/7；1/7 国联民生因 `_FORBIDDEN_OUTPUT` 三次拒绝；sections=0，broker_research 分节为已知产品缺口。
- 验收栏要求每份3 artifacts、无安全门命中、调用次数7，显然与记录不符，不能统一勾选完成。
- GP task_plan §5 仍“申请文档完成，待KD-08批准”，同组 progress 已写实际执行完成；后者过度笼统。
- 当前 registry 197/197 passed 是机器登记事实；例如 BR-11 指向 `BR_11.json`，内容是 wiki `tests/contract/test_zr504_page_fidelity.py` 10 passed（2026-09-03T09:27:30.901399+00:00），tier=T1。它不证明生产七研报 sections 已生成；该条 fixture_hash/oracle=null。

建议：GP-010 显示 `authorized / partial_execution / safety_rejection_expected / sections_gap_open`；申请准备已完成和授权已获得分别注明。不要重写历史 registry 或为了字面完成绕过安全门。将“BR仍blocked”旧句限定为当时生产语义验收，另说明当前 registry 的T1 passed与production sections=0并存。

### RF-P04：N-1 文件状态、映射、窗口与批次说明漂移

- 顶部待批准与末尾owner A+B批准矛盾；§5尚未开始与已有手动period1矛盾；末尾仍“批1→2→3每批独立commit”与§3.2批1+2必须单commit矛盾。
- §2 successor 映射不同于冻结 `assurance/unified_completion/legacy/legacy_disposition.json`。正确映射：

| 旧项 | 冻结registry successor |
|---|---|
| FC-1501 | CA-107 / CA-108 / CA-109 |
| FC-1502 | CA-301 / CA-303 |
| FC-1503 | CA-302 |
| FC-1504 | CA-206 / CA-304 |
| FC-1505 | CA-305 / CA-306 |

建议：保留owner批准历史，修正说明表（不改冻结registry），勾选“owner批准记录”，将运行验证、删除与最终复扫保持未完成。状态写“已获A+B批准，未执行删除；GP-008代码阻塞、实际部署action待查；0 completed窗口”。批次统一“revenue批1+2单commit，随后wiki批3独立commit，逐提交全矩阵验证/可revert”。

### RF-P05：当前状态入口与根三件套需要路由覆盖，不应改写历史

- 根task_plan/findings/progress开头都仍是8/18 ZR-408停点；真实state中ZR-408已经accepted，末端CA-201已终局。
- 根`TERMINAL_NOTICE.json` covers明确包括三件套，status=`closed_superseded_incomplete`；应保留历史，不覆盖旧日期记录。
- `audit_review/README.md` §0 已completed，但正文仍“现在只能领取CA-001”“当前卡CA-001”；它被 `plan_inputs.json` 的 control_page_sha256绑定，不能普通追加后偷偷重算冻结证据。
- `assurance/runs/session-2026-08-13/task_plan.md` 首个“最新状态”是ZR-206，其尾部已到9/1终局；progress尾部9/2已创建GP续接。session组现应归“实施历史/GP之前的工作记忆”，不是当前唯一活动组。
- `review_audit/task_plan.md`、`IMPLEMENTATION_PLAN.md` 仍把FCAP r2当后续入口；已被terminal/state接管，不能从其pending开工。

建议：创建未hash绑定的当前状态入口（如`PLANNING_STATUS.md`或本次同步索引），统一解释：原DAG终局、活动GP状态、历史根/旧审计/隐藏克隆只读、不再领取旧CA/FC/WU/ZR。冻结包保留原字节，通过索引逐文件处置；若更新README控制面必须走显式plan-drift/CAS版本化，不能只为美观修manifest。根三件套在已冻结边界下同样以外部入口覆盖为优先。

## 逐文件处置建议（活动6文件均已完整读取）

路径以下均相对 revenue-forecast 根。

| 文件 | 全文覆盖 | 建议处置 |
|---|---|---|
| assurance/runs/2026-09-02_remaining-gap-closure/task_plan.md | 是，146行/11453 bytes | 重写§5当前状态；保留原实施要求作基线；GP006 partial、GP008 blocked、GP009仅历史注册/自然证据未完、GP010授权后部分执行 |
| assurance/runs/2026-09-02_remaining-gap-closure/findings.md | 是，78行/5501 bytes | 顶部声明A~D是9/2审查快照；增加9/4最新纠偏，A-2“空值短路，不放行”应是旧缺陷“空值短路导致放行”；不得把旧0-artifact/197pending当现在 |
| assurance/runs/2026-09-02_remaining-gap-closure/progress.md | 是，135行/21138 bytes | 状态总览删除“GP001~010全部完成/剩余只自然时间”；修GP006/008/009/010行，追加9/4只读审计和未知部署状态；旧日志不抹除 |
| assurance/runs/2026-09-02_remaining-gap-closure/gp008_009_deployment_guide.md | 是 | 修“无需重注册”；手动catalog应使用默认值或`../company-wiki/.source_catalog/catalog.sqlite3`，现写revenue/.source_catalog错误；不得自动执行注册/手动run |
| assurance/runs/2026-09-02_remaining-gap-closure/gp010_cohort_cutover_request.md | 是 | 头尾改已批准/部分执行；保持未满足验收，区分registry T1与生产语义；历史批准原文保留 |
| assurance/runs/2026-09-02_remaining-gap-closure/n1_r9_removal_request.md | 是 | 正确映射、已批准/未执行、0completed窗口、批1+2单commit统一；不重发批准 |
| audit_review/README.md | 是（1~235在前次输出，236~EOF另读） | hash-bound控制面；外部入口说明冻结旧指令，不普通编辑 |
| IMPLEMENTATION_PLAN.md | 是，130行 | 历史只读；索引覆盖FCAP旧入口，不执行pending；阶段总览与内嵌pending为历史漂移 |
| audit_review/task_plan.md | 是，246行 | 历史归档已声明，不追加新实施；索引引用 |
| review_audit/task_plan.md | 是，51行 | 历史审查完成；索引纠正过时FCAP入口 |
| task_plan.md | 仅首段明确语义覆盖；全量输出被截断 | 根terminal覆盖的历史，2680行/153125 bytes；不得声称全文已读 |
| findings.md | 1~65明确语义覆盖；全量输出被截断 | 根terminal历史，1434行/160038 bytes |
| progress.md | 1~65明确语义覆盖；全量输出被截断 | 根terminal历史，1870行/164460 bytes |
| assurance/runs/session-2026-08-13/task_plan.md | 1~100、440~EOF片段，非全文 | 519行/81160 bytes；历史session，添加外部当前路由；不把ZR206首段当当前 |
| assurance/runs/session-2026-08-13/progress.md | 尾部1046~1119及此前尾读，非全文 | 1119行/208649 bytes；9/2已明确交接GP组 |
| assurance/runs/session-2026-08-13/findings.md | 尾35行，非全文 | 314行/55565 bytes；历史事实与教训，不追写GP状态 |
| assurance/runs/session-2026-08-13/panorama.md | 仅盘点 | 63419 bytes，同组概览必须纳入处置索引 |
| audit_review/findings.md | 头12行，仅片段 | 历史归档声明+只读索引；595行/75796 bytes |
| audit_review/progress.md | 头12行，仅片段 | 历史归档声明+只读索引；270行/38897 bytes |
| review_audit/findings.md | 头10行，仅片段 | 历史审查；184行/16417 bytes |
| review_audit/progress.md | 仅盘点 | 历史审查；360行/25770 bytes |

## 冻结历史与隐藏副本索引

### 全文覆盖追加（后续读取，覆盖前表“仅盘点”状态）

以下均已读取到EOF，工具返回未截断（FCAP在两段组合输出遭中部总预算截断后，另读301～410行补全缺口）：

- `review_audit/roadmap.md`：全文；原R1～R9根因路线已superseded，FCAP链接只是历史路由，不能继续实施。
- `audit_review/2026-08-08_adversarial_plan/task_plan.md`：1～230、231～655全文。旧WU全部pending与审查completed分开；文件顶部已superseded，内部“config-only即可”后被本文件§9调查否定。
- `audit_review/2026-08-09_data_lake_refactor_plan/task_plan.md`：1～420、421～840、841～1260、1261～1625全文。74卡/旧WU与旧72/84场景停止推进，由FCAP接管；当前不可从WU1500等指令执行删除。
- `audit_review/2026-08-09_full_completion_assurance_plan/task_plan.md`：1～330、331～650及301～410补读，全文。历史Phase9标题in_progress与FC906 complete并存，Phase13 67/71与旧账66/71不一致；原数据不改，当前外部状态入口解释原DAG已由CA/ZR继承。
- `audit_review/2026-08-12_zijin_skill_run_audit/task_plan.md`：90行全文。只证明8/12真实运行审计完成，不是产品或投资研究的新执行入口。
- `audit_review/2026-08-13_three_repo_completion_rebaseline_plan/task_plan.md`：121行全文；编制A～F completed、实施A～J pending是冻结当时状态，已由state终局接管。
- 同组`authoritative_execution_plan.md`：190行全文；只读A～J annex，明示README是唯一领取入口，不能独立领取。
- `audit_review/2026-08-13_zijin_data_lake_remediation_plan/task_plan.md`：298行全文；92 ZR和六目标需求规范，计划P0～P2 completed不表示产品完成；后由CA主链吸收。
- 同组`dynamic_assurance_plan.md`：145行全文；“有脚本不等于实际运行”和7/2/1/1自然证据要求不能由registered状态代替。
- 同组`migration_rollout_plan.md`：134行全文；12波次是历史规范，真实cohort/删除需当次授权和自然时间门，禁止自动照跑。
- 同组`legacy_plan_disposition.md`：77行全文；只读投影，KEEP/REOPEN是8/13时点，不是当前卡片状态。

### 活动GP可编辑边界复核

- 在可读`assurance/`、`audit_review/`、`compatibility/`、`.github/`及全仓JSON/manifest/snapshot字面查找，未发现GP活动目录或3辅助文档名被hash绑定；44-entry plan_inputs不含GP组，六冻结old-plan dirs不含GP组。
- 已在本审计目录准备`revenue-docs.patch`（apply_patch格式，未应用到源仓）：六个GP文档各加当前状态覆盖，保留历史日志/批准原文；部署指南手动catalog路径另作精确更正。无代码、state、receipt或manifest更改。
- company-wiki四个历史docs/plans组未在revenue可读manifest/json中找到确切Markdown hash绑定；仅CodeGraph freeze引用portfolio的Python文件、legacy closure ledger泛称docs/plans。它们仍建议sidecar，不改旧正文。
- CA-306契约明确六个revenue日期audit目录的唯一可新增文件为TERMINAL_NOTICE；因此不要在那六目录新放CURRENT_STATUS。统一状态sidecar应放在根或新审计目录，不改变冻结目录文件集合。

- `assurance/unified_completion/manifests/plan_inputs.json`完整读；44 entries 全部重新SHA-256核对，mismatch=0。它绑定8/9 FCAP及8/13 rebaseline/remediation多份planning/findings/progress/规范，不能因过时而重写。
- 六个日期audit包均有`TERMINAL_NOTICE.json`，作为不可改历史/规范：`2026-08-08_adversarial_plan`、`2026-08-09_data_lake_refactor_plan`、`2026-08-09_full_completion_assurance_plan`、`2026-08-12_zijin_skill_run_audit`、`2026-08-13_three_repo_completion_rebaseline_plan`、`2026-08-13_zijin_data_lake_remediation_plan`。
- 每包task_plan/findings/progress已盘点但尚未逐份全文语义阅读；同组`plan_self_audit`、`PLAN_MANIFEST`、`legacy_plan_disposition`、`migration_rollout_plan`、`dynamic_assurance_plan`、`command_registry_plan`、`code_quality_plan`、`authoritative_execution_plan`也纳入保留索引。
- `.review-zr407-20260818/filing-fetch/`含三件套；`.review-zr407-20260818/company-wiki/`含根三件套、task_plan_v2、task_plan_cw_recovery_20260725、review_plan、verification_CW-2.24_plan，以及docs/plans四组三件套（catalog-space-remediation/core-section-extraction/portfolio-reuse-automatic/portfolio-reuse-fix），还有docs/archive六份`*PLAN.md`。这是历史独立review克隆，不是第三份活动执行队列；不修改、不删除，仅在当前入口注明快照性质。此部分目前盘点覆盖，不是全文语义覆盖。
- 可读`.tmp-zr408-unit`、`-retry`、`-final`是测试fixture；本轮rg精确plan文件模式未发现其planning副本。不可访问tmp内是否含副本未知。

## 访问限制与审计错误

- 2026-09-05 续读时一次 PowerShell `foreach {...} | Sort-Object` 再次触发 empty pipe element ParserError；未产生任何写入。后续统一先累计 `$rows` 再排序，避免重复该写法。

### 2026-09-05 续读完成：session `task_plan.md` 与 `findings.md`

- `assurance/runs/session-2026-08-13/task_plan.md` 已通过既有 1～100、440～EOF 片段和本轮 101～439 补读形成 1～519 无缺口全文覆盖。它是按时间追加的工作记忆：从 `CA-001`/`ZR-206` 等旧停止点推进到 117/117 终局，再到 8/31 push 与 9/1 CI 修复；文件自身已明示唯一执行入口另有其页。其所有中间 `current_next` 均是历史快照，不能作为今日领取指令。
- `assurance/runs/session-2026-08-13/findings.md` 已通过本轮全文输出及 134～201 精确补读形成 1～314 无缺口全文覆盖。该文件保留了从控制面、Windows/CAS、真实 49GB catalog、ZR/CA 实施到终局/CI 修复的调查链；其中旧生产事实与流程教训可作证据，但不能代替 9/4 GP 动态状态和自然时间证据。
- `assurance/runs/session-2026-08-13/progress.md` 已补读 1～300；该段覆盖 CA-001 至 ZR-406 的逐卡日志以及多次停止点。当前尚在继续补读 301～1045；既有 1046～1119 尾段仍保留为已读。
- `assurance/runs/session-2026-08-13/progress.md` 续读已到 600：301～450 记录 ZR-407/408、阶段 D 出口、阶段 E 与 F1 入口；451～600 记录 F1 及 F2 至 ZR-608。该日志多次出现“实现完成但尚未复核/closure”、随后才 accepted 的序列，进一步证明不能抽取中间标题作为今日状态。
- `assurance/runs/session-2026-08-13/progress.md` 续读已到 900：601～750 覆盖 F2、阶段 G、ZR-902～905；751～900 覆盖 ratchet、渐进发布、legacy 门及 CA-202/203。这里的 ZR-902/903 与 CA-202/203 是历史验收/测试记录，不证明 9/3 之后的实际 Windows 任务注册 Action 或自然触发已经成功。
- `assurance/runs/session-2026-08-13/progress.md` 已完整覆盖 1～1119：本轮补完 901～1045，并复读 1046～1119。尾部确实以 8/31 原 DAG 117/117、9/1 CI 修复结束，9/2 明确创建新的 GP 组并交接；因此 session 组整体只能列为历史工作记忆/证据链，不能和当前 GP 状态并列为两个活动入口。
- `assurance/runs/session-2026-08-13/panorama.md` 已全文覆盖 1～539：整文件输出的中段 188～376 另以两段补读，无缺口。它按时间堆叠许多快照，顶部仍留 43/117、ZR-501 等旧视图，尾部才到 117/117 与 9/1 CI；其正确处置同样是历史快照，由根状态页路由，而不是改写冻结工作记忆。
- `audit_review/2026-08-08_adversarial_plan/findings.md` 已补读 1～320。前半从三仓架构与真实数据根调查推进到“物理 data lake 已成形、语义 data lake 未成立”，并明确早期 `Dropbox config-only` 结论已被真实 resolver 探针证伪；这些是后继 WU/FC/CA/ZR 计划的历史输入，不是今日未关闭事项清单。继续补读 321～597。
- `audit_review/2026-08-08_adversarial_plan/findings.md` 已完整覆盖 1～597。本轮 321～597 补读包含专项矩阵、风险登记和 F-037～F-060；最终裁决明确 `config-only` 不成立、真正耦合集中在 ingest/semantic normalization。该整包已有 TERMINAL_NOTICE，正文保持冻结；其旧 WU 后续项不从本页重开。

### 2026-09-04 补读检查点：根 `task_plan.md` 1～1200

- 已逐行读取根 `task_plan.md` 1～1200（总2680行）；本段仍是2026-07-26～30的旧13 Phase计划，顶部8/18 ZR-408停止点和8/9 superseded声明已明确说明它不是当前活动队列。
- 1～1200中 Phase 2～9 大量 `completed_in_name_only → reopened` 与未勾选条目是 `verify_plan_claims` 在历史计划上的审计结果；不得据此重新领取。尤其 Phase 9 的“找不到canonical filing-fetch repo”已被后来三仓创建/实施事实取代。
- 本检查点只声明1～1200全文覆盖；1201～2680仍待逐行补读。

### 2026-09-04 补读完成：根 `task_plan.md`

- 已逐行读完1～2680；先前1801～2400组合输出中2001～2200被截断，随后单独补读2001～2200，现无行段缺口。
- 该文件自身包含多层相互覆盖的历史状态：早期Phase 2～14机器复核标为reopened，后续“当前执行状态”称Phase 1～20完成，再于2421起并入8/3审查的A～D整改及8/4完成表；顶部8/18又覆盖为ZR-408停止点。它因此只能作为累积历史账，不适合作今日领取入口。
- 关键漂移已在后续CA/ZR/GP体系解决或重新定义：例如Phase 9找不到canonical filing-fetch、Phase 19 `pending`、8/3 Critical审查，均被同文件后续完成表以及外部state/registry接管。应由根`PLANNING_STATUS.md`显式路由，不改写2680行历史。

### 2026-09-04 补读完成：根 `findings.md`

- 已逐行读完1～1434；最初1～600组合输出漏掉161～406，随后专段补齐；其余按150/120行块读到EOF，现无缺口。
- 文档是7/26初审、7/31～8/1真实运行故障、8/3独立审查的累积事实账；顶部8/18 ZR-408停止点覆盖“当前”，但不应抹去早期证据。后续CA/ZR accepted和GP续接应由外部状态页解释。
- 内部历史时点互相覆盖是预期但易误读：例如末尾1423～1430已写invest-core CodeGraph初始化并给出结构证据，1432～1434却保留更早的“未初始化/需授权”限制；这证明根文件不适合作单一当前状态页。
- 与GP最新审计相关的长期证据仍成立：历史文件多次区分“注册/测试/哈希通过”与生产语义及自然时间证据，支持把GP-006/008/009/010标为partial/blocked/未完成，而不是按旧completed标题放行。

### 2026-09-04 补读完成：根 `progress.md`

- 已逐行读完1～1870，按100行块并以末段90行块到EOF，无输出截断和行段缺口。
- 它从7/26审计、7/28～8/4实施一直累积到顶部8/18 ZR-408暂停点；正文同时保留多次“全部完成”、稍后复盘发现未完成、再实施关闭的历史序列。顶部8/18 `current_next=ZR-408`也已被后续session/state/terminal接管，不能继续当今日游标。
- 历史日志本身揭示了状态表误读风险：多处先写pending/blocked，后面完成；也有“全量环境spawn损坏”随后纠正为测试闭包不可pickle。这些应保留为证据链，但统一由新根状态页明确“历史日志，不是当前领取指令”。
- 根三件套现均全文覆盖；先前表中“根巨型三件套尚不能声称全文”应撤销。

### 追加全文覆盖（历史同组附件，2026-09-04）

- `review_audit/findings.md`：184行全文；`review_audit/progress.md`：360行全文（组合输出中部截断后补读1～100，全部缺口已补）。该组确有R1～R9完整实施历史及后续FC502～604，但最后“下一FC604”已过时，仅保留历史。
- `audit_review/findings.md`：595行全文，分1～200、201～400、401～595及1～35补读；`audit_review/progress.md`：270行全文，分1～135、136～270及231～270补读。原归档说明已要求从session/state读取，不应再追加逐卡进度；最后83/117/ZR902是8/23历史，不是当前。
- `2026-08-09_data_lake_refactor_plan/{findings.md,progress.md}`：184/169行全文。虽progress含8/10、8/11旧legacy观察h>0与period5下一步命令，这些是冻结历史，不得与9/3新period1混为连续观察，也不应照抄旧命令执行。

- `2026-08-13_three_repo_completion_rebaseline_plan/{findings.md,progress.md}`：分别190/53行全文；`2026-08-13_zijin_data_lake_remediation_plan/{findings.md,progress.md}`：分别192/38行全文；`2026-08-09_full_completion_assurance_plan/progress.md`：47行全文。全部保留为编制/实施历史，不从当时pending重开卡。
- FCAP组 `plan_self_audit.md`、`legacy_plan_disposition.md`、`dynamic_assurance_plan.md`、`command_registry_plan.md`、`code_quality_plan.md`、`implementation_runbook.md`、`execution_matrix.md`：全文。组合输出中部截断后，command/code_quality两份单独补读全文，现无缺口。旧总账的“当前唯一r2/68 implementation FC/95 mandatory”是8/9快照；后由117 CA/ZR及197场景取代。动态计划明确历史complete不等于当前健康、真实层不可替代，支持GP006/008不完成的判断。
- 两个8/13组的 `PLAN_MANIFEST.md`、`plan_self_audit.md`：全文。前者明示分别12/14内容文件hash冻结，以及唯一领取入口README；不得把manifest内pending/首卡ZR001或CA001按今日执行。
- remediation `implementation_runbook.md`：全文。属于冻结92ZR规范，20步、层级不可替代、自然时间要求仍是证据解释规则；不作为恢复旧执行队列的授权。
- 新确认：FCAP历史 `legacy_plan_disposition.md` §4精确列出company-wiki四个docs/plans路径并给历史处置，但它只是文字状态索引，不是这四组原文的hash绑定；这一“被引用”和“被hash绑定”须明确区分。

- rg拒绝访问：`.tmp-zr409-review`、`.tmp-zr409-review2`、`.tmp-zr409-review3`、`.tmp-zr501-review`、`.tmp-zr501-review2`、`.tmp-zr501-review3`、`.tmp-zr501-r1`、`.tmp-zr501-r2`、`.tmp-zr501-r3`、`.tmp-zr501-delta1`、`.tmp-zr501-delta2`、`.tmp-zr502-t1`、`.tmp-zr502-t2`。
- 递归目录列表另拒绝`assurance/unified_completion/.pytest_cache`、`audit_review/2026-08-09_data_lake_refactor_plan/.pytest_cache`；均不是已确认planning覆盖。
- 最初把根三件套一次Get-Content输出造成截断；已记录不计全文。某次组合输出也被上限截断，后续活动文件单独读取解决。
- 一次PowerShell foreach直接接管道ParserError，随后先赋值rows再ConvertTo-Json解决。
- CodeGraph可查询但run_daily未命中（返回无关run_family），故已知文件完整源码读取；不从图无结果推断无代码。
- 误查`assurance/unified_completion/TERMINAL_NOTICE.json`不存在；正确位置是根及六旧audit包。
- Task Scheduler提权只读查询仍Access denied；需要owner自己导出任务Action/LastTaskResult，不能据权限失败标missing。

### 2026-09-05 续读：8/8 `progress.md` 中段

- 已复读本审计总计划，确认当前仍处于“全文覆盖 → 证据分层 → 仅同步审计文档”阶段；冻结包正文及 revenue 仓均不写入。
- `audit_review/2026-08-08_adversarial_plan/progress.md` 已补读 201～600。该段是 WU-6.2 至 WU-4.1 的历史回执，包含多处 `pending independent review`、后续 reviewer 修复及 mutation 证据；这些时点状态由后继 FC/CA/ZR 接管，不能按中段的 pending 重新领取，也不能将当时测试通过外推为 9/5 生产运行健康。
- 同文件已补完 601～992；组合输出在 801～900 中段截断后已单独复读该段，现结合既有 1～200 形成 1～992 无缺口全文覆盖。后段从 WU-3.3 回溯到 WU-0.1，并追加 8/9 架构调查的最终裁决；该文档最终状态是 `completed_audit_only`/由后继计划接管，不是当前执行队列。
- `audit_review/2026-08-08_adversarial_plan/closure_ledger.md` 1～142 全文覆盖。账本自己明示 99 行中 5 行在当时仍 partial，禁止“全部消除”的说法；这是 8/8 历史闭包，后续状态仍须按 CA/ZR/GP 证据更新。
- FCAP `architecture_target.md` 1～123 全文覆盖。它是目标不变量（控制面所有权、RootPolicy、normalized metadata、activation/rollback、artifact compatibility），不是完成回执；当前 GP 的 Windows 任务/自然触发问题不能从该目标文档推定已实现。
- FCAP `findings.md` 已全文覆盖 1～558；两次组合输出截断的 161～320 与 321～464 均另行精确补读。该事实账从 r2 编制、FC-101 起一直累积到 R8/R1 组合翻转，包含多次“测试绿但生产空”、真实 T2/T3 暴露缺陷及 reviewer 误重置用户 dirty 文件的过程教训；最终 8/13 的 R9 自然观察仍是后继 CA/ZR/GP 接手的历史起点，而非 9/5 当前完成证明。
- FCAP `fc_904_change_contract.md`（82行）、`fc_906_preflight_blocker.md`（51行）、`fc_execution_packet_template.md`（104行）与 `independent_review_protocol.md`（78行）均全文覆盖。前两件是特定历史 FC 的变更边界/阻塞快照，后两件是执行和独立审查协议；共同要求未知计数 fail、不同 agent/干净 worktree 复核、真实层不被 mock 替代。它们支持当前审计保留 UNKNOWN 与独立审查门，而不直接证明今日状态。
- FCAP `scenario_matrix.md` 1～197 全文覆盖，明确 95 个 mandatory scenario、T0～T4 不可替代与真实层 blocked 不能算 pass。
- FCAP `work_unit_registry.md` 1～162 全文覆盖；组合输出仅 line 46～47 被截断后已补读 40～58。该表的最终历史快照是 FC-1304 accepted、FC-1501～1505 pending；它后续已由 CA/ZR 完成链和 GP 维护链接管，不能把旧 pending 当当前活动 backlog，也不能把历史 accepted 外推到 9/5 任务注册/自然触发健康。
- 旧 data-lake `implementation_runbook.md` 已按 1～190、191～380、381～570、571～760、761～952 分段全文覆盖，无缺口。文件顶部已标 `superseded_by_FCAP-r2`，74 张 WU 卡、命令字典和 reviewer 规则只保留历史需求/失败证据；尤其末尾已记录后台 worker 会造成 catalog 字节哈希抖动，稳定指纹必须用真实根快照与 catalog 聚合，不能误把 ambient writer 的字节变化当产品完成或失败。
- 8/12 紫金审计 `findings.md` 已全文覆盖 1～589；组合输出漏掉的 201～260、559～589 已单独补读。它给出当时真实慢/失败链：只读 resolve 在 `CatalogStore.__init__` 触发 WAL/DDL/migration/fingerprint seed，与后台 writer 争锁；SQLite lock 又未归一成可重试 `catalog_locked`，所以 reuse-only 可等待约60秒后 fatal。这是历史根因证据，但仍需以 GP 当前代码/调度证据判断是否已修复。
- 同组 `progress.md` 已全文覆盖 1～126，记录 111 个动作并明确后台 worker/其他 agent 并发使整库字节不变不可归因；第三轮只证明内部 exact reuse/零下载，revenue-ready 仍被 `not_reviewed` 阻断。递归盘点确认该包另有 10 份 Markdown 附件/trace，继续逐份覆盖，不能只读顶层三件套便称整包完成。
- 8/12 紫金审计包的全部 13 份 Markdown 现均全文覆盖：除三件套外，`audit_report.md` 268行、`RUN_MANIFEST.md` 86行、`TRUST_BOUNDARY.md` 71行、`dropbox_broker_report_audit.md` 46行、`mine_coverage_matrix.md` 84行、`outputs/draft_report.md` 115行、`sources/README.md` 5行、`trace/filing_fetch_events.md` 73行、`trace/source_review.md` 24行、`trace/web_events.md` 59行。它们共同界定为 8/12 隔离 draft/审计历史，未实施产品修复；manifest 只认证封存时快照，不能认证后续代码或 worker 状态。
- 8/13 three-repo rebaseline 包的 15 份 Markdown 现全部全文覆盖。本轮补齐 `completion_assurance_registry.md` 206行、`completion_audit.md` 91行、`current_state_audit.md` 115行、`input_snapshot.md` 56行、`legacy_fc_status_registry.md` 107行、`legacy_transition_matrix.md` 130行、`project_goal_and_pain_points.md` 133行、`traceability_and_acceptance.md` 117行、`weak_model_execution_checklist.md` 148行；此前已覆盖该包其余六件。
- 该包的关键处置是：旧71 FC 在 8/13 严格投影为 I=31/C=26/S=9/P=5、current verified complete=0，并由 CA/ZR successor 接管；这不是说资产全无，而是拒绝历史 receipt 自动继承。后继 session 已把 CA/ZR 做到终局，因此当前必须再由 GP 状态页路由，不能停在 8/13 `CA-001 current_next`。
- 8/13 Zijin remediation 包的 13 份 Markdown 现全部全文覆盖。本轮补齐 `architecture_target.md` 237行、`scenario_matrix.md` 193行、`traceability_matrix.md` 85行、`work_unit_registry.md` 174行；此前已覆盖其三件套、`PLAN_MANIFEST.md`、`plan_self_audit.md`、`dynamic_assurance_plan.md`、`implementation_runbook.md`、`legacy_plan_disposition.md`、`migration_rollout_plan.md`。architecture/scenario/registry 是冻结目标与验收合同，不是当前实现证明。
- `assurance/fc/` 的 16 份 Markdown（801行、96,397 bytes）已逐份全文覆盖，包括 8 份 WU/波次/变更合同、5 份独立 reviewer 报告及 mutation evidence。它们是 8/11～8/13 的历史执行与评审证据：例如 FC-1204 经 r1/r2 拒绝、r3 才 accepted，Phase-14 的 R9 当时仍受自然时间门阻塞；不得只取文件标题或早期 verdict 覆盖后续状态，也不得将当时 accepted 外推为 9/5 的 Windows 调度健康。
- `assurance/unified_completion/` 已全文读到排序索引 0～73：README、CA-001～CA-306 卡/RED、ZR-001～004、ZR-1001～1009、ZR-101～102（其中 CA-105 目录只有 RED、没有 `00_wu_card.md`，如实按实际文件集计数）。这一段完整呈现“先 RED、再卡级验收、再 reviewer/closure”的历史治理链，也反复区分“产品代码零改动的验收卡”和“真实部署/自然时间动作”；因此 117/117 卡状态不能证明 Task Scheduler 已正确注册，也不能把 CA-304 的门测试等同于真实 legacy 删除。
