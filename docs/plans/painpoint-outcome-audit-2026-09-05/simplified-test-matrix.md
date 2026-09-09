# R4测试、真实数据E2E与审计检查矩阵

状态：PLAN_ONLY。所有case均待实际实施授权后执行，本页不含产品PASS。当前编排仅见[simplified-execution-plan.md](simplified-execution-plan.md)。旧合成测试保留诊断价值，但不得替下面真实结果。

## 1. 共用真实语料与执行合同（避免每阶段重新搭一套）

一份corpus manifest可供A/B/C/D/M引用，同一版本无需重复人工批准；发生source字节/使用目的/外发对象/费用范围改变才重审相关批准。既有owner授权不被自动扩大。

最低样本：三家真实不同公司（紫金、异构矿企、非矿企）各至少一份真实财报；合法取得的真实修订对一组（无则该项blocked）；原broker七PDF+两HTML用于对应解析能力，列表式/跨页表/多实体至少各一例可重叠。只有读取功能的B阶段不必等齐矿业计算和九份broker语料，明确测试适用范围。

两组根测试不可互换：

- **位置等价组**：一份真实PDF及同一可信metadata，复制到四个获批隔离root，控制唯一变量为位置/priority/可用性；用于证明位置不改变业务结果。副本不计四份独立来源。
- **既有根覆盖组**：每个实际已注册root选择其原生真实资料/sidecar/命名格式，保留原相对拓扑到隔离目录，经对应真实adapter索引与读取；输出逐root结果。不能把companies副本命名Dropbox替代此测试。某root没有符合样本明确not_available，不算覆盖通过。

所有写/移动/坏文件/撤副本实验仅在独立批准隔离副本；生产源保持只读。复制SQLite必须一致快照且有空间预算，不直接复制活动WAL库；不可为测试灌满系统盘。云盘真实离线/hydration无可控安全条件时记未验证，用故障夹具仅验证机制，不能声称真云盘已验收。

每个case记录：ID、阶段、真实/诊断/自然层、公司/期间/根/来源ID与原hash、独立oracle、三仓精确HEAD+dirty与配置版本、命令argv/cwd/解释器/env键、开始结束/rc/业务结果、前后OS/文件/DB/网络/费用事实、结果hash、reviewer、remaining。秘密值/私有原文不写公开日志。

**oracle与不变投影**：Data Reviewer先看原文/来源元数据，独立确定公司、期间、修订关系和locator；不调用被测resolver生成expected。位置等价比较document/source版本/hash、身份/期间/原文字节与可用能力；仅诊断path/location、耗时、观测时间允许不同。新导入时间可以不同，不能用它替发行日期或修订排序。性能原始样本保留全部异常值。

执行命令须在阶段DR从当前真实CLI解析器确认，输出到批准run目录；本文不提供猜测flag。隔离真实程序使用专用配置、OS级禁止生产写/网络，不能只靠mock env。基线已过的case计保留回归，不能故意恢复旧缺陷制造RED。

## 2. L：本地数据湖（A/B，12组）

