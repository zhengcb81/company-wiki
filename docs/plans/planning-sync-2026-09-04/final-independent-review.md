# 最终独立文档审查

审查日期：2026-09-04～2026-09-05  
审查方式：独立 agent、只读核对；本文件是唯一审查写入。  
阶段：**第一阶段 PASS；第二阶段预应用审查 PASS**。revenue-forecast 补丁只有在下列HEAD/CAS均未漂移时可应用；应用后仍须做最终diff与冻结证据复核。

## 复核日志

- 2026-09-05：按 planning-with-files 续读主审计 `task_plan.md`、`progress.md` 与本文件；第一阶段仍未闭环，当前首要风险仍是 inventory 的读取状态落后于已完成的两份全文覆盖报告。
- 2026-09-05：逐项重算 inventory 所列文件的长度与 SHA-256。除 `PLANNING_STATUS.md` 外，已列文件均与 inventory 的内容指纹一致；该入口现为 4,397 bytes、`ffc0bedd7cf43250ff4c3d74264d2d5e2f7cc0d1d58997ef5c8a27879f5fb829`，inventory 仍记录旧的 3,922 bytes / `d2f179...`。此外 reviews、根大文档、v5 investigation/history/plan 的 `read_status` 仍未承接已经完成的覆盖报告。
- 2026-09-05：全文复核 company-wiki 六个当前入口与两份独立覆盖报告。六个入口均将旧 completed/测试数/运行态限定为历史，不会恢复 legacy writer、旧 Strategy A、worker、生产写或旧 GP；根报告完整记录 8,600/8,600 行及十个根对象指纹，v5 baseline 报告完整记录 13 份 Markdown、6,691 行，并明确“全文覆盖≠技术/冻结/实施 PASS”。但 reviews/history/investigation 的完整复读尚未在一个可核对的覆盖表中封板，只有叙述称由主任务另行负责；inventory 又仍标 pending，因此不能把该部分算作已证明的全量覆盖。
- 2026-09-05：六个入口提取到的本地 Markdown 链接均解析到预期仓库位置（最终表仍需输出 `Exists` 失败清单复核）。审查期间 company-wiki HEAD 已从入口记载的 `a0c7629...` 前进到 `853dca2...`，因此“代码基线”若不注明是审计冻结点会被读成当前 HEAD；最终入口需要明确审计基线与当前 HEAD 的区别，并检查期间变更是否影响事实结论。
- 2026-09-05：六个入口共 19 个本地链接，机械解析 `BROKEN=0`。`TERMINAL_NOTICE.json` 仍为 `b3f3ceb2...`；真实 v5 import manifest 路径是 `source-catalog-worker-recovery-v5-2026-09-03/import_manifest.v5.json`，SHA-256 仍为 `da7d116e...`。`a0c7629..853dca2` 只有 section extractor 与其 contract test 共 237 行新增/2行删除；它增加 broker_research 代码能力，但没有提供已对七份生产文档重新生成 sections 的证据，所以旧执行记录 `sections=0` 仍只能按日期保留，不能改称已生产闭环。
- 2026-09-05：全文复核 filing-fetch 当前 `PLANNING_STATUS.md`、已修改 `e2e/E2E_DESIGN.md` 与独立审计。Git 仅显示 `E2E_DESIGN.md` 17增/18删及新增状态入口；收据与 terminal notice 指纹保持 `010699...`、`bcfb14...`、`b3f3...`。应用后的 E2E 文本与独立审计逐条建议一致，正确收窄了 hermetic、全字段、退出码、自动 pre-commit 和三仓全链路等旧过度声明；没有把静态核对冒充重跑。
- 2026-09-05：filing 两个当前文档共 6 个本地链接，`BROKEN=0`；HEAD 仍为 `89c8bdb...`。当前文档 SHA 为 `PLANNING_STATUS=0392929f...`、`E2E_DESIGN=89bda8fa...`。先前 `patch-review.md` 的 scoped PASS 精确绑定 `filing-docs.patch=68678884...`，且明确要求应用后复核；本轮已完成应用后内容/diff/链接/冻结哈希复核。该 PASS 不扩张为功能、CI、E2E、117项或 receipt-binding PASS。
- 2026-09-05：审查过程中主任务按行动项更新了 `company-inventory.json`。重读当前文件得到 56 项且 `read_status=full` 56/56，`PLANNING_STATUS.md` 已同步为 4,397 bytes / `ffc0bedd...`；因此上文“inventory 落后”是修复前发现，不再是当前阻断项。仍需对这 56 项逐一重算指纹并检查清单边界后才能关闭。
- 2026-09-05：已对更新后的 56 项逐一重算现文件长度/SHA，`BAD=0`。`docs/plans` 排除本次审计自身后共有 40 份 Markdown，40/40 均在 inventory；`docs/archive` 原有 16 份 Markdown（加新 `CURRENT_STATUS` 共17份）的名称也被当前 sidecar 完整列出，且 sidecar明确这16份是历史关联材料、不是活动三件套。inventory 的元数据范围说明“archive companions separately recorded”，因此不要求把全部16份重复塞入 JSON，但最终报告须保持这个限定，不能称 JSON 单独等于全仓清单。
- 2026-09-05：重读更新后的 v5 覆盖报告，已新增主任务封板表：当前入口/reviews/history/investigation 共 10 份、2,053 行，逐文件列出行数与 SHA 前缀；与 baseline/plan 13份、6,691行合并，v5 Markdown 覆盖边界闭合。表内继续明确机械 import 校验不等于技术评审、冻结或实施授权，并逐条保留每个关键节点独立 D/G 或 D/OP/G 阻断审查要求。
- 2026-09-05：主任务同步修正了 company 根入口的并发 HEAD 漂移：现写明审计冻结起点 `a0c7629...`、封板前观测 `853dca2...` 及二者之间仅 BR section extractor/contract test 变化，并明确代码能力推进不证明七份生产 sections 已闭环。inventory 中该入口的 4,731 bytes / 36行 / `ff16f8bf...` 与当前文件完全一致。
- 2026-09-05：最终机械复核再次得到 inventory 56项 `BAD=0`、company 六入口19个本地链接 `BROKEN=0`。四个历史子计划 sidecar 仍精确匹配旧 scoped-review 哈希，根入口匹配新 `ff16f8bf...`；archive sidecar 已从旧审查绑定的 `24efd981...` 变为 `195e582c...`，属于并发补充，必须重读该新版本后才可签第一阶段 PASS，不能沿用旧哈希的 scoped verdict。
- 2026-09-05：已全文重读 archive sidecar 当前 `195e582c...` 版本；正文完整列出10份规划/完成说明及其余6份关联归档，历史/当前、职责边界、单线程LLM、旧测试/性能/调度均有正确限定，本版本内容可接受。它的旧 scoped-review 哈希与当前 raw hash 不同，但本轮是独立读取当前字节后重新判定，不把旧 verdict 移植到新字节。
- 2026-09-05：第二阶段开始。重新全文读取 planning-with-files 技能、主审计 plan/progress 与本审查记录；只读目标锁定为 `revenue-docs.patch` 当前声称的 `80acde09...`、revenue HEAD `2cbd585...`、六份 GP 活动文档、根状态入口、范围报告及其代码/机器证据。本阶段不修改 revenue 仓或 patch。
- 2026-09-05：补丁实测 15,720 bytes、SHA-256=`80acde09d9ee07a40deba7cdaac4abcf4ec5031501458cb9cd79734e067d4d0d`，包含六份活动GP文档更新、部署指南另两处精确替换及新增根 `PLANNING_STATUS.md`。范围报告判定canonical 93份/25,163行/2,304,586 bytes全文，新增状态页后应为94份；46份唯一冻结输入hash 46/46匹配，13个不可访问 `.tmp-*` 明确为UNKNOWN并排除，未误称绝对全文件系统完整。
- 2026-09-05：revenue 实测 HEAD=`2cbd585efa6f7901e850ef205b6271b156e4f90d`，根 `PLANNING_STATUS.md` 尚不存在；六目标当前 CAS 依次为 task `c47e5e47...`、findings `4795e004...`、progress `78aa9279...`、deployment `48d76850...`、GP010 `11a0c6d8...`、R9 `8d287d55...`，行数147/78/157/79/79/99，与范围报告一致。工作树含既有未跟踪历史计划/运行/tmp资料，补丁不得清理、覆盖或把它们归入本次diff。
- 2026-09-05：全文重读三份辅助GP文档，确认其当前原文确有补丁所覆盖的旧矛盾：部署指南仍称03:30、`--run-daily`缺陷已修且“无需重注册”；GP010页首/页尾仍待批准而批准记录已存在、旧sections=0；R9页首仍待批准、旧successor映射/03:30时间线/末尾批1→2→3与§3.2冲突。补丁采用顶部状态覆盖并仅精确修正指南路径/22:00，不擦除批准与历史证据，处置方向正确。
- 2026-09-05：当前源码精确证实 daily `cmd_register` 仍在Action写入`"daily_t2_schedule.py" --run-daily`，trigger为22:00；`build_parser()`只注册必选子命令`run-daily`。weekly则一致地生成/解析`run-weekly`。因此补丁将GP008写为`blocked_code + deployment_action_unverified`、把电源/StartWhenAvailable/22:00仅视为已修的一组调度条件是正确的；不能沿用2cbd585提交说明中的“root-cause fixed”作闭环结论。
- 2026-09-05：在确认`parse_args()`先于任何runner/注册操作后，独立执行安全探针`python -B tools/daily_t2_schedule.py --run-daily`；返回非零并报`the following arguments are required: command`，未进入`run_daily`。这直接支持补丁的GP008代码阻塞结论；本轮没有读取/注册/启动/修改Windows任务，也没有写manifest、period或catalog。
- 2026-09-05：机器运行文件仍为`daily_manifest.latest_run_id=20260903T211059Z`、`observation_period=1`、started_at 9/3 21:11 UTC；`legacy_periods`只有period1且`status=observing`、hits=0，close gate明确`completed=0`/`close_allowed=false`。因此补丁撤回03:30/22:00固定日历放行、要求两个实际completed且各≥24h零hit窗口，并将GP009/R9保持未验收/未执行，均与当前字节一致。
- 2026-09-05：统一机器state解析为`plan_status=completed`、`implementation_status=completed`、117个unit全部accepted、`current_next=CA-201`；它只支持原DAG终局，不支持GP部署/自然触发/生产语义外推。`plan_inputs.json`结构为44 entries+3 sources，存在路径重复，范围报告用唯一46文件而非47计数的解释合理；仍需本轮独立复算46个source hash后签字。
- 2026-09-05：独立合并manifest entries/sources并按路径去重，得到raw47、unique46；唯一重复是three-repo rebaseline的`input_snapshot.md`两次，46份当前字节全部匹配预期hash，`BAD=0`。冻结输入没有被补丁修改或通过重算manifest掩盖漂移。
- 2026-09-05：列明session真实第四份为`panorama.md`后，按报告的精确canonical规则独立重算：93份、25,163行、2,304,586 bytes，与范围报告完全一致。该计数不含补丁将新增的根状态页；应用后94份的数学关系成立，13个拒绝访问tmp仍必须保持UNKNOWN限定。
- 2026-09-05：只读解析apply-patch文本：8个Update hunk的旧上下文在各自HEAD文件中均恰好匹配1次，新增根状态页目标不存在；9项`BAD=0`，当前补丁可应用且没有模糊上下文。新增内容仅含3个本地Markdown链接，全部解析到现存活动计划或company审计报告，`BROKEN=0`。
- 2026-09-05：GP006源码证据与补丁一致：`quality.yml`的`real-roots`运行于`windows-latest`但`continue-on-error:true`；注释明确真正REAL_DATA套件需有生产catalog的self-hosted runner且未纳入，该job只跑9个sibling依赖的tmp-data测试。故状态只能是`partial`，不能沿用历史表格的D-3 closed/CI三job全绿断言。
- 2026-09-05：已确认生产catalog文件存在且约49.7GB，只准备使用SQLite只读模式核对5/7，不执行extract/normalize/LLM或任何写事务；表名/字段必须先由只读schema确认，避免凭文档猜查询。
- 2026-09-05：SQLite `-readonly` schema确认`documents`、`document_entities`、`entities`与`artifacts`关系，artifacts以`artifact_role/status`记录normalized/summary/sections。`company-name:紫金矿业`当前关联12份document；下一步只按`document_kind=broker_research`和active状态列出目标并聚合角色，避免把其他财报误入七份cohort。
- 2026-09-05：只读生产catalog最终按active + `broker_research` + 标题含“紫金矿业”得到恰好7份：completed normalized=7/7、summary=6/7、sections=5/7；民生与国联民生sections为0，且国联民生summary=0。前一条仅按entity join漏掉长江行业对比报告，故未把6份中间查询当最终cohort。补丁中的GP010/GP005分层及5/7、6/7、7/7数字与当前DB一致。
- 2026-09-05：冻结`legacy_disposition.json`逐字确认FC-150x successor映射与补丁完全一致：1501→CA107/108/109，1502→CA301/303，1503→CA302，1504→CA206/304，1505→CA305/306。补丁只在非冻结R9活动申请顶部纠偏，不修改或重签冻结JSON，正确避免沿用原申请中的错误映射。
- 2026-09-05：scenario registry当前含197个唯一场景，197/197 status=passed且197均有evidence_path；这支持补丁保留registry层T1完成，同时明确它不等于七份生产语义7/7。原DAG、registry、能力实现、DB产物四层未被混写。
- 2026-09-05：post-apply阶段开始。重新全文读取planning-with-files技能、主审计plan/progress及本审查记录；只读检查revenue实际工作树与冻结证据，唯一写入仍为本文件。主任务报告旧Codex apply-patch路径首次失败且确认零写、随后以当前路径成功；本reviewer不据口述签字，以下结论只采用应用后的实际diff/hash/链接。
- 2026-09-05：应用后HEAD仍为`2cbd585...`。目标status恰为六份活动GP Markdown修改+根`PLANNING_STATUS.md`新增；六文件diff为71行新增/2行替换，`git diff --check` exit 0。根Add目标现已存在，未见补丁将源代码、配置、机器state或冻结包加入tracked diff。
- 2026-09-05：修正审查器后逐hunk比较应用后内容：8个Update新序列均恰好出现1次，新增根状态页40行与patch Add正文逐字相等，9项`BAD=0`。根页当前5,297 bytes、SHA=`1da0b403...`，历史/当前路由、93→94、46冻结hash、13 tmp UNKNOWN及独立review边界均完整保留。

