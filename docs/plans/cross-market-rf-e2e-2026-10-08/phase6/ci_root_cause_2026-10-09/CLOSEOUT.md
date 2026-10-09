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
