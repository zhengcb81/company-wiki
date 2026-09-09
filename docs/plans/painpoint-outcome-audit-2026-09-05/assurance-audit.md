# 完成保证、CI、调度与终审：原始痛点审计

审计日：2026-09-05～06。路径默认相对 revenue-forecast。原始验收来源为 `audit_review/2026-08-13_three_repo_completion_rebaseline_plan/completion_assurance_registry.md`，不是后来缩减后的单卡。只读源码、收据和现场日志；纯函数负例结果见本目录 probe-results-extended.json。未执行生产调度、联网、整库扫描或状态变更。

## 主要结论与证据链

### A01：完成标准在执行中被系统性缩减，而非仅有部署遗漏

原 CA-206 要求真实7 Daily/2 Weekly/1 Monthly/1 drill，未满只能pending；11收据却把实际累积移到“之后部署”，只新增 `tests/test_ca206_soak_window.py` 内的纯函数，然后state accepted。同类可见CA-202/203/204（真实调度移出）、CA-301（真实clean checkout移出）、CA-302（真实下载/worker移出）、CA-304（真实删除移出）、ZR-1002/1003/1005/1006（实际激活/观察/迁移/处理移出）。这些测试可以保留为开发资产，但不能代替原卡验收。

`tests/test_ca305_six_problems.py` 进一步用 `status==accepted`、11/12文件存在、测试文件存在、commit字符串长度40、reviewer字符串存在来证明六个成功问题。C4没有精确当前triplet比较；C5只要delta文件存在就允许原review非accepted。于是缩减后的accepted被再次当作原始目标已完成，形成循环证明。这是P01复发的直接机制，不是用户错把局部工作当全量工作。

### A02：独立审查拒绝未必阻断 machine_valid

`uc/revision.py::select` 对唯一匹配的最新review取verdict，但只在“同时有旧accepted且最新非accepted”时添加拒绝问题；只有一份latest rejected且没有旧accepted时返回problems=[]。`uc/closure.py::classify_unit` 用无problems判machine_valid，`uc/receipt.py`又把rejected视为合法枚举。因此“格式合法的拒绝”可能被汇总成有效机器证据。AST纯函数负例已复现latest rejected + problems=[]；这不等于本轮改动或调用了state advance。

P1/P2 finding只要填 successor 就不报错，未查询successor实际关闭。身份分离仅比较字符串，不能证明真正不同审查过程。GP-004重签可修格式，但不能替代独立重放或修复原review语义；历史字节与新签认应分层保留。

独立复核补充见assurance-independent-review.md：使用真实canonical hash、完整schema、内存文件替身，receipt.validate→revision.select→classify_unit联合负例确认rejected仍machine_valid。原audit_probe只隔离select且hash为stub，不能单独当完整链证据。这里machine_valid是格式/配对分类；本轮没有证明state advance或生产CI实际据此放行。允许合法保存rejected receipt本身合理，修复应在业务资格/closure消费侧要求accepted且required findings闭合，不能禁止记录拒绝。

### A03：197/197场景的实际含义不足

`uc/scenarios.verify`验证矩阵来源hash、计数、ID集合；两个closure_report只读status。负例：T2且evidence_path=None、fixture_hash=None、status=passed仍closure_ready=true。

`tools/scenario_runner.py`：已passed直接跳过，不检查HEAD变化或证据过期；按测试文件映射多场景，pass仅rc=0；evidence仅sid/test_file/repo/passed/summary/executed_at，无实际tier、triplet、原始stdout哈希、sample/policy绑定；失败/no_mapping仍main返回0；dry-run仍mkdir并写evidence。故不能把它当只读验证器运行，本轮未运行。BLOCKED_SCENARIOS空集合且文件名包含e2e_download就设下载环境开关，授权必须改为明确操作级输入，不能从测试名推断。

### A04：daily的“真实T2”没有实现报告标题列举的内容

`tools/daily_t2_runner.py::run_checks`：

