# W20-RF-ADOPTION 第二轮 ROOT 独立复验（2026-10-29）

**结论：CHANGES_REQUESTED，剩余两项同根因遗漏，暂不并线。** 原三项已明显改进：原“异源借哈希”和fake source_id反例均已拒绝为unverifiable；同span跨2026/2027真实路径现在完整聚合；小gzip炸弹按resource_limit拒绝。独立重跑交付短包 **37 passed / 10.95秒**。不能因此跳过下面实际复现的新反例。

受测源码 `e4657377`（返工链含`a1edda18`），实际交接HEAD `b2979af6`。四份最终源码/测试SHA与最新交接一致，详见JSON。旧R1报告保留，不改写作者旧独审或37绿测。

## RF-R2-01 · P1 · 同份原件的不同片段仍能串用

位置：`tools/narrative_adoption_audit/audit.py` 的 `_evaluate_dependency` claim edges。返工已校验来源、父hash、claim target与formula，但 **claim_material仍只比整份原件hash**；最终claim的locator/excerpt/excerpt_sha256没有与实际transported span对齐。

这次反例不是伪造任意ID：同一份经真实wire校验的合成资料，由真实`consume_narrative_input`各跑一次。A选CEO回答“added two overseas lines”，B选表格行“Overseas | 1,240”（显式合法group/view0），两次使用相同本地claim_id/parameter_id及公式。把 **A真实forecast + B真实receipt** 交工具，它把表格span判 **used**，没有材料或run错误；但A的实际claim locator/excerpt指向CEO回答。原件hash、来源ID与公式相同不能证明该段被最终claim采用。

**为什么这不是合法补充证据：** 这里使用的是现有 `source_narrative_context.py` 的具体消费合同：`_claim`第70–80行将所选span的raw_text原样写为excerpt、计算excerpt_sha，并以第62–63行选择legacy locator或projected source_locator；第133–145行要求新claim_id唯一，已有claim_id会拒绝，不提供“给旧claim追加另一段”的语义。receipt第150–153行记录的正是这次新claim的所选span。两次合法run的同名claim是不同材料记录，不能仅凭display ID和整份capture相同互换。实际已声明冲突：A claim locator=`loc:v1/paragraph:3/chars:91-154`，B receipt locator=`loc:v1/table:1/row:2/chars:219-235`；A excerpt SHA=`fb18d51e652d0fe77c430bf832861226cb246dfcd50b7b86fa8abaab503e49b5`，B真实生成claim excerpt SHA=`72f2498e8150bfc40b0b0d05ffd6afc584615d5fb949db659f1987f2ce05aa29`。本发现仅要求校验这个**已有明确生成合同的材料绑定**，不要求所有研究quote与support逐字相等，不禁止同参数多证据，也不把缺字段变成新必须hash。若未来另一合同明确允许多证据，应按那个合同报告可观测绑定，而非套用此单claim生成规则。

返工：在既有共同链解析owner核对已知的claim→span材料边。沿原consume合同：legacy比较span locator/raw_text与claim locator/excerpt及其hash；/3比较实际父与structured source_locator及raw_text。缺失可选字段仍按现有宽松unknown处理，**不增加人工许可或身份门禁**；明确矛盾必须unverifiable。新增同capture不同span的两次真实consume→forecast错配测试，保留合法旧路径和/3多父正例。

完整可直接运行复现：`rf-evidence/material_probe.py`；实测输出：`material-probe-results.json`。初次探针遗漏显式view被真实adapter正确拒绝为ambiguous，之后改为明确group/view0；这是探针配置错误，未作产品问题。

## RF-R2-02 · P2 · 有效gzip头＋坏DEFLATE仍跳出命名错误处理

位置：`tools/narrative_adoption_audit/cli.py` 的 `_gunzip_bounded` except。流式上限已正确工作，但只捕获EOFError/BadGzipFile/OSError；`zlib.error`不属于这些类型。

真实CLI子进程读19字节 `1f8b0800000000000003070000000000000000`，结果 **exit1 + zlib.error traceback**，而不是约定exit2 / input_decompress_failed。没有半份输出，是错误分类/CLI恢复可靠性的遗漏。

返工：把解压库自身zlib.error归一到现有input_decompress_failed，不笼统吞所有异常、不抬额度。增加该小坏流的真实CLI测试，与正常恰好limit、超limit、截断案例一起短测。复现和完整stderr见`rf-evidence/additional_probe.py`与其results。

## /3多父与宽松兼容实测

ROOT另用真实validated projected_context（实际父在parent refs[1]）→真实consume→真实forecast复验：正常used；缺receipt hash仍used并记录hash_missing_unknown；提供错误refs[0] hash则unverifiable。这条新增修复方向正确，不应回退为固定首父或要求新增许可。原多路径探针也核实两年cited_by都在且只有一个span item。

## 范围、清理及后续

本次只用小合成wire与真实本地CLI/validator/forecast，0付费/网络/下载，不是公司实际RF采用验收。作者工区未改，测试资料全部位于ROOT自有`.planning/w20-reception-r2-20261029/rf`。pytest临时树在核实绝对边界/无symlink后清理，compact脚本/结果/JUnit/清理收据在本报告旁。主线循环保持暂停。

请原harness只修上述剩余共同根因，补有意义RED、修复、跑相关短包并由真正独立agent复审后重交新源码commit/SHA。无需反复全量、提高额度或新增小节点审查。合并建议及命令实测见`rf-review.json`。
