# DU-PROFILES 接收修复交接

实现 commit `e033b4bef8a33676e05208843075d4826e1b3525`，branch `codex/du-profiles-fix-20261013`；base `f734ef926de9f64f530bc11f5254dd2f51de2665`。仅独占 profiles 子包与其新增测试，共同入口不变。ROOT确认 additive modifiers；所有必须的 DU/1 字段及 vocab 不改。

修复共同根因：组合 role 时完整保留 CN/HK/SEC aliases，规范化稳定去重、后续更具体块显式覆盖 priority；封面/跨跨度 heading/普通正文各有机会，字符预算公平分配，字符前缀保留截短标记，防止长 prose 被截成伪标题。固定默认 200单元/64,000字符/16children 不增。

S-1/F-1 使用现有 prospectus 策略而不猜 IPO；8-K/6-K 保留 SEC 容器。外层打印表单优先于附带表单，附件季度措辞不能抹掉 current-report 元信息。同源 Exhibit 范围包含实际 heading+正文，必须全部在本次探测内且未截短/缺页。外链、reference、单空标记不宣称已读。摘要 extent 与修订 revision 单独透传，未披露 revision 为 unknown，不把正文 Summary 或引用别的修订稿改成全文属性。

验证：首次 RED 18FAIL/2PASS，修复边界 RED 9FAIL/21PASS；最终 **180PASS=150旧+30新，0FAIL/0SKIP，1.972s**，旧断言改动0。ruff PASS、mypy9文件 PASS，正常提交 hooks全部通过。真实策略探针输出 S-1/F-1→prospectus；8-K/6-K→SEC容器 + Exhibit u3–u6 results_release。701单元前300heading压力，12探测包含 h0、4个普通body及tail，106字符，诚实 probe_limited。

复跑：`python -m pytest tests/unit/document_understanding_profiles -q`；`python -m ruff check src/company_wiki/document_understanding/profiles tests/unit/document_understanding_profiles/test_reception_root_causes.py`；`python -m mypy src/company_wiki/document_understanding/profiles`。仅 A/B/C 集中节点。

本包 0模型/0下载/0费用/0原件写/0生产配置写/0新依赖；证据提交前约69KB，输入纯内存不改，冗余过程XML已删。原150包含已有真实形态短片段回归；30新例为明确synthetic，未证明真实全文语义/供应商效果。ROOT仍要检验 aliases/child/modifiers 在共享选择、摘要与缓存中实际生效。旧 QA child marker 路由未扩展，由结构与 ROOT closure 配合。DU2三包和旧作者树均未改。

请 ROOT 接收本实现与 receipt commit，集中跨层验收后并主线；本worker未并/推主线、未安装技能。
