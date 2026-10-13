> 2026-10-13新增：[文档理解升级独立子计划及三卡](../../../document-understanding-2026-10-13/README.md)。仅设计/调查，生产未切换；三卡可与剩余W08接收并行，ROOT集成后共用G2/G4/G5，不重复扩张日常测试。

# ROOT 当前接收与下一步 — 2026-10-11

这是本批次共享 PWF 的当前入口。下面各计划旧状态是历史；失败证据保留，不重跑一次性封存脚本。

| 包 | 当前事实 | 后续动作 |
|---|---|---|
| W05-CWP-OCR | 已发布代码master8862372f、CI38140484490成功；收尾PWF057f2f8d已推送，正常资料快测148PASS25.73s。54集中+34非作者+148快测；正常push3257PASS。真实微软PPTX83.006s、原85/90s限额、22旧行保持、两条定义恢复。ROOT接受树已正常移除，worker与原件保留 | 完成；POSIX仅静态/未测峰值RSS，不认证全部OCR或研究质量 |
| W05-RF-FLOW | main/origin/main30ddae8e；CI38142227109成功。390+36工程绿、非作者31案例及16原P1入口均绿。17运行文件×2物理安装副本/34SHA匹配，安装后两个fresh进程的合法预测/两强reader/原P1共8拒绝边界通过1.921s；未选元数据和缓存保持 | 完成并线、安装、发布。ROOT干净工作树已正常移除，branch/worker/evidence保留；仅数学与运行接口范围 |
| W06-AUDIT-MEASURES | main9cd5ff8a；296大节点/最终77/非作者反例绿，技能两份各26文件匹配。Audit无remote | 完成；算术审查不认证来源真值 |
| W06-CWP-PORTABILITY | 共用Finding outcome单调聚合已修：69PASS1SKIP9.07s，七场景实际Reader/CLI4.051s；非作者53纯案例/原4输入SHA重放通过，11产品/8producer未变 | 正常ROOT5f10af0b并线发布master6dd7a119，精确CI38145427297成功/正常push3305PASS；ROOT干净checkout已移除。手动工具无需技能安装 |
| W06-FF-MATRIX / W07-FF-PERF | 原41全PASS/99.9624秒；26fresh原文证明、零oracle、目录恢复。FF64b4d29/ETd0ac42c6本地与远端相同；FF精确CI38170433893 成功。225集中、ET53、正常push708＋78subtests；两文件×两安装/各5边界及三仓配置体检绿 | 接收、并线、同步完成；真实供应商/经济质量仍留G4/G5 |
| W04业务信息召回 | 当前ROOT473集中绿/原六真实115.4879s PASS、6legacy一致/4绑定事实完整；正常本地merge c1d6ab92，旧18FAIL已根修 | 正常push/精确CI收尾；W08与G2/G4/G5仍开放 |
| W08-CWP-G2-REPLAY | 作者a6010480，ROOT补实际观测/真缓存失效a90fada2；35集中/50.3324秒真实九文档链路绿，预存哨兵恢复、203690字节归档；main本地已并be963081 | 正常push/精确CI收尾；真实供应商摘要和公司审查仍留G2/G4/G5 |
| W08-RF-COMBOS | 作者4d5c9f05已交，但C02仅年度标签、C05以预测当实际且入口记错，实际原生覆盖未闭；不照自报CLOSED接收 | ROOT优先补真实dated贡献及独立actual原生回测，再并线 |
| W08-AUDIT-EVIDENCE | 作者96889c6/e9146453已交，初始INPUTS字节保持 | ROOT独立接收可选有界实读层，再正常并线/安装 |

## 执行顺序

CWP来源层已正常并入master并推送8bd23344（实现983c1732），推送前2816PASS/208.66秒。唯一静态annotation问题由正常pre-commit发现并修复，原freeze保留；精确CI38148948361已成功。FF工具main4167dac4的精确CI38148263309已成功。来源代码并线不代表ET剩余诊断或W04真实召回已通过。

1. FF工具已正常并线推送且CI绿；CWP来源12文件静态hook发现单处空dict annotation，补类型后正常并线发布。旧freeze与失败保留。
2. ET/FF单一错误投影已修：集中独审7PASS，正常分支commit ETd0ac42c6/FF2d380a05。旧失败保留；原41第二完整attempt仍因180秒截止1/27/13，W07-FF-PERF负责运行共因，此条为前次失败历史；W07验收后已正常并线FF64b4d29/ETd0ac42c6，详最新接收条目。
3. W04旧365工程绿与六原件3FAIL保留；新375工程/同六原件87.4409秒/非作者17＋4均绿。18文件已精确集成且51集中测试通过；正常hook发现18既有边界FAIL，远端尚未发布。ROOT先修共因并验收，不跳过hook、不盲目重跑全套；G2四文件仍独立后移。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

本批次0真实provider/LLM/费用；原件、生产配置、Dayu、IQS及他人WIP不改。预算母账保持413778tokens/334463µUSD+FX2764hold，累计上限$20/200万tokens。目标工具当前paused；用户授权的独立接收正常推进。