## 审查错误记录

- 首次取 v5 import manifest hash 时误用了不存在的 `baseline/import-manifest.v5.json`，`Get-FileHash` 报错；没有写入。下一步只通过文件清单确认真实路径后再计算，不重复猜路径。
- 首次把 PowerShell `foreach` 语句直接接到格式化管道时触发 `An empty pipe element is not allowed`；没有写入。改为先把循环结果赋给数组再输出。
- 为诊断 archive sidecar 哈希差异时将 PowerShell 辅助函数误命名为 `H`，与 `Get-History` 别名冲突，造成大量只读错误输出；没有写入。该诊断不作为证据，后续使用框架静态 SHA 方法或直接采用 `Get-FileHash`，不重复调用该函数名。
- 第二阶段首次合并读取活动组 task/findings/progress 时总输出被截断；该次不计作本 reviewer 的三文件全文复读。后续以精确 hunk 上下文核对、独立范围报告的EOF游标和必要分段重读为准，不重复同一大合并输出。
- 首次独立重算93份canonical集合时误猜session第四份为不存在的`handoff.md`，且递归枚举碰到`.pytest_cache`访问拒绝；输出仅得92份，不能作为范围反证，也没有写入。下一次先列出现有session文件名，再显式使用准确四件，并抑制已明确排除的cache诊断。
- 一次scenario registry只读解析因命令的工作目录字符串输入错误，进程创建返回Windows error 267；没有执行或写入。改回已验证的company-wiki绝对工作目录后重试，不改变查询内容。
- post-apply内存验证器首次在`*** End Patch`和循环结束各flush一次Add目标，导致第一个完整AddedFile比较PASS后又产生一个空的伪FAIL；这是审查脚本状态清理错误，不是项目差异。下一次在flush后清空Add目标，再报告最终计数。