| ID / 阶段 | 输入与步骤 | 独立预期 / 检查点 |
|---|---|---|
| L01 A/B | 位置等价四副本分别单独索引→query→open；再四副本同时存在，调换priority | 同source版本/业务投影/字节；非companies也可用；零网络/原文件修改 |
| L02 B | 独立既有根覆盖组，按真实adapter索引→查公司/期间→读取 | 每root真实成功/缺口单列；引用source与实际原文相符，不因root名制造新逻辑分支 |
| L03 B | 四副本撤首选、撤两个、移动/改名、恢复同hash；所有副本不可用 | 有合格副本自动切换且引用不变；全失效unavailable，不取另修订、不自动下载 |
| L04 B | 第五个支持格式root只新增注册；另测未知adapter、显式deny、未注册root | 合法第五根无需消费者代码改动；未知/deny拒绝，不以平权绕过能力限制 |
| L05 B/C | 打开后文件被替换/同size内容改/路径重指、symlink/reparse逃逸；用稳定流/快照读取 | 只返回验证版本字节或明确失败，TOCTOU不混读；越界零读/写，无mtime冒充hash |
| L06 B | 文件占用/ACL拒绝/云占位不可读/损坏PDF/超大文件/读取中断 | 明确原因与同版本副本选择；有限资源/可取消。真实云场景与人工注入分层，不伪覆盖 |
| L07 B | 搬目录重新索引；保存旧source/version/页或span locator再打开；真实修订对同时存在 | 原引用仍指原字节；新修订独立版本，不能只因mtime/accession词序决定新旧；未知关系ambiguous |
| L08 B | 相同source来自两个root，交换priority/扫描顺序；完整metadata与缺字段/矛盾字段 | 业务事实不随位置改变；可信字段有来源，冲突保留而非按priority默选 |
| L09 A/B | 真实本地PDF缺下载URL/捕获日志但有本地导入source hash；分别请求preview、正式已验证输入 | preview可读并标provenance缺口；正式合同缺身份/期间则不通过；不伪造URL、不默认联网 |
| L10 A/B/C | 同文档原文ready、文本缺失、sections失败、summary安全拒绝；逐次请求不同能力 | 只检查所需能力；原文不因无summary消失；LLM/正式分析不能继承preview许可 |
| L11 B/C | 当前协议、明确支持N-1、缺版本、未知schema、缺policy合同；从filing/revenue真实入口调用 | 支持兼容由单adapter转换且来源不变；未知拒绝，无companies静默fallback，无第二权限语义 |
| L12 A/B/C | 真query_local→open两次，针对不完整/不存在/本地latest分别运行；旁观文件/DB/子进程/network | 查询零写/联网/worker控制；不以ensure填缺。原文读取可产生实际读I/O，不能声称零成本；二次0parser/LLM/download由独立观察证明 |

## 3. P：消费者与生产链（C，8组）

| ID | 步骤 | 预期/独立证据 |
|---|---|---|
| P01 | revenue实际入口查询已索引资料，追完整进程树；冷/热各≥10次记录启动与总wall | 一次query_local≤1跨仓CLI边界，其他调用为进程内；无产品子进程层层套壳。无绝对速度承诺，回归阈值DR事先冻结 |
| P02 | 从同稳定只读源输送filing/revenue，记录全文件读取次数/字节；中途替换源 | 减少重复hash有可证明字节合同，独立消费者所需验证仍满足；不能通过不验完整性提速 |
| P03 | 原文/normalized/sections等needed_roles请求；改变一role版本/源hash/policy | producer决定最小失效，消费者不导入完整上游DAG；无关文档/产物不重算，revenue研究缓存不入wiki |
| P04 | 真队列API进程提交退出→另一进程claim→kill→恢复→读结果；重复100次key/过期lease旧worker提交 | demand持久/唯一合法完成；start/finish/unknown完整，失败无artifact仍有attempt。机制进程与真实worker分层，真实worker用真实PDF加工 |
| P05 | 明确query_local/refresh/fetch/process分别调用；未授权/过期授权/未知size/超byte或费用/多gap只成功一项 | 本地不触发provider；真实外发预算守住；部分成功仍partial，剩余项真实记录；未知费用不填0 |
| P06 | 真实CN/HK/US获批case首次下载→再次复用→真实修订；诊断注入耗时/timeout/post-send未知/commit失败 | 真实服务请求ID/字节/次数对账；10秒deadline不被9秒调用+5秒sleep越界；真实修订不可得则blocked不编版本 |
| P07 | 隔离真实目录读者持续query/open，单写者短事务/崩溃/锁释放/重启；尝试超时取消 | 原文与已提交版本可读、无交叉DB写、writer单一；无普通查询pause/resume，未知写结果先对账不盲重试 |
| P08 | 真实cohort1→停审→3→停审→7；每级结束核源hash/精确PK与文件/调用成本/语义字段/失败 | 每级独立Ops与source审查，新增范围要许可；安全拒绝是负例正确，不算该份正向业务完成；7不扩为kind全部752 |

