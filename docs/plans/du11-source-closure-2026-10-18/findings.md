## 当前两卡接收与发布结果（2026-10-18；优先于历史）

RF/FF两张DU11卡功能工程已接收、全部交付提交进入各自主线。CWP producer先发布0ccdc689（6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success）；RF runtime f8002f5f（18独立行为接收、416PASS＋36子测、CI39092538354 success、6源码定点安装）；FF最终e8740748（873PASS7SKIP78subtests91.13s、精确CI39095654355 success、6物理源码依赖序原子安装，双根imports/help通过）。RF唯一兼容版本表两阶段正常更新：e7364639的wiki pin/CI39094965965 success，再9669c4d7收敛filing=e874、wiki=0cc、revenue=f800，最终416PASS＋36子测73.74s、远端一致，精确CI39095818018已completed/success，三仓本次发布CI全部绿。

正常FF发布共3次尝试=2RED+1GREEN：先修异构schema类型丢失及既有mypy hook漏掉transitive scripts依赖，再修旧“未知日期”夹具缺provider导致测试错位。保留原完整拒绝/0下载/日期资格断言，不删测试/提高阈值/跳hook。JSON stdout的GBK/UTF8根因和集中CI表漏DU11纯回归也已修并独审；最终类型delta独立公共mypy＋10有限控制通过。详细收据见review/du11-reception-closeout.md以及各publication报告。

未动生产原件/gold/配置/密钥/Dayu/IQS或作者树，没有新收费模型调用。RF旧3个assurance WIP保留，stage1曾观察weekly_manifest自然变化，不归因/不恢复旧值；stage2前后相同。一个RF外层审查Temp仍NOT_CLEAN，历史PermissionError后平台拒删，保留且不换通道重试；内部端到端原样恢复。未知发布日期的/3投影仍如实source_availability_unknown，不伪造日期或另加许可。

整体PWF仍OPEN：t32最新真实诊断不再selected；t34仍缺有界先行词。下一实现按review/antecedent-source-interface-final.md，在现source/operating唯一owner、同parent16M及8units/4原block/2048chars封闭依赖，再做正式三供应商摘要、收费/activation恢复、同跨run缓存及真实FF/RF消费C，之后holdout与RF循环。不要把工程/金标命中当内容C通过，不重做已接受DU11或新增小节点签收。

# Findings

发布前实际检查又封闭三类共因，而不是给失败加豁免：FF CLI的JSON输出曾按Windows宿主GBK编码、消费者按UTF-8解码，改唯一输出owner为ASCII JSON后中文/emoji路径语义不变，原错误退出保留；集中CI表35→38补已有DU11纯回归，未加入重型真实端到端。新qualifications schema值全为class-info但异构dict丢失静态类型，补准确类型注解，公共mypy通过。旧pre-commit只看2个直接入口，现同一既有hook覆盖scripts运行依赖，命令仍仅检查原2公共入口（4.018s），不增加全仓mypy或新门。

完整FF回归还发现一个旧fixture同时省略provider与日期，使原“未知发布日期不重复下载”测试先撞上“显式fmp不可冒认未知provider”。只补当前reader manifest.provider=fmp/published_date=None，保留原0provider调用/SourceRef/asof=False全部断言；该例及现unknown-provider拒绝反控2PASS0.24s，生产校验不放宽。正常push历史的type RED、fixture RED均保留；最终873PASS7SKIP78subtests91.13s后才真正推送e8740748。按已发布producer pin先行、consumer后发，RF兼容版本表是唯一CI依赖owner，安装技能不另造compatibility副本。

受审4个生产文件与母主线逐字节一致。2个新文本测试在Git checkout转CRLF、归一化LF及Git blob相同；最初误要求六文件物理字节全等的诊断断言已记录为检测假设错误，不重写测试/原件迁就。真实母仓完整6801及精确CI已验证其实际checkout，不对原件或来源SHA采用行尾归一化。