## 第一阶段结论 — PASS

**Verdict：FIRST_STAGE_DOCUMENT_REVIEW_PASS。未发现阻断问题。**

- company-wiki 六个当前状态入口的历史/当前边界、职责边界和危险操作授权边界清楚；未把旧账本、旧测试数字、旧 worker 运行态、代码存在或 import 机械校验误称为当日产品/生产验收。
- 并发代码变化已被如实封板：审计冻结起点 `a0c7629...` 与观测 HEAD `853dca2...` 分列，BR 能力代码推进没有被误写成七份生产 sections 已闭环。
- `company-inventory.json` 当前 56/56 项为 `full`，逐项长度、行数与 SHA-256 重算均匹配；`docs/plans` 非本审计自身的40份 Markdown全部入表。archive 原有16份关联 Markdown由 sidecar逐名覆盖，inventory 也明确这部分另记，未误称 JSON 单独就是全仓所有 Markdown。
- 根文档覆盖报告为 8,600/8,600 行；v5 覆盖报告为 `baseline/plan` 13份6,691行 + current/reviews/history/investigation 10份2,053行。两份报告都明确“语义全文阅读”不等于功能、技术、冻结、Gate、运行或实施 PASS。
- v5 的“每个关键节点独立 agent 审查”要求没有被降级为一次末尾总审：历史规范明确实施型节点至少 D/G，生产节点 D→OP→G，实施者/operator 不得自审，证据漂移使旧 PASS 失效。正式 v5 版本合同尚 pending，因此本轮只确认该要求被保留为阻断门禁，**不声称 v5 已完成机器化落地或审查**。
- company 六入口19个本地链接、filing 两文档6个本地链接均无断链；company terminal notice 与 v5 import manifest 哈希保持 `b3f3ceb2...`、`da7d116e...`。
- filing-fetch 应用后的变更仅为新增 `PLANNING_STATUS.md` 与修改 `e2e/E2E_DESIGN.md`；历史根三件套、terminal notice、FC-903契约/报告/收据未改。E2E 已正确收窄为 companies-root reuse-only，并明确本轮未复跑。FC-903 `receipt_binding_mismatch` 被披露而未伪造修复。

