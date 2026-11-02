# R7 Invest E2E 独立增量审查

结论：**PASS，保留一次未查明的 Windows I/O 观察**。审查只覆盖本次11文件增量；无产品源码、测试仓库、配置、Git、全局技能或原文改写。精确SHA、复现源码、日志和清理收据见同名JSON。

## 实际验证

- 11/11交付SHA在执行前后均一致。与真实基线Git blob比较，355个共同数值节点和embedded input完全一致；12个经济golden值与module counts不变。
- 显式generator真正调用canonical RF并强验，重算对象与交付fixture完全相同，版本3.7/4.3.0、unattested，没有换标签假迁移。
- 单字及长UTF-8摘录正常；错误摘录SHA、source引用、单位仍被公开合同拒绝。有效结果无需registry许可；错误货币/单位仍被同reference owner强验拒绝。
- 真实CLI在独立新目录双跑，通过两轮3–8、9确定性、10golden；不可用registry文件未改，旁人sentinel保留，仅删除自有临时子树。
- 真实CLI即使`--update-golden`也拒绝经济漂移，原golden字节不变。实际生成的估值中间文件乘1000后，公开execution验证失败。
- 静态核对相邻重复强验只收敛到`revenue_reference`；legacy无reference分支与独立公开执行读验仍保留。网络禁用、dotenv/signer关闭，未运行模型/API。

## 真实运行历史与边界

首轮7项为**6P/1F，10.112s**。唯一失败是既有未改`write_execution`在原子目录rename处收到WinError5，CLI正确失败并清理，而非假成功。同轮另一经济漂移CLI的两次同类写入成功。随后只对失败CLI节点在全新目录复验：**1P，5.221s**。

这不能证明首轮原因是杀毒软件，也不能称I/O鲁棒性已经根修；原失败日志完整保留。暂无证据将它归因于本次增量语义，ROOT应保留为运行观察，若复现再做有证据的I/O诊断。没有抬超时、加重试或吞错误。

没有重复作者38/19组或全仓套件；没有声称Windows结果覆盖Linux运行，也没有把固定回归数值当作投资结论正确性的保证。

## 清理

自有独立目录最初不存在；测试源码和全部观察已保存到JSON。最终只清除此目录，结果以JSON cleanup字段为准。未读、枚举或清理历史`e2e/.runs`，没有触碰RF四份WIP；最终SHA与作者前后记录一致。
