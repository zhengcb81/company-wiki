# ROOT 当前接收与下一步 — 2026-10-11

这是本批次共享 PWF 的当前入口。下面各计划旧状态是历史；失败证据保留，不重跑一次性封存脚本。

| 包 | 当前事实 | 后续动作 |
|---|---|---|
| W05-CWP-OCR | 已发布代码master8862372f、CI38140484490成功；收尾PWF057f2f8d已推送，正常资料快测148PASS25.73s。54集中+34非作者+148快测；正常push3257PASS。真实微软PPTX83.006s、原85/90s限额、22旧行保持、两条定义恢复。ROOT接受树已正常移除，worker与原件保留 | 完成；POSIX仅静态/未测峰值RSS，不认证全部OCR或研究质量 |
| W05-RF-FLOW | main/origin/main30ddae8e；CI38142227109成功。390+36工程绿、非作者31案例及16原P1入口均绿。17运行文件×2物理安装副本/34SHA匹配，安装后两个fresh进程的合法预测/两强reader/原P1共8拒绝边界通过1.921s；未选元数据和缓存保持 | 完成并线、安装、发布。ROOT干净工作树已正常移除，branch/worker/evidence保留；仅数学与运行接口范围 |
| W06-AUDIT-MEASURES | main9cd5ff8a；296大节点/最终77/非作者反例绿，技能两份各26文件匹配。Audit无remote | 完成；算术审查不认证来源真值 |
| W06-CWP-PORTABILITY | 共用Finding outcome单调聚合已修：69PASS1SKIP9.07s，七场景实际Reader/CLI4.051s；非作者53纯案例/原4输入SHA重放通过，11产品/8producer未变 | 正常ROOT5f10af0b并线发布master6dd7a119，精确CI38145427297成功/正常push3305PASS；ROOT干净checkout已移除。手动工具无需技能安装 |
| W06-FF-MATRIX | 工具34PASS，实际41case19PASS/21FAIL/1PARTIAL132.54s已冻结。共因已确认：canonical入库事实与local_reconcile资格脱节，已排除旧期又被当当前缺口；多数ET未启动是primary前置失败 | 最终独审发现CaseSpec权威缺口，正式RED后统一工具修复；ROOT独立生产施工计划 .planning/w06-cross-period-acquisition，先真实RED再共用修复，不能以换fixture/skip换绿 |

## 执行顺序

1. 发布已验收并线的 Portability；关闭 FF CaseSpec 权威缺口，接收矩阵的真实范围，正常 commit/并线/push。独立测试只有大节点，不增加人工许可或每 commit 全链。
2. ROOT 独立工区修复已确认的 CWP 跨期来源共因，重放原失败。
3. 返回母 W04：新具体包 `.planning/w04-root-novelty-recall/`。已查出数字/阶段被软重复压制、数量主体误认等价，先真实token/group RED再共用修复；旧selector指纹、原件SHA、硬cap保留。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

本批次0真实provider/LLM/费用；原件、生产配置、Dayu、IQS及他人WIP不改。预算母账保持413778tokens/334463µUSD+FX2764hold，累计上限$20/200万tokens。目标工具当前active。

详细证据：W05/evidence/root-{cwp-ocr,rf-flow}-acceptance/publication.json；W06/evidence/root-audit-measures-acceptance/publication.json，以及另两包独立ROOT接收目录。精选本地计划 .planning/w05-{cwp-ocr,rf-flow}-reception、.planning/w06-{cwp-portability,ff-matrix}-reception。