本 PASS 仅覆盖本节列出的 company/filing 文档及覆盖元数据；不等于 worker 恢复、生产任务状态穷举、CI/E2E/117项重验、FC-903互证修复、v5冻结或产品功能完成。

## 第二阶段结论 — PASS（revenue 补丁预应用）

**Verdict：SECOND_STAGE_PRE_APPLY_REVIEW_PASS。当前未发现补丁阻断问题。**

被审对象严格绑定：

- revenue HEAD：`2cbd585efa6f7901e850ef205b6271b156e4f90d`
- `revenue-docs.patch`：`80acde09d9ee07a40deba7cdaac4abcf4ec5031501458cb9cd79734e067d4d0d`
- 六目标CAS：task `c47e5e472d1554686e8e301a30133dc05c9befc6250b7ff375801b8bf5c79d80`；findings `4795e004080d57cf0d8ea388602aa2ee2d01ce45b68eebadd38c75fc13198211`；progress `78aa9279795254ca434012b8927e569b6bd86ec073601dc536257b04615a261e`；deployment `48d76850eeab891daaf36c74bf96db0dabbee71cc52814e079359004604c7968`；GP010 `11a0c6d8dbaefd4a4b2e8fbfa27cbfeb5ce9a6d661876d59095d782fba1e6f80`；R9 `8d287d55f043b003223c28a8da2c9f6fd2a9ecca060f4dcaa6ad67632bbba2ca`
- 冻结 `plan_inputs.json`：`9e43255e5e56102cbc49e04615d1a1adeb34dece918b976bb0d8867b282d85e4`
- 应用前根 `PLANNING_STATUS.md` 不存在。

