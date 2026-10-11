# ROOT 当前接收与下一步 — 2026-10-11

这是本批次共享 PWF 的当前入口。下面各计划旧状态是历史；失败证据保留，不重跑一次性封存脚本。

| 包 | 当前事实 | 后续动作 |
|---|---|---|
| W05-CWP-OCR | 已发布代码master8862372f、CI38140484490成功；收尾PWF057f2f8d已推送，正常资料快测148PASS25.73s。54集中+34非作者+148快测；正常push3257PASS。真实微软PPTX83.006s、原85/90s限额、22旧行保持、两条定义恢复。ROOT接受树已正常移除，worker与原件保留 | 完成；POSIX仅静态/未测峰值RSS，不认证全部OCR或研究质量 |
| W05-RF-FLOW | main/origin/main30ddae8e；CI38142227109成功。390+36工程绿、非作者31案例及16原P1入口均绿。17运行文件×2物理安装副本/34SHA匹配，安装后两个fresh进程的合法预测/两强reader/原P1共8拒绝边界通过1.921s；未选元数据和缓存保持 | 完成并线、安装、发布。ROOT干净工作树已正常移除，branch/worker/evidence保留；仅数学与运行接口范围 |
| W06-AUDIT-MEASURES | main9cd5ff8a；296大节点/最终77/非作者反例绿，技能两份各26文件匹配。Audit无remote | 完成；算术审查不认证来源真值 |
| W06-CWP-PORTABILITY | 共用Finding outcome单调聚合已修：69PASS1SKIP9.07s，七场景实际Reader/CLI4.051s；非作者53纯案例/原4输入SHA重放通过，11产品/8producer未变 | 正常ROOT5f10af0b并线发布master6dd7a119，精确CI38145427297成功/正常push3305PASS；ROOT干净checkout已移除。手动工具无需技能安装 |
| W06-FF-MATRIX | 固定CaseSpec/RunSpec 195PASS，非作者28/28；FF main4167dac4与CWP master8bd23344已发布且精确CI成功。旧41从19/21/1升到40/1、164.62秒；新cutoff结果原因正确，独审39PASS/3FAIL发现坏stdout抹去已验stderr用量 | 修单一错误投影后集中复验；最新41因180秒批次截止为2PASS/31PARTIAL/8NOT_RUN、182.86秒，fresh proofs未执行，不算完成。原限额/期望保留；重型测试错开后新attempt收尾 |
| W04业务信息召回 | 质量带共用排序375PASS/13.57秒；ROOT同一固定检查点真实六原件87.4409秒PASS，LPCVD数量、钨验证/重复订单、PRISMO PD5新事实及供应交期四项均有同source同完整group见证。六个legacy指纹/raw/cap/组完整性保持 | 非作者Phase2复核和正常并线待完成；摘要及投资研究仍未验收 |

## 执行顺序

CWP来源层已正常并入master并推送8bd23344（实现983c1732），推送前2816PASS/208.66秒。唯一静态annotation问题由正常pre-commit发现并修复，原freeze保留；精确CI38148948361已成功。FF工具main4167dac4的精确CI38148263309已成功。来源代码并线不代表ET剩余诊断或W04真实召回已通过。

1. FF工具已正常并线推送且CI绿；CWP来源12文件静态hook发现单处空dict annotation，补类型后正常并线发布。旧freeze与失败保留。
2. 独立ET/FF工区cutoff工程绿，非作者39PASS/3FAIL已封存：坏JSON/非对象stdout不能抹去已实测stderr usage。仅修这一共因、集中复验；原41完整联调新attempt在180秒批次到期，不能按2/31/8签收。根因分类与后续见 `.planning/w06-cross-period-acquisition/matrix-deadline-diagnosis.md`。
3. 母W04旧365工程绿与六原件3项FAIL永久保留。Phase2 soft quota抢先于质量已共用修复，375工程绿；ROOT六原件新87.4409秒PASS，四项主体绑定事实完整恢复，不抬cap、不特判。当前为非作者复核和并线收尾。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

本批次0真实provider/LLM/费用；原件、生产配置、Dayu、IQS及他人WIP不改。预算母账保持413778tokens/334463µUSD+FX2764hold，累计上限$20/200万tokens。目标工具当前active。

详细证据：W05/evidence/root-{cwp-ocr,rf-flow}-acceptance/publication.json；W06/evidence/root-audit-measures-acceptance/publication.json，以及另两包独立ROOT接收目录。精选本地计划 .planning/w05-{cwp-ocr,rf-flow}-reception、.planning/w06-{cwp-portability,ff-matrix}-reception。
