# 当前交接 — R6工程已发布且主线CI绿，T3实施中

唯一入口：[CURRENT_STATUS](CURRENT_STATUS.md)/[json](CURRENT_STATUS.json)。`PLAN_ID=du11-source-closure-2026-10-18`，`PWF_PLAN_ROOT=docs/plans`。用户已恢复实施，不执行历史暂停或再revert候选；ROOT唯一维护主PWF和集成。

## 1. 当前代码和结果

| 位置 | 版本 / 实际状态 |
|---|---|
| ROOT `master` / `origin/master` | 工程runtime10767b86，主线bundle`c6bb801b`已正常推送；精确主线CI41381788839成功，候选CI/最终独审均过。 |
| ROOT独占 `tmp/architecture-r2` | `codex/architecture-rectification-r2-20261101`，`10767b86`已正常commit/push；精确完整CI41380285347成功，最终28场景独审PASS；已正常并本地master。 |
| W23/daily自有 `tmp/w23-r6` | 已复用为T3分支`codex/architecture-t3-source-scope-20261102`，base c6bb801b；ROOT做TERM（48P），recipe agent做NOTE/PHYS在途。旧daily/W23均已发布，不重做。 |
| RF | main/origin957c6283，精确CI41304681319成功，选定runtime已定点安装；本轮无新RF改动。 |
| StockWiki | Q09本地master381811e5已并；历史无remote，未声称推送。 |

R4候选2b0787dc完整CI70F保留。R5已按原合同修复：材料eligible/自足信息不表示世界事实核实；业务范围、计划和定义不应一律降格。原70期待全恢复。唯一20file最后1044P/4F31.23s，四处17P5.19s恢复；后续资源兼容98P/1F8.18s，同prepared文本/生产两投影修复后16P5.54s。**没有把这些数相加或称最后1048全绿。** 正常commit的Ruff/全src mypy绿；正常push固定167P28.67s，总34.86s成功。

- 冻版：[R6-source-contract-r5](review/architecture-quality-20261101/implementation-results/R6-source-contract-r5.md)，9源码/3自增测试manifest为`R6-r5-freeze-manifest.json`、SHA `d45fc6875e411b2e2911e78e838b84a47af98fdf27c35c50438e5bc03b863650`；另ROOT预算spy同次提交。
- 合同独审调查：`R6-independent-source-contract-r5.md`，消费链调查：`R6-source-material-consumers-r5.md`；它们是合同调查；最终代码独审`R6-independent-ci-r5.md/json`已PASS，28场景及13SHA绑定10767b86，自有tmp/k5恢复absent。
- T3六个新测试在候选工区`tests/unit/document_understanding_note_scope/`，**untracked且行为RED，必须排除R5暂存**；只随T3产品实现提交。R5源码作者已STOP，最终独审已通过；T3 NOTE/PHYS作者现在施工，不要在其运行测试时改索引/提交工区；后续改动必须有新节点证据，不能挪用本次冻版签收。

## 2. 单一下一步与后续顺序

1. `10767b86`最终独审和完整CI已通过，已正常FF本地主线；不要重复旧整改/1048/整仓。主线c6bb801b已正常发布且精确CI绿，不重做。
2. FF已逐13SHA/物理mode证明ROOT在途内容不变；正常发布已完成；后续保持Git hook索引100755，不把外来Windows物理644变化提交。原件/生产配置不变，不取Git缓存凭证、不绕hooks。
3. T3实施中：ROOT仅text_boundaries/adapter/layout与纯helper测试，NOTE/PHYS作者负责sections/scopes/native proof/partial传播，不重叠。TERM48P，adapter identity随后9→10，最终合并测试需绑定最终身份。按[R6-T3-implementation-plan](review/architecture-quality-20261101/implementation-results/R6-T3-implementation-plan.md)实施。已冻47例首跑28F19P，其中27真行为RED＋1夹具错误；夹具单修1P、未再跑47。统一编号完整句/闭引号原语，source-marked长/换行备注局部frame，保留本scope主体引介；仅缺推断证据时局部partial，不把bbox变普遍许可。只设工程冻版独审与真实大节点，不新增小签收。
4. 单次最终H1使用`.planning/architecture-quality-20261101/real-acceptance/README.md`的runner/cases/oracle：90s/16M/112不变，核12业务unit/111原生成员、9对context/member和正向主体引介。runner硬绑定ROOT/src，不能只改PYTHONPATH假称跑候选。旧v1数量通过与v2公开合同失败不代最终。
5. 来源通过后，在新隔离catalog/AUTO仅引用既有原件，按`C-preparation.md`做配置真实摘要、paid prepared中断/same/cross-run零重复、**同一新artifact**实际RF参数/公式/报告/snapshot采用，再集中独审。两旧P1配置已absent；不得复制原PDF/旧DB，不改R3/R4封存。

