# ROOT 当前接收与下一步 — 2026-10-11

这是本批次共享 PWF 的当前入口。下面各计划旧状态是历史；失败证据保留，不重跑一次性封存脚本。

| 包 | 当前事实 | 后续动作 |
|---|---|---|
| W05-CWP-OCR | 已发布代码master8862372f、CI38140484490成功；收尾PWF057f2f8d已推送，正常资料快测148PASS25.73s。54集中+34非作者+148快测；正常push3257PASS。真实微软PPTX83.006s、原85/90s限额、22旧行保持、两条定义恢复。ROOT接受树已正常移除，worker与原件保留 | 完成；POSIX仅静态/未测峰值RSS，不认证全部OCR或研究质量 |
| W05-RF-FLOW | main/origin/main30ddae8e；CI38142227109成功。390+36工程绿、非作者31案例及16原P1入口均绿。17运行文件×2物理安装副本/34SHA匹配，安装后两个fresh进程的合法预测/两强reader/原P1共8拒绝边界通过1.921s；未选元数据和缓存保持 | 完成并线、安装、发布。ROOT干净工作树已正常移除，branch/worker/evidence保留；仅数学与运行接口范围 |
| W06-AUDIT-MEASURES | main9cd5ff8a；296大节点/最终77/非作者反例绿，技能两份各26文件匹配。Audit无remote | 完成；算术审查不认证来源真值 |
| W06-CWP-PORTABILITY | 共用Finding outcome单调聚合已修：69PASS1SKIP9.07s，七场景实际Reader/CLI4.051s；非作者53纯案例/原4输入SHA重放通过，11产品/8producer未变 | 正常ROOT5f10af0b并线发布master6dd7a119，精确CI38145427297成功/正常push3305PASS；ROOT干净checkout已移除。手动工具无需技能安装 |
| W06-FF-MATRIX | 固定CaseSpec/RunSpec 195PASS，非作者28/28；已并FF main4167dac4、精确CI38148263309成功，正常push645PASS/7host或显式环境SKIP。CWP来源修复191PASS+13/1独审通过；原41从19/21/1升到40/1、164.62秒 | 剩余call_past_cutoff仅ET→FF原因丢失；TDD共用结构化诊断，原期望不改。整个矩阵C仍开放；手动工具不在每commit跑41场景 |

## 执行顺序

CWP来源层已正常并入master并推送8bd23344（实现983c1732），推送前2816PASS/208.66秒。唯一静态annotation问题由正常pre-commit发现并修复，原freeze保留；精确CI38148948361已成功。FF工具main4167dac4的精确CI38148263309已成功。来源代码并线不代表ET剩余诊断或W04真实召回已通过。

1. FF工具已正常并线推送且CI绿；CWP来源12文件静态hook发现单处空dict annotation，补类型后正常并线发布。旧freeze与失败保留。
2. 独立ET/FF工区实施来源cutoff原因及闭集投影；非作者一个大节点，原41按原期望/180秒新attempt回放，再正常发布/必要定点安装。
3. 母W04工程365与非作者范围绿；真实六原件77.681秒、旧6指纹/raw/cap保持但LPCVD数量、钨验证量产订单、PRISMO PD5新事实3项FAIL。soft quota抢先于质量的共因已确认，Phase2质量带/同带公平TDD修复，不抬cap、不特判。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

本批次0真实provider/LLM/费用；原件、生产配置、Dayu、IQS及他人WIP不改。预算母账保持413778tokens/334463µUSD+FX2764hold，累计上限$20/200万tokens。目标工具当前active。

详细证据：W05/evidence/root-{cwp-ocr,rf-flow}-acceptance/publication.json；W06/evidence/root-audit-measures-acceptance/publication.json，以及另两包独立ROOT接收目录。精选本地计划 .planning/w05-{cwp-ocr,rf-flow}-reception、.planning/w06-{cwp-portability,ff-matrix}-reception。