复核结果：

- 8个Update hunk的旧上下文均唯一匹配，1个Add目标不存在，9项可应用检查`BAD=0`。补丁只更新活动GP六文档并新增根状态页；不触碰代码、配置、任务、运行state、receipt、scenario registry、冻结日期包或manifest。
- 新增3个本地Markdown链接全部可解析。根状态页明确初始基线`6b4e3cf`已被并发HEAD`2cbd585`取代，后续实施仍需重新核对，未把审计快照伪装成永久现状。
- GP006=`partial`有直接workflow证据：Windows job非阻断，真实生产roots测试仍被排除。GP008=`blocked_code + deployment_action_unverified`有源码与安全argparse探针直接证据；22:00、电源条件及StartWhenAvailable修复没有被误写成Action/CLI已闭环。GP009保留owner重注册历史，但自然触发、7/2/1/1周期及实际Action仍未验收。
- daily manifest仍停在9/3手动run/period1；legacy periods只有一个observing窗口、completed=0、close_allowed=false。补丁正确覆盖03:30及22:00旧固定时间线，改为只按两个实际completed、各≥24h且hits=0窗口判门。
- GP010状态为`authorized / partial_execution`而非待批准或完成：只读生产catalog实证normalized7/7、summary6/7、sections5/7，两份列表式研报仍无sections；1份summary安全拒绝保持fail-closed。scenario registry的197/197 passed被正确限定为registry层，不替代生产语义产物。
- R9的A+B批准原文保留，删除仍未执行；successor映射与冻结`legacy_disposition.json`逐项一致，批1+2 revenue单commit、随后wiki批3独立commit的口径正确。补丁没有重签批准或执行删除。
- canonical范围独立重算为93份、25,163行、2,304,586 bytes；新增根状态页后为94份。manifest raw47条去重为46个文件且hash 46/46匹配；13个不可访问tmp继续明确为UNKNOWN，没有扩大成绝对全文件系统无遗漏。
- 活动计划已有“每个GP独立复核”的统一门禁；补丁又要求未来代码修复/部署核验另行授权并独立复核。此审查只批准当前文档补丁，不代表未来GP节点、Scheduler部署、自然时间窗口、R9删除或生产重处理已经通过独立agent验收。