详细证据：W05/evidence/root-{cwp-ocr,rf-flow}-acceptance/publication.json；W06/evidence/root-audit-measures-acceptance/publication.json，以及另两包独立ROOT接收目录。精选本地计划 .planning/w05-{cwp-ocr,rf-flow}-reception、.planning/w06-{cwp-portability,ff-matrix}-reception。

## W07 已完成分发与接收（三包历史）

[总览、三个独立卡与实际目录](../w07_parallel_quality_2026-10-11/README.md)：W07-FF-PERF（优先）、W07-RF-MODEL、W07-AUDIT-ANALYST。W07已交付并接收，RF组合覆盖仍PARTIAL；初始READY是准备历史。已有独立PWF/固定输入/交接接口。ROOT并行推进W04→G2，接收后将新工具用于G4/G5，不把工程报告当真值/经济判断。

2026-10-11准备时再次只读核对：三条工作树HEAD分别为FF2d380a05、RF30ddae8e、Audit9cd5ff8a，分支与卡一致。这是准备历史，不是实时状态。

### W07-AUDIT-ANALYST 已接收

用户交付34b5c8ee/e3206880，ROOT独立反例及agent试读发现scope/ref/actual共因；已在独立接收树系统修复，原assertions保持。最终90PASS+4子案例/2.30s、原13真CLI COMPLETE/1.4392s、技能结构绿。正常Audit main实现e7c92577及收尾2c494913，主仓干净；两副本只变三文件，各28文件SHA一致，两个安装后实际CLI通过。无remote/CI，不宣称远端发布；0provider/LLM/费用。详细 `.planning/w07-audit-analyst-reception/publication.json`。RF与FF最新接收结果见本文后续条目；此句为历史记录。ROOT回W04→G2；此诊断工具不替代G4/G5真实研究及独立判断。

## W07-RF-MODEL ROOT 接收结果

工程工具接收、整卡部分覆盖：作者d282c9d/72d0ced保留，ROOT22RED/1PASS暴露误报共因；系统修复异常分类、per-case真实request/result、未知/空比较、完整清单、CLI/readonly/清理状态和原目录恢复。原assertions不变，最终36PASS/4.19s，原16向量11PASS/5REJECT_OK、三实际CLI0/2/0，1.394767s。正常main/origin/main8dc26710，推送前390PASS＋36subtests/32.07s，精确CI38168556914成功；150WIP文件SHA保持，不安装工程工具。

仍缺CNY/HKD、并购控制/跨FY、联合量价、累计/净额/防双计、future actual/WAPE五组覆盖，不能称整卡COMPLETE，详[后续](../w07_parallel_quality_2026-10-11/ROOT-rf-remaining-coverage.md)。ROOT留证只存单份压缩native JSON与摘要，当前约330KB。0provider/LLM/费用；来源真值/买方经济判断仍未认证。CWP母PWF提交可在本地保存，远端发布仍待W04旧18失败修复，不以RF CI代替CWP发布。

## 2026-10-11 W07-FF-PERF ROOT 最终接收

W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。

证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。

## W08 新三包 — 2026-10-12

用户要求新的排他施工包；ROOT已核真实Git/PWF并准备三个固定工区，全部READY_NOT_STARTED，无worker开工。
[总入口与三张施工卡](../w08_parallel_completion_2026-10-12/README.md)：RF补W07五组实际遗漏；Audit在已有coverage上补optional实读执行证据；CWP新tools做有限摘要→read→固定RF消费离线联调，不写ROOT的W04 src。各包不同repo/workdir、固定代码输入、独立PWF、接口/测试/交接合同，只有A/B/C大节点，不增加许可门。
ROOT保留W04核心修复/当前主线/安装及真实G2/G4/G5；CWP工具可先开发并交如实PARTIAL，修W04后ROOT重跑同CaseSpec。三个包不等待彼此，也不运行收费模型/provider。

## ROOT W04当前收尾 — 2026-10-12

2026-10-12 ROOT W04完整owner/质量/stage共因已正常分支4e58e347＋2d9f9d12并入本地主线c1d6ab92；473集中PASS13.22s，原脚本同六原件PASS115.4879s、6legacy full hashes一致、4complete source-bound事实齐全，原件/三生产配置不变、临时metadata恢复absent。旧18FAIL及所有RED保留，正常主线push/精确CI待收尾；工程绿不认证完整召回/摘要或研究。三个W08均DELIVERED_NOT_ROOT_ACCEPTED，实际初始INPUTS均保持；先基础发布，再RF→Audit→CWP工具接收与G2真实配置摘要/RF消费→G4原三家四独审→G5新三及循环。本轮0收费，母累计预算不变。用户续行已授权完整目标，工具goal字段仍paused，不另建或缩小目标。


## 当前发布结果

CWP已验收发布：代码主线/远端d75e9698a3401854dfd4368bbe9b7c40f73c3263，正常push3648PASS197.96秒，精确CI38304041971 success。35工具测试/50.3324秒真实九文档联调，复用0POST，版本/spec各1POST、70输入SHA/mtime不变，预存哨兵及独立测试目录恢复。证据203690字节ZIP，136自有重复文件187288字节已逐字节验证归档后移除。W04原件/legacy/四事实节点和CWP工具工程接收完成；真实供应商摘要、RF/Audit两包、G4/G5真实研究与循环仍待做，完整母目标未完成；本轮0付费。