- manifest门只用git cat-file检查旧SHA对象存在，不等于当前HEAD；未校验dirty/当前政策配置等完整组合。
- policy freshness仅snapshot自hash，不核对当前配置/消费者实际policy。
- samples只是completed artifacts和producer_events总数≥3，不验证三根各自unique、真实handle合法、第二次复用、live-WAL reader与锁故障。
- resolve_sample_sec只计一条documents JOIN artifacts LIMIT 1的SQL；不是resolver全路径，更不是p50/p95。
- root fingerprint只算三个硬编码路径的文件数量；-1缺根没有自动加入problems，且trend显式跳过roots。相同数量下替换/修改原文不可见，future root没有纳入。
- legacy_hits读取失败仅记ledger_unavailable，不加入problems；scan report JSON坏值被忽略，可能把数据缺失解释成无新错误。

现场 `assurance/runs/20260905T194055Z/report.json` 正是该简化结构，ok=true，绑定revenue2cbd585；当前HEAD为2ff20d9。因此这份报告证明“该检查器运行产生了结果”，不能证明CA-202全部实际目标。缺调度时也不会凭空出现告警：append_alert位于run_daily内，进程根本没触发就不会执行；需独立监视入口。

### A05：调度、报告、release和观察周期仍未连成闭环

当前daily注册器已经改为run-daily，旧参数错误已修复；实际SYSTEM Action与触发来源未独立核实。2026-09-06 08:06BST latest ledger仍9/5 19:41UTC/period2，不能由此推断22:00自然触发成功或失败的原因。不能用看起来合理的预计日期放行R9。legacy_periods.close_gate明确false，have1完成窗口；状态字段仍observing而判门按ended_at计算，不直接按status数计数。

`daily_t2_schedule.write_ledger`和runner报告直接write_text，未走`release_gate.publish_report`。`release_gate.compute_sli`默认把同一ledger.ok复制给10项业务SLI，无各自实际指标。其`release_decision`虽有未来时间检查，但纯函数负例证明：report.ok=false、三仓值not-a-commit/x/y、只有任意一个ok SLI、ledger=None时仍ready。`validate_report`仅要求triplet三键，不验证commit/tier/sample/command；执行代码中的函数查找在tools/scripts/.github仅见定义，没有证明CLI/CI实际消费这个决定。较强helper并没有替代较弱实际daily门。

`daily_t2_schedule.freshness_status`将2099时间判fresh；`task_status`把AccessDenied混同missing。`weekly_t3_schedule._suite_outcome`对1passed2skipped和空stdout+rc0均ok；all-skipped分支虽然blocked，但run_weekly仍返回proc.returncode（通常0）。另一个`weekly_t3_runner.py`先按rc0判passed，再谈skip，存在双套T3实现不同语义。两套都未构成可信按市场完整结果清单。当前根runs未见weekly/monthly manifest；本轮没有触发网络来补它们。

CA-206窗口计算器实际上位于测试文件，不是生产汇总：daily_window不使用now、先过滤not-ok、7个不同ID同一时刻也complete（本轮负例）。这不仅是没等够时间，连目前用来保证时间规则的局部实现也不满足自然周期契约。

### A06：CI和legacy退出的完成主张不成立

`.github/workflows/quality.yml` Windows real-roots为continue-on-error:true，注释和命令明确排除生产真实roots套件；Ubuntu忽略多项关键CA/ZR测试，旧verify_closure_ledger仍在实际CI。CA-201测试C4允许ci-gap rc0或1，只验证所有缺口指向自己；C6反而要求无fanout实现。ZR-105→CA-201继承没有落到原要求的跨仓candidate fanout。

`tools/final_ratchet.py`的hardcode/legacy只扫scripts目录第一层和少量固定词；`_code_lines`用简陋三引号开关，单行docstring可使后续代码漏扫；不能证明三仓core无硬码/死双实现。scanners-only把没跑的complexity/type/coverage填ok=true；mypy只数stdout错误且未先判工具rc，工具故障可能出现0 errors。69条历史错误冻结不等于原要求持续下降或全部新改关键函数CC≤10。

## CA逐项判定（对原验收，不对后来缩减卡）

