# 代码质量共因整改细则 — 原工程已发布，真实C继续

入口：[原始审查](README.md) → [逐项核对](implementation-results/checklist-verification-20261102/checklist.md) → 主计划`../../task_plan.md`。原14项工程13项完成、Q11按边界保留；R7及本次新增漏项的当前独审/发布/CI见主CURRENT_STATUS。下方A/B/C保留原实施要求，不是要求重新施工。真实C未完成。

早期候选63F、隔离/revert与之后重施的失败历史均保留在有日期的原报告；它们不再表示当前master暂停或仍待早期候选并线。

## 原则和接口责任

1. CWP 保存来源事实与质量，不保存买方结论；StockWiki/RF 各自负责研究和预测。
2. 上层只拿 SourceRef、版本化 export、已验证源字节/locators。physical roots、SQL、CAS 位置和 parser 生命周期归存储 owner。
3. reading owner 组合原文材料、依赖和算法 recipe；DU/profile 提供纯布局/策略能力；automation 只编排和记账，不反向成为阅读算法类型库。
4. 所有变更先用去公司化正反例表达行为；保留历史版本回放。禁止新增企业/证券代码/页码判定、扩大额度换过、全仓 hash 让任意修改都付费重跑。
5. 不增加人工签收或逐小节点审查。以下 A/B/C 是集中工程节点，普通修改只跑受影响快速用例。

## A — 先修阅读泛化和结果身份（Q01/Q02/Q12，与 R4 来源修复合并）

- RED：冻结“未知对象＋普通陈述动词”“时态/同义词替换”“中文无兜底词”的跨行业原文保留例；同时包含问题句、目录、泛化模板、纯会计口径、缺主体/跨主体上下文的反例。记录原文/locator 和 admission reason，不要求系统凭空识别事实类型。
- 修改 `narrative_source_passage`/prepared assessment 的可读资格职责；event/measurement/issuer proof 继续在各 owner 判定。旧 R4 p12、承诺串组和新陌生业务反例在同一源层收束，不为每家公司建词库。
- 将 `_candidates/_prose_reading_packages` 按已准备材料、依赖闭合、准入和预算投影分为纯阶段，入口和旧 selector replay 保持。不得再多次扫描同一 source 或复制 context 判定。
- reading 组合 owner 声明实际 carrier 所用组件 recipe，generic decision inventory 只消费声明。依赖改变需失效，未参与的格式/测试/不适用 profile 改动不能失效；源码和策略版本仍需绑定，不接受人工“记得升版本”作为唯一机制。
- 最小集成：antecedent/parent-composition/signals/strategy 改动分别使适用 recipe 变化；不适用组件无变化。构造旧/新产物，证明真实 cache 比较拒绝受影响旧决策，等价缓存仍复用。用合成 fixture 先做，不调用付费模型。
- A 集中独审：核 source-unit 归属/未知事实不升级、无企业特判、实际 cache 入口和历史兼容。不因模拟指纹反例通过就宣称真实缓存已验证。

## B — 存储、调度和旧入口统一 owner（Q03–Q11/Q13/Q14）

### 查询与预算

- Q03：候选 owner 提供可索引的身份/期间超集，纳入权威纠错、别名和冲突候选；reader 保留最终语义判定。不能简单按 display_name 筛掉冲突，也不能直接删 20k 上限变成无界扫描。
- tmp DB 参数化：19,999/20,000/20,001 无关同类来源、相关项在前/后、正好 EOF、未知日期、身份冲突和纠错。用查询/投影次数计数验证复杂度，不靠易抖动的毫秒门槛。
- Q04：CAS/登记提交返回实际新增/复用 bytes，AUTO 原 run 账记录增量；共享全局容量采样独立且低频。预算预留、unknown usage、原有数据库/lease/outbox继续复用。
- 两写者隔离测试：B 的合法写入不能算成 A 的新增空间；A 自己超限仍停止。恢复中已记账对象不重算、未知费用不退，空闲等待目录遍历次数有界。

### 生命周期与 I/O

