# Phase 2 初始事实

ROOT真实六文档回放80s：FAIL_CRITICAL_RECALL；六legacy hashes、cap、whole group、raw SHA、omitted partition均通过。绑定事实只有supplier lead time通过；LPCVD专属三百、钨系列整体验证/重复量产、PRISMO PD5四腔/6&8英寸/验证通过重复订单均失败。工程365绿只保证覆盖到的行为，不能证明实际召回。

报告保留所有omitted budget_diagnostics和完整selectedgroups；actual score/reasons只在focus_decisions中，未保存全候选budget_items或全组score。因而不能声称已获得所有候选的完整排序轨迹；可精确查明聚合category占用和固定落选组真实评分，必要时ROOT下一次回放只加metadata捕获，不重新解析原件作设计。

首次只读打印遇到控制台GBK编码错误并输出截断，改为UTF8与小聚合，原报告未改。

确定的rank因果：_over_share是offer_key首位；product取4+5=9后已大于share7，未满share的泛化其它category即使低score也必在其前。三绑定组成本3/5/3均小于cap且完整candidate=true，没有原件丢失或group_exceeds_limit；这里不是需要抬cap或特殊packing补丁，而是质量顺序被配额遮蔽。Phase1保护句不同是保守正确：薄膜300整体与LPCVD专属三百不可混同，两个薄膜段也没有证明完整逻辑相等。

ROOT明确要求：重要risk/量化行业变化与已实现产品同质量带保持软公平；计划/实现在商业完整组内沿用stage_assertions proofs而非只信reason标签。类别与评分仍归source-owner，预算只消费其metadata/signature，不从payload或文件重做分类。

首次集中375=357PASS/18FAIL。新10个质量带反例均通过，ruff/mypy通过。17个旧novelty测试的“WEAK”实际上写了已实现设备交付，质量带正确识别为0并优先于计划/未知阶段2，造成原隔离softdup断言被另一个真实事实抢位；已明确提交ROOT确认夹具语义修正，不偷偷改断言。另1个旧named-only公平测试失败属产品分类问题：我误把只有名称上下文置band2而industry泛化背景为3。仅named context不证明业务动作，应同泛化band3，已回归；其包含实际stage proof时仍可由同一个proof逻辑进入0。原集中FAIL保留。

ROOT确认夹具修正：原WEAK设计角色是用于隔离softdup的泛化背景，但“已经交付”实为已实现进展；改其正文/注释为无stage证明的技术背景。仅改2处夹具文字，数字/主体/阶段/截断保护的所有选择断言不变。新增实际低score真实进展优先于高score计划的4正控原样保留。该修正与产品name-only分类修复分别有记录；真实六原件固定检查、legacy full hashes、96/160cap均不改。

第二次集中375=374PASS/1FAIL，数字/单位/主体/阶段等17个原断言均绿；剩下旧格式重复用例也复用已改为泛化的WEAK，因此band0真事实与band2泛化比较违反同质量softdup设计。该用例保持{1,3}重复降级断言，但单独采用有客户验证/重复订单证明的低score新医疗事实，恢复同带0比较；不调整产品排序或真实原件检查。18FAIL、此1FAIL两次集中证据均保留，已向ROOT报告。

最终集中attempt3：375PASS/1既有asyncio_mode配置警告，pytest13.57s（驱动14.156s）；ruff/type均exit0。测试为原330+Phase1新增35+Phase2新增10。独立短tmp恢复，产品测试期间SHA不变，22其他原WIP与HEAD保持，原Phase1 manifest的15份留证均保持。新freeze只属于phase2七产品；旧b17freeze与18FAIL/1FAIL记录未覆盖。冻结后辅助只读source片段打印的定位字符串不匹配，打印退出1，但冻结、SHA检查和375集中执行早已成功，未再执行测试或改产品。
