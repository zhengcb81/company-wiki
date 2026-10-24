# IR-REPORT-GENERATION：行业研究报告输出可靠性

状态：READY；不阻塞 company-wiki 主线。项目 C:/Users/郑曾波/Projects/industry-research。独立工作目录 C:/Users/郑曾波/Projects/industry-research-report-generation。branch codex/ir-report-generation-20261024。冻结起点 main@4a80f9988f9325fb0a348c8acd9e41d615005c5f；派卡前原仓干净且没有显示 remote。PLAN_ID=ir-report-generation-2026-10-24，PWF_PLAN_ROOT=docs/plans。

## 目标与边界

现有 tools/report_generator.py 从框架、问题和公司 JSON 生成 Markdown。当前 JSON 缺失会被 load_json_file 静默转为空对象，日期直接取系统日期，输入字符串进入 YAML frontmatter、表格和正文。该目录目前没有专属测试。任务是用可复现的离线测试找出并修复报告输出边界问题：无效输入不得伪装成正常空报告；特殊字符不能破坏 Markdown/YAML；写入失败不能留下半成品或截断旧报告；固定输入和固定日期应有稳定输出。

不改变研究评分、业务结论、行业框架、数据采集或 T02 集成。

## 唯一写入范围

允许：tools/report_generator.py；新增 tests/test_report_generator.py 与 tests/fixtures/report_generator/**；本卡 docs/plans/ir-report-generation-2026-10-24/** 和 docs/handoff/IR-RG-2026-10-24/**。

禁止：SKILL.md、modules/**、config.yaml、cache/**、生产 outputs/**、references/**、安装副本，以及 local-skills、StockWiki、IQS、company-wiki 中的任何路径。禁止真实公司数据、PDF 转换、DeepSeek、Web/API 和下载。

## 实施与验收

先冻结 JSON 输入最小合同，再用合成样例复现：必需文件缺失、损坏 JSON、顶层类型错误、合法可选字段缺失、空列表、中文和 YAML/Markdown 特殊字符、表格分隔符和换行、超长字段、目标已存在、目标目录不可写。区分必需字段与可选字段；兼容的可选字段继续可省略，必需输入则明确报路径/字段错误。不要改 company_list.json 与 companies.json 的命名，那属于 IN-02。

将内容构造和文件写入职责分开，使日期可注入测试。对 frontmatter 和表格字段做正确转义；不要改写、丢失或臆造来源内容。先完整生成并校验，再以安全方式替换目标；保留成功时覆盖旧报告的既有行为。异常时保留旧目标字节并清本次临时件。

最低验收：固定 synthetic golden 的 UTF-8 字节/关键结构；错误输入非零退出与可读诊断；特殊字符不破坏 frontmatter/表格；同输入同日期输出确定；生成异常/不可写路径保留旧 SHA；临时目录清理前后 inventory 一致。

运行：

    python -B -m unittest discover -s tests -p "test_report_generator.py" -v
    python -B -m py_compile tools/report_generator.py tests/test_report_generator.py

用标准库 unittest 优先，不新增运行时依赖。项目既有检查若因环境或 install 副本基线失败，如实记录并隔离，不改无关路径求绿。

## 独立审查与交接

实现者提交分支并冻结 SHA 后，独立 agent 审完整 diff、独立运行上述测试，并自行加入一个破坏 YAML 或 Markdown 表格的反例。修复所有发现并复审最终 SHA PASS 后才能交接。交付包含 docs/plans/ir-report-generation-2026-10-24、docs/handoff/IR-RG-2026-10-24/handoff.md/json、review 报告、测试日志及清理清单。若无 remote，标注 NO_REMOTE。
