# Findings

真实生产接线与合成夹具的差异必须显式验证：旧PDF parser输出没有mime，合成source_case却填了mime；新native sourceflow最初未在真实PDF激活。其次DocumentStructure.coverage_complete合并了全局细表缺页，不能作为所有已观察正文pair的开关。pair未读/opaque或coarse不完整应把该已知pending依赖defer；其它页细表不足不影响可证明pair，不把不完整半句放回默认singleton。当前真实p17断句/指代仍存在，说明物理检查与语义/指代readiness须同源owner衔接；模仿synthetic通路或看gold命中并不充分。

缓存原来只hash source adapter，未hash实际共享operating_states/归一化/兼容grammar；代码移动后import方偶然改变会掩盖此漏口。Inventory1.8绑定5个实际owner真字节，匹配层不依赖人工记得bump常量。新English subject判断也必须在首个finite边界停，遍历所有后续predicate反复扫描前缀会以线性预扣执行N²，已用实际扫描字符计数先RED再修。

FF原查库合格不等于当前reader metadata合格：最终发布日期future/invalid/None必须覆盖旧资格；当前canonical代码格式只由CWP投影，FF不得另抄lstrip0。reader CLI原open/describe两个观察又有可避免的重复；统一现open_described_version，not-applicable None与未观察sentinel分开，维持原指纹兼容，不增加许可门。

Final preallocation evidence: source candidates originally spent193 of300 then still iterated32 heading IDs before the prose reservation rejected; native continuity atparent0 copied32heads/64body IDs before charging. Length-based reservations before ID visitation remove both loopholes; source headings are now constructed only after prose succeeds and their own reservation succeeds. Nine metadata controls and prior730 related cases all pass739/50.52s. Recursive immutable-IR snapshot checks every dataclass field and mapping value without requiring pickle or altering production IR.

读取现有20源码接口调查后明确：SourceOperatingSession groups/citation_views可以复用；native_range禁止跨页；context name_classes并不代表实际产品指代已解决。4个关键陷阱：analysis owner重叠、target/context refs误映、TOC混入家具、跨页block号码重启与必要context5blocks超过现4。详细约束与真实定位见task_plan引用，不复制原PDF。

Current same-page finish correctly does not assert cross-page continuity, but source owner independently admits page fragments. Therefore a source-level atomic dependency is needed before selection; late summary rewording or a changed max_claims cannot fix a half-sentence selected under a one-span budget. Source block IDs reset on each page: the new cross-page envelope must use tuple identities. Current global WorkBudget must also include new continuity observations; keep local geometric ceiling as a nested ceiling, never a second free allowance.

Measured quadratic source context: a background package withNmembers called context() for each body, rebuilding set(owner.members) each time. 16members288visits,32members1088visits. Source-specific nouns/models cannot fix this; precompute external-context dependencies once per owner and combined exclusions once per source, while actual membership/fan-out/sort costs consume the existing account. StageB initial implementation is isolated pending broader integration/independent final review, not called production-ready.