## 3. 已完成与不得重做/夸大的范围

- W23工具runtime ae438a32、候选6b70394b和主线848b4ee0完整CI绿。真实X1漏cache/无inflight/零余额/NaN已根修并独审；旧8页实验仍PARTIAL，实际总elapsed=null、1800合规/峰值/小米精度/生产适用性未证，两次真实失败保留。没切生产OCR、没新模型推理/下载。见`R6-W23-publication.json`与独审/精确PNG清理收据。
- daily快检819cef31已独审、候选和主线完整CI绿。代码范围只跑固定原167smoke，已确认文档范围0pytest；不再AST影响图扩选千例。precommit仍静态，完整CI/作者定点测试/重大E2E保留；超时/输出/子进程错误仍真实失败。不是削弱用例来掩盖产品回归。
- 消费者50P、独立7P＋稳定窗口CF3 1P；AUTO/离线关联72P正常host；四种frozen Exception传播根修、CI4096 annotation分组修复已随10767b86发布，主线c6bb801b完整CI绿。
- 早期华利15卡/12原子、Berkshire73卡/10原子、恢复/RF v6 45项是历史有界成果；15个BRK未处理与全文partial保持，不能代当前runtime正式验收。

## 4. 数据、环境与所有权

使用宿主`C:/Miniconda/python.exe -B -X utf8`。正常host执行已授权Git/原子写测试；sandbox os.link WinError5曾造成假产品失败，同72域host全绿已证，不为此削弱CAS。pytest禁自动插件时要显式启pytest_timeout/asyncio；cache关闭，独立短tmp先证明初始absent、测试后恢复。无法证明归属的历史临时文件不猜删。

ROOT主工区在途自有PWF/AGENTS语义注释及两份hook/config过期header注释；header执行body保持。外来hook物理mode、旧未跟踪产物/原始gold和RF四assurance WIP保留。Dayu/IQS/Dashboard及其他owner工区不改。source DB/WAL bytes＋mtime保持，SHM允许仅mtime不同但存在性/大小/SHA相同；不可构造生产AutomationStore作只读观察。

冻结AUDIT `runs/r1-20261021-cn-wuxi-apptec/execution_replays/r1-remediation-04`：585件/64,240,251B、manifest75f2871b…c568保持。模型/预算只按`config/models.yaml`与`config/resource_budget.yaml`：10Mtokens/$20，公司150k/$1软目标；最近母账1,965,633tokens/762,082microUSD估计，unknown8＋prior7保持，**本轮0收费调用**。沿用用户授权，不新造逐材料许可或签收链。

## 5. 整体目标未完

ghost-formula/期间补集、原R4六issue与买方反证/经营幅度校准、代码方法/检测演进、W21真实增强/严格成员对齐、长文/US监管PDF/HK/RPO、固定八家/药明合联和Snowflake泛化/连续三家clean均仍OPEN。旧native goal为paused且工具无active-resume操作；本次按用户恢复指令手动续接，不新建竞争目标或声称整体完成。

历次返修/真实失败详见[R6-ROOT](review/architecture-quality-20261101/implementation-results/R6-ROOT.md)和各带版本收据。更早交接快照在Git `1bf3d388` 的本路径保留；历史结论不作为当前施工指令。
