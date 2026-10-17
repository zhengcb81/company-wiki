# 共享阅读生产接线与正式摘要恢复 — ROOT 实施卡

状态：IN_PROGRESS；起点 master 34a7dd71；承接母 PWF，2026-10-17。

## 当前根因与目标

DU9 POLICY/PLANNER 与 DU10 回归基准已接收；实际 PDF 0.9 仍由旧关键词双 OR 决定昂贵页面，source 1M 与后置 2M 工作账户分离，空选择可能重新 full-scan。组件通过不能代替生产接线。必须把唯一策略、真实 source 材料、请求与实际覆盖接到同一正式 worker，再做实际配置 LLM/缓存恢复。

原件/生产配置保持，Dayu/IQS不改，不创建新任务库/许可文件/签收链。仅 A/B/C 大节点测试与独立质量审查。费用沿既有20USD/2M token母账，unknown历史不归零；模型/endpoint/输出设置按当前配置，不擅自修改。

## 所有权与接口

- ROOT：source_catalog 的 PDF parser/collector 与新增窄 source 执行器；automation 的原 select/bound selector、dependency inventory、必要共享工作预算基础实现；相关专属测试、真实 E2E 与母 PWF。
- 内部实现 agent：strategy_binding 原 owner 的公开 SectionPolicyMatcher、geometry_intent/reading.py、tests/unit/du11_reading_plan。复用原 router/profile/compiler/planner，不能另起业务正则/章节策略。其文件 ROOT 不同时编辑，完成后由不同 agent 独立复审。
- 用户外包 DU11：仅 RF 引文闭合与 FF 本地电话会复用，分别独立新工区，完全不写 CWP 生产目录；施工卡和精确白名单另列总表。未派发不声称正在施工。

`PdfReadingContext(title, declared_kind, language)` 是纯不可变 caller 元数据；实际源前两页用当前 source emitter 产生 canonical probe units，随后同单位复用，不生成第二全文/第二TextPage。`prepare_geometry_reading` 产出已解析profile、compiled policy、真实native窗口、原PLANNER计划、诊断和request digest。导航是资源计划依据，不是body证据；没有真实probes保持generic。

source执行器用同一DICT中的实际行列/对齐验证候选，再由原PLANNER准入，统一决定finder/fine。纯金额列、目录词和空/扫描页不能仅凭词汇触发表查找；财务章节内真实经营表仍可请求，最终经营资格继续归原qualify_table。不抬64页、1M source几何或15秒限额。共享WorkBudget作为调用内账户，子阶段本地上限是父账户的收紧视图，不复制余额、不重置。source和后置正式selector共用2M总工作账户，所有实际收费在执行前。

## A — 行为契约与RED

1. 原 matcher 与新公开服务 full path/Part/Item/冲突等价；native父business不能覆盖显式risk子章。真实无units不靠标题认证profile。
2. 80页默认 synthetic PDF：前部目录/会计，后部经营与项目；真实native目录，默认table_pages=None，finder必须到后部且非全扫；原canonical文本/ID/次序不变。0work/0page/0fine/空页诚实，不触发第二parse。
3. production handler 0.9 一次parse；真实相同WorkBudget从source到selector；旧版本显式历史回放保持原语义。自定义parser/selector不通过签名探测或异常重试强传新参数。
4. source planner/实际coverage因果身份在原dependency inventory，真正采纳策略改变应失效，无关策略不误失效。

## B — 集中实现与实源默认回放

1. 共享 matcher/profile/native窗口→原POLICY+PLANNER，source单parser接不可变context；first2 probe/source units复用；最多2个native页，所有页面原DICT一次，选择页才WORDS/finder。
2. 真实金禾/名创默认解析，记录实际finder/WORDS/TextPage、运行时间、深页223/224与经营表/客户销量覆盖、限额与未执行理由；禁止测试传显式目标页冒充默认。另选无outline来源，局限写partial/needs_source，不能伪造完整。
3. 共享预算贯穿collector、projection、plan及理解/选择；局部上限继续收紧，耗尽前停止昂贵工作。旧0.8回放和显式/full/empty调用兼容集中验证。
4. 0.9空选择不隐式重新全篇扫描；保留真实partial缺口。request与actual coverage分开进入原因果库存/缓存，不以有plan宣称capture完成。

## C — 正式摘要、恢复与发布

1. worker→select→configured model→verify→publish→公共read；真实精选业务片段原语言摘要，不复制全文、不翻译。MiMo/DeepSeek/MiniMax按当前配置分配，费用从已有母账继续，先工程闭环再花模型预算。
2. 同run恢复、跨run复用与激活前中断恢复：额外模型POST=0、费用/token不重置，原文变更或采用策略变更不能误复用。只能复用已有有效正式产物，不能把stale版本当本次绿。
3. 新盲样本与DU10已看过回归集区分，独立实读审查事实/对象/期间/角色/单位及遗漏；发现共因先行为RED再修，不把数字出现过视为语义证明。
4. 测试使用独立根，起点清单/sentinel与原件/config SHA前后核对；结束恢复测试目录，只保留精简收据，无源全文副本。平台拒绝清理如实列路径/体积，不换通道绕过。
5. 集中测试/独立复审后正常commit/push，核精确CI，更新母task_plan/findings/progress与本卡。必要安装定点同步，不整套覆盖用户目录。

## Next Step

先保存 A 的 source/parser/预算 RED；同时内部纯matcher/native计划实现，外部DU11两卡定界并发布给用户。B/C在实际调用链通过前保持OPEN。
