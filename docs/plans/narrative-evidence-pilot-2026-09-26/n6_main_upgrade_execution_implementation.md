# N6 MAIN：版本升级后的批次执行隔离

## 先核事实与归属

本轮RF仍main6e6b817a，三owner日志保留；三外线worktree仍bootstrap，未收到交接。这不是confirmed-live wait。上一轮是实际progress：13bba07业务框架与6b68b78收据均推远端，精确CI74秒绿。本项补最终接线前的执行身份责任，MAIN只写独立测试/本细则/总PWF；不提前更新共享版本或外线实现。

旧final兼容9项证明旧资料读取不依赖新selector，但未证明AUTO实际创建新一代任务。源码已证request hash包含selector/parser/prompt，仍需以真正CLI/子进程/持久化验证升级后的新批次与旧批次分开。

## 一次小型集中实验

1. 复用既有隔离catalog/CLI/loopback/生产保护fixture，只有一份管理办法PDF；内容确无业务事实，正式selector应skip，model requests=0。保留原件/foreign jobs，fixture最后恢复目录。
2. 当前实际代码版本运行旧run至完成，保存正式旧reference、原artifact字节、三个job IDs和预算记录。
3. 测试专用scratch bootstrap在新Python启动及其Worker子进程中模拟下一selector版本；只改变模块内版本常量，选择逻辑不变。绝不修改仓库源码或生产配置。复用旧run/work-dir必须拒绝，原run/jobs/预算/artifact不变；不是自动清理旧运行材料去勉强继续。
4. 新run ID与独立work-dir实际完成，任务ID集合和artifact版本与旧run分离；new bundle绑定模拟下一版本，旧reference仍返回旧字节，foreign jobs与原件保持，两run全0 tokens/费用/POST。相同新run恢复没有额外任务。
5. 收口只跑此责任case与Ruff；finally关闭DB/删除bootstrap、raw副本、DB、目录；不扩日常CI、不重跑旧并发kill/ACK或九文档长测。

模拟下一版本只是检查编排/版本传播，不能证明尚未交付的候选/预算质量。最终MAIN实际版本更新后，新进程真实E2E仍核artifact selector版本与当前源码一致，冻结compat9项与九样本基准在同一大节点执行。已有请求配置不换模型，不额外调用真实provider。

测试私有_invoke仅增加expected_run_id可选参数，默认cli-e2e不变，便于新run明确身份核对。旧run冲突可能由work-dir hash校验先拒绝，测试验零写/零误复用，不依赖异常类文本把内部顺序变成公共合同。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest -p no:cacheprovider --basetemp tmp/n6uv tests/integration/test_n6_batch_upgrade_identity.py
```

状态：local_complete，1 passed/16.33秒、Ruff绿；当前版本旧run与模拟下一版本新run均正式完成，三个job ID集合分离，新artifact绑定下一版本，旧reference字节保持，新run恢复无新任务/模型调用。实际版本更新后仍在最终大节点运行此case；不声称新selector业务已完成。

前三次失败均为测试组合问题：内部SourceRef误当公共DTO（7.09秒）、ir_policy标签误当规范化catalog身份（6.48秒）、Windows spawn重载无入口保护launcher造成额外stdout（15.41秒）。按既有公共DTO转换、catalog既定investor_relations身份、__main__入口保护修正，不改产品SHA/身份校验或Worker。没有虚报产品RED。所有运行0 HTTP/费用，四个自有pytest根收口恢复absent。