## 4. O：安全/性能/运维（D，8组）

| ID | 步骤 | 预期/审核 |
|---|---|---|
| O01 | 空旧archive目录+新retired未归档行；坏manifest/hash/缺压缩包/活跃引用/重激活/同日覆盖 | 默认回收不可达或严格拒绝；不能日期一到删全retired。执行在隔离数据，生产删除另批 |
| O02 | 稳定snapshot导出期间有新增/状态变化，原子发布前kill；归档后按精确PK恢复locator/parser/hash | 集合和字节一致，非仅COUNT相等；未归档行不进入删除资格；失败产物不假装归档完成 |
| O03 | 同文档跨root移位、过期review、换policy/normalized字节、未知provider fallback、超cohort/费用 | 原文预览与外发权限分开；位置变化不能洗掉拒绝；真实外发前当前绑定与预算有效 |
| O04 | v5正式阈值下同拓扑真实一致副本测SQL/扫描/启动/hash/parser/commit/暂停/circuit | 继承旧warm≥30/P95<2s等已列最低门，正式冻结后适用；不同数据量不比较倍数，有限样本不称49GB真实通过；原CPU/902秒只作历史 |
| O05 | 唯一runtime/ledger路径与代际迁移；错路径/旧green/未来时间/同刻7run/中间失败/空triplet | 明确拒绝无效资格，文件存在不代表当前；迁移保留两边历史，不拼接伪连续窗口 |
| O06 | 实际required CI失败/工具缺失/部分skip/空stdout/scanners-only/旧组合；冻结证据mutation | 失败阻断对应发布，not_run不写ok，旧accepted不代当前；不让发布资格成为每次本地读取前置 |
| O07 | 授权注册disabled任务→独立核SID/Action/cwd/凭据访问/电源补跑→有限启用→错过run告警 | 实际平台事件+用户告警ack；真实7daily/间隔weekly/monthly/drill按合同，不用时钟mock计窗口；任务注册不授无限未来外发 |
| O08 | 每旧分支退役前真实caller清单、隔离/真实cohort回归、回退演练；恢复/安装/登录各单独批准 | 只退出已证明被替代路径；不会自动恢复已删旧工具；raw/历史receipt/费用事实不回滚擦除，后台资格仍独立 |

## 5. M：业务正确性与完整三公司链（8组）

| ID | 输入与步骤 | 独立oracle/不得替代 |
|---|---|---|
| M01 | 真实资产表raw→parser/table→asset/assertion/review→只读export | wiki事实源带locator/单位/时效/冲突；收入helper不是上游生产证明 |
| M02 | 矿石/金属/kt-t/%-ratio/g-t/湿干/TC-RC/payability/FX/0与缺失/NaN-inf | 独立Decimal量纲消去，关键公式旧M01–M12全继承，不能模型自算expected |
| M03 | 整期间A→B→A股权/associate/内部flow双边/合并口径，改单矿参数 | 实际operating_units驱动相关节点；independent reference有真实来源，差额不plug清零 |
| M04 | 真generator→仅填source值→lint/validate→draft→render | 禁换手工forecast_document；纯prepare/validate实际registry路径零写 |
| M05 | 发布P01–P09所有异常/进程kill点，重启/磁盘满/文件占用/相同operation并发 | 同operation恰一次可见commit，文件与registry一致，失败事实append-only；不同合法发布可同input |
| M06 | 至少两个真实当时冻结origin和后来actual，重复snapshot换日期/跨公司/单观测等对抗 | 无未来信息泄漏、真实误差/置信cap进入最终输出；缺origin保持cap，不制造旧预测 |
| M07 | 紫金+异构矿企+非矿企，从各自真实raw到参数/模型节点/收入/输出/独立reference | 三条链不可换名复用一文档；每参数join可追，真实source与合法明确假设分开 |
| M08（C主归属，M按需复用） | 真broker7PDF+2HTML、多栏/跨页/列表/多实体，经实际parser/demand/consumer；与M07按需要相连 | 属C解析能力原目标，不等收入模型；人工pages数组不算parser成功；每份缺字段/unsupported/安全拒绝如实报告，不以文件计数代语义成果 |

