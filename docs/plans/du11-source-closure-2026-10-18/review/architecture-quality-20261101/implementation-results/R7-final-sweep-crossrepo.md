# R7 跨仓最终只读复核（当前源码）

结论：**还有明确残留，不能把R7当前清单当成全部做完。** 本次不改源码/测试/配置/部署，不重测试。ROOT接RF/FF；invest只在ROOT读完下面设计后，做E2E入口/fixture与共同摘录规则。

当前证据绑定同名JSON的GitHEAD/工作状态和逐文件SHA：RF80个当前runtime Python＋27公开文档，FF18＋3，invest10＋24；另按ROOT新指令读tracked Biren E2E脚本及fixture版本/attestation元数据。没有据名字把所有limit判为多余。

## 确认的当前残留

| 项目 | 实际入口/位置 | 结论与最小收敛 |
|---|---|---|
| invest摘录10–500 | leaf/finalize/create → validate_artifact → _validate_claims，invest_contracts.py:1644/:2522 | 真正输入门，和引用hash/单位事实无关。改非空完整原句，保SHA/归属/单位/期间/错误quote反控。 |
| RF目标及实际值摘录10–500 | documented build_management_target API/input_targets.py:105；backtest main → evaluate_snapshot → validate_actuals → _validate_actual_claims:328 | 共有摘录规则只在主evidence路径修了，helper/backtest仍残留。不是声称每个forecast都调用目标builder。 |
| RF总驱动10、每驱动证据10 | validate_document:1155/输出校验:1410 → drivers.py:478/:170 | **是拒合法输入的上限，不是展示top-N。** 保非空、唯一ID、来源与因果DAG、排名归属/合并重算；去固定上限，展示可另做top-N。 |
| FF本地config64KiB | resolve_filing:1210 → load_connection_root → ff_configuration.py:29/:34 | trusted配置即使仅JSON空白增长也先拒；不是下载流实际字节预算。单owner去64KiB，保schema/实际I/O/路径根校验。 |
| FF/RF optional localprep观察 | FF fetch_filing:778/:784、ff_local_preparation_observation:16/:29/:69；RF filing_upstream_cause:364/:400/:485 | 仍128KiB/8层/32键/1024项。FF已blocked状态有附加budget观察时可能被改判invalid_result；其它路径主要是观察丢失，不冒称ready原文普遍被拒。去表示门，保持原主状态，坏附注unknown，不把未知paid变0/新下载许可。ET supervisor usage还有8192字节转unknown的同类表示检查。 |
| RF availability证明文本2048 | source_clock.py:80，被原文receipt、叙述receipt、source资格owner调用 | 非空pathless evidence_ref/locator仍因字符数拒。建议只去任意长度、核producer对齐；错源SHA/日期/未来信息必须照常拒。纯只读未造真实语料反例，不冒已实测。 |
| Biren E2E | run_biren_invest_e2e.py:94、fixture | 冻结schema3.7/engine4.0.0本来不合法，host_signed却没有真实签名记录；ROOT精确E2E已复现。step1还把预登记registry当必须成功。不能换标签或简单更新golden吞掉。 |
| invest即时双重RF验真 | run_company:161/:162、run_bundle:289/:290、validate_bundle_artifact:265/:267；revenue_reference:473内部再验 | 相邻两次对同dict无中间修改。后续让existing reference owner一次验证即可；跨独立public边界仍需要验真，更广复用先真正immutable值，不造skip flag。属效率后续，非人工许可。 |

完整caller/精确SHA、必要定点反控在JSON `findings`。这是当前可达规则；没有把已修的叙述body/receipt/depth、默认registry/host签名许可再报一遍。

## 明确保留与不误报

实际流式下载/HTTP/子进程输出资源、时间、累计费用token、原件保护、来源身份/SHA/期次/as-of、币种单位/公式数学仍保留。RF/invest公式500字符是限制递归算术解析工作，和资料quote不同；需要更长公式应另设计实际AST工作预算，不直接无替代删除。comparison两工件、sensitivity两个不同值等是语义维度。FF credential scalar检查不是文档表示门，本次只读代码，未读凭证。

normal RF/invest当前没有再查到默认host签名/registry许可；自称signed仍应真验。FF旧authorization仅可选scope/caps、expiry不授权；RF processed_artifact_canary是显式只读诊断，没有正常预测caller，不能见名字就说没清干净。RF dated migration3.6→3.7参考页仍记当时unattested默认拒、registry标签，归历史说明/入口清晰度，不冒当前runtimegate；现SKILL明确unattested可用。

## 下一项invest施工设计（ROOT先读，尚未写代码）

1. 保持现有冻结embedded input原值。建立显式、可重放的fixture生成命令，在canonical当前RF、禁网络/host signer/dotenv、独立registry下调用真正run_forecast，冻结实际产物。**不每次测试动态生成自证，不把旧result改tag，不冒旧binary已运行。**
2. 先比较旧golden的经营/收入/利润/估值/SOTP和模块覆盖。技术版本/hash/attestation元数据可以有意迁移，但逐项记录；任何实质数值或模块差异先解释根因，不能`--update-golden`压平。
3. E2E强校验后不再要求registry预登记；添加明确runs目录等隔离参数，真实orchestrator CLI双跑与负例都用独立根。不得枚举/删除旧e2e/.runs，不做自动下载或模型调用。
4. 摘录同owner改非空完整引用；先短/长合法句真RED，错SHA/币种单位/来源反控保留。E2E现有无效pair/假signed作为错误输入反控，新的冻结合法artifact走真实CLI。
5. 仅必要短域＋一轮完整离线E2E（含双跑）；归档源/资产/测试SHA与数学比较。独立delta审查，ROOT正常Git/CI/PWF；RF兼容矩阵/强验/四assurance WIP不动。

## 方法与范围纠错

先用了CodeGraph，但服务仍给CWP符号/历史RF镜像，未当跨仓当前依据，未建索引。**首轮原生筛选误用`/scripts/`，不慎读到已跟踪.planning代码镜像**；发现后立即弃用结果，改严格顶层allowlist，只据当前AST与公开代码/文档给结论。这里如实记录读范围失误，不伪称从未误读；没有打开密钥/原件或执行历史脚本。FF Git status只出现credential文件名，没有读其内容。源/测试/Git/部署均零写，未跑测试或收费，只有本报告两文件落盘，无新持久scratch。