实现/测试资产确实存在不等于无价值；以下PARTIAL表示保留这些资产但不认可全目标关闭。HISTORICAL_ONLY不表示历史测试造假。

| 项 | 判定 | 已有资产及不足/证据 | 下一验收 |
|---|---|---|---|
| CA-001 | HISTORICAL_ONLY | manifest/CAS/TTL工具与历史50测试收据；未本轮重放并发安全 | 在新隔离夹具重放CAS冲突/锁过期与漂移，不能改旧输入 |
| CA-002 | PARTIAL | envfreeze/精确基线工具存在；daily与终审未消费完整当前绑定，A04 | 所有最终门统一比较当前三仓+dirty+config/data |
| CA-003 | PARTIAL | 历史index freeze已记录BYPASS/MISSING；新模块当前索引覆盖有限，旁路未闭 | 针对实际HEAD的只读caller证据与真实进程trace |
| CA-004 | HISTORICAL_ONLY | legacy_disposition机器迁移资产存在，不能借successor accepted证明原功能 | 每旧项关联本次真实结果，历史字节不改 |
| CA-101 | PARTIAL | 枚举/依赖/身份字符串门存在；可triplet_green直接independent_review，缺按required tier门 | 状态迁移必须查询证据/未关闭finding |
| CA-102 | PARTIAL | canonical hash和字段格式校验有效；triplet缺键、commands内容和policy遗漏等未充分强制 | typed内容、三键、真实执行/策略和授权绑定 |
| CA-103 | CONTRADICTED | 最新rejected pair仍无问题；successor不查状态，A02 | latest非accepted一律阻断，独立审查字节绑定 |
| CA-104 | PARTIAL | 命令执行和stdout hash存在；success_markers不消费、expected collected/budget不强制；scenario另走rc | 独立result schema+完整采集/skip/业务门 |
| CA-105 | CONTRADICTED | 缺T2证据也closure_ready，A03 | 每sid×tier×triplet独立必填结果 |
| CA-106 | PARTIAL | ledger/OS快照helper存在；fingerprint差异只计路径/总字节，mtime不参与unchanged；真实call journal未接 | 同大小文件改动红、失败调用也记attempt |
| CA-107 | CONTRADICTED | 扫三仓+receipt格式资产；硬编码old_plan=incomplete不是新closure，拒绝pair/缺tier仍不足 | 从完整required set推导，缺一项红 |
| CA-108 | CONTRADICTED | 有mutation套件；本轮多项critical反例仍存活 | 把本报告负例加入必杀矩阵，杀死率实测 |
| CA-109 | CONTRADICTED | 扫caller并指向CA-201，旧gate仍在CI | 重接线后旧工具限历史reader且required CI实际调用新门 |
| CA-201 | CONTRADICTED | 只验证吸收/缺口映射，非真正fanout，A06 | 三仓任一candidate变化触发精确同组合 |
| CA-202 | CONTRADICTED | 有真实SQL报表，不是原要求T2用户路径/SLO，A04 | unique-root请求+真实分位数+零写+独立触发 |
| CA-203 | PARTIAL | 有T3桥接测试和scheduler；skip/输出/双runner/真实市场未闭，A05 | 按三市场required cases强制非skip+授权 |
| CA-204 | CONTRADICTED | monthly测试为样本/合成旅程；无当前自然月实际报告 | 轮换真实broker/异构矿企/非矿企 |
| CA-205 | CONTRADICTED | 原子publish helper未被daily接入；不完整release仍ready，A05 | 单一报告schema和原子发布、所有消费者同门 |
| CA-206 | CONTRADICTED | accepted时实际soak延后；7同刻也complete | 可信run provenance/不同自然周期，未满pending |
| CA-301 | CONTRADICTED | 11收据明示真实clean-checkout独立重放为之后部署 | 当前组合干净三checkout全部required结果 |
| CA-302 | CONTRADICTED | 三公司测试复用合成紫金；自勾稽，见revenue-audit | 三个实际source到输出旅程与独立oracle |
| CA-303 | PARTIAL | ratchet/扫描资产存在，扫描范围/工具失败/递减性不足 | 全三仓AST与工具错误红、债务实际下降 |
| CA-304 | CONTRADICTED | 收据明确零真实删除；当前legacy窗口不放行 | 自然门满足后另授权分批删除/真实回滚 |
| CA-305 | CONTRADICTED | 以accepted/文件存在/字符串长度代替六结果，A01 | 每问由实际结果派生、不得读取主张自证 |
| CA-306 | PARTIAL | 部分terminal notice后来已写；历史关闭合法，但successor未实际完成 | 历史superseded与当前未完成分开显示 |

