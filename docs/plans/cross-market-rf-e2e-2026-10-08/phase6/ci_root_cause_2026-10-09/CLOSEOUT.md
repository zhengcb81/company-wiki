# CI 失败根因与防漏检收尾

2026-10-09。五次真实失败逐一归因见[findings](findings.md)，原始REST和历史exact复现留存。直接业务/测试修复此前已发布；本次关闭的是普通本地检查与CI入口的漏检机制。没有删必要行为测试或增人工签收。

## 已发布与实测

| 仓库 | 已推主线代码提交 | 正常本地验证 | 精确远端CI |
|---|---|---|---|
| CWP master | d1ce50eee0340a217565d69945bad3a23a691b81 | 正常commit5.76秒；实际push2346PASS/113.39秒（检查工具变更，保守完整unit+6contract，一次pytest） | [37910840899](https://github.com/zhengcb81/company-wiki/actions/runs/37910840899) SUCCESS，104秒 |
| FF main | 23d25644a78390ebd5d7fd4da20e42d6788c1240 | 实际普通push553PASS/4SKIP/78subtests，59.80秒；全部static/config检查绿 | [37911571894](https://github.com/zhengcb81/filing-fetch/actions/runs/37911571894) SUCCESS，83秒 |

收尾提交41024525的正常push仅13项smoke（2.38秒），其精确远端[CI37912573122](https://github.com/zhengcb81/company-wiki/actions/runs/37912573122)亦SUCCESS（100秒）。本条后续Markdown补记按现有workflow路径规则不触发新CI；代码验收以表内提交为准。

CWP没有让每次commit跑pytest。声明文件静态parity由同一函数供commit和unit使用；push读取所有未推送ref的完整范围、保守受影响unit+原smoke。配置/依赖/动态范围不明回退完整unit，重大变更可能仍需约两分钟；不能许诺每次push都几秒。纯文档变化不增加unit，CI继续全unit。独立审查实际发现并先RED验证动态别名/消费者，修后集中责任53PASS；新增Git child上下文隔离也由上述整体验收覆盖。

FF把原26文件+runner自测收敛到一份27文件清单，由CI/push共用；正常hook无需手工export工程路径，优先CI override、否则复用既有FF公开配置loader。实际普通push首轮发现548/5SKIP与显式env549/4不同，补修后553/4，不把首轮误记为一致。原SKIP明确展示：1个旧DB-only环境opt-in、2个生产security-master快照缺失、1个Windows symlink能力不可用；这些不算通过，也不靠复制生产库求绿。受影响真实跨仓重大联调仍按主计划独立跑。

JUnit收集失败改为抽真实异常类，私有正文/断言仍不打印到公开annotation；本地失败不再只截尾而丢首个失败node。Git hook仓库环境不传入测试自身的子Git。Linux/3.12及远端兼容pin与本机Windows/3.13的差异保留，正常本地绿仍需精确远端结果。

## 隔离与空间

四个MAIN确切创建的测试根均在核对绝对TEMP范围及无reparse后恢复不存在：21,569,142 + 102,158,559 + 11,571 + 7,254 = **123,746,526B**。成功JUnit362,090B改保留小型hash/摘要。FF独占worktree在HEAD已并main、干净且远端绿后恢复不存在。其他历史worktrees、ownerWIP、FMP密钥、生产配置与原件没有删除/修改。本次完整调查证据约153KB，不复制公司资料库。

## 回主线

原三家四独立角色已全部完成，64真实finding；原生audit check三次exit2/needs_remediation，schema/event/manifest无错误。工程CI绿不代表研究通过。独立专家正在[新共因PWF](../fresh_root_remediation_2026-10-09/task_plan.md)归并全部问题，MAIN继续主线；本调查关闭不暂停/完成总体goal。

## 最新只读复核

2026-10-09再次核对精确SHA：CWP2a978b67 [37914735874](https://github.com/zhengcb81/company-wiki/actions/runs/37914735874) SUCCESS，103秒；FF23d25644 [37911571894](https://github.com/zhengcb81/filing-fetch/actions/runs/37911571894) SUCCESS，83秒。后续RF数值共因修复与新增责任测试亦已推8bbb81c7，[37917444152](https://github.com/zhengcb81/revenue-forecast/actions/runs/37917444152) SUCCESS。这些结果是本轮已发布提交的事实，不承诺以后静态或行为检查不会发现新缺陷；仍不把本地未发布W02或待修W04/W07标为通过。

## 新入口实际阻止一次远端失败

W02正常push在本地拦住旧测试的0.5.0写死断言（1939PASS/1FAIL，108.51秒），没有上传929db846。已改为版本传播与generation失效的真实行为测试，相关60PASS/1.36秒；commit仍快速静态，完整正常push与精确远端验收随后补记。没有降回selector版本、删除该测试或绕过hook。

## 最新发布最终验收

CWP W02及版本行为测试已正常推送至 `b1888522525f3dad28891c999adc0919bd59443b`：完整待推送范围119个受影响unit路径与去重smoke共1940PASS，107.99秒，未旁路hook。精确远端[37920455948](https://github.com/zhengcb81/company-wiki/actions/runs/37920455948) SUCCESS（10:54:24→10:56:06 UTC，102秒）。此前一次1939PASS/1FAIL在本地成功拦截，未上传；不是远端失败。FF23d25644/37911571894及RF最新主线5acad6a1/[37919247211](https://github.com/zhengcb81/revenue-forecast/actions/runs/37919247211)亦SUCCESS。本次CI根因修复关闭，commit仍快速static；跨平台/未知动态依赖继续由真实CI负责，不保证以后没有新缺陷。


## 后续主线验证（W03/W04/W07）

新的同一入口已实际支持连续主线集成：CWP cba23b8e普通push2387PASS/142.74s，exactCI37923124555 SUCCESS94s；W03合入284328bb普通commit约6.2s、push2418PASS/122.65s，exactCI37925080695 SUCCESS86s。FF44c778b4正常push601PASS/7explicitSKIP/78subtests/62.07s，exactCI37923517689 SUCCESS87s。新摘要29项契约纳入现有FAST_CONTRACT_CASES，CI与push共用，入口先2RED→66PASS，commit仍无pytest。完整unit回退发生在runner/config/动态执行重大改动，纯文档推送只shared smoke；不把两分钟push误说成每次commit两分钟，也不许诺所有跨平台未知变化都能由本机阻止。

本子包已关闭；主PWF剩余来源/研究共因仍ACTIVE，不以这些工程绿代替三家研究E2E。用户本次CI请求根因和现状可直接查本文件与findings。


## 2026-10-09 17:05 UTC：新修改的防漏检实证

CWP新整批push在上传前拦住2428PASS/3FAIL（144.26s）：一个真实transcript0.1.0兼容缺口，两个fixture误宣0.1.1而实际0.2.0。RF新push拦住147PASS/2FAIL（19.69s）：来源reader真实拒绝被通用failure丢掉有限原因。当前两仓新修改未上传，正在根修后按正常push复验。不能把上一精确绿色CI当这些新修改已验证。

FF新W08主线41ba0150正常push601PASS/7明确SKIP/78subtests/62.63s；精确CI37961753941 SUCCESS（81s），并仅定点同步5文件两物理skill根共10文件，未选公共代码drift=0，配置/output保留。CWP与RF当前修复发表结果将在下一段追加，旧红结果保留。

诊断命令一次猜错邻仓handoff.md文件名（Get-Content不存在）；未改文件、未作产品失败统计。实际交接位于roottyped_cause_usage_diagnosis/w08_safe_boundary/IMPLEMENTATION_HANDOFF.md和own仓PWF记录。


## 2026-10-09：RF新增拒绝原因修复发布完成

实际normalpush先147PASS/2FAIL上传拒绝，通用有限原因根修后151PASS/23.06s；3c3c03792b189734aac5a0c8900b67b2c6f73ca5已推main，精确CI37965179206 SUCCESS/37s。独立21测试/12实际CLI控验通过；保留损坏原件/错期失败与恢复断言，没有忽略两个失败。CWP最新兼容/cache后续已接受合主线，正常最终push待，结果另追加。
