## 2026-10-13 当前接收结果

W08三包离线工程接收完成，RF main/origin b9208a21（精确CI38367459762绿）、Audit main e5189a0及两安装副本6CLI绿。详acceptance-2026-10-13.json及audit/independent-review/final-review.md。A/B/C本卡均完成，整个母目标仍开放。下一步G2准备/DU集成；旧pending为历史。

# Findings

## 2026-10-13 ROOT RF/Audit修复事实

- 两包已进入独立ROOT worktree：`Projects/_harness_worktrees/w08-root/rf|audit`，不改作者或DU工作域。RF main的assurance三文件/output owner WIP保持。
- RF公开create_snapshot/evaluate_snapshot在合成临时registry可直接运行，165/181.5对独立actual160/170的WAPE=0.05；之前工具零误差是自己把forecast当actual，未发现生产引擎同样缺陷。
- RF7关键RED真实失败；工具改用3.10非日历FY控制窗/尾季/derived ancestry与实际adjustment_total/parameter_trace。缺窗/双计由原生拒绝，C05实读独立actual/空SegmentB WAPE null。76集中绿8skip（原工具scalar适配对无相应数值的拒绝/专用路径跳过；全31 native矩阵20PASS11REJECT_OK、0NOT_RUN/ERROR）；三真实CLI，独立scratch恢复、scripts/tests SHA未变。未改scripts/core、不需要同步RF技能。
- Audit项目AGENTS要求独立agent大节点试读；独立审查实证事件ID/角色未配对、当前路径旧报告未诊断、free-text数字位置冒计、NaN与增长读取破限。共享pointer可合法复用，保留声明行并另报唯一位置，不新增权限门。
- Audit13ROOT RED失败中两项是自己测试读UTF8忘编码，修为显式utf8后校验；产品集中修复事件/报告观测、实际numeric定位、预算finite/整数/有界stream与pointer上限。63集中PASS9.07s，真实14CLI链通过并恢复。原40测试仅更新一处过时诊断句子断言为唯一位置实际计数，合法fixture补实际声明stdout文件，不放松数值/来源要求。
- Audit首次C节点工具入口要求cwpe-*目录，旧名字在入口退出未创建scratch；改为自有cwpe-w08-root-final后通过。完整工程测试正在跑；仍待正常commit/并线/安装/发布。

实际交付：RF4d5c9f05（handoffimplementation=PENDING，机器Git为准），Audit实现e9146453/交接96889c6，CWP a6010480（handoff implementation空）。自引用commit字段可由ROOT补实际HEAD，不成为人工签收阻断。

作者主张RF31case/五组CLOSED、71PASS6SKIP+24旧ROOT边界；但C02仅FYE/季度契约而非dated-composition、C05新增bootstrap.evaluate_draft_scope需独立确认不是第二计算/期待从actual造出。Audit50集中/427+122全量与真本地CLI，新增allow-evidence-root属于显式读入范围，不应做身份/许可门。CWP26工具测试、9读/RF读、第二run0POST，但初始INPUTS SHA声明3200与dispatch5088不同，需调查行尾/显式fixture修复/实际输入改动，不凭hash差一刀拒绝，也不静默接受改造证据。

三包原型已核独立code commit；作者工区未提交都是自己的PWF初始准备，保留。尚未ROOT验收或并主线，不能把COMPLETE字段当质量证明。

## CWP ROOT 实际接收检查

最新 ROOT selector 上原26工具单元测试全部通过（0.28s）。正常隔离集成分支接收作者 a6010480；作者树不修改。原样九文档 E2E 启动，记录唯一进程，不能用这一轮证明尚未实施的缓存失效。