## 6. 审计与完工规则

每阶段DR先签oracle/适用case及测试层/命令和资源预算；VR独立agent第二隔离环境重跑本次冻结的全部隔离层required case，自己增加一个对抗变体；AR再按获准范围对真实数据/外部服务/实际后台结果查来源与OS/文件/DB事实。不得把外网、放量或自然观察AR设成自身VR前置，也不得从必需AR清单删除它们以宣称完成。样本不足、工具/权限缺失、required skip都不算对应层通过。本地读取AR可以成立而外部服务/后台AR仍pending，必须分栏显示。

### 测试层与批准边界（使用同一case ID，不再建多套门）

| 测试组 | VR可以且必须验证的隔离层 | 后续AR仍须取得的独立真实证据 |
|---|---|---|
| L01–L12、P01/P02/P03只读部分 | 真原文隔离索引/字节/协议/消费/进程追踪；故障注入仅机制层 | B和C本地栏对真实原文与既有root覆盖独立核验；不要求网络/worker |
| P03加工、P04、P07 | 真队列/DB/进程/崩溃与离线解析，OS禁止生产写/网络；未测worker不能称worker通过 | 获批真实加工链、再次复用、实际候选worker与并发结果，记C加工栏；不进入C.local.AR |
| P05/P06 | 操作分离、预算/拒绝/超时/未知结果等隔离机制；模拟外部故障明确diagnostic | C联网栏真实CN/HK/US及真实修订；只有C相应隔离VR+D.SAFE+动作授权后执行，不要求先有联网AR |
| P08 | 精确scope/停止/成本/恢复控制的隔离负例 | C09逐1→3→7真实运行，每级独立签收才到下级；不作C.VR前置 |
| O01–O03 | 隔离真库副本/精确行与故障恢复，或自动prune硬不可达证明 | D.SAFE限定安全准备；实际删除/迁移/外发另有明确许可与结果，不能借安全准备签全D |
| O04–O06/O08 | 隔离profile/配置与账本/真实CI测试及退役回归；真实尺度不足如实标缺 | 对应规模性能、实际required CI、真实小cohort/回退结果；不以旧accepted替代 |
| O07 | 时间/事件/权限/告警逻辑的隔离负例，不提前注册生产任务 | D持续栏真实平台动作与自然窗口，只等待拟启用C路线的AR；不等无关市场/M，也不作为D.SAFE前置 |
| M01–M07 | 真来源独立算账/生成/发布故障/已有真实origin离线回测 | 独立三公司完整结果与真实历史；新外部调用另走C/D授权，不要求先自然soak |
| M08 | C负责真broker离线parser与语义oracle；合成pages仅诊断 | C真实demand→parser→consumer以及获批放量；M仅复用所需证据，不成为broker完成前置 |

原WP中的E/C/D/S/B/M/P/K/Q/O/T/H负例由[r4-transition](r4-transition.md)分配；新测试组不是删减原case的理由。实施DR把同义case合并为一次测试并保留多ID关联，非同义不得只以“已覆盖”吞掉。117目标的current资格绑定实际结果；未实施、历史only、业务失败、部分解决分开。

每轮结束独立核raw不变、只写授权区域、失败历史保留、子进程实际终止、worker控制未被误改。发布/观察审计不要求每次读财报重新进行；批准有效范围内的日常只读查询不重复人工签门。
