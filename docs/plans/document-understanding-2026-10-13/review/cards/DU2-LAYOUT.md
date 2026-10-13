# DU2-LAYOUT：格式证据保真与经营表格结构提示

状态 READY；可独立开工。任务比增加关键词重要：真实名创经营表被抽成单格行，调整路由/摘要提示无法凭空恢复列与表头。

仓库：company-wiki。
工作目录：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/layout
分支：codex/du2-layout-20261013
PLAN_ID=du2-layout；PWF_PLAN_ROOT=<本worktree>/.planning。

先读AGENTS、[report](../report.md)、[ROOT计划](../root_implementation.md)、[INTERFACES第5节](../INTERFACES.md)、原DU STRUCTURE卡和样本清单。当前字体/几何在部分边界丢失，root adapter已有column猜测；你提供一个更可靠的纯辅助能力，ROOT负责将旧推断统一替换和接现有parser。

## 独占路径

- src/company_wiki/document_understanding/layout_hints/**
- tests/unit/document_understanding_layout_hints/**
- tests/fixtures/document_understanding_layout_hints/**
- .planning/du2-layout/**

禁止创建父包init；禁止改原document_normalization/parser/observation_adapter/structure/profiles/summary、其他测试、pyproject/requirements/config/CI/总PWF和安装副本。不能新建PDF→MD流水线、OCR引擎、文档读取器、任务库或供应商配置。

## 公开功能及步骤

1. 以公共第5节的derive_layout_hints输入/输出写RED。输入全部是调用方提供的units和可选字体/bbox；locator不变。至少覆盖：无编号标题vs普通短句、年份不是标题、跨栏页眉、左右中英栏、表格数字孤立行、表头/期间/单位/脚注、跨页续表、坏几何/缺字体/空页面。
2. 分页/分区域做布局分析：用字体相对正文尺度、字重和几何位置作标题证据；缺字体不得仅因短文本强标high。栏识别排除全宽页眉/跨栏表；reading order只输出关系提示，不改原始units排序或删除任何文字。
3. 经营表结构：通过bbox邻接、行列对齐、标题/单位/表头/脚注把已有units组成候选表区/行组。一个表跨页须有明确列/表头延续依据；表中的多个时期/地区/经营模式不能混为一个数量。输出原unit引用和必需上下文，不猜缺失数值、不对表格求投资结论。
4. 负例包括相邻无关表、金额相同但项目不同、两个语种并非逐句对应、表格无表头、脚注属于上一图、坐标越界。合理低置信或partial通过，错误complete/high必须失败。不能靠公司名/固定页码/数字白名单。
5. 真实C样本以名创p12门店表、恒锋跨页项目、另一公司不同排版为基础；额外HTML/PPT输入只在已有前端能够提供真实几何时测，缺能力如实列needs_upstream。可以用已安装PyMuPDF只读观测字号/几何，但该采样脚本只属于测试，不能作为生产第二parser。probe IDs与原页面坐标的映射留证，不伪称已有生产locator。
6. 运行1k/10k/40k合成规模测趋势，记录units/groups/work_units/耗时/峰值RSS（未测明确未测）；避免全量N²与无限跨页关联。限额来自调用方，超限partial。性能作为集中节点观察，不在CI放脆弱毫秒断言。
7. 交付API文档、实现、精简fixtures与测试、真实样本对照、ROOT需要保留/传入哪些字段清单。不得声称未接生产的辅助函数已修复最终召回或摘要。ROOT后续只接一个共享几何实现，清掉被替代的重复逻辑。

## 三节点、测试与恢复

- A：接口与正反形态RED；确认来源坐标/输入保留。
- B：本包unit、确定性、非修改输入、关系引用存在、预算/复杂度、反例。
- C：真实原件小样本对照、另一公司泛化、空间/恢复与一次交接。

命令：python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q

按仓内规则仅对本包运行ruff。真原件测试默认离线opt-in；缺binding为UNAVAILABLE/SKIP，不计真实通过；不能因为测试路径算错导致永远skip。验证集中命令实际运行过真实用例。

测试在自有tmp放哨兵，失败也finally清理；原件只读SHA/mtime保持。局部裁图只作C节点检查，用完删除；不存整页截图集/全文MD/PDF副本。fixtures合计建议≤256KiB，真实摘录每source≤8KiB；超出说明必要性，不假删证据。

0供应商调用/费用，无新增依赖。正常提交本分支，handoff按公共第6节并额外列输入几何要求、未支持载体、歧义/partial条件、复杂度和ROOT接线建议；然后停止，不合主线/push主线/安装。
