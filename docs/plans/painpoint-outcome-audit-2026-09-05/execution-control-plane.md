# 控制面逐步施工卡：WP00 / WP11 / WP12 / WP14

> **R4状态覆盖（2026-09-07）**：本文正文是R3历史方案/测试细节库，已不再作为活动执行队列。唯一活动编排为[R4实施计划](simplified-execution-plan.md)，测试见[R4矩阵](simplified-test-matrix.md)，原WP归属见[迁移表](r4-transition.md)。仅按迁移表继承领域步骤、反例与原始成果要求；不执行下文旧G0–G5依赖或95门DAG。历史review只签当时字节，本次新增状态头使当前文件hash变化，不能宣称旧签收绑定修改后文件。旧gate-dag.json及validate_execution_plan.py原样保留为R3历史工具，不用于R4验收。文档更新不授权产品实施。

状态：PLANNING_ONLY，未授权实施。先读remediation-plan第0、5、6节及execution-handbook。本文将步骤拆小，不新增授权、不降低真实数据要求。步骤ID唯一；每一步只能在本包run目录写结果，执行过/失败/未执行分开。任何命令在G1绑定实际CLI与完整argv前都不可运行；不凭本文猜参数。

## WP00：先建立能拒绝假完成的能力，不能等待全部业务先修好

候选：revenue `assurance/unified_completion/uc/{receipt,revision,closure,scenarios,commands,strict_state,legacy_disposition}.py`、真正CI/CLI消费者；原文件位置先在G0重核。

| 步骤 | 具体动作与输入 | 产物/检查点/独立门 |
|---|---|---|
| 00.01 | 读取原P01–P11、117项、GP10、legacy81继承表；逐条记录不可删的用户结果，不用accepted反向推目标 | requirements.csv；Reviewer-A核每原条款有ID/原文hash/required tier，缺项停，G0 |
| 00.02 | 记录精确三仓HEAD、dirty文件hash、运行环境、旧冻结证据；划分历史格式valid和当前business accepted/production verified | baseline.json+状态ADR；不得重签旧11/12/13使之匹配，独立审查旧字节保留 |
| 00.03 | 将每条审计finding映射WP/RED/真实E2E/消费者；先用本目录traceability作种子，细化到原条款，不机械复制整文件测试名 | mapping.csv；ID唯一且每条有oracle及真实证据需求；Reviewer-B G1拒绝缺映射 |
| 00.04 | 在独立临时证据树复制真实历史receipt/scenario结构，保留原hash为历史；构造新candidate结果分支，禁止写原registry/state | fixture manifest+只读哨兵；真实历史输入不是当前业务成功证据 |
| 00.05 | 对真实CLI closure逐个运行E01–E13，逐次只改一个变量：拒绝review/缺T2/换HEAD/未来/跳过/空required/dry-run副作用等 | 每ID基线真实红因+candidate期望；不能以文件不存在/import失败冒充RED；G1独立oracle |
| 00.06 | 最小修改资格计算与调用者，格式valid允许保存rejected，但业务资格必须拒绝；状态推进调用同一资格入口 | diff+caller证据；Reviewer-A G2核没有另一个旁路或hardcoded终局 |
| 00.07 | 把执行结果绑定sid×tier×triplet×dirty×sample×config×command×result hash；collected/skip/error/unknown分别保留 | schema/CLI样例；伪造stdout、rc0空输出不能过；未执行不补hash |
| 00.08 | 独立Test-Agent重跑所有mutation，补一个未在实现者清单中的变体；OS写哨兵检查dry-run 0写 | G3原始stdout/stderr/rc+拒绝原因，失败保留不得只报“通过率” |
| 00.09 | 用真实历史证据只读导入到隔离CLI，显示历史accepted与当前资格不足同时存在；验证日志不含secret env值 | G4=isolated_cli，Ops审核零生产副作用，不需要先跑WP13/自然窗口 |
| 00.10 | Reviewer-C重新算hash，检查所有原目标缺口仍pending，不用能力通过关闭业务目标 | G5仅证据能力签收，释放后续DEV；最终原目标资格留WP14 |

## WP11：CI能力bootstrap与全矩阵最终签收分开

候选：三仓`.github/workflows/`，revenue `tools/ci_checkout_siblings.py`、`tools/final_ratchet.py`及实际closure消费者。托管CI触发/配置变更需要明确DEV/托管权限，不能由文档授权推导。

