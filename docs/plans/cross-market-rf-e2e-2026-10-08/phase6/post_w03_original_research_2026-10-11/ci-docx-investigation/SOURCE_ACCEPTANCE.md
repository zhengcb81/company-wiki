# native DOCX/HTML/PPTX 边界与 DOCX 解析版本共因验收

7源码实现已集中接受；正常发布/精确新HEAD CI待ROOT后续真实回执。不能以本文件代签远端CI。

- 根因：按hash重排物理原生单元，generic context跨表格/标题，并重新引入财务cell；DOCX parser未保存outline/style；Worker按手列格式漏传DOCX冻结parser。
- selector新0.7.1按物理units/结构barrier处理；旧0.6/0.7保持原行为和真实TXT指纹。
- DOCX default1.1，样式继承/真实outline/9正文覆盖；explicit1.0全字段before=after，旧指纹a6580fca…和6精确locator回放不变。
- TDD初始10FAIL/2PASS→112集中PASS；ROOTheading2FAIL→2PASS。parser11FAIL/6PASS→104集中PASS，最后typing后37DOCX PASS。这些组有交集，不相加。
- 公共selector四职责联合GREEN；native14PASS及DOCX公共首RED真实Worker map漏项；修map后只重验公共1PASS/21.68pytest秒，不冒称重跑15。4真实CLI全部exit0，old items/binding/SQL/budget不变、新version不同artifact、reuse0HTTP/0新费用，总2 loopbackPOST。
- staticRuff绿，parser四源mypy绿但本机lxml-stubs缺失明示import-untyped排除；未删除类型责任。
- 最终fresh独立39checks/29最小probes接受，material_findings=[]。报告SHA1eba0243e1d32b035faf255a214742d92f19e3ec42c7bd4375ccc26b3367fc1b / 8f778369fe40e3c7ded5ab6aff9664d0fba01048e049a725a3d71c015d8980ac。
- 原77,565B远端失败日志、所有RED/首attempt/旧before/actualdocx原件保留。0真实provider/model/新费；原三家公司旧execution seal不改变。

证据见 evidence/root-final-node、docx-heading-implementation、final-heading-independent-review 与本PWF。测试owned临时根已恢复；生产原件/config/Dayu及其它仓库owner WIP保持。

## 2026-10-11T02:54:29.485947+00:00 发布事实补充

7产品源码ee293769普通提交/主线/推送，本地3196PASS199.24s，精确LinuxCI38105648234实际2FAIL/3057PASS/6skip76.96s。两失败现精确归ZIP fixture宿主create_system；唯一test-only补丁双宿主TDD RED1FAIL/1PASS→集中39PASS及独立4probe+2定点PASS接受，原正文/locator/完整旧字段断言/历史recordSHA保持。源产品7SHA和生产2config保持。下一次普通发布后只以其精确LinuxCI接收，不把本地或旧CI冒签绿。公司四审质量另有真实FAIL待共因专家，未完成总目标。

## 2026-10-11T03:10:01.647836+00:00 — ZIP跨平台fixture修复正式关闭

普通commit d3d807691efa68a30ae50fffb9980db4942eccae，normalpush3198PASS/191.38s；精确GitHub CI38106925215 completed/success，同HEAD。原ee293769两项FAIL和原日志不改，新fixture保持d428原DOCX及a658全record指纹，独立报告2a40a946…/b6171d18…接受。来源7产品/2配置前后不变。本次只签工程DOCX责任，不签三公司研究。后续推送范围修复为独立效率事项，不能替代原CI接受。