实际parser的ordinal是source全局顺序，paragraph_index是页内定位；跨页把两者都要求+1会错误否定真实连续页。更深一层，parser顺序可先观察下一页底部普通counter再观察顶部正文；不能把这个未证实家具当正向proof，也不能让它提前释放上一页pending半句。现保留有界pending依赖，实际顶部前缀未证明则两原span诚实defer；独立新issuer仍独立放行，不以整页黑名单解决。实际旧t32已不再selected，产品t34仍需独立先行词owner。

全量本地push测试集合增大且两阶段独立后，串行unit600s仍可能在96%超时。完整unit采用已声明xdist两个进程、按文件调度，不删测试或放大deadline；成功/断言失败/skip与真正worker进程均有反控。真实timeout实验表明subprocess返回会等待execnet既有约15s关停，返回时两worker/SQLite/自有Temp已回收。因此不凭猜测另造process-tree管理，也不宣称总墙钟严格600。真实全量运行是下一次正常push门，不用微型fixture替代。

真实生产接线与合成夹具的差异必须显式验证：旧PDF parser输出没有mime，合成source_case却填了mime；新native sourceflow最初未在真实PDF激活。其次DocumentStructure.coverage_complete合并了全局细表缺页，不能作为所有已观察正文pair的开关。pair未读/opaque或coarse不完整应把该已知pending依赖defer；其它页细表不足不影响可证明pair，不把不完整半句放回默认singleton。当前真实p17断句/指代仍存在，说明物理检查与语义/指代readiness须同源owner衔接；模仿synthetic通路或看gold命中并不充分。

缓存原来只hash source adapter，未hash实际共享operating_states/归一化/兼容grammar；代码移动后import方偶然改变会掩盖此漏口。Inventory1.8绑定5个实际owner真字节，匹配层不依赖人工记得bump常量。新English subject判断也必须在首个finite边界停，遍历所有后续predicate反复扫描前缀会以线性预扣执行N²，已用实际扫描字符计数先RED再修。

FF原查库合格不等于当前reader metadata合格：最终发布日期future/invalid/None必须覆盖旧资格；当前canonical代码格式只由CWP投影，FF不得另抄lstrip0。reader CLI原open/describe两个观察又有可避免的重复；统一现open_described_version，not-applicable None与未观察sentinel分开，维持原指纹兼容，不增加许可门。

Final preallocation evidence: source candidates originally spent193 of300 then still iterated32 heading IDs before the prose reservation rejected; native continuity atparent0 copied32heads/64body IDs before charging. Length-based reservations before ID visitation remove both loopholes; source headings are now constructed only after prose succeeds and their own reservation succeeds. Nine metadata controls and prior730 related cases all pass739/50.52s. Recursive immutable-IR snapshot checks every dataclass field and mapping value without requiring pickle or altering production IR.

读取现有20源码接口调查后明确：SourceOperatingSession groups/citation_views可以复用；native_range禁止跨页；context name_classes并不代表实际产品指代已解决。4个关键陷阱：analysis owner重叠、target/context refs误映、TOC混入家具、跨页block号码重启与必要context5blocks超过现4。详细约束与真实定位见task_plan引用，不复制原PDF。

Current same-page finish correctly does not assert cross-page continuity, but source owner independently admits page fragments. Therefore a source-level atomic dependency is needed before selection; late summary rewording or a changed max_claims cannot fix a half-sentence selected under a one-span budget. Source block IDs reset on each page: the new cross-page envelope must use tuple identities. Current global WorkBudget must also include new continuity observations; keep local geometric ceiling as a nested ceiling, never a second free allowance.

Measured quadratic source context: a background package withNmembers called context() for each body, rebuilding set(owner.members) each time. 16members288visits,32members1088visits. Source-specific nouns/models cannot fix this; precompute external-context dependencies once per owner and combined exclusions once per source, while actual membership/fan-out/sort costs consume the existing account. StageB initial implementation is isolated pending broader integration/independent final review, not called production-ready.