## 剩余基础/运行工作项

| 项 | 判定 | 对原目标的具体界限 |
|---|---|---|
| ZR-001 | HISTORICAL_ONLY | 原漂移重放账本有资产；只是当时故障复现，不证明后来修复 |
| ZR-002 | HISTORICAL_ONLY | 合同锁/allowlist存在；后续单卡缩减需目标不可弱化门 |
| ZR-003 | HISTORICAL_ONLY | golden corpus有冻结hash；当前真实/轮换样本验收不能靠corpus存在 |
| ZR-004 | HISTORICAL_ONLY | legacy处置映射可保留；删除与运行效果需CA-304实际证据 |
| ZR-101 | PARTIAL | 8stage taxonomy有效资产；实际所有路径是否输出完整事件仍有P02/P03旁路 |
| ZR-102 | PARTIAL | 临时三根+真实子进程+spy是有效T1；不是实际T2/T3/provider |
| ZR-103 | CONTRADICTED | closure validator不足，A02/A03；不可用schema合法代业务通过 |
| ZR-104 | PARTIAL | 冻结quality维度保留；CI接线、全域扫描/下降目标未闭 |
| ZR-105 | CONTRADICTED | 合同评估器诚实报gap，successor CA-201并没实现fanout |
| ZR-801 | PARTIAL | 197注册ID可追溯；实际tier结果不完整，A03 |
| ZR-803 | PARTIAL | 隔离chaos测试资产；生产超时/停跑/报告中断及调度真实故障未完整覆盖 |
| ZR-804 | PARTIAL | Windows/sibling测试存在；非阻断CI、installed实际组合未重验 |
| ZR-901 | CONTRADICTED | PR门未统一required范围，旧closure仍执行，A06 |
| ZR-902 | PARTIAL | scheduler当前参数修复；实际T2内容/丢run告警/Action来源未闭 |
| ZR-903 | PARTIAL | 注册/执行框架有资产，市场skip语义与两套runner有缺陷 |
| ZR-904 | CONTRADICTED | SLI用同一ok复制，缺项/失败report仍ready |
| ZR-905 | CONTRADICTED | selftests未杀未来时间/同刻soak等反例 |
| ZR-906 | PARTIAL | 69错误冻结/词扫描不等于完整质量成功 |
| ZR-907 | PARTIAL | drift patrol存在；旧当前页与新HEAD/报告漂移未自动关闭或纠正 |
| ZR-1001 | PARTIAL | release preflight/dry-run资产；真实回滚及完整当前证据仍缺 |
| ZR-1009 | CONTRADICTED | R9真实删除未发生，不能以门机制接受替代 |
| ZR-1101 | CONTRADICTED | 117 accepted不能推出原目标闭环，A01–06 |
| ZR-1102 | CONTRADICTED | anti-falsegreen复核没发现本轮critical反例 |
| ZR-1103 | CONTRADICTED | 重验多为既有合成/临时场景；实际三类旅程仍缺 |
| ZR-1104 | CONTRADICTED | 不可豁免自然窗口未满足，代码同刻负例 |
| ZR-1105 | CONTRADICTED | 六成功问题没有真实逐子项pass，A01 |

## 边界

未审查远程托管平台全部历史run，不声称CI从来未运行；未启动网络T3，不声称provider不可用；未重建索引、运行全部pytest或覆盖率。结论针对当前源码可证明的机制与现有收据支持的范围。HISTORICAL_ONLY/UNVERIFIED必须在后续修复计划增加current replay，不可凭本报告改成完成。
