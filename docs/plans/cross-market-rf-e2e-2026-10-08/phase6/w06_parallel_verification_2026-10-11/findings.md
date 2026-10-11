# W06 调查事实

- 2026-10-11：三个 W05 树均已有各自 task_plan.md，Audit 树新增 pool_progress.py/fixtures/tests；只读观察，不清理他人 WIP。
- Audit main c0993332 干净。numeric_audit.py 实读：只做 Decimal 单位/币种转换；现有七类测试包括 billion/亿、FX 方向、比例、非法数、精度及 CLI。新包不是修复已证实发生的幻觉事故，而是补充可观察检查能力。
- FF main 08ec85b2；唯一未跟踪项 config/FMP_API_KEY.txt 是用户配置，不读、不复制、不提交。已有 ET /2 producer fixtures、CWP SourceRef 2.0/receipt 2.1、isolated_wiki 及 transport 测试；新矩阵要记录既有覆盖，不重写它们。
- ET 已提交起点 c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52；未跟踪 .workbuddy-ai/、eval_results.json 不动。真正入口在仓库根 transcript_tool.py，已有 tests/test_retrieval_cli_e2e.py 的 private launcher 可只替换 worker HTTP，保留实际 supervisor/API。不能给生产工具添加 fake CLI 开关。
- CWP SourceRef 2.0 只有 document_id/source_id/SHA/size/MIME/schema；公开 reader 每次验证当前根和字节。根迁移、相对路径改名、重新登记与新内容版本是不同操作，不能要求所有 document_id 永远不变。
- N5-DOCSET 已完成，43 case、9原件/86点/744定位的历史报告保持，不重派、不重标 golden。
- 只读工具问题：默认 sandbox git status 在外部 worktree 报 not a work tree；同命令经已有授权 require_escalated 只读成功。CodeGraph audit 未初始化、CWP/FF 索引缺新模块，未重扫或修改索引，改读已知源码。猜测 numeric-lineage.md、OWNER_MATRIX.json、readiness.json 和 ET scripts/earnings_transcripts.py 路径不存在；实际 rg --files 确认入口，不伪造缺失文件。
- ROOT 当前 stage/budget 独立审查 FAIL：真实年报 p41/p44/p62 强候选确实 candidate=true/selected=false；公开 0.8 旧候选 regex 绕过新 stage helper。六原件 ALL_DONE PASS 只指字节/预算/旧指纹，不能替代语义质量。

准备结果：三树 clean before inputs；12固定输入/36源码参考已实核，代码展开共17870965B，无原件副本。首次--no-checkout留下空index，核新树仅.git后read-tree物化；首次physical bytes与blob不等是i/lf,w/crlf，git diff实际无改，最终分别记录physical与blob SHA。这两个失败均保留，不reset用户内容。未来本包测试NOT_RUN、0网络/模型/新费用。

ROOT接口补充另发而未覆盖12原输入；最终18输入SHA/三卡同字节/三树仅docs/handoffs输入WIP/相对链接/两生产配置指纹均通过。未来实现和E2E未跑，未以准备PASS代工程质量。

命令诊断补记：提前读取尚未完成的独审report.json不存在，未据此宣称无审查/失败；等待实际交付后接收。所有准备异常都保留，不再重复猜入口。

Git diff --check发现新增current头CRLF被当trailing whitespace；只将新头转LF，全部历史tail原字节保持，不改仓库whitespace规则。

独立卡片大节点试读STOP：NO_DESIGN_BLOCKER_FOUND；20实际源码/三卡/三inputs及ROOT补充已绑定。报告e07d7ffc/MD b194cd94实核。三树可分派；未来测试0，原0.8源码FAIL保持。接下来普通commit/push计划，ROOT继续源码共因修复。

首次git add的PowerShell拼接数组被当成单pathspec，退出1、未stage或commit。改用Python subprocess参数数组逐路径传递，普通hooks保留；不放宽Git检查。

staged diff --check发现本次全新W06 PWF的Python append默认CRLF，未commit；仅新三文件归一LF并明确append newline，旧计划tail和封存输入/审查报告不改，检查不放宽。