| 步骤 | 操作 | 测试/检查点/独立审查 |
|---|---|---|
| 11.01 | 盘点每job在何OS/三仓组合/测试层级运行，列ignore/continue-on-error/skip和旧gate调用 | CI矩阵baseline；G0 Reviewer-A区分local fixture与真实root，禁止以job名real-roots判真 |
| 11.02 | 冻结bootstrap required job与私有数据边界；每WP后续适用矩阵独立版本，不等全部业务修完 | G1 Reviewer-B核WP11.G3能先交付；明确公共runner不得接真实私有原文/密钥 |
| 11.03 | 用最小有意失败变更在授权隔离CI证明Q01 required Windows红、Q02缺T2、Q03skip、Q04工具缺失 | 实际CI结论/原始JUnit，不是读YAML字样；基线不阻断即RED |
| 11.04 | 三仓checkout由精确manifest锁commit，N-1/current独立；dirty来源明确导入，不能偷偷借开发树 | Q05陈旧sibling必须拒绝；独立环境agent复核路径/HEAD |
| 11.05 | 接真实result资格消费者，selected-scope未跑维度not_run，工具异常非0阻断，缺required不能绿 | Q10改文件名不得扩大network grant；Q11 scanners-only不能虚填ok |
| 11.06 | AST质量覆盖指定core递归文件；新改函数阈值事前冻结，禁止抬门/删测试/加skip解红 | Q06子目录硬编码/Q07单行docstring/Q08旧gate/Q09缩scope；Reviewer-A审diff，G2 |
| 11.07 | 独立Test-Agent在第二个干净checkout重跑bootstrap，增加一个旁路变体，核实际job结论与每case | G3签收bootstrap；真实roots没有授权时不计已通过，但不阻塞无副作用包设计 |
| 11.08 | 获托管/自托管授权后验证一仓变更触发三仓适用矩阵，凭平台run ID/checkout日志/结果hash | G4按scope；缺远程权限保持pending，不以本地模拟fanout替代 |
| 11.09 | 每后续WP merge候选先独立核新增required RED/E2E映射，矩阵差异写变更卡 | 不重签bootstrap冒充后来新增业务已测；新增或删required需Reviewer-B批准 |
| 11.10 | Reviewer-C签本版本已实际执行的层级；WP14单独核最终矩阵无遗漏 | G5能力和最终coverage分字段，不产生笼统ALL GREEN |

## WP12：12a隔离报告 → WP13真实case → 12b持续运行 → 12c自然资格

候选：revenue `tools/daily_t2_schedule.py`、`tools/weekly_t3_schedule.py`、`tools/run_daily_t2.py`、`tools/run_weekly_t3.py`及实际report/soak/alert消费者；G0核路径。禁止直接执行旧GP部署guide默认生产catalog命令。

