# 昨日 CI 失败根因与本地漏检修复

## 目标

逐一核对2026-10-08及相邻日期company-wiki、revenue-forecast、filing-fetch真实失败run，区分已修复历史与当前问题。以失败SHA/具体测试/真实日志为证据，解释为什么本地pre-commit/pre-push未拦截，再修复责任代码、测试或入口漂移；不通过删必要测试、关hooks或把每次commit升级成几十分钟全套检查求绿。

## 阶段

1. **complete** — 真实三仓run/job/annotations已落盘：CWP3次、FF2次失败，RF没有失败。公开完整日志403；已有历史实读记录及独立exact blob复现分别标明，不混称新取得完整日志。
2. **in_progress** — 已核对HTTPX双安装声明、旧metadata断言、空generation绑定/3兼容缺陷和每格式parser版本；FF两历史分数阻断各自exact复现。当前CWP正常OS全unit2299PASS/128.21秒；sandbox假失败不算CI根因。下一步防漏检RED。
3. **pending** — CWP从整个Git未推送范围选择受影响unit及既有contract smoke，单次pytest；CI继续全unit。FF将26文件focused列表归一并供push/CI共用。依赖声明静态检查在相关commit执行，不跑pytest。配置/runner/conftest/无法判定依赖时CWP回退完整unit。
4. **pending** — 验收正常commit/push、远端精确SHA CI，更新主PWF；研究四独立审查保持只读运行，随后恢复主线施工。

## 边界

本包由MAIN维护。原件/生产配置/密钥不改，配置只读白名单；Dayu零修改、IQS与邻仓owner WIP不动。外包审查者仍仅写自己的run角色/报告。需要邻仓代码修改时用独占干净工作目录并正常并线/定点安装，避免混入其他owner内容。

## Next Step

先写选择器和依赖静态入口RED，再实现。并行FF独占worktree共享回归入口，MAIN做CWP。提交快速静态；受影响单元在push检查，不在每小节点新增人审。正常commit/push后核对精确SHA远端CI，随后继续原研究主线。

## 防漏检接口与验收

- Git hook stdin四列ref作为输入，比较remote-old到local-new全部commit的路径并集（删除/rename两端包括），不是HEAD^；新分支、对象缺失或格式不明回退完整unit，不联网猜基线。
- 选择器仅用stdlib AST本地导入传递关系；变更test/support会带入调用者；非字面动态导入、子进程CLI、未知依赖/配置/测试入口变更保守全unit。它不声称能证明所有动态行为，远端仍跑全unit。
- 受影响unit与现有smoke合并一次pytest，去除同文件重复node。仅文档变更不加unit；本次修改检查工具本身应全unit集中验收。
- 依赖一致性使用同一个stdlib函数供静态commit入口和既有unit测试使用，相关文件触发，0下载/0模型。
- 选择器反例覆盖多commit末尾docs、多个ref、delete/rename、相对/传递import、fixture、动态调用回退、缺基线、pytest非零传递和tmp清理。重放历史335df/1a58/002824df/d11db范围证明会选失败责任unit；不需再完整恢复公司资料。
- FF共享26文件focused命令，保留现有语法/类型/合同检查、复杂度仅诊断。列表或runner变更本身有责任测试，实际时长记录后再决定是否有必要进一步优化，不先做第二套影响图。