- Q05/Q07：legacy prune 与确需保留的复制/清理都由来源 owner 选择生命周期/引用范围。废弃 CLI 直接移除或轻量说明退役，不补环境许可。普通写函数/复制调用不能继续依赖字符串 grep 假装冻结。
- tmp DB 检查 current/unknown parser 与活引用不被 legacy prune 删除，明确 retired 版本定点清理可重复零变化；保持原件/source facts 不变。不能把用户授权任意清中间件解释成删除仍在用的对象无需范围合同。
- Q06：现有 CAS 对象校验共享有界读取 helper；小输入+大损坏对象、FileExistsError 并发分支、重复零写/不覆盖损坏对象均测。采用小 limit 和伪 stream，勿造 GB 文件演练。
- Q09：StockWiki 在自己的 transport 内流式计数 stdout/stderr 并终止/回收超量进程树；不 import CWP 私有 helper。两个小持续输出子进程验证超过限额即时停、无孤儿和成功 receipt；保留 hash/wire 反控。

### 合同、兼容与诊断

- Q10：纯 source identity/verified bytes 值和 Protocol 移到无 runtime 依赖的 contract；canonical writer 从登记 owner 直接取得返回身份，export 不强制具体 reader。至少一个替身 backend + root relocation + corrupt bytes 正反例。
- Q11：先封装可信同进程读结果，再测同次 SHA 次数，才合并重复 hash；不要删除跨进程接收校验、跨时间重开和复制提交后的独立校验。收益小可后置，不阻挡 A/C。
- Q13：区分 invalid_request / unavailable，坏参数不被当环境恢复问题；错误仍无源 bytes，诊断不泄露本机路径/凭证。
- Q14：将旧 rollout 解码/回放放到明确 compat 边界；普通扫描预览不要求伪两轮计数。保留 dry-run 零写、事务/CAS并发控制和必要历史读取；去掉当前 UI/CLI 对 epoch/cohort/reviewer 的日常依赖。未完成迁移前不能直接丢历史 assertion。
- Q08：复用已有 AST 层测试扩展到实际公开边界，覆盖相对/qualified/alias/包初始化/常量动态 import；不扫描关键字判罪。两个 CLI 负例、文档/注释/配置别名正例。移除未使用恒真 helper和过时重复合同；轻量测试入现有 unit，不把全部历史 gate/E2E 加回 commit。
- B 集中独审：检验责任唯一性、真正读取时限额、坏数据负例与旧入口关闭；根据修改域跑有界集成，不做超时整仓轮回。

## C — 接回原主线真实验收与交付

- 复用原隔离环境和合格原件，冻结不同市场/文种/新行业检查点。只选受本次变化影响的真实例；年报/半年报/IR/电话会/招股资料原有责任不缩减为几句合成数据。
- 原文→可读材料→来源摘要→同 run/跨 run 恢复→RF 实际采用：逐级检查必要业务单位、主体/时间限定、表格上下文、旧结果正确失效。unchanged cache 应零追加模型调用；真需要新摘要才按配置预算发起，不改封存 R4。
- 与 R4 的六 issue、ghost-formula/期间补集/经济范围检查合并一次大节点独审；来源召回通过不等于买方预测可靠，外部能力/未知日期保留真实限制。
- 每批完成正常提交/推送、必要定点安装、更新当前主 PWF；不让纯 P3 清理或无经济影响的旧描述问题阻断已具备条件的复验。
- 测试目录前后清单与原件 SHA 一致；只删本次测试新增，保留已有原件/失败证据和 unknown 账。禁止完整恢复备份演练、不新发外包卡。

## 当前验收与后续状态

逐项表覆盖原41正式项和后续补漏，每项都有源码、测试、独审及发布边界。已取消的任意表示许可不能恢复；真正源字节/身份/期间/as-of、引用/数值与实际资源保护按owner保留。StockWiki原Q09与本次wire补修仅签本地主线，未配置remote。

当前下一步：按T4-source-note-parent-plan.md冻结去公司化父链正反例并在来源树owner根修，再单H1原90s/16M/112复验；随后新版真实摘要、paid中断/同跨run零重复与同artifact实际RF采用。 R4六共因、ghost/period/经济范围、固定公司与泛化责任保持。两个可选非阻断优化单列未做，不用“全完成”吞掉，也不拖住主线。