| 步骤 | 操作 | 独立门与验收 |
|---|---|---|
| 12.01 | 将每项SLI绑定实际事件/唯一source/root/请求/attempt；禁止一项ledger.ok复制十次 | G0需求表包含resolve全路径、真实复用、来源完整性、调用/费用、延迟、失败恢复、告警 |
| 12.02 | 冻结report schema、atomic publish、fail/skip/not_run/unknown与freshness规则；两套weekly收敛一个canonical | G1独立Ops+Reviewer-B，明确未来/迟到/时区/DST/主机睡眠及报告过期 |
| 12.03 | 真实runner在隔离目录消费真实源资料的本地case结果，未获联网许可则network suites保持not_run | 不将真实原文替换预制成功JSON；尚无WP13结果时只测12a能力，不计真实持续成功 |
| 12.04 | O01–O14逐个注入：停跑/权限拒绝/未来/旧绿/缺SLI/坏hash/同刻7run/半报告/告警sink失败/坏scan/ledger缺失 | G2/G3独立重跑；结果从实际消费者证明release拒绝，不只helper异常 |
| 12.05 | 独立验证watchdog在被监测job根本没启动时仍能发现缺run；隔离告警sink验证失败/重试/ack | 12a G3通过只证明能力；测试clock、测试sink都明确标签，不计自然drill |
| 12.06 | 等WP13.G5真实case签收与全部scope安全门，再冻结schedule授权卡 | 最大run数/失效/每日每月预算/SID/Action/cwd/profile/恢复原任务快照；未批则停在12a |
| 12.07 | 获schedule_register_or_update授权后先disabled注册，读取实际平台Action与触发设置逐字段比对 | Ops独立证据；参数源码已修不等于已部署；不从任务存在推成功 |
| 12.08 | 获12b运行授权与manual/network各subtype后，先一次受控真实case，检查原始源→实际程序→独立输出 | 所有调用成本与OS/文件/DB账实一致；越界即停，不能靠summary ok放行 |
| 12.09 | 按当前授权启用有限持续运行；观察自然平台事件，非手动启动伪装cron，watchdog独立运行 | Daily/Weekly/Monthly使用WP13已审真实case；发布新HEAD/config需重绑并重验适用门 |
| 12.10 | 每次run独立检查唯一ID/实际起止/时区/有效case/skip/失败链/fresh/current；实时保留缺run原因 | 12c连续7daily、间隔≥7天2weekly、35天内monthly、真实drill ack；相同时间7次不算 |
| 12.11 | 独立Ops演练真实主机睡眠/错过触发/权限变化须另批，核用户实际告警到达和ack，不只本地JSONL | 演练预算、恢复原任务、失败结果保留；不能为观察自动付费 |
| 12.12 | Reviewer-C重算自然资格，未满足observing；符合才WP12.G5，仍不自动恢复worker或legacy删除 | 计划不承诺几号完成；还需WP14实际退出门 |

## WP14：真实效果关闭与legacy退出，不是又一轮文档互签

| 步骤 | 操作 | 检查点/测试/独立审查 |
|---|---|---|
| 14.01 | 从每条原requirement读取当前证据，不从旧accepted推结论；列缺tier、缺sample、缺授权、未闭finding | G0 Reviewer-A核117+GP+历史继承没有悄悄缩目标 |
| 14.02 | 冻结精确legacy符号/caller/flags/文件与每批可恢复边界，检查source-only职责 | G1独立CodeGraph影响审查；旧Strategy A/研究writer不恢复，旧批准scope需重核 |
| 14.03 | 先在隔离checkout删候选并跑当前矩阵，故意留下一个legacy调用应失败 | G2/G3独立测试，不能删测试/放宽ignore/skip；失败不接生产 |
| 14.04 | 等WP13.G5、WP12.G5及S01/02/04/05/06与当前操作授权，读取真实两个completed≥24h零hit窗口 | G4 entry缺一停；不能手工填ended_at或拷贝旧窗口 |
| 14.05 | 实际受控批次前记录文件hash、DB恢复对象、任务快照及不可撤销provider事实 | 独立Ops审核恢复不是擦日志，SQL快不代表prune安全 |
| 14.06 | 每批小范围变更→三仓required矩阵→真实原文三公司旅程→legacy调用复扫；停下来独立评审 | G4每批签hash，不把最后总审代每批；任何不一致暂停 |
| 14.07 | 按预审范围恢复该批，再验证raw不变、locator/产物/注册账本语义可恢复；重新激活单独授权 | 失败演练在隔离环境先通过，生产禁止试错式删除；外部费用不承诺撤回 |
| 14.08 | Worker观察两小时≥5完整cycle与7/2/1/1分开核；前者不能抵后者 | CPU无进展/超预算/未知调用/取消失败即暂停，保留实际失败链 |
| 14.09 | Reviewer-C逐原目标签：修复前反证、当前正反测试、真实E2E、独立数值/来源oracle、自然资格 | 任何unknown对其目标保持未闭，允许局部目标通过，禁止总数accepted代效果 |
| 14.10 | 用户明确批准后才做安装/切换/当前session启动；AUTOSTART另走v5正式冻结与双授权/真实登录验证 | 默认交接回paused；没有批准时可交付修复成果但不能开启后台 |

## 计划级验证与实施级验证的界线

本目录的gate-dag.json及validate_execution_plan.py只检查计划结构、依赖、链接/引用，不执行上述流程；PASS不能替代任何产品G3/G4/G5。所有真实case必须有未经mock替换的原始字节、真实进程、真实消费者和独立输出核验；自然运行再加平台事件与不可伪造的时间。副作用故障注入可作为负例补充，但不得用其模拟输出充当正向真实E2E。