该PASS在任一HEAD、补丁hash、六目标CAS、根Add目标或冻结manifest漂移时立即失效，必须停止应用并重新审查。

## 审查范围

- `company-wiki/PLANNING_STATUS.md`
- `company-wiki/docs/archive/CURRENT_STATUS.md`
- `company-wiki/docs/plans/{catalog-space-remediation,core-section-extraction,portfolio-reuse-automatic,portfolio-reuse-fix}/CURRENT_STATUS.md`
- `company-wiki/docs/plans/planning-sync-2026-09-04/` 内 inventory、覆盖审计与校验材料
- `filing-fetch/PLANNING_STATUS.md` 与 `filing-fetch/e2e/E2E_DESIGN.md` 当前 diff

## 待办行动项

- [x] 同步 `company-inventory.json` 的 `read_status`、当前入口 hash 与已完成全文审计；补齐 v5 current/reviews/history/investigation 的覆盖封板。
- [x] 完成 company/filing 当前文档链接、hash、Git diff、历史/当前边界、不可变证据及覆盖清单复核；第一阶段给出 PASS。
- [x] 对SHA=`80acde09...`、HEAD=`2cbd585...`及上述六目标CAS完成第二阶段独立预应用复审，给出PASS。
- [ ] 主任务应用前再次比较HEAD/patch/CAS/根Add目标；任一变化即停止，不能引用本PASS。
- [ ] 应用后仅允许出现根`PLANNING_STATUS.md`与六份活动GP文档变化；重算链接、94份计数、46个冻结hash并保存最终diff，才能宣称三仓文档同步完成。
