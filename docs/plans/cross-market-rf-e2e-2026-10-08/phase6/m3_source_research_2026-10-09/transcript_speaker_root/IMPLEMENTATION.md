# 电话会发言与QA归属共因施工（M3真实RED后的新节点）

## 实证与范围

RED-real-speaker-attribution.json由同一273436B官方原件、public transcript extract/verify/parse真实复现：515units/5QA组；六个首发言“姓名, 机构:”被挂在OPERATOR而非analyst。actor无机构的后续致谢能识别，却每次启动新QA组。原件SHA/旧0.2解析/失败摘要与全部费用不覆盖。MAIN原先只依据base regex提出假设，随后也检查natural speaker_fields，没有affiliation fallback，并实际公共解析证实；证据在本节点，不靠关键词或只数selected来定案。

## 隔离写集和发布顺序

1. 复用已附加、已交付W12且clean的fresh-capture工作树，保留原branch，从当前master新建codex/m3-transcript-role-20261009；只写transcript_layout.py、narrative_evidence.py、一个现有short官方layout合同测试及新增最小角色/QA合同测试。主线CWP、三executor scope/runtime在封存前不切换，当前真实RED/来源声明独立保留。
2. TDD先RED：6位不同虚构人物的comma-affiliation首轮→正确analyst；management prepared/QA名字大小写变化仍同角色；同analyst closing/followup不另开QA，下一analyst另组；literal Revenue/Financial Results/Contact/nav/空heading不变成speaker；未识别内容保留unknown；source sentence/line/char定位仍可回放。新测试用标准小HTML/TXT而非微软人名/产品特判，真实原件只引用、零供应商调用。
3. 解析新版本0.3.0和独立natural_affiliation布局：0.1.0/0.1.1 legacy与0.2.0 natural逻辑冻结，明确版本分派；新版参数不能偷偷改变旧span语义。新版name/affiliation用有界通用grammar和现有valid_speaker规则；不要加issuer或银行名称allowlist。casefold仅用于本次发言者归属，source显示姓名与raw text原样。
4. 新版QA只在新问题发言者切换时新建parent组；同发言者实际追问/致谢与其回答保持同parent，已有first/second子问题语义保持。旧版每turn计组逻辑不动。未明确问题是否有回答的语义不自动补答或造支持，qa归属不等于summary命题成立。
5. 默认parser_component/generation pin用0.3.0；旧0.2及legacy replay仍按记录版本回放，老cache不可冒充新版，默认PDF/filing parser不受影响。先新RED转GREEN，再既有短layout/叙述选择/replay/generation责任集合一次集中验收，不增加新每日/commit全流程测试。
6. 主节点实际同一微软原件公共extract→0.3 parse→选择→每QA+answers/限制抽查与全部选中locator replay，保留0.2复跑五组/旧同SHA产物对照；新未见合成布局、旧JSON/TXT/HTML版本控制都验证。对齐source actor原始6问，不把gratitude算问题、不把selector全候选覆盖宣称全文覆盖。
7. 独立复审工程写集与实际proof后正常commit/push/精确CI，再一次协调运行时版本交接。只有配置/摘要共因也处理后，才能收费重跑对应失败calls；无免费模型/对重复下载/新预算假设。
8. 四路M3研究检查保持独立，工程发布不核销原/新finding。问题和风险检查点最终在audit技能中通用升级，不重复CWP/RF/FF身份验证，不增加小节点人工review。

## 验收标准

六个原始首问正确actor/role，问和其management回答同QA parent；当前所有selected原文可回放，实际原件不变、没有公司特殊规则；0.2与legacy解析/单位SHA稳定，新version输出pin确不同；positive与negative责任controls全绿，真实旧失败保留。仅工程接受，不预宣称分析师模型质量或新三家泛化已完成。

## 19:50 UTC隔离实现及真实对照

新增通用13cases先10FAIL/3PASS，再连同旧layout/选择/TXT与JSON原文/架构共90PASS/2.22秒，原RED与源码修改前0.2fingerprint保留。正常ruff选定四文件通过。新版真实微软原件公共parse/select/全部selected replay1.393秒、515units，原6首问actor/role准确且致谢不增parent；0.2原件仍5parent/41selected/2parent，0.3为6parent/50selected/4parent，50/50回放通过。新版归属修好不等于全部6组已被选择，尚缺两组的价值/选择判定，后续review/expert单列，不伪造“全文QA覆盖”。

新增短13cases纳入既有tools/pre_push_gate.py共享CI/push FAST_CONTRACT_CASES（现有10case official layout旁），不加commit runtime或新CI job；责任写集为2 runtime、2 contract测试、1既有共享快测入口。源码当前只在codex/m3-transcript-role-20261009隔离工作树，尚未merge/push/主运行时安装；三executor冻结执行不被暗改。

共享快测入口/commit静态政策/TEMP恢复连同新增13cases实际58PASS/1.71秒，owned TEMP已恢复（GREEN-shared-gate.json）。隔离支线正常commit8c154b1170bc5121f1ba602edf4c52ef5074cfb5，25.213秒；ruff/mypy/host guard全绿，未绕过钩子。此时尚未推送或合主线，独立审查及实际发布仍待。

后续正常push首轮2491PASS/1FAIL/148.49秒，阻上传：既有native format集成测试仍写死default0.2，与明确新版0.3合同不符。只更新该默认身份断言，原byte binding/角色/完整回放/变更SHA拒绝全部保留，旧版本责任仍固定；native+兼容+角色35PASS/1.44秒，owned TEMP恢复。责任写集增加一个既有unit测试为共6文件，正常commit3f3f55c1c3ebfae55279a963eefadfdf13ec8c0f，第二push2492PASS/136.71秒并成功推隔离支线，首轮log不覆盖。不绕hooks、不提前安装；US-storage在M3同一大节点独立复审，主线研究不因这次工程push自动通过。