查出工具层遗漏：_case_model_posts 根据摘要状态推算每文档 POST，而非读取 loopback 请求 source_id；locator_replay_verified 仅以 locators 非空判断，未消费真实公开 replay receipt；required_span_text/forbidden_summary_text 有固定声明却未使用；RF period_preserved 是 as_of=None 的回显，未验证非空期间；版本/spec 改变后的真实失效未跑；剩余 deadline 强制最少1s会在超限后继续启动命令；报告没有保存其 receipt_ref 指向的原始 receipt。以上是联调工具的观测可靠性问题，不得把它们归为生产权限门禁，也不得据作者 PASS 冒签。ROOT 按一次 RED→集中 GREEN→同公开入口 E2E 补齐，不加逐材料批准或新任务库。

基础主线 W04 已正常 merge c1d6ab92，21个明确验证文件正常记录提交72992376；自动审批先前拒绝的是整目录混入历史untracked，明确逐文件提交已通过。正常 push 的既有最后检查正在运行；本轮0付费调用。

RF只读进一步证实两项覆盖缺口，详rf/scope-review.md：C02实际输入只是年度36/90与年结标签，没有dated-contribution；C05记录入口evaluate_snapshot，实际调用新tool wrapper且把forecast同值当actual生成零误差。复用原生算术不等于原生实际回测，不按五组CLOSED接收。工程测试绿不认证缺失的接口覆盖；下一主线先修真正日期/独立actual的观测与反例，再决定需不需要产品共因修复。作者树和RF主仓WIP保持。

ROOT实际intake复核：三个INITIAL INPUTS.json逐字节均等于初始dispatch，CWP真实5088未变。handoff所写3200是报告字段不同，不代表输入被改；先前怀疑已被实际字节反证，应修准确metadata而不是追加审查许可。三个工区HEAD分别4d5c9f05835c46cc445288f2883c6bf215c39348、96889c6a6d0d85b9c0ff6f54e35c4ea73e648bb6、a60104801be78ec2b1c441ac45afec46508e9439；完整intake包含实际写集，未签收。


## CWP 大节点验收 — 2026-10-12

# W08-CWP-G2-REPLAY ROOT 验收

已接收作者 a6010480，ROOT 修复 a90fada2，正常并入本地主线 be9630817b84fcd92332b532a80a37f4f119af61。
35集中测试通过；9独立RED保留。最终真实离线联调 50.3324 秒通过。
9类文档均真实登记/批次/公开读取，RF 9读成功，8份有证据，IR管理办法正确跳过。
首次8实际POST，同版本复用0；新TXT版本与模型生成参数变化各1次，原版本字节不变。
非空截止日2026-10-12/财年/期间保留，真实公开locator回放，业务原句和claim引用检查。
预存哨兵恢复、测试根恢复absent；70个生产配置/固定RF代码输入SHA和mtime不变。
原始request/receipt/bundle/context/本地模型prompt/draft＋失败过程压缩归档 203690 字节。

本包仅验证合成原件、原生链路、证据绑定和复用。模型语义质量未评估、真实公司未验，0付费。
不会加入每次commit或CI重型门禁。作者pinned-base失败记录保留，不能当作当前HEAD已复现失败。
正常push/精确CI尚待收尾；RF/Audit两包仍待ROOT接收，完整母目标未完成。

可复现入口见 tools/narrative_g2_replay/README.md；参数使用独立测试目录和固定RF快照。
不要重跑本目录一次性prepare/implement/accept脚本，不要改作者INITIAL INPUTS或旧失败报告。



## CWP发布收尾 — 2026-10-12

CWP已验收发布：代码主线/远端d75e9698a3401854dfd4368bbe9b7c40f73c3263，正常push3648PASS197.96秒，精确CI38304041971 success。35工具测试/50.3324秒真实九文档联调，复用0POST，版本/spec各1POST、70输入SHA/mtime不变，预存哨兵及独立测试目录恢复。证据203690字节ZIP，136自有重复文件187288字节已逐字节验证归档后移除。W04原件/legacy/四事实节点和CWP工具工程接收完成；真实供应商摘要、RF/Audit两包、G4/G5真实研究与循环仍待做，完整母目标未完成；本轮0付费。
